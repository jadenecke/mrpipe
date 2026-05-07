import sqlite3
import hashlib
from mrpipe.meta import LoggerModule
from tqdm import tqdm

logger = LoggerModule.Logger()

class LogToDB:
    def __init__(self, path):
        self.path = path
        self.dbName = "logs"
        with sqlite3.connect(self.path, timeout=120) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                -- Primary key (computed from subject, session, jobname)
                hash TEXT PRIMARY KEY,
                
                -- MRPIPE environment variables
                subject TEXT,
                session TEXT,
                jobname TEXT,
                processingmodule TEXT,
                
                -- Job status
                processed INTEGER,
                
                -- Job execution
                timestampstart TEXT,
                timestampend TEXT,
                error INTEGER,
                stdout TEXT,
                stderr TEXT,
                command TEXT,
                
                -- Resource usage
                Realtime REAL,
                Usertime REAL,
                Systime REAL,
                MaxRSS REAL,
                
                -- SLURM environment variables
                slurmdnodename TEXT, --  SLURMD_NODENAME
                slurmclustername TEXT, --  SLURM_CLUSTER_NAME
                slurmjobid TEXT, --  SLURM_JOBID
                slurmjobaccount TEXT, --  SLURM_JOB_ACCOUNT
                slurmjobname TEXT, --  SLURM_JOB_NAME
                slurmjobnodelist TEXT, --  SLURM_JOB_NODELIST
                slurmjobnumnodes TEXT, --  SLURM_JOB_NUM_NODES
                slurmjobpartition TEXT, --  SLURM_JOB_PARTITION
                slurmjobqos TEXT, --  SLURM_JOB_QOS
                slurmjobuid TEXT, --  SLURM_JOB_UID
                slurmjobuser TEXT, --  SLURM_JOB_USER
                slurmnprocs TEXT, --  SLURM_NPROCS
                slurmntasks TEXT, --  SLURM_NTASKS
                slurmprocid TEXT, --  SLURM_PROCID
                slurmstepid TEXT, --  SLURM_STEPID
                slurmstepnodelist TEXT, --  SLURM_STEP_NODELIST
                slurmstepnumnodes TEXT, --  SLURM_STEP_NUM_NODES
                slurmstepnumtasks TEXT, --  SLURM_STEP_NUM_TASKS
                slurmsteptaskspernode TEXT, --  SLURM_STEP_TASKS_PER_NODE
                slurmsubmitdir TEXT, --  SLURM_SUBMIT_DIR
                slurmsubmithost TEXT, --  SLURM_SUBMIT_HOST
                slurmtaskspernode TEXT --  SLURM_TASKS_PER_NODE
            )
            """)
        logger.info(f"Tried to create database for logs (if not already exist): {path}")

    @staticmethod
    def compute_row_hash(subject, session, jobname) -> str:
        out_hash = hashlib.sha256(f"{subject}:{session}:{jobname}".encode()).hexdigest()
        logger.debug(f"Computed hash for {subject}:{session}:{jobname}: {out_hash}")
        return out_hash

    def create_entry_unprocessed(self, module) -> bool:
        with sqlite3.connect(self.path, timeout=120) as conn:
            for session in module.sessions:
                for job in module.pipeJobs:
                    try:
                        h = LogToDB.compute_row_hash(subject=session.subjectName, session=session.name, jobname=job.name)
                        conn.execute("INSERT OR IGNORE INTO logs (hash, subject, session, jobname, processingmodule) VALUES (?, ?, ?, ?, ?)",
                                         (h, session.subjectName, session.name, job.name, module.moduleName))
                        logger.debug(f"Created entry for {session.subjectName}:{session.name}:{job.name} in database {self.path}")
                    except Exception as e:
                        logger.logExceptionError(f"Could not create entry for {session.subjectName}:{session.name}:{job.name} in database {self.path}", e)



    def set_processed(self, subject, session, jobname, processed) -> bool:
        try:
            with sqlite3.connect(self.path, timeout=120) as conn:
                h = LogToDB.compute_row_hash(subject=subject, session=session, jobname=jobname)
                conn.execute("UPDATE logs SET processed = ? WHERE hash = ?", (processed, h))
            logger.debug(f"Set processed status for {subject}:{session}:{jobname} in database {self.path}. Status: {processed}")
            return True
        except Exception as e:
            logger.logExceptionError(f"Could not set processed for {subject}:{session}:{jobname} in database {self.path}", e)
            return False

    def create_log_call_identifier(self, subject, session, jobname):
        h = LogToDB.compute_row_hash(subject=subject, session=session, jobname=jobname)
        return f"{self.path} {self.dbName} {h}"
