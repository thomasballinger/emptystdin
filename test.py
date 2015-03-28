import os
import socket
import sys
import threading
import termios
import tty
import re

from termcast_client import pity


if sys.version_info.major == 2:
    input = raw_input
    ConnectionRefusedError = socket.error


class Cbreak(object):

    def __init__(self, stream):
        self.stream = stream

    def __enter__(self):
        self.original_stty = termios.tcgetattr(self.stream)
        tty.setcbreak(self.stream, termios.TCSANOW)

    def __exit__(self, *args):
        termios.tcsetattr(self.stream, termios.TCSANOW, self.original_stty)


def get_cursor_position(to_terminal, from_terminal):
    with Cbreak(from_terminal):
        return _inner_get_cursor_position(to_terminal, from_terminal)


def _inner_get_cursor_position(to_terminal, from_terminal):
    query_cursor_position = u"\x1b[6n"
    to_terminal.write(query_cursor_position)
    to_terminal.flush()

    def retrying_read():
        while True:
            try:
                c = from_terminal.read(1)
                if c == '':
                    raise ValueError("Stream should be blocking - should't"
                                     " return ''. Returned %r so far", (resp,))
                return c
            except IOError:
                raise ValueError('cursor get pos response read interrupted')

    resp = ''
    while True:
        c = retrying_read()
        resp += c
        m = re.search('(?P<extra>.*)'
                      '(?P<CSI>\x1b\[|\x9b)'
                      '(?P<row>\\d+);(?P<column>\\d+)R', resp, re.DOTALL)
        if m:
            row = int(m.groupdict()['row'])
            col = int(m.groupdict()['column'])
            extra = m.groupdict()['extra']
            if extra:  # TODO send these to child process
                raise ValueError(("Bytes preceding cursor position "
                                  "query response thrown out:\n%r\n"
                                  "Pass an extra_bytes_callback to "
                                  "CursorAwareWindow to prevent this")
                                 % (extra,))
            return (row - 1, col - 1)


def connect_and_wait_for_close():
    s = socket.socket()
    s.connect(('localhost', 1234))
    b'done' == s.recv(1024)
    assert b'' == s.recv(1024)


def set_up_listener():
    def forever():
        while True:
            conn, addr = sock.accept()
            lines_available, _ = get_cursor_position(sys.stdout, sys.stdin)
            conn.send(b'done')
            conn.close()

    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('localhost', 1234))
    sock.listen(10)
    t = threading.Thread(target=forever)
    t.daemon = True
    t.start()
    return sock, t


def master_read(fd):
    data = os.read(fd, 1024)
    return data


if __name__ == '__main__':
    if sys.argv[1] == 'inner':
        while True:
            input('>>> ')
            connect_and_wait_for_close()
    elif sys.argv[1] == 'outer':
        set_up_listener()
        pity.spawn(['python', 'test.py', 'inner'],
                   master_read=master_read,
                   handle_window_size=True)
