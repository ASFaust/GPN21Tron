import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import socket
import time

HOST = '151.216.211.107'
PORT = 4000
USERNAME = "Snek"
PASSWORD = "yousorandomxd"

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))
print(f"Connected to {HOST}:{PORT}", flush=True)

def send(msg):
    print(f"[SEND] {msg}", flush=True)
    sock.sendall((msg + "\n").encode('utf-8'))

def recv_lines():
    buffer = ""
    while True:
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            yield line
        chunk = sock.recv(4096)
        if not chunk:
            raise RuntimeError("Connection closed by server")
        buffer += chunk.decode('utf-8')

send(f"join|{USERNAME}|{PASSWORD}")

for raw_line in recv_lines():
    ts = time.strftime("%H:%M:%S")
    parts = raw_line.split("|")
    print(f"[{ts}] {raw_line!r}  ->  {parts}", flush=True)
    if parts[0] == "tick":
        send("move|up")
