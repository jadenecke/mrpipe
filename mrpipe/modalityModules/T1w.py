from mrpipe.modalityModules.ProcessingModule import ProcessingModule
from mrpipe.schedueler.PipeJob import PipeJob
from mrpipe.schedueler import Slurm
from mrpipe.Toolboxes.envs.ants import envANTS
from mrpipe.Toolboxes.ANTSTools.N4BiasFieldCorrect import N4BiasFieldCorrect
from mrpipe.meta.PathClass import Path


class T1w_base(ProcessingModule):
    requiredModalities = ["T1w"]

    def setup(self) -> bool:
        N4biasCorrect = PipeJob(name="N4biasCorrect_T1w", jobDir=self.jobDir, job=Slurm.Scheduler(
            taskList=[N4BiasFieldCorrect(infile=session.subjectPaths.T1w.bids.T1w,
                                         outfile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected) for session in self.sessions],  # something
            cpusPerTask=2, cpusTotal=self.args.ncores,
            memPerCPU=2, minimumMemPerNode=4),
                                env=envANTS)
        self.addPipeJob(N4biasCorrect)
        return True
