#!/usr/bin/env python3
"""DropSpace secure runtime and coordination module.

Provides hardened path resolution, directory creation, exclusive/no-follow state
management, and journal logging to eliminate predictable /tmp attacks.
"""

import os
import stat
import sys
import time
import syslog

STATE_FILENAME = "dropspace_is_open"
LOG_FILENAME = "dropspace.log"
_syslog_initialized = False


def init_journal(ident: str = "dropspace"):
    """Initialize connection to systemd user journal via syslog."""
    global _syslog_initialized
    if not _syslog_initialized:
        try:
            syslog.openlog(ident=ident, logoption=syslog.LOG_PID, facility=syslog.LOG_USER)
            _syslog_initialized = True
        except Exception:
            pass


def get_runtime_base_dir() -> str:
    """Resolve base runtime directory from $XDG_RUNTIME_DIR or fallback."""
    xdg = os.environ.get("XDG_RUNTIME_DIR")
    if xdg and os.path.isabs(xdg) and os.path.isdir(xdg):
        return xdg
    fallback = f"/run/user/{os.getuid()}"
    if os.path.isdir(fallback):
        return fallback
    cache_fallback = os.path.expanduser("~/.cache")
    try:
        os.makedirs(cache_fallback, mode=0o700, exist_ok=True)
        return cache_fallback
    except OSError:
        pass
    import tempfile
    return tempfile.gettempdir()


def get_runtime_dir() -> str:
    """Return plugin-specific directory created with mode 0700 and verified ownership."""
    base = get_runtime_base_dir()
    p = os.path.join(base, "dropspace")

    # Ensure directory creation with mode 0700
    old_umask = os.umask(0o077)
    try:
        os.makedirs(p, mode=0o700, exist_ok=True)
    finally:
        os.umask(old_umask)

    # Strictly verify ownership, type, and permissions
    st = os.lstat(p)
    if stat.S_ISLNK(st.st_mode):
        # Symlink in runtime directory is prohibited; remove and recreate
        os.unlink(p)
        old_umask = os.umask(0o077)
        try:
            os.makedirs(p, mode=0o700, exist_ok=True)
        finally:
            os.umask(old_umask)
        st = os.lstat(p)

    if not stat.S_ISDIR(st.st_mode):
        raise RuntimeError(f"Runtime path {p} is not a directory")
    if st.st_uid != os.getuid():
        raise RuntimeError(f"Runtime path {p} is not owned by current user ({st.st_uid} != {os.getuid()})")
    if (st.st_mode & 0o777) != 0o700:
        os.chmod(p, 0o700)

    return p


def get_state_file_path() -> str:
    """Return path to the coordination state file."""
    return os.path.join(get_runtime_dir(), STATE_FILENAME)


def get_log_file_path() -> str:
    """Return path to the secure user log file."""
    return os.path.join(get_runtime_dir(), LOG_FILENAME)


def set_state_open():
    """Create coordination state file with exclusive, no-follow semantics, mode 0600."""
    state_file = get_state_file_path()

    # If already present, safely unlink first to enforce exclusive creation semantics
    try:
        if os.path.lexists(state_file):
            st = os.lstat(state_file)
            if stat.S_ISLNK(st.st_mode) or st.st_uid == os.getuid():
                os.unlink(state_file)
    except OSError:
        pass

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    old_umask = os.umask(0o177)
    try:
        fd = os.open(state_file, flags, 0o600)
    finally:
        os.umask(old_umask)

    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise RuntimeError("State file is not a regular file")
        if st.st_uid != os.getuid():
            raise RuntimeError("State file is not owned by current user")
        if (st.st_mode & 0o777) != 0o600:
            os.fchmod(fd, 0o600)
        os.write(fd, b"open\n")
    finally:
        os.close(fd)


def set_state_closed():
    """Remove coordination state file safely."""
    try:
        state_file = get_state_file_path()
        if os.path.lexists(state_file):
            st = os.lstat(state_file)
            if stat.S_ISLNK(st.st_mode) or st.st_uid == os.getuid():
                os.unlink(state_file)
    except OSError:
        pass


def is_state_open() -> bool:
    """Verify regular-file ownership, mode 0600, and non-symlink status of state file."""
    try:
        state_file = get_state_file_path()
        st = os.lstat(state_file)
        if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode):
            return False
        if st.st_uid != os.getuid():
            return False
        if (st.st_mode & 0o777) != 0o600:
            return False
        return True
    except OSError:
        return False


def log(msg: str):
    """Log message to systemd user journal and secure private log file."""
    init_journal()

    # 1. Log to user journal via syslog
    try:
        syslog.syslog(syslog.LOG_INFO, msg)
    except Exception:
        pass

    # 2. Interactive terminal output (stderr)
    try:
        if sys.stderr.isatty():
            sys.stderr.write(f"[{time.strftime('%X')}] {msg}\n")
            sys.stderr.flush()
    except Exception:
        pass

    # 3. Secure file in $XDG_RUNTIME_DIR/dropspace/dropspace.log
    try:
        log_file = get_log_file_path()
        if os.path.islink(log_file):
            try:
                os.unlink(log_file)
            except OSError:
                return

        flags = os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW
        try:
            fd = os.open(log_file, flags)
        except FileNotFoundError:
            create_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
            old_umask = os.umask(0o177)
            try:
                fd = os.open(log_file, create_flags, 0o600)
            finally:
                os.umask(old_umask)

        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid():
                return
            if (st.st_mode & 0o777) != 0o600:
                os.fchmod(fd, 0o600)
            entry = f"[{time.strftime('%X')}] {msg}\n".encode("utf-8")
            os.write(fd, entry)
        finally:
            os.close(fd)
    except Exception:
        pass
