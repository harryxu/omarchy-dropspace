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
PID_FILENAME = "edge_watcher.pid"
_syslog_initialized = False

# Workspace card layout constants
BASE_CARD_WIDTH = 160
DEFAULT_CARD_HEIGHT = 100
CARD_SPACING = 16
TOP_MARGIN = 36
MAX_WORKSPACE_COUNT = 5
DROP_ZONE_EXTRA = 60


def calc_card_layout(screen_width: float, screen_height: float, workspace_count: int):
    """Calculate card dimensions and horizontal positioning for workspace cards.

    Returns:
        tuple: (card_width, card_height, total_width, start_x, end_x)
    """
    count = max(1, min(workspace_count, MAX_WORKSPACE_COUNT))
    available = screen_width - 64
    card_width = max(100, min(BASE_CARD_WIDTH, int((available - (count - 1) * CARD_SPACING) // count)))

    aspect = (screen_width / screen_height) if screen_height > 0 else (16.0 / 10.0)
    card_height = max(50, round(card_width / aspect))

    total_width = count * card_width + (count - 1) * CARD_SPACING
    start_x = (screen_width - total_width) / 2.0
    end_x = start_x + total_width
    return card_width, card_height, total_width, start_x, end_x


def is_in_vertical_drop_zone(rel_y: float, card_height: float = DEFAULT_CARD_HEIGHT) -> bool:
    """Check if relative Y coordinate is within the top dock drop zone."""
    return 0 <= rel_y <= (TOP_MARGIN + card_height + DROP_ZONE_EXTRA)


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


def get_pid_file_path() -> str:
    """Return path to the private edge-watcher PID file."""
    return os.path.join(get_runtime_dir(), PID_FILENAME)


def write_edge_watcher_pid(pid: int):
    """Write edge-watcher PID to private runtime directory with mode 0600."""
    pid_file = get_pid_file_path()

    # Safely remove existing PID file if present
    try:
        if os.path.lexists(pid_file):
            st = os.lstat(pid_file)
            if stat.S_ISLNK(st.st_mode) or st.st_uid == os.getuid():
                os.unlink(pid_file)
    except OSError:
        pass

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    old_umask = os.umask(0o177)
    try:
        fd = os.open(pid_file, flags, 0o600)
    finally:
        os.umask(old_umask)

    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid():
            raise RuntimeError("PID file is not a regular file owned by current user")
        if (st.st_mode & 0o777) != 0o600:
            os.fchmod(fd, 0o600)
        os.write(fd, f"{pid}\n".encode("utf-8"))
    finally:
        os.close(fd)


def remove_edge_watcher_pid():
    """Safely remove private edge-watcher PID file."""
    try:
        pid_file = get_pid_file_path()
        if os.path.lexists(pid_file):
            st = os.lstat(pid_file)
            if stat.S_ISLNK(st.st_mode) or st.st_uid == os.getuid():
                os.unlink(pid_file)
    except OSError:
        pass


def verify_process_identity(pid: int, expected_script: str = "edge-watcher.py") -> bool:
    """Strictly verify PID is alive, owned by current UID, and matches target script."""
    if pid <= 0 or pid == os.getpid():
        return False

    # 1. Check if process exists and current user can signal it
    try:
        os.kill(pid, 0)
    except OSError:
        return False

    # 2. Check proc entry ownership
    proc_path = f"/proc/{pid}"
    try:
        st = os.stat(proc_path)
        if st.st_uid != os.getuid():
            return False
    except OSError:
        return False

    # 3. Check cmdline for expected script
    try:
        with open(f"{proc_path}/cmdline", "rb") as f:
            raw = f.read()
        args = [arg.decode("utf-8", errors="ignore") for arg in raw.split(b"\0") if arg]
        # Must match expected script in argument list
        return any(expected_script in arg for arg in args)
    except Exception:
        return False


def get_verified_edge_watcher_pid() -> int | None:
    """Read private PID file and return PID only if process identity is verified."""
    pid_file = get_pid_file_path()
    try:
        st = os.lstat(pid_file)
        if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode):
            return None
        if st.st_uid != os.getuid() or (st.st_mode & 0o777) != 0o600:
            return None

        with open(pid_file, "r") as f:
            content = f.read().strip()
        if not content:
            return None
        pid = int(content)

        if verify_process_identity(pid, "edge-watcher.py"):
            return pid
        else:
            # Stale or mismatched PID file; clean it up safely
            remove_edge_watcher_pid()
            return None
    except Exception:
        return None


def stop_edge_watcher(timeout: float = 1.0) -> bool:
    """Gracefully stop edge-watcher by sending SIGTERM to verified PID only."""
    import signal

    pid = get_verified_edge_watcher_pid()
    if pid is None:
        remove_edge_watcher_pid()
        return False

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        remove_edge_watcher_pid()
        return False

    start = time.time()
    while time.time() - start < timeout:
        if not verify_process_identity(pid, "edge-watcher.py"):
            remove_edge_watcher_pid()
            return True
        time.sleep(0.05)

    # If still alive after timeout, send SIGKILL to verified PID as last resort
    if verify_process_identity(pid, "edge-watcher.py"):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass

    remove_edge_watcher_pid()
    return True

