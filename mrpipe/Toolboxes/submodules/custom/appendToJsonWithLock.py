#!/usr/bin/env python3

import json
import os
import sys
import tempfile
import time


class NFSLock:
    """Lock based on atomic exclusive file creation (works on NFSv3+)."""

    def __init__(self, path, timeout=60, poll=0.1, stale_after=300):
        self.lock_path = path + ".lock"
        self.timeout = timeout
        self.poll = poll
        self.stale_after = stale_after
        self.fd = None

    def __enter__(self):
        start = time.time()
        while True:
            try:
                self.fd = os.open(
                    self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                )
                os.write(self.fd, f"{os.uname().nodename}:{os.getpid()}".encode())
                return self
            except FileExistsError:
                # Break stale locks left behind by crashed jobs
                try:
                    age = time.time() - os.stat(self.lock_path).st_mtime
                    if age > self.stale_after:
                        os.unlink(self.lock_path)
                        continue
                except FileNotFoundError:
                    continue
                if time.time() - start > self.timeout:
                    raise TimeoutError(f"Could not acquire {self.lock_path}")
                time.sleep(self.poll)

    def __exit__(self, *exc):
        if self.fd is not None:
            os.close(self.fd)
        try:
            os.unlink(self.lock_path)
        except FileNotFoundError:
            pass


def add_name_value_pair(file_path, name, value):
    try:
        with NFSLock(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)

            data[name] = value

            # Atomic write: temp file in same dir, then rename
            dir_name = os.path.dirname(os.path.abspath(file_path))
            fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
            try:
                with os.fdopen(fd, 'w') as tmp:
                    json.dump(data, tmp, indent=4)
                    tmp.flush()
                    os.fsync(tmp.fileno())
                os.replace(tmp_path, file_path)
            except Exception:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise

        print(f'Successfully added "{name}: {value}" to {file_path}')
    except FileNotFoundError:
        print(f'File {file_path} not found.')
        sys.exit(1)
    except json.JSONDecodeError:
        print(f'Error decoding JSON in {file_path}.')
        sys.exit(1)
    except Exception as e:
        print(f'An error occurred: {e}')
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: ./add_entry.py <file_path> <key> <value>")
        sys.exit(1)

    add_name_value_pair(sys.argv[1], sys.argv[2], " ".join(sys.argv[3:]))