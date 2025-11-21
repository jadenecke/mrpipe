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
            logger.info(f"Added Session: {session} to subject: {self.id}")

    def configurePaths(self, basePaths: PathBase):
        for session in self.sessions:
            logger.info(f"Configuring paths for subject {self.id} with session: {session}")
            for ses in self.sessions:
                ses.subjectPaths.path_yaml = basePaths.bidsProcessedPath.join(self.id).join("subjectPaths.yaml")
            if session.modalities.T1w:
                logger.info(f"Configuring T1w Paths for session: {session}")
                session.subjectPaths.setT1w(sub=self.id, ses=session.name, basepaths=basePaths,
                                            basedir=session.modalities.T1w)

            if session.modalities.flair:
                logger.info(f"Configuring FLAIR Paths for session: {session}")
                session.subjectPaths.setFlair(sub=self.id, ses=session.name, basepaths=basePaths,
                                            basedir=session.modalities.flair)

            if session.modalities.megre:
                logger.info(f"Configuring MEGRE Paths for session: {session}")
                session.subjectPaths.setMEGRE(sub=self.id, ses=session.name, basepaths=basePaths,
                                              basedir=session.modalities.megre)

            if session.modalities.pet_av45:
                logger.info(f"Configuring PET-AV45 Paths for session: {session}")
                session.subjectPaths.setPETAV45(sub=self.id, ses=session.name, basepaths=basePaths,
                                              basedir=session.modalities.pet_av45)

            if session.modalities.pet_nav4694:
                logger.info(f"Configuring PET-NAV4694 Paths for session {session}")
                session.subjectPaths.setPETNAV4694(sub=self.id, ses = session.name, basepaths=basePaths,
                                                   basedir=session.modalities.pet_nav4694)
            if session.modalities.pet_fbb:
                logger.info(f"Configuring PET-FBB Paths for session {session}")
                session.subjectPaths.setPETFBB(sub=self.id, ses = session.name, basepaths=basePaths,
                                               basedir=session.modalities.pet_fbb)
            if session.modalities.pet_av1451:
                logger.info(f"Configuring PET-AV1451 Paths for session {session}")
                session.subjectPaths.setPETAV1451(sub=self.id, ses = session.name, basepaths=basePaths,
                                                  basedir=session.modalities.pet_av1451)
            if session.modalities.pet_pi2620:
                logger.info(f"Configuring PET-PI2620 Paths for session {session}")
                session.subjectPaths.setPETPI2620(sub=self.id, ses = session.name, basepaths=basePaths,
                                                  basedir=session.modalities.pet_pi2620)
            if session.modalities.pet_mk6240:
                logger.info(f"Configuring PET-MK6240 Paths for session {session}")
                session.subjectPaths.setPETMK6240(sub=self.id, ses = session.name, basepaths=basePaths,
                                                  basedir=session.modalities.pet_mk6240)
            if session.modalities.pet_fmm:
                logger.info(f"Configuring PET-FMM Paths for session {session}")
                session.subjectPaths.setPETFMM(sub=self.id, ses=session.name, basepaths=basePaths,
                                                  basedir=session.modalities.pet_fmm)

            if session.modalities.pet_fdg:
                logger.info(f"Configuring PET-FDG Paths for session {session}")
                session.subjectPaths.setPETFDG(sub=self.id, ses=session.name, basepaths=basePaths,
                                                  basedir=session.modalities.pet_fdg)

            session.pathsConfigured = True


    def __str__(self):
        return self.id
