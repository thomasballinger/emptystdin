import errno
import logging
import os
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
    logger.debug('connected')
    b'done' == s.recv(4)
    logger.debug('received done string')
    assert b'' == s.recv(1024)
    logger.debug('received empty string')


def set_up_listener():
    def forever():
        while True:
            conn, addr = sock.accept()
            lines_available, _ = get_cursor_position(sys.stdout, sys.stdin)
            logger.debug('handler done running')
            conn.send(b'done')
            logger.debug('data sent from server side')
            conn.close()
            logger.debug('socket closed on server side')

    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('localhost', 1234))
    sock.listen(10)
    t = threading.Thread(target=forever)
    t.daemon = True
    t.start()
    return sock, t


def master_read(data):
    logger.debug("read byte %r written to master device" % (data, ))
    return data

if __name__ == '__main__':
    if sys.argv[1] == 'inner':
        logging.basicConfig(filename='debug-outer.log', level=logging.DEBUG)
        logger = logging.getLogger('inner')
        logger.debug('\n\nnew session')
        while True:
            logger.debug('about to write prompt')
            sys.stderr.write('>>> ')
            sys.stderr.flush()
            logger.debug('just wrote prompt')
            input()
            logger.debug('got input')
            connect_and_wait_for_close()
    elif sys.argv[1] == 'outer':
        logging.basicConfig(filename='debug-inner.log', level=logging.DEBUG)
        logger = logging.getLogger('outer')
        set_up_listener()
        proc = pexpect.spawn(sys.executable, ['test.py', 'inner'],
                             logfile=open('pexpect.log', 'w'))
        proc.interact(output_filter=master_read)
