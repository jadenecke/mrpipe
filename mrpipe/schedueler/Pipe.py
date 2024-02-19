import re
import sys

from mrpipe.meta import loggerModule
from mrpipe.schedueler import PipeJob
from typing import List
import os
from mrpipe.meta import PathClass
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
import networkx as nx
import matplotlib.pyplot as plt
from mrpipe import helper
from enum import Enum
from mrpipe.meta.Subject import Subject
from mrpipe.meta.Session import Session

logger = loggerModule.Logger()


class PipeStatus(Enum):
    UNCONFIGURED = "unconfigured"
    CONFIGURED = "configured"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"

class Pipe:
    def __init__(self, args, maxcpus: int = 1, maxMemory: int = 2):
        self.jobList:List[PipeJob.PipeJob] = []
        self.maxcpus = maxcpus
        self.maxMemory = maxMemory
        self.args = args

        #unsettable
        self.name = None
        self.pathModalities = None
        self.pathT1 = None
        self.status = PipeStatus.UNCONFIGURED
        self.subjects: List[Subject] = []
        self.pathBase: PathBase = None

    def createPipeJob(self):
        pass


    def appendJob(self, job):
        job = helper.ensure_list(job)
        for el in job:
            if isinstance(job, PipeJob.PipeJob):
                for instance in self.jobList:
                    if el.name == instance.name:
                        logger.error(f"Can not append PipeJob: A job with that name already exists in the pipeline: {el.name}")
                        return
                logger.info(f"Appending Job to Pipe ({self.name}): \n{el}")
                self.jobList.append(el)
            else:
                logger.error(f"Can only add PipeJobs or [PipeJobs] to a Pipe ({self.name}). You provided {type(job)}")


    def configure(self):
        #setup pipe directory
        self.pathBase = PathBase(self.args.input)
        self.pathBase.pipePath.createDir()
        #set pipeName
        if self.args.name is None:
            self.args.name = os.path.basename(self.pathBase.basePath)
        logger.info("Pipe Name: " + self.args.name)

        self.identifySubjects()
        self.identifySessions()
        #there needs to be a bunch more stuff inbetween here

        self.topological_sort()
        self.visualize_dag()
        

    def run(self):
        self.jobList[0].runJob()


    def analyseDataStructure(self):
        #TODO infer data structure from the subject and session Descriptor within the given directory
        pass


    def identifySubjects(self):
        logger.info("Identifying Subjects")
        potential = os.listdir(self.pathBase.bidsPath)
        for path in potential:
            if re.match(self.args.subjectDescriptor, path):
                self.subjects.append(Subject(os.path.basename(path),
                                             os.path.join(self.pathBase.bidsPath, path)))
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
                    subject.addSession(Session(os.path.basename(path),
                                                 os.path.join(self.pathBase.bidsPath, path)))
                    logger.info(f'Session found: {path}')

    def topological_sort(self):
        job_dict = {job.job.jobDir: job for job in self.jobList}
        stack = []
        for job in self.jobList:
            if not job.dag_visited:
                if not self.dfs(job, stack, job_dict):
                    logger.critical("Cyclic dependency graph: Can not solve the order in which to execute jobs, because there is a dependency circle.")
                    return
        # stack.reverse() #i dont think that is necessary, as the first job to be executed should be [0], except for if my printing is wrong
        self.jobList = stack
        logger.info("Setting nextJobs for each job after topological sort")
        for index, job in enumerate(self.jobList):
            if index < len(self.jobList) - 1:
                logger.info(f'setting job dependency after sort: {index}')
                self.jobList[index].setNextJob(self.jobList[index + 1])


    def dfs(self, job, stack, job_dict): #depth first search
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
                bbox=dict(facecolor="skyblue", edgecolor='black', boxstyle='round,pad=0.2'))  # 's' denotes a square (box) shape
        plt.savefig(os.path.join(self.pathBase.pipePath, "DependencyGraph.png"), bbox_inches="tight")

    def __str__(self):
        return "\n".join([job.name for job in self.jobList])