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

        self.identifySubjects()
        self.identifySessions()
        self.identifyModalities()
        self.writeModalitySetToFile()
        self.appendProcessingModules()

        # there needs to be a bunch more stuff inbetween here
        for subject in self.subjects:
            subject.configurePaths(basePaths=self.pathBase) #later to be shifted towards run implementation
        self.setupProcessingModules()  # later to be shifted towards run implementation, needs also to run after subject specific paths have been set up.

        logger.critical(str(self.subjects[0].sessions[0].subjectPaths))
        logger.critical(str(self.subjects[0].sessions[0].modalities))
        x = ""
        while x != "go":
            x = input()

        self.readModalitySetFromFile()
        for subject in self.subjects:
            subject.configurePaths(basePaths=self.pathBase)
        logger.critical(str(self.subjects[0].sessions[0].subjectPaths))
        logger.critical(str(self.subjects[0].sessions[0].modalities))


        self.topological_sort()
        self.visualize_dag()

    def run(self):
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
                            if not name in self.modalitySet.keys():
                                self.modalitySet[name] = suggestedModality

                    # potential = os.listdir(session.path + "/unprocessed")
                    # matches = {}
                    # for name in potential:
                    #     suggestedModality = dummyModality.fuzzy_match(name)
                    #     if not suggestedModality:
                    #         continue
                    #     matches[suggestedModality] = name
                    #     if not (name, suggestedModality) in self.modalitySet:
                    #         self.modalitySet.add((name, suggestedModality))
                    # logger.info(f'Identified the following modalities for {subject}/{session}: {str(matches)}')
                    # session.addModality(**matches)
                    # if not matches:
                    #     logger.warning(f"No modalities found for subject {subject} in session {session}")
            logger.process(
                f"Found {len(self.modalitySet)} modalities. This will be written to disk and you can modify them before you run the pipeline:")
            for key, value in self.modalitySet.items():
                logger.process(f'{key}: {value}')


    def appendProcessingModules(self):
        sessionList = [session for subject in self.subjects for session in subject.sessions]
        for modulename, Module in moduleList.items():
            filteredSessionList = Module.verify(availableModalities=[m for m in self.modalitySet.values()])
            if filteredSessionList:
                module = Module(name=modulename, sessionList=sessionList, jobDir=self.pathBase.pipeJobPath, args=self.args)
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
                            if not (name, suggestedModality) in self.modalitySet:
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

    def visualize_dag(self):
        job_dict = {job.job.jobDir: job for job in self.jobList}
        G = nx.DiGraph()
        for job in self.jobList:
            G.add_node(job.name)
            for dependency_id in job.getDependencies():
                G.add_edge(job_dict[dependency_id].name, job.name)

        # Create a new position dictionary based on execution order
        pos = {job.name: (i, 0) for i, job in enumerate(self.jobList)}

        # Adjust y-coordinates based on dependencies
        for job in self.jobList:
            dependencies = job.getDependencies()
            if dependencies:
                max_y = max(pos[job_dict[dep_id].name][1] for dep_id in dependencies)
                pos[job.name] = (pos[job.name][0], max_y + 0.1)  # Adjust the y-coordinate increment here

        nx.draw(G, pos, with_labels=True, node_size=1500, arrows=True,
                node_shape="s", node_color="none",
                bbox=dict(facecolor="skyblue", edgecolor='black',
                          boxstyle='round,pad=0.2'))  # 's' denotes a square (box) shape
        plt.savefig(os.path.join(self.pathBase.pipePath, "DependencyGraph.png"), bbox_inches="tight")

    def __str__(self):
        return "\n".join([job.name for job in self.jobList])
