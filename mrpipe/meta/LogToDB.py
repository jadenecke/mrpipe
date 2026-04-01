import sqlite3
import hashlib
from mrpipe.meta import LoggerModule

logger = LoggerModule.Logger()

class LogToDB:
    def __init__(self, path):
        self.path = path
        with sqlite3.connect(path, timeout=120) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                hash TEXT,
                subject TEXT,
                session TEXT,
                jobname TEXT,
                processingmodule TEXT,
                success INTEGER,
                timestamp TEXT,
                node TEXT,
                jobid TEXT,
                stdout TEXT,
                stderr TEXT
            )
            """)
        logger.info(f"Tried to create database for logs (if not already exist): {path}")

    # def log(node, thread, msg):
    #     conn.execute(
    #         "INSERT INTO logs VALUES (?, ?, ?, ?)",
    #         (datetime.utcnow().isoformat(), node, thread, msg)
    #     )
    #     conn.commit()
    #

    def compute_row_hash(self, subject, session, jobname) -> str:
        out_hash = hashlib.sha256(f"{subject}:{session}:{jobname}".encode()).hexdigest()
        logger.debug(f"Computed hash for {subject}:{session}:{jobname}: {out_hash}")
        return out_hash

