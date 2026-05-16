from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path


class DWIEXTRACTFIRSTB0(Task):

    def __init__(self, inputImage: Path, outputB0: Path, session, name: str = "dwiextractFirstB0", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = inputImage
        self.outputB0 = outputB0

        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles([self.outputB0])

    def getCommand(self):
        cpusPerTask = getattr(self.parent, "cpusPerTask", None)
        c1 = f"dwiextract {self.inputImage} - -bzero"
        c2 = "mrconvert - -coord 3 0 -axes 0,1,2 {self.outputB0}"

        if cpusPerTask:
            c1 += f" -nthreads {cpusPerTask}"
            c2 += f" -nthreads {cpusPerTask}"
        if self.clobber:
            c1 += " -force"
            c2 += " -force"
        command = c1 + " | " + c2
        return command

    @staticmethod
    def dwiextractFirstB0(inputImage: Path, outputB0: Path, clobber=False, ncpus = None):
        c1 = f"dwiextract {inputImage} - -bzero"
        c2 = "mrconvert - -coord 3 0 -axes 0,1,2 {self.outputB0}"

        if ncpus:
            c1 += f" -nthreads {ncpus}"
            c2 += f" -nthreads {ncpus}"
        if clobber:
            c1 += " -force"
            c2 += " -force"
        command = c1 + " | " + c2
        return command


class DWIEXTRACTALLB0(Task):

    def __init__(self, inputImage: Path, outputB0: Path, session, name: str = "dwiextractAllB0", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = inputImage
        self.outputB0 = outputB0

        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles([self.outputB0])

    def getCommand(self):
        cpusPerTask = getattr(self.parent, "cpusPerTask", None)
        command = f"dwiextract {self.inputImage} - -bzero"
        if cpusPerTask:
            command += f" -nthreads {cpusPerTask}"
        if self.clobber:
            command += " -force"
        return command

class DWIEXTRACTMEANB0(Task):

    def __init__(self, inputImage: Path, outputB0: Path, session, name: str = "dwiextractMeanB0", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = inputImage
        self.outputB0 = outputB0

        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles([self.outputB0])

    def getCommand(self):
        cpusPerTask = getattr(self.parent, "cpusPerTask", None)
        c1 = f"dwiextract {self.inputImage} - -bzero"
        c2 = "mrmath - mean {self.outputB0} -axis 3"

        if cpusPerTask:
            c1 += f" -nthreads {cpusPerTask}"
            c2 += f" -nthreads {cpusPerTask}"
        if self.clobber:
            c1 += " -force"
            c2 += " -force"
        command = c1 + " | " + c2
        return command

class DWIEXTRACTTRACE(Task):

    def __init__(self, inputMif: Path, outputTrace: Path, session, name: str = "dwiextractTrace", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = inputMif
        self.outputB0 = outputTrace

        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles([self.outputB0])

    def getCommand(self):
        cpusPerTask = getattr(self.parent, "cpusPerTask", None)
        c1 = f"dwiextract {self.inputImage} - -shells 1000"
        c2 = "mrmath - mean {self.outputB0} -axis 3"

        if cpusPerTask:
            c1 += f" -nthreads {cpusPerTask}"
            c2 += f" -nthreads {cpusPerTask}"
        if self.clobber:
            c1 += " -force"
            c2 += " -force"
        command = c1 + " | " + c2
        return command


class DWIEXTRACTForDTI(Task):

    def __init__(self, inputMif: Path, outputImage: Path, outputBval, outputBvec, session, name: str = "dwiextractTrace", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = inputMif
        self.outputImage = outputImage
        self.outputBval = outputBval
        self.outputBvec = outputBvec

        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles([self.outputB0])

    def getCommand(self):
        cpusPerTask = getattr(self.parent, "cpusPerTask", None)
        command = f"dwiextract {self.inputImage} {self.outputImage} -shells 0,1000 -export_grad_fsl {self.outputBvec} {self.outputBval}"

        if cpusPerTask:
            command += f" -nthreads {cpusPerTask}"
        if self.clobber:
            command += " -force"
        return command






