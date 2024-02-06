from mrpipe.meta import loggerModule
from mrpipe.schedueler import Slurm
from mrpipe.schedueler import Bash

logger = loggerModule.Logger()


class Pipe:
    pass

class PipeJob:
    def __int__(self, name: str, job: Bash.Script):