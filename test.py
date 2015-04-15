import re
import socket
import sys
import threading

import pexpect
from termhelpers import Cbreak

if sys.version_info.major == 2:
    input = raw_input
    ConnectionRefusedError = socket.error


def get_cursor_position(to_terminal, from_terminal):
    with Cbreak(from_terminal):
        query_cursor_position = u"\x1b[6n"
        to_terminal.write(query_cursor_position)
        to_terminal.flush()

        def retrying_read():
            while True:
                c = from_terminal.read(1)
                return c

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
                assert not extra
                return (row - 1, col - 1)


def set_up_listener():
    def forever():
        conn, addr = sock.accept()
        get_cursor_position(sys.stdout, sys.stdin)
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


if __name__ == '__main__':
    if sys.argv[1] == 'inner':
        while True:
            sys.stderr.write('>>> ')
            sys.stderr.flush()
            input()
            s = socket.socket()
            s.connect(('localhost', 1234))
            b'done' == s.recv(1024)
            assert b'' == s.recv(1024)
    elif sys.argv[1] == 'outer':
        set_up_listener()
        proc = pexpect.spawn(sys.executable, ['test.py', 'inner'],
                             logfile=open('pexpect.log', 'w'))
        proc.interact()
