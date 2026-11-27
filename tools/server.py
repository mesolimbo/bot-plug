"""Start, stop or check the local game server. One server, always on the same port."""
import os
import signal
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "docs")  # the game itself: served here, by GitHub Pages, and zipped for itch.io
PIDFILE = os.path.join(ROOT, "tools", ".server.pid")
LOGFILE = os.path.join(ROOT, "tools", ".server.log")
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
        [sys.executable, "-I", os.path.abspath(__file__), "serve"],
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


def serve():
    """Serve docs/ and tell the browser not to cache, so a reload always picks up edits."""
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    import json

    LEVELS = os.path.join(GAME, "levels.json")

    class NoCache(SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def reply(self, code, body):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        # The map editor asks whether it can save here (only this local server answers; GitHub Pages and itch.io
        # can't), then posts the whole levels file, written to docs/levels.json as the editor formats it.
        def do_GET(self):
            if self.path == "/__dev/ping":
                return self.reply(200, {"save": True})
            return super().do_GET()

        def do_POST(self):
            if self.path != "/__dev/levels":
                return self.reply(404, {"error": "not found"})
            size = int(self.headers.get("Content-Length", 0))
            if not 0 < size < 1_000_000:
                return self.reply(400, {"error": "bad size"})
            text = self.rfile.read(size).decode("utf-8")
            try:
                data = json.loads(text)
                ok = isinstance(data.get("difficulties"), list) and all(isinstance(d.get("levels"), list) for d in data["difficulties"])
            except (ValueError, AttributeError):
                ok = False
            if not ok:
                return self.reply(400, {"error": "not a levels file"})
            with open(LEVELS, "w", encoding="utf-8", newline="\n") as f:
                f.write(text if text.endswith("\n") else text + "\n")
            return self.reply(200, {"saved": os.path.relpath(LEVELS, ROOT).replace(os.sep, "/")})

    ThreadingHTTPServer((HOST, PORT), partial(NoCache, directory=GAME)).serve_forever()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    sys.exit({"start": start, "stop": stop, "status": status, "serve": serve}[cmd]())
