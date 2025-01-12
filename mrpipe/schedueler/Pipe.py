import asyncio
import re
import sys
import os
import yaml
import matplotlib.pyplot as plt
from networkx.drawing.nx_agraph import write_dot
import networkx as nx
from mrpipe.modalityModules.ProcessingModule import ProcessingModule
from mrpipe.meta import LoggerModule
from mrpipe.schedueler import PipeJob
from typing import List
from mrpipe.meta.PathClass import Path
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.Helper import Helper
from enum import Enum
from mrpipe.meta.Subject import Subject
from mrpipe.meta.Session import Session
from mrpipe.modalityModules.Modalities import Modalities
from mrpipe.modalityModules.ModuleList import ProcessingModuleConfig
from collections import Counter
from itertools import combinations
import pandas as pd
from tabulate import tabulate
import matplotlib.pyplot as plt
import numpy as np
from mrpipe.Helper import Helper
from matplotlib.colors import ListedColormap
import matplotlib.patches as mpatches
from mrpipe.modalityModules.PathDicts.LibPaths import LibPaths
import dagviz
from dagviz.render import render
from dagviz.style.metro import svg_renderer, StyleConfig
from mrpipe.modalityModules.PathDicts.Templates import Templates
import glob
import shutil
from tqdm import tqdm

# import pm4py



logger = LoggerModule.Logger()


class PipeStatus(Enum):
    UNCONFIGURED = "unconfigured"
    CONFIGURED = "configured"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"


class Pipe:
    modalityNamesFile = "ModalityNames.yml"
    def __init__(self,  args, maxcpus: int = 1, maxMemory: int = 2):
        self.maxcpus = maxcpus
        self.maxMemory = maxMemory
        self.args = args

        # unsettable
        self.pathModalities = None
        self.pathT1 = None
        self.status = PipeStatus.UNCONFIGURED
        self.subjects: List[Subject] = []
        self.pathBase: PathBase = None
        self.modalitySet = {}
        self.jobList: List[PipeJob.PipeJob] = []
        self.processingModules: List[ProcessingModule] = []
        self.libPaths: LibPaths = None
        self.templates: Templates = Templates()

    def createPipeJob(self):
        pass

    def appendJob(self, job):
        job = Helper.ensure_list(job)
        for el in job:
            if isinstance(el, PipeJob.PipeJob):
                for instance in self.jobList:
                    if el.name == instance.name:
                        logger.error(
                            f"Can not append PipeJob: A job with that name already exists in the pipeline: {el.name}")
                        return
                logger.info(f"Appending Job to Pipe: {el.name}")
                logger.debug(f"{el}")
                self.jobList.append(el)
                asyncio.run(el.pickleCallback())
            else:
                logger.error(f"Can only add PipeJobs or [PipeJobs] to a Pipe. You provided {type(job)}")

    def configure(self, reconfigure=True):
        # setup pipe directory
        self.pathBase = PathBase(self.args.input)
        self.pathBase.pipePath.create()
        # set pipeName
        if self.args.name is None:
            self.args.name = os.path.basename(self.pathBase.basePath)
        logger.info("Pipe Name: " + self.args.name)

        # remove old files
        self.cleanup()

        if reconfigure and not self.pathBase.libPathFile.exists():
            logger.critical("It seems like you never run mrpipe config yet. Please run mrpipe config first before you run process.")

        # set scratch dir if it was not set:
        if self.args.scratch is None:
            self.args.scratch = str(self.pathBase.basePath.join("scratch"))

        #write/read LibPaths:
        if self.pathBase.libPathFile.exists():
            self.libPaths = LibPaths.from_yaml(self.pathBase.libPathFile)
            self.libPaths.to_yaml(self.pathBase.libPathFile) #write again in case of any LibPath changes which were added, so that they are added to the file.
        else:
            self.libPaths = LibPaths()
            self.libPaths.to_yaml(self.pathBase.libPathFile)
        logger.process("Library Paths: \n" + str(self.libPaths))

        self.identifySubjects()
        self.identifySessions()
        if reconfigure:
            self.identifyModalities()
            self.writeModalitySetToFile()
        else:
            self.readModalitySetFromFile()

        logger.process("Configuring subject Paths: \n" + str(self.libPaths))
        for subject in tqdm(self.subjects):
            subject.configurePaths(basePaths=self.pathBase)
        self.cleanModalitiesAfterPathConfiguration()
        self.loadProcessingModules()
        self.appendProcessingModules()
        self.setupProcessingModules()


        self.summarizeSubjects()
        self.writeSubjectPaths()
        self.filterPrecomputedJobs()


        self.determineDependencies()
        self.topological_sort()
        self.visualize_dag2()
        #self.visualize_dag3()

    def run(self):
        #TODO Somehow logs dir is required before made
        self.pathBase = PathBase(self.args.input)
        self.cleanup(deep=True)
        self.pathBase.createDirs()
        self.configure(reconfigure=False)
        self.removePrecomputedPipejobs()
        self.jobList[0].runJob()

    def analyseDataStructure(self):
        # TODO infer data structure from the subject and session Descriptor within the given directory
        pass

    # def determineDependencies(self):
    #     logger.process("Automatically determining dependencies...")
    #     for job in tqdm(self.jobList):
    #         for otherJob in self.jobList:
    #             if job is not otherJob:
    #                 if not otherJob.isDependency(job): #check if job is already set as dependency
    #                     for inpath in job.getTaskInFiles():
    #                         if inpath in otherJob.getTaskOutFiles():
    #                             job.setDependencies(otherJob)
    #                             break

    def filterPrecomputedJobs(self):
        logger.process("Searching for precomputed jobs.")
        for job in self.jobList:
            job.filterPrecomputedTasks()

    def determineDependencies(self):
        logger.process("Automatically determining dependencies...")
        output_to_job = {outpath: job for job in self.jobList for outpath in job.getTaskOutFiles()}
        # pathsAlreadyDone = []
        #TODO Fix that it grows with the number of subjects.
        for job in tqdm(self.jobList):
            # for inpath in job.getTaskInFiles():
            #     # pathName = inpath.get_varname()
            #     # if pathName in pathsAlreadyDone:
            #     #     continue
            #     if inpath in output_to_job.keys() and job is not output_to_job[inpath]:
            #         job.setDependencies(output_to_job[inpath])
            #         # pathsAlreadyDone.append(pathName)
            for inpath in job.getFirstTaskInFiles():
                if inpath in output_to_job.keys() and job is not output_to_job[inpath]:
                    job.setDependencies(output_to_job[inpath])


    def cleanup(self, deep=False):
        jobScripts = glob.glob("**/*.sh", recursive=True, root_dir=self.pathBase.pipeJobPath)
        for jobScript in jobScripts:
            os.remove(os.path.join(self.pathBase.pipeJobPath, jobScript))

        if deep:
            shutil.rmtree(str(self.pathBase.logPath))

    def removePrecomputedPipejobs(self):
        logger.process("Removing empty pipe jobs...")
        lastValidJob = 0
        countRemoved = 0
        for i in range(len(self.jobList)):
            if i == 0:
                continue
            curJob = self.jobList[i]
            if curJob.allTasksPrecomputed():
                logger.info(f"Found and removing empty pipe job: {curJob.name}")
                nextJob = curJob.getNextJob()
                if nextJob is not None:
                    logger.debug(f"Setting next job after removal of previous job for {self.jobList[lastValidJob].name} to {nextJob.name}")
                    self.jobList[lastValidJob].setNextJob(nextJob, overwrite=True)
                    countRemoved += 1
                else:
                    self.jobList[lastValidJob].removeNextJob()
                    countRemoved += 1
            else:
                lastValidJob = i
        logger.process(f"Removed {countRemoved} jobs from pipeline, {len(self.jobList) - countRemoved} jobs remaining.")

    def identifySubjects(self):
        logger.process("Identifying Subjects.")
        potential = os.listdir(self.pathBase.bidsPath)
        for path in potential:
            if re.match(self.args.subjectDescriptor, path):
                self.subjects.append(Subject(os.path.basename(path),
                                             Path(os.path.join(self.pathBase.bidsPath, path), isDirectory=True)))
                logger.info(f'Subject found: {path}')
        logger.process(f'Found {len(self.subjects)} subjects')

    def identifySessions(self):
        logger.process("Identifying Sessions.")
        if self.args.modalityBeforeSession:
            logger.critical("Session matching not implemented yet, exiting.")
            sys.exit(1)
        for subject in self.subjects:
            potential = os.listdir(subject.path)
            for path in potential:
                logger.debug(path)
                if re.match(self.args.sessionDescriptor, path):
                    subject.addSession(Session(name=os.path.basename(path),
                                               path=subject.path.join(path, isDirectory=True),
                                               subjectName=subject.id))
                    logger.info(f'Session found: {path} for subject {subject}')

    def identifyModalities(self):
        #TODO DONT USE category does not work and produces an error
        logger.process(f"Identifying Modalities, looking for {self.pathBase.pipePath.join(Pipe.modalityNamesFile)}")
        if self.pathBase.pipePath.join(Pipe.modalityNamesFile).exists():
            logger.process(f"Found Modality name file in pipe directory. Using this definitions: {self.pathBase.pipePath.join('ModalityNames.yml')}")
            self.readModalitySetFromFile()
        else:
            # dummyModality = Modalities()
            for subject in self.subjects:
                for session in subject.sessions:
                    matches = session.identifyModalities()
                    if matches:
                        for suggestedModality, name in matches.items():
                            if isinstance(name, list):
                                for n in name:
                                    if n not in self.modalitySet.keys():
                                        self.modalitySet[name] = suggestedModality
                            else:
                                if name not in self.modalitySet.keys():
                                    self.modalitySet[name] = suggestedModality
            logger.process(
                f"Found {len(self.modalitySet)} modalities. This will be written to disk and you can modify them before you run the pipeline:")
            for key, value in self.modalitySet.items():
                logger.process(f'{key}: {value}')

    def summarizeSubjects(self):
        logger.process("Summerising subject data.")
        # Summary table for the amount of available sessions
        session_summary = Counter([len(subject.sessions) for subject in self.subjects])

        # Summary table for the amount of available modality combinations
        modality_summary = Counter()
        for subject in self.subjects:
            for session in subject.sessions:
                modalities = session.modalities.available_modalities()
                for r in range(1, len(modalities) + 1):
                    for subset in combinations(modalities, r):
                        modality_summary[subset] += 1

        modality_summary = {", ".join(k): v for k, v in modality_summary.items()}

        self.summarizeSubjectsToCsv(session_summary, modality_summary)
        self.summarizeSubjectsToAscii(session_summary, modality_summary)
        self.summarizeSubjectsToImage()

    def writeSubjectPaths(self):
        logger.process("Writing subject paths dictionaries to disk.")
        for subject in self.subjects:
            for session in subject.sessions:
                session.subjectPaths.to_yaml(session.subjectPaths.path_yaml)

    def summarizeSubjectsToCsv(self, session_summary, modality_summary):
        # Convert the Counter objects to pandas DataFrames
        session_df = pd.DataFrame.from_dict(session_summary, orient='index', columns=['Count'])
        modality_df = pd.DataFrame.from_dict(modality_summary, orient='index', columns=['Count'])

        # Write the DataFrames to CSV files
        session_df.to_csv(self.pathBase.pipePath.join("session_summary.csv"), mode='w')
        modality_df.to_csv(self.pathBase.pipePath.join("modality_summary.csv"), mode='w')

    def summarizeSubjectsToAscii(self, session_summary, modality_summary):
        # Convert the Counter objects to lists of tuples and sort them
        session_summary = sorted(session_summary.items())
        modality_summary = sorted(modality_summary.items(), key=lambda x: (-x[1], x[0]))

        # Print the session summary as an ASCII table
        logger.process("Session Summary:")
        logger.process(tabulate(session_summary, headers=['Sessions', 'Count']))

        # Print the modality summary as an ASCII table
        logger.process("Modality overview saved to {}".format(self.pathBase.pipePath))
        logger.info("Modality Summary:")
        logger.info(tabulate(modality_summary, headers=['Modalities', 'Count']))

    def summarizeSubjectsToImage(self):
        # Assuming subjects is a list of custom class instances
        # Each subject contains sessions with available modalities
        dummyModality = Modalities()
        # Calculate image dimensions
        num_rows = sum([len(subject.sessions) for subject in self.subjects])
        num_columns = len(dummyModality.modalityNames())
        availability_matrix = np.zeros((num_rows, num_columns))

        for row, session in enumerate(Helper.flatten([subject.sessions for subject in self.subjects])):
            for col, modality in enumerate(session.modalities.modalityNames()):
                availability_matrix[row, col] = any(
                    modality == m for m in session.modalities.available_modalities())

        #remove all zero columns:
        non_zero_columns = availability_matrix.any(axis=0)
        filtered_matrix = availability_matrix[:, non_zero_columns]
        xnames = [modality_name for i, modality_name in enumerate(dummyModality.modalityNames()) if non_zero_columns[i]]

        num_rows, num_columns = filtered_matrix.shape
        colors = ['#EE6677', '#228833']
        cmap_binary = ListedColormap(colors)

        # Dynamically adjust figure size based on content
        # fig, ax = plt.subplots(figsize=(num_columns * .5, num_rows * 0.2))
        # fig, ax = plt.subplots(figsize=(None, num_rows * 0.2))
        fig, ax = plt.subplots(figsize=np.add(np.multiply(plt.rcParams["figure.figsize"], [1, 1]), [0, num_rows * 0.2]))
        # Plot the filtered matrix
        ax.matshow(filtered_matrix, cmap=cmap_binary)
        plt.xticks(range(sum(non_zero_columns)), xnames, rotation=90)
        plt.yticks(range(num_rows), [f"{subject.id} / {session.name}" for subject in self.subjects for session in subject.sessions])
        plt.xlabel("Modalities")
        plt.ylabel("Subjects")
        plt.title("Modality Availability")
        # plt.colorbar(label="Availability", ticks=[0, 1])
        patches = [mpatches.Patch(color=colors[0], label="Not Available"),
                   mpatches.Patch(color=colors[1], label="Available")]
        # put those patched as legend-handles into the legend
        plt.legend(handles=patches, bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)

        plt.tight_layout()

        # Save the image
        plt.savefig(str(self.pathBase.pipePath.join("modalities_image.png")))
        print("Image saved as modalities_image.png")

    def appendProcessingModule(self, module: ProcessingModule):
        self.processingModules.append(module)

    def appendProcessingModules(self):
        sessionList = [session for subject in self.subjects for session in subject.sessions]
        for modulename, Module in self.processingModuleList.items():
            filteredSessionList = Module.verifyModalities(availableModalities=[m for m in self.modalitySet.values()])
            if filteredSessionList:
                logger.process(f"Appending Processing Module: {modulename}")
                module = Module(name=modulename, sessionList=sessionList, basepaths=self.pathBase, libPaths=self.libPaths, templates=self.templates, inputArgs=self.args)
                self.appendProcessingModule(module)

    def setupProcessingModules(self):
        logger.process("Setting up Processing Modules.")
        for module in self.processingModules:
            isSetup = module.safeSetup(self.processingModules)
            if isSetup:
                self.appendJob(module.pipeJobs)

    def loadProcessingModules(self):
        if self.pathBase.moduleListPath.exists():
            logger.process("Loading Processing modules from file.")
            loaded_config = ProcessingModuleConfig.from_yaml(self.pathBase.moduleListPath)
            self.processingModuleList = loaded_config.construct_modules()
            logger.process(f"Loaded Processes: {self.processingModuleList}")
        else:
            logger.process("Processing modules not found yet, creating new. Feel free to modify this file to remove processing modules which are not needed.")
            self.processingModuleList = ProcessingModuleConfig()
            self.processingModuleList.to_yaml(self.pathBase.moduleListPath)
            self.processingModuleList.construct_modules()



    def writeModalitySetToFile(self):
        with open(self.pathBase.pipePath.join(Pipe.modalityNamesFile), 'w') as outfile:
            outfile.write(f"# please use only this modalities: {Modalities().modalityNames()}.\n" +
                          yaml.dump(self.modalitySet))

    def readModalitySetFromFile(self):
        # must not only load it from disk, but also go through all subject/sessions to verify that the modality paths are updated if there were changes.
        with open(self.pathBase.pipePath.join(Pipe.modalityNamesFile), 'r') as infile:
            self.modalitySet = yaml.safe_load(infile)
            logger.debug(f"Loaded {self.modalitySet}")
        #TODO: It seems like different modality paths which have the same modality are lost when read from file. Presumably its because of the dict key/value swapping and key conflicts. Investigate-
        for subject in self.subjects:
            for session in subject.sessions:
                if session:
                    matches = session.identifyModalities(self.modalitySet)
                    if matches:
                        for suggestedModality, name in matches.items():
                            if isinstance(name, list): #specifically only for the DontUse list.
                                for n in name:
                                    if n not in self.modalitySet.keys():
                                        logger.critical(
                                            f"Appending newly defined Modality: {(name, suggestedModality)}")
                                        self.modalitySet[n] = suggestedModality
                            else:
                                if name not in self.modalitySet.keys():
                                    logger.critical(f"Appending newly defined Modality: {(name, suggestedModality)}")
                                    self.modalitySet[name] = suggestedModality
                    session.modalities.adjustModalities(self.modalitySet)
                else:
                    logger.warning(f"No modalities found for subject {subject} in session {session}")
        logger.process(
            f"Loaded {len(self.modalitySet)} modalities. You can still modify them before you run the pipeline: ")
        for key, value in self.modalitySet.items():
            logger.process(f'{key}: {value}')


    def cleanModalitiesAfterPathConfiguration(self):
        logger.process("Cleaning subjects modalities for which no data or only invalid data was found.")
        for subject in self.subjects:
            for session in subject.sessions:
                if session:
                    for mod in session.modalities.available_modalities():
                        if not getattr(session.subjectPaths, mod, None):
                            session.modalities.removeModality(mod)

    def topological_sort(self):
        logger.process("Sorting jobs for processing order.")
        job_dict = {job.job.jobDir: job for job in self.jobList}
        stack = []
        for job in self.jobList:
            if not job.dag_visited:
                if not self.dfs(job, stack, job_dict):
                    logger.critical(
                        "Cyclic dependency graph: Can not solve the order in which to execute jobs, because there is a dependency circle.")
                    return
        # stack.reverse() #i dont think that is necessary, as the first job to be executed should be [0], except for if my printing is wrong
        self.jobList = stack
        logger.info("Setting nextJobs for each job after topological sort")
        for index, job in enumerate(self.jobList):
            if index < len(self.jobList) - 1:
                logger.debug(f'setting job dependency after sort: {index}')
                self.jobList[index].setNextJob(self.jobList[index + 1])
            self.jobList[index].name = str(index) + "-" + self.jobList[index].name


    def dfs(self, job, stack, job_dict):  # depth first search
        if job.dag_processing:
            return False
        job.dag_processing = True
        for dependencyPath in job.getDependencies():
            dependency = job_dict[dependencyPath]
            if not dependency.dag_visited:
                if not self.dfs(dependency, stack, job_dict):
                    return False
        job.dag_visited = True
        job.dag_processing = False
        stack.append(job)
        return True

    def visualize_dag(self):
        figure_width = 10 + 2 * len(self.jobList)
        plt.figure(figsize=(figure_width, 6))
        ax = plt.gca()
        job_dict = {job.job.jobDir: job for job in self.jobList}
        G = nx.DiGraph()
        for job in self.jobList:
            G.add_node(job.name)
            for dependency_id in job.getDependencies():
                G.add_edge(job_dict[dependency_id].name, job.name)

        # Create a new position dictionary based on execution order
        pos = {job.name: (i * 0.4, 0) for i, job in
               enumerate(self.jobList)}  # Adjust the x-coordinate increment here for 60% overlap

        # Adjust y-coordinates based on dependencies
        for job in self.jobList:
            dependencies = job.getDependencies()
            if dependencies:
                max_y = max(pos[job_dict[dep_id].name][1] for dep_id in dependencies)
                pos[job.name] = (pos[job.name][0], max_y - 0.02)  # Adjust the y-coordinate increment here

        # Draw nodes with box shape
        for node in G.nodes():
            ax.add_patch(mpatches.Rectangle(pos[node], 0.1, 0.1, facecolor="skyblue", edgecolor='black'))

        # Draw edges with half circle
        for edge in G.edges():
            start, end = pos[edge[0]], pos[edge[1]]
            patch = mpatches.FancyArrowPatch(start, end, connectionstyle="arc3,rad=.5", arrowstyle="-|>",
                                             mutation_scale=20, lw=1, color="k")
            ax.add_patch(patch)

        # Draw labels
        for node, (x, y) in pos.items():
            plt.text(x, y, node, fontsize=12, ha='center', va='center')

        plt.savefig(os.path.join(self.pathBase.pipePath, "DependencyGraph.png"), bbox_inches="tight")

    def visualize_dag2(self):
        logger.process("Creating Pipeline visualisation.")
        job_dict = {job.job.jobDir: job for job in self.jobList}
        G = nx.DiGraph()
        for job in self.jobList:
            G.add_node(job.name, community=job.moduleName)
            for dependency_id in job.getDependencies():
                G.add_edge(job_dict[dependency_id].name, job.name)

        r = dagviz.make_abstract_plot(G) #, order=[job.name for job in self.jobList] # lets see, orders in the actual processing order
        rsvg = render(r, dagviz.style.metro.svg_renderer())
        with open(self.pathBase.pipePath.join("DependencyGraph2.svg"), "wt") as fs:
            fs.write(rsvg)

    def visualize_dagPM4Py(self):
        job_dict = {job.job.jobDir: job for job in self.jobList}
        G = nx.DiGraph()
        for job in self.jobList:
            G.add_node(job.name, community=job.moduleName)
            for dependency_id in job.getDependencies():
                G.add_edge(job_dict[dependency_id].name, job.name)

        # pm4py.convert.

    def visualize_dag3(self):
        #TODO broken (requires pygraphviz)
        job_dict = {job.job.jobDir: job for job in self.jobList}
        plt.figure(figsize=(12, 12))
        #ax = plt.gca()
        G = nx.DiGraph()
        for idx, job in enumerate(self.jobList):
            G.add_node(job.name, community=job.moduleName) #, layer=idx)
            for dependency_id in job.getDependencies():
                G.add_edge(job_dict[dependency_id].name, job.name)

        # pos = nx.multipartite_layout(G, subset_key="layer")
        pos = nx.spring_layout(G)

        #for idx, p in enumerate(pos.values()):
        #    p[1] += np.linspace(1, -1, len(pos))[idx]


        communities = set(nx.get_node_attributes(G, 'community').values())
        colors = plt.cm.rainbow(np.linspace(0, 1, len(communities)))
        community_color_dict = dict(zip(communities, colors))
        node_colors = [community_color_dict[G.nodes[node]['community']] for node in G.nodes]
        nx.draw(G, pos, node_color=node_colors, with_labels=True)
        nx.write_graphml(G, os.path.join(self.pathBase.pipePath, "graph.graphml"))
        write_dot(G, os.path.join(self.pathBase.pipePath, "graph.dot"))
        plt.legend()

        #for edge in G.edges():
        #    start, end = pos[edge[0]], pos[edge[1]]
        #    patch = mpatches.FancyArrowPatch(start, end, connectionstyle="arc3,rad=.5", arrowstyle="-|>",
        #                                     mutation_scale=20, lw=1, color="k")
        #    ax.add_patch(patch)
        plt.savefig(os.path.join(self.pathBase.pipePath, "DependencyGraph3.png"), dpi=300, bbox_inches='tight')


    def __str__(self):
        return "\n".join([job.name for job in self.jobList])




