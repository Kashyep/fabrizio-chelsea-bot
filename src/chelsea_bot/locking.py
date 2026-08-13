from __future__ import annotations

import os
from pathlib import Path
from types import TracebackType


class AlreadyRunningError(RuntimeError):
    """Raised when another bot process holds the state lock."""


class ProcessLock:
    """Small cross-platform advisory lock based only on the standard library."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._stream = None

    def __enter__(self) -> ProcessLock:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = self.path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt

                self._stream.seek(0, os.SEEK_END)
                if self._stream.tell() == 0:
                    self._stream.write(b"0")
                    self._stream.flush()
                self._stream.seek(0)
                msvcrt.locking(self._stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as exc:
            self._stream.close()
            self._stream = None
            raise AlreadyRunningError(f"Another bot process is using {self.path}") from exc
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._stream is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                self._stream.seek(0)
                msvcrt.locking(self._stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._stream.fileno(), fcntl.LOCK_UN)
        finally:
            self._stream.close()
            self._stream = None
