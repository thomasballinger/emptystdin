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
                                              raw_input('>>> ')
                                              s.connect(server)
                      t = server.accept
                      t.send('done')
                                    \
                                     +------->s.recv()
                                              sys.stderr.write('>>> ') ??????
                                              sys.stderr.flush()
                                              raw_input()

the second '>>> ' doesn't appear onscreen until a key has been entered.
I think this is because stdin is incorrectly being returned.
"""

import socket
import sys
import threading
import termios
import tty

import pexpect


def get_cursor_position(to_terminal, from_terminal):
    original_stty = termios.tcgetattr(from_terminal)
    tty.setcbreak(from_terminal, termios.TCSANOW)
    try:
        query_cursor_position = u"\x1b[6n"
        to_terminal.write(query_cursor_position)
        to_terminal.flush()

        while True:
            if from_terminal.read(1) == 'R':
                return
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
    sock.listen(1)
    t = threading.Thread(target=get_cursor_on_connect)
    t.start()


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'inner':
        raw_input('>>> ')
        s = socket.socket()
        s.connect(('localhost', 1234))
        b'done' == s.recv(1024)
        sys.stderr.write('>>> ')
        sys.stderr.flush()
        raw_input()
    else:
        set_up_listener()
        proc = pexpect.spawn(sys.executable, ['test.py', 'inner'])
        proc.interact()
