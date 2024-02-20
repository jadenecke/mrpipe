from modalityModules.ProcessingModule import ProcessingModule
from mrpipe.schedueler.PipeJob import PipeJob
from mrpipe.schedueler import Slurm
from mrpipe.Toolboxes.envs.ants import envANTS
from mrpipe.Toolboxes.ANTSTools.N4BiasFieldCorrect import N4BiasFieldCorrect
from mrpipe.meta.PathClass import Path


class T1w_base(ProcessingModule):
    requiredModalities = ["T1w"]

    def setup(self):
        N4biasCorrect = PipeJob(name="N4biasCorrect", job=Slurm.Scheduler(
            #TODO: implement as soon as session has path dictionaries.
            taskList=[N4BiasFieldCorrect(infile=session.T1Paths) for session in self.sessions],  # something
            jobDir=self.jobDir, cpusPerTask=2, cpusTotal=self.args.ncores,
            memPerCPU=2, minimumMemPerNode=4),
                                env=envANTS)
        self.addPipeJob(N4biasCorrect)
