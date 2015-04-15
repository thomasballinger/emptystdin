r"""
outer                                         inner

starts thread
             \_______
                     \
                      listen()

pexpect subprocess
process.interact()
                  \__________________________
                                             \
                                              input('>>> ')
                                              s.connect(server)
                      t = server.accept
                      t.send('done')
                                    \
                                     +------->s.recv()
                                              sys.stderr.write('>>> ') ??????
                                              sys.stderr.flush()
                                              input()

the second '>>> ' doesn't appear onscreen until a key has been entered.
I think this is because stdin is incorrectly being returned.
"""


import re
import socket
import sys
import threading
import termios
import tty

import pexpect

if sys.version_info.major == 2:
    input = raw_input
    ConnectionRefusedError = socket.error


def get_cursor_position(to_terminal, from_terminal):
    original_stty = termios.tcgetattr(from_terminal)
    tty.setcbreak(from_terminal, termios.TCSANOW)
    try:
        query_cursor_position = u"\x1b[6n"
        to_terminal.write(query_cursor_position)
        to_terminal.flush()

        resp = ''
        while True:
            c = from_terminal.read(1)
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
    finally:
        termios.tcsetattr(from_terminal, termios.TCSANOW, original_stty)


def set_up_listener():
    def get_cursor_on_connect():
        conn, addr = sock.accept()
        get_cursor_position(sys.stdout, sys.stdin)
        conn.send(b'done')
        conn.close()

    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('localhost', 1234))
    sock.listen(10)
    t = threading.Thread(target=get_cursor_on_connect)
    t.start()
    return sock, t


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'inner':
        input('>>> ')
        s = socket.socket()
        s.connect(('localhost', 1234))
        b'done' == s.recv(1024)
        sys.stderr.write('>>> ')
        sys.stderr.flush()
        input()
    else:
        set_up_listener()
        proc = pexpect.spawn(sys.executable, ['test.py', 'inner'],
                             logfile=open('pexpect.log', 'w'))
        proc.interact()
