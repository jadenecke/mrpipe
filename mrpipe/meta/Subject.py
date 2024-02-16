from mrpipe.meta.Session import Session
from mrpipe.meta import loggerModule
from typing import List


logger = loggerModule.Logger()

class Subject:
    def __init__(self, subjectId:str):
        self.id = subjectId
        self.sessions: List[Session] = []

    def getSessions(self):
        pass