#!/usr/bin/env python3
"""
missing_db.py - tiny file-based database for "which output files are still missing?"

Pure standard library (sqlite3 is bundled with Python, no server needed).

Hierarchy:   module > node > (subject, session) = one *task*
Each task stores: how many files it expects (optional), and the list of missing files.

Usage from your pipeline:
    from missing_db import save_task_result, register_node
    save_task_result("preproc", "eddy", "sub-001", "ses-1", missing_files, n_expected=12)

Command line:
    python missing_db.py report                  # -> missing_report.html (open in browser)
    python missing_db.py summary                 # quick text overview
    python missing_db.py export-missing out.txt --node eddy --subject "sub-0*"
    python missing_db.py demo --db demo.sqlite   # fake data to try the UI
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple
from mrpipe.meta import LoggerModule

logger = LoggerModule.Logger()

DB_PATH = Path("missing_files.sqlite")
REPORT_PATH = Path("missing_report.html")
SEP = " \u203a "  # separator for hierarchical keys in the report

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id         INTEGER PRIMARY KEY,
    module     TEXT NOT NULL,
    node       TEXT NOT NULL,
    subject    TEXT NOT NULL,
    session    TEXT NOT NULL,
    n_expected INTEGER,          -- NULL = unknown
    n_missing  INTEGER,          -- NULL = task never checked yet
    updated_at REAL,
    UNIQUE (module, node, subject, session)
);
CREATE TABLE IF NOT EXISTS missing_files (
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    path    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_missing_task ON missing_files(task_id);
"""


# --------------------------------------------------------------------------- #
# Database access
# --------------------------------------------------------------------------- #
@contextmanager
def open_db(db_path: Path | str = DB_PATH):
    """Open (and create if needed) the database. Commits on success.

    Use one `with open_db() as con:` around many calls when saving lots of
    results - it is far faster than one connection per call.
    """
    con = sqlite3.connect(str(db_path), timeout=120)
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(SCHEMA)
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _task_id(con: sqlite3.Connection, key: Tuple[str, str, str, str]) -> int:
    con.execute(
        "INSERT OR IGNORE INTO tasks(module, node, subject, session) "
        "VALUES (?,?,?,?)", key)
    return con.execute(
        "SELECT id FROM tasks WHERE module=? AND node=? "
        "AND subject=? AND session=?", key).fetchone()[0]


def register_node(module: str, node: str,
                  subject_sessions: Iterable[Tuple[str, str]],
                  db_path: Path | str = DB_PATH,
                  con: Optional[sqlite3.Connection] = None) -> None:
    """Announce which (subject, session) pairs a node is supposed to process.

    Tasks that were registered but never saved show up as "not checked" (grey)
    in the report, so nothing silently disappears from the overview.
    Existing results are never overwritten.
    """
    rows = [(module, node, str(s), str(ses)) for s, ses in subject_sessions]
    sql = ("INSERT OR IGNORE INTO tasks(module, node, subject, session) "
           "VALUES (?,?,?,?)")
    if con is not None:
        con.executemany(sql, rows)
    else:
        with open_db(db_path) as c:
            c.executemany(sql, rows)


def save_task_result(module: str, node: str,
                     subject: str, session: str,
                     missing_files: Iterable[str | Path],
                     n_expected: Optional[int] = None,
                     db_path: Path | str = DB_PATH,
                     con: Optional[sqlite3.Connection] = None) -> int:
    """Save the result of ONE task (node x subject x session).

    Idempotent: calling it again for the same task replaces the previous result.
    An empty `missing_files` means "checked, nothing missing" (complete).
    `n_expected` (total number of output files the task should produce) is
    optional but gives much better percentages in the report.
    Returns the number of missing files stored.
    """
    missing = sorted({str(p) for p in missing_files})
    key = (module, node, str(subject), str(session))

    def _do(c: sqlite3.Connection) -> None:
        tid = _task_id(c, key)
        c.execute("DELETE FROM missing_files WHERE task_id=?", (tid,))
        c.executemany("INSERT INTO missing_files(task_id, path) VALUES (?,?)",
                      ((tid, p) for p in missing))
        c.execute("UPDATE tasks SET n_expected=?, n_missing=?, updated_at=? WHERE id=?",
                  (n_expected, len(missing), time.time(), tid))

    if con is not None:
        _do(con)
    else:
        with open_db(db_path) as c:
            _do(c)
    return len(missing)


# --------------------------------------------------------------------------- #
# HTML report
# --------------------------------------------------------------------------- #
def build_report(db_path: Path | str = DB_PATH,
                 out_html: Path | str = REPORT_PATH,
                 max_files_per_task: int = 25,
                 max_files_total: int = 100_000) -> Path:
    """Write a self-contained HTML file (no internet, no server needed).

    Task-level numbers are always complete. The *lists* of missing paths are
    embedded only up to `max_files_per_task` per task and `max_files_total`
    overall, to keep the HTML small; use `export-missing` for full lists.
    """
    strings: list[str] = []
    index: dict[str, int] = {}

    def sid(s: str) -> int:
        i = index.get(s)
        if i is None:
            i = index[s] = len(strings)
            strings.append(s)
        return i

    rows: list[list[int]] = []
    files: dict[str, list[str]] = {}
    budget = max_files_total

    with open_db(db_path) as con:
        task_rows = con.execute(
            "SELECT id, module, node, subject, session, n_expected, n_missing "
            "FROM tasks ORDER BY module, node, subject, session").fetchall()
        for tid, module, node, subj, ses, exp, mis in task_rows:
            rows.append([sid(module), sid(f"{module}{SEP}{node}"),
                         sid(subj), sid(ses),
                         -1 if exp is None else exp,
                         -1 if mis is None else mis])
            if mis and budget > 0:
                n = min(max_files_per_task, budget)
                paths = [r[0] for r in con.execute(
                    "SELECT path FROM missing_files WHERE task_id=? LIMIT ?", (tid, n))]
                files[str(len(rows) - 1)] = paths
                budget -= len(paths)

    payload = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "db": str(db_path),
        "sep": SEP,
        "strings": strings,
        "rows": rows,
        "files": files,
    }
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    data = data.replace("</", "<\\/")  # keep </script> out of the JSON
    template = Path(__file__).with_name("report_template.html").read_text(encoding="utf-8")
    out = Path(out_html)
    out.write_text(template.replace("__DATA__", data), encoding="utf-8")
    return out


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #
def print_summary(db_path: Path | str = DB_PATH) -> None:
    with open_db(db_path) as con:
        rows = con.execute(
            "SELECT module, COUNT(*), SUM(n_missing IS NULL), "
            "SUM(n_missing = 0), SUM(n_missing > 0), COALESCE(SUM(n_missing), 0) "
            "FROM tasks GROUP BY module ORDER BY module").fetchall()
    logger.process(f"{'module':40} {'tasks':>8} {'done':>8} {'incompl':>8} "
          f"{'unchecked':>9} {'missing files':>14}")
    tot = [0, 0, 0, 0, 0]
    for module, n, unk, ok, bad, miss in rows:
        unk, ok, bad = unk or 0, ok or 0, bad or 0
        logger.process(f"{module:40} {n:8} {ok:8} {bad:8} {unk:9} {miss:14}")
        for i, v in enumerate((n, ok, bad, unk, miss)):
            tot[i] += v
    logger.process("-" * 92)
    logger.process(f"{'TOTAL':40} {tot[0]:8} {tot[1]:8} {tot[2]:8} {tot[3]:9} {tot[4]:14}")


def export_missing(out_txt: Path | str, db_path: Path | str = DB_PATH, **flt: Optional[str]) -> int:
    """Write all missing paths (one per line) matching the filters. Filters use
    SQLite GLOB patterns, e.g. subject="sub-0*"."""
    where, params = [], []
    for col in ("module", "node", "subject", "session"):
        if flt.get(col):
            where.append(f"t.{col} GLOB ?")
            params.append(flt[col])
    sql = ("SELECT m.path FROM missing_files m JOIN tasks t ON t.id = m.task_id "
           + (("WHERE " + " AND ".join(where)) if where else "")
           + " ORDER BY t.module, t.node, t.subject, t.session, m.path")
    n = 0
    with open_db(db_path) as con, open(out_txt, "w", encoding="utf-8") as f:
        for (p,) in con.execute(sql, params):
            f.write(p + "\n")
            n += 1
    return n


def make_demo(db_path: Path | str, n_subjects: int = 60, n_sessions: int = 2, seed: int = 1) -> None:
    """Fill a database with synthetic data so you can try the report."""
    rnd = random.Random(seed)
    dag = {
        "T1w_preproc": ["denoise", "bias_correct", "brain_mask"],
        "T1w_segmentation": ["fast", "first"],
        "dwi_preproc": ["topup", "eddy", "dtifit"],
        "dwi_tractography": ["csd", "tckgen", "connectome"],
        "qsm": ["unwrap", "bgremove", "dipole_inv"],
        "r2star": ["fit"],
        "func_preproc": ["mcflirt", "smooth", "ica"],
    }
    subjects = [f"sub-{i:03d}" for i in range(1, n_subjects + 1)]
    sessions = [f"ses-{i}" for i in range(1, n_sessions + 1)]
    bad_subjects = set(rnd.sample(subjects, 6))
    with open_db(db_path) as con:
        for module, nodes in dag.items():
            for k, node in enumerate(nodes):
                for s in subjects:
                    for ses in sessions:
                        r = rnd.random()
                        if r < 0.04:
                            # never ran -> registered but "not checked"
                            register_node(module, node, [(s, ses)], con=con)
                            continue
                        n_exp = 10
                        p_fail = 0.08 + 0.1 * k + (0.5 if s in bad_subjects else 0)
                        n_miss = 0 if rnd.random() > p_fail else rnd.randint(1, n_exp)
                        missing = [f"/data/{module}/{node}/{s}/{ses}/out_{i:02d}.nii.gz"
                                   for i in range(n_miss)]
                        save_task_result(module, node, s, ses, missing,
                                         n_expected=n_exp, con=con)


# --------------------------------------------------------------------------- #
def run(cmd: str,
        db: Path | str = DB_PATH,
        out: Path | str | None = None,
        max_files_per_task: int = 25,
        max_files_total: int = 100_000,
        module: Optional[str] = None,
        node: Optional[str] = None,
        subject: Optional[str] = None,
        session: Optional[str] = None,
        subjects: int = 60):
    """Run one command. Call this from your own scripts; main() just forwards
    the parsed command-line arguments here.

    cmd:
      "report"          -> build the HTML overview; `out` = html path
                           (default missing_report.html). Returns the Path.
      "summary"         -> print a text summary. Returns None.
      "export-missing"  -> write missing paths to `out` (required), filtered by
                           module/node/subject/session (GLOB patterns).
                           Returns the number of paths written.
      "demo"            -> fill `db` with synthetic data for `subjects` subjects.

    Example:
        run("report", db="my.sqlite", out="overview.html")
        run("export-missing", db="my.sqlite", out="eddy_missing.txt", node="eddy", subject="sub-0*")
    """
    if cmd == "report":
        path = build_report(db, out or REPORT_PATH, max_files_per_task, max_files_total)
        logger.process(f"wrote {path}  ({path.stat().st_size / 1e6:.1f} MB) - open it in a browser")
        return path
    if cmd == "summary":
        return print_summary(db)
    if cmd == "export-missing":
        if out is None:
            raise ValueError("export-missing needs `out` (target text file)")
        n = export_missing(out, db, module=module, node=node,
                           subject=subject, session=session)
        logger.process(f"wrote {n} paths to {out}")
        return n
    if cmd == "demo":
        make_demo(db, subjects)
        logger.process(f"demo data written to {db}")
        return None
    raise ValueError(f"unknown command: {cmd!r}")


def main(argv: Optional[Sequence[str]] = None) -> None:
    """Command-line entry point: only parses arguments, then calls run()."""
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=str(DB_PATH), help="database file (default: %(default)s)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("report", help="build the HTML overview")
    p.add_argument("--out", default=str(REPORT_PATH))
    p.add_argument("--max-files-per-task", type=int, default=25)
    p.add_argument("--max-files-total", type=int, default=100_000)

    sub.add_parser("summary", help="print a text summary per module")

    p = sub.add_parser("export-missing", help="dump missing paths to a text file")
    p.add_argument("out")
    for col in ("module", "node", "subject", "session"):
        p.add_argument(f"--{col}", help="GLOB pattern, e.g. 'sub-0*'")

    p = sub.add_parser("demo", help="fill the db with synthetic data")
    p.add_argument("--subjects", type=int, default=60)

    run(**vars(ap.parse_args(argv)))


if __name__ == "__main__":
    main()