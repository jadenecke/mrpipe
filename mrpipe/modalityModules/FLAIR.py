from mrpipe.modalityModules.ProcessingModule import ProcessingModule
from functools import partial
from mrpipe.schedueler.PipeJob import PipeJob
from mrpipe.schedueler import Slurm
from mrpipe.Toolboxes.ANTSTools.N4BiasFieldCorrect import N4BiasFieldCorrect
from mrpipe.Toolboxes.standalone.HDBet import HDBET
from mrpipe.Toolboxes.standalone.SynthSeg import SynthSeg
from mrpipe.Toolboxes.standalone.QCVis import QCVis
from mrpipe.Toolboxes.FSL.Binarize import Binarize
from mrpipe.Toolboxes.FSL.Split4D import Split4D
from mrpipe.Toolboxes.FSL.Add import Add
from mrpipe.Toolboxes.FSL.Erode import Erode
from mrpipe.Toolboxes.standalone.QCVisSynthSeg import QCVisSynthSeg
from mrpipe.Toolboxes.standalone.RecenterToCOM import RecenterToCOM
from mrpipe.Toolboxes.ANTSTools.AntsRegistrationSyN import AntsRegistrationSyN
from mrpipe.Toolboxes.FSL.FlirtResampleToTemplate import FlirtResampleToTemplate
from mrpipe.Toolboxes.FSL.FlirtResampleIso import FlirtResampleIso


class FLAIR_ToT1w(ProcessingModule):
    requiredModalities = ["T1w", "flair"]
    moduleDependencies = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)



    def setup(self) -> bool:
        self.addPipeJobs()
        return True




class FLAIR_ToMNI(ProcessingModule):
    requiredModalities = ["T1w", "flair"]
    moduleDependencies = ["FLAIR_ToT1w"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)



    def setup(self) -> bool:
        self.addPipeJobs()
        return True