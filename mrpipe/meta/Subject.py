from mrpipe.meta.Session import Session
from mrpipe.meta import LoggerModule
from typing import List
from mrpipe.meta.PathClass import Path
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase

logger = LoggerModule.Logger()

class Subject:
    def __init__(self, uid: str, path: Path):
        self.id = uid
        self.path = path
        self.sessions: List[Session] = []

    def getSessions(self):
        return self.sessions

    def addSession(self, session: Session):
        if session not in self.sessions:
            self.sessions.append(session)
            logger.debug(f"Added Session: {session} to subject: {self.id}")

    def configurePaths(self, basePaths: PathBase):
        for session in self.sessions:
            logger.debug(f"Configured paths for session: {session}")
            for ses in self.sessions:
                ses.subjectPaths.path_yaml = basePaths.bidsProcessedPath.join(self.id).join("subjectPaths.yaml")
            if session.modalities.T1w:
                logger.debug(f"Configuring T1w Paths for session: {session}")
                session.subjectPaths.setT1w(sub=self.id, ses=session.name, basepaths=basePaths,
                                            basedir=session.modalities.T1w)

            if session.modalities.flair:
                logger.debug(f"Configuring FLAIR Paths for session: {session}")
                session.subjectPaths.setFlair(sub=self.id, ses=session.name, basepaths=basePaths,
                                            basedir=session.modalities.flair)

            if session.modalities.megre:
                logger.debug(f"Configuring MEGRE Paths for session: {session}")
                session.subjectPaths.setMEGRE(sub=self.id, ses=session.name, basepaths=basePaths,
                                              basedir=session.modalities.megre)

            if session.modalities.pet_av45:
                logger.debug(f"Configuring PET-AV45 Paths for session: {session}")
                session.subjectPaths.setPETAV45(sub=self.id, ses=session.name, basepaths=basePaths,
                                              basedir=session.modalities.pet_av45)

            session.pathsConfigured = True


    def __str__(self):
        return self.id
