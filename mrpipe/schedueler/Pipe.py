import re
import sys
import os
import yaml
import matplotlib.pyplot as plt
import networkx as nx

from mrpipe.modalityModules.ProcessingModule import ProcessingModule
from mrpipe.meta import loggerModule
from mrpipe.schedueler import PipeJob
from typing import List
from mrpipe.meta.PathClass import Path
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.Helper import Helper
from enum import Enum
from mrpipe.meta.Subject import Subject
from mrpipe.meta.Session import Session
from mrpipe.modalityModules.Modalities import Modalities
from mrpipe.modalityModules.ModuleList import moduleList
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


logger = loggerModule.Logger()


class PipeStatus(Enum):
    UNCONFIGURED = "unconfigured"
    CONFIGURED = "configured"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"


class Pipe:
    modalityNamesFile = "ModalityNames.yml"
    def __init__(self, args, maxcpus: int = 1, maxMemory: int = 2):
        self.maxcpus = maxcpus
        self.maxMemory = maxMemory
        self.args = args

        # unsettable
        self.name = None
        self.pathModalities = None
        self.pathT1 = None
        self.status = PipeStatus.UNCONFIGURED
        self.subjects: List[Subject] = []
        self.pathBase: PathBase = None
        self.modalitySet = {}
        self.jobList: List[PipeJob.PipeJob] = []
        self.processingModules: List[ProcessingModule] = []
        self.libPaths: LibPaths = None

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
                logger.info(f"Appending Job to Pipe ({self.name}): \n{el}")
                self.jobList.append(el)
            else:
                logger.error(f"Can only add PipeJobs or [PipeJobs] to a Pipe ({self.name}). You provided {type(job)}")

    def appendProcessingModule(self, module: ProcessingModule):
        logger.process(f"Appending Processing Module: {module}")
        self.processingModules.append(module)

    def configure(self):
        # setup pipe directory
        self.pathBase = PathBase(self.args.input)
        self.pathBase.pipePath.createDir()
        # set pipeName
        if self.args.name is None:
            self.args.name = os.path.basename(self.pathBase.basePath)
        logger.info("Pipe Name: " + self.args.name)

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
        self.identifyModalities()
        self.writeModalitySetToFile()
        self.appendProcessingModules()

        # there needs to be a bunch more stuff inbetween here
        for subject in self.subjects:
            subject.configurePaths(basePaths=self.pathBase) #later to be shifted towards run implementation
        self.setupProcessingModules()  # later to be shifted towards run implementation, needs also to run after subject specific paths have been set up.
        self.summarizeSubjects()

        self.readModalitySetFromFile()
        for subject in self.subjects:
            subject.configurePaths(basePaths=self.pathBase)

        self.topological_sort()
        self.visualize_dag2()

    def run(self):
        self.pathBase = PathBase(self.args.input)
        self.pathBase.createDirs()
        self.readModalitySetFromFile()
        self.jobList[0].runJob()

    def analyseDataStructure(self):
        # TODO infer data structure from the subject and session Descriptor within the given directory
        pass



    def identifySubjects(self):
        logger.info("Identifying Subjects")
        potential = os.listdir(self.pathBase.bidsPath)
        for path in potential:
            if re.match(self.args.subjectDescriptor, path):
                self.subjects.append(Subject(os.path.basename(path),
                                             Path(os.path.join(self.pathBase.bidsPath, path), isDirectory=True)))
                logger.info(f'Subject found: {path}')
        logger.process(f'Found {len(self.subjects)} subjects')

    def identifySessions(self):
        logger.info("Identifying Sessions")
        if self.args.modalityBeforeSession:
            logger.critical("Session matching not implemented yet, exiting.")
            sys.exit(1)
        for subject in self.subjects:
            potential = os.listdir(subject.path)
            for path in potential:
                logger.debug(path)
                if re.match(self.args.sessionDescriptor, path):
                    subject.addSession(Session(name=os.path.basename(path),
                                               path=subject.path.join(path, isDirectory=True)))
                    logger.info(f'Session found: {path} for subject {subject}')

    def identifyModalities(self):
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

    def appendProcessingModules(self):
        sessionList = [session for subject in self.subjects for session in subject.sessions]
        for modulename, Module in moduleList.items():
            filteredSessionList = Module.verifyModalities(availableModalities=[m for m in self.modalitySet.values()])
            if filteredSessionList:
                module = Module(name=modulename, sessionList=sessionList, basepaths=self.pathBase, libPaths=self.libPaths, args=self.args)
                self.appendProcessingModule(module)

    def setupProcessingModules(self):
        for module in self.processingModules:
            isSetup = module.safeSetup()
            if isSetup:
                self.appendJob(module.pipeJobs)

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

    def topological_sort(self):
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
                logger.info(f'setting job dependency after sort: {index}')
                self.jobList[index].setNextJob(self.jobList[index + 1])

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

    import matplotlib.patches as mpatches

    import matplotlib.patches as mpatches

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
        job_dict = {job.job.jobDir: job for job in self.jobList}
        G = nx.DiGraph()
        for job in self.jobList:
            G.add_node(job.name)
            for dependency_id in job.getDependencies():
                G.add_edge(job_dict[dependency_id].name, job.name)

        r = dagviz.render_svg(G)
        with open(self.pathBase.pipePath.join("DependencyGraph.svg"), "wt") as fs:
            fs.write(r)

    def __str__(self):
        return "\n".join([job.name for job in self.jobList])
