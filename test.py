import os
import random
import socket
import sys
import threading

import blessings
from termcast_client import pity

from findcursor import get_cursor_position


terminal = blessings.Terminal()


if sys.version_info.major == 2:
    input = raw_input
    ConnectionRefusedError = socket.error


def connect_and_wait_for_close(port):
    s = socket.socket()
    s.connect(('localhost', port))
    assert b'' == s.recv(1024)


def set_up_listener(handler, port):
    def forever():
        while True:
            conn, addr = sock.accept()
            handler()
            print 'handler done running'
            conn.close()

    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('localhost', port))
    sock.listen(10)
    t = threading.Thread(target=forever)
    t.daemon = True
    t.start()
    return sock, t


def write(data):
    sys.stdout.write(data)
    sys.stdout.flush()


def restore():
    n = 2
    lines_available, _ = get_cursor_position(sys.stdout, sys.stdin)
    for _ in range(n):
        write(terminal.move_up)
    for _ in range(200):
        write(terminal.move_left)
    write(terminal.clear_eos)


def master_read(fd):
    data = os.read(fd, 1024)
    return data


def hi():
    sys.stderr.write('hi')

if __name__ == '__main__':
    if sys.argv[1] == 'inner':
        while True:
            input('>>> ')
            connect_and_wait_for_close(4243)
    elif sys.argv[1] == 'outer':
        set_up_listener(restore, 4243)
        pity.spawn(['python', 'test.py', 'inner'],
                   master_read=master_read,
                   handle_window_size=True)
