from mrpipe.Toolboxes.Task import Task
class Sleep(Task):

    def getCommand(self):
        command = f"sleep {self.time} "
        return command

    def __init__(self, time, name: str = "Sleep"):
        super().__init__(name)
        self.time = time

