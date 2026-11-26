"""Send a Python file to the live Blender bridge and print what it returns."""
import json
import socket
import sys

code = open(sys.argv[1], encoding="utf-8").read()
with socket.create_connection(("127.0.0.1", 9876), timeout=900) as s:
    s.sendall(code.encode("utf-8"))
    s.shutdown(socket.SHUT_WR)
    data = b""
    while chunk := s.recv(65536):
        data += chunk
res = json.loads(data)
print(res.get("output", ""), end="")
if not res["ok"]:
    print(res["error"], file=sys.stderr)
    sys.exit(1)
