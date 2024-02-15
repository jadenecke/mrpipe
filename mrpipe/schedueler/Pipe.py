from mrpipe.meta import loggerModule
from mrpipe.schedueler import PipeJob
from typing import List
import os
from mrpipe.meta import PathClass
import networkx as nx
import matplotlib.pyplot as plt


logger = loggerModule.Logger()


class Pipe:
    def __init__(self, name: str, dir:PathClass, maxcpus: int = 1, maxMemory: int = 2):
        self.dir = dir
        self.name = name
        self.jobList:List[PipeJob.PipeJob] = []
        self.maxcpus = maxcpus
        self.maxMemory = maxMemory

    def createPipeJob(self):
        pass


    def appendJob(self, job: PipeJob.PipeJob):
        if isinstance(job, PipeJob.PipeJob):
            logger.debug(f"Appending Job to Pipe ({self.name}): \n{job}")
            job = [job]
        if isinstance(job, list):
            for el in job:
                for instance in self.jobList:
                    if el.name == instance.name:
                        logger.error(f"Can not append PipeJob: A job with that name already exists in the pipeline: {el.name}")
                        return
                logger.debug(f"Appending Job to Pipe ({self.name}): \n{el}")
                self.jobList.append(el)
        else:
            logger.error(f"Can only add PipeJobs or [PipeJobs] to a Pipe ({self.name}). You provided {type(job)}")


    def configure(self):
        self.dir.createDir()
        self.topological_sort()
        self.visualize_dag()
        

    def run(self):
        self.jobList[0].runJob()

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
        logger.debug("Setting nextJobs for each job after topological sort")
        for index, job in enumerate(self.jobList):
            if index < len(self.jobList) - 1:
                logger.debug(f'setting job dependency after sort: {index}')
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

    # def visualize_dag(self):
    #     job_dict = {job.job.jobDir: job for job in self.jobList}
    #     G = nx.DiGraph()
    #     for job in self.jobList:
    #         G.add_node(job.name)
    #         for dependency_id in job.getDependencies():
    #             G.add_edge(job_dict[dependency_id].name, job.name)
    #
    #     pos = nx.spring_layout(G)
    #     nx.draw(G, pos, with_labels=True, node_color='lightblue', node_size=1500, arrows=True)
    #     plt.savefig(os.path.join(self.dir.path, "DependencyGraph.png"))

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
        plt.savefig(os.path.join(self.dir.path, "DependencyGraph.png"), bbox_inches="tight")

    class PipeConfig:
        def __init__(self, path):
            #settable:
            self.path = path
            #unsettable:

    def __str__(self):
        return "\n".join([job.name for job in self.jobList])