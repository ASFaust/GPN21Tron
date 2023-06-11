import socket

class TronPlayer:
    def __init__(self):
        self.host = 'gpn-tron.duckdns.org'
        self.port = 4000
        self.username = "pineapple internet v1.2"
        self.password = "yousorandomxd"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

tp = TronPlayer()