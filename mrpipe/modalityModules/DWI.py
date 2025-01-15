from mrpipe.modalityModules.ProcessingModule import ProcessingModule
from functools import partial
from mrpipe.schedueler.PipeJob import PipeJob
from mrpipe.schedueler import Slurm
from mrpipe.Toolboxes.ANTSTools.N4BiasFieldCorrect import N4BiasFieldCorrect

from mrpipe.Toolboxes.standalone.cp import CP

# INFO: field encoding direction from DWI json sidecar, i.e. PhaseEncodingDirection field and its differences for sagittal and axial acquisition schemes:
# https://neurostars.org/t/phaseencodingdirection-in-json-file/20259


# TIP 1: If reverse phase encoding is 4D, it needs to include bval and bvec file, if it only is 3D I assume its b0



class DWI_base(ProcessingModule):
    requiredModalities = ["dwi"]
    moduleDependencies = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4)

        self.flair_native_copy = PipeJobPartial(name="FLAIR_native_copy", job=SchedulerPartial(
            taskList=[CP(infile=session.subjectPaths.flair.bids.flair,
                         outfile=session.subjectPaths.flair.bids_processed.flair) for session in
                      self.sessions]), env=self.envs.envMRPipe)

        # Step 1: N4 Bias corrections
        self.N4biasCorrect = PipeJobPartial(name="FLAIR_base_N4biasCorrect", job=SchedulerPartial(
            taskList=[N4BiasFieldCorrect(infile=session.subjectPaths.flair.bids.flair,
                                         outfile=session.subjectPaths.flair.bids_processed.N4BiasCorrected) for session in
                      self.sessions],  # something
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=3, minimumMemPerNode=4),
                                            env=self.envs.envANTS)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True
