"""Start, stop or check the local game server. One server, always on the same port."""
import os
import signal
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game")
PIDFILE = os.path.join(ROOT, ".server.pid")
LOGFILE = os.path.join(ROOT, ".server.log")
HOST = "127.0.0.1"
PORT = int(os.environ.get("PORT", "8807"))
URL = f"http://{HOST}:{PORT}/"


def port_busy():
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex((HOST, PORT)) == 0


def read_pid():
    try:
        return int(open(PIDFILE).read().strip())
    except (OSError, ValueError):
        return None


def start():
    if port_busy():
        pid = read_pid()
        if pid:
            print(f"Already running at {URL} (pid {pid})")
            return 0
        print(f"Port {PORT} is taken by another program; not starting a second server.")
        return 1
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    log = open(LOGFILE, "ab")
    proc = subprocess.Popen(
        [sys.executable, "-I", "-m", "http.server", str(PORT), "--bind", HOST, "--directory", GAME],
        stdout=log, stderr=log, stdin=subprocess.DEVNULL, creationflags=flags,
        start_new_session=os.name != "nt",
    )
    open(PIDFILE, "w").write(f"{proc.pid}\n")
    for _ in range(30):
        if port_busy():
            print(f"Serving {URL}")
            return 0
        time.sleep(0.1)
    print(f"Server did not come up; see {LOGFILE}")
    return 1


def stop():
    pid = read_pid()
    if not pid:
        print("Not running" if not port_busy() else f"Port {PORT} is in use, but not by a server this Makefile started.")
        return 0
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    os.remove(PIDFILE)
    print(f"Stopped server (pid {pid})")
    return 0


def status():
    pid = read_pid()
    if pid and port_busy():
        print(f"Running at {URL} (pid {pid})")
    elif port_busy():
        print(f"Port {PORT} is in use, but not by a server this Makefile started.")
    else:
        print("Not running")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    sys.exit({"start": start, "stop": stop, "status": status}[cmd]())
