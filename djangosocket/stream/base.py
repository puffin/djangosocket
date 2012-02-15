# -*- coding: utf-8 -

import logging
import collections

from eventlet import semaphore

from djangosocket.stream import const

class MalformedWebSocket(ValueError):
    pass

class ConnectionTerminatedException(Exception):
    """
    This exception will be raised when a connection is terminated
    unexpectedly.
    """

    pass


class InvalidFrameException(ConnectionTerminatedException):
    """
    This exception will be raised when we received an invalid frame we
    cannot parse.
    """

    pass


class BadOperationException(Exception):
    """
    This exception will be raised when send_message() is called on
    server-terminated connection or receive_message() is called on
    client-terminated connection.
    """

    pass


class UnsupportedFrameException(Exception):
    """
    This exception will be raised when we receive a frame with flag, opcode
    we cannot handle. Handlers can just catch and ignore this exception and
    call receive_message() again to continue processing the next frame.
    """

    pass

class UnsupportedProtocolException(Exception):
    """
    This exception will be raised when we receive a frame with protocol
    we cannot handle.
    """

    pass

class InvalidUTF8Exception(Exception):
    """
    This exception will be raised when we receive a text frame which
    contains invalid UTF-8 strings.
    """

    pass


class StreamBase(object):
    """
    Base stream class.
    """
    
    _socket_recv_bytes = 4096
    
    def __init__(self, socket):
        """
        Construct an instance.

        socket: django request websocket object.
        """

        self._logger            = logging.getLogger('djangosocket.stream')
        self._socket            = socket
        self._buffer            = ""
        self._message_queue     = collections.deque()
        self._sendlock          = semaphore.Semaphore()
        self.closed             = False
    
    
    def _send_handshake(self):
        """
        Send handshake to the client.
        """
        
        raise NotImplementedError()
    
    def send(self):
        """
        Send a message to the client.
        """
        
        raise NotImplementedError()
    
    def do_handshake(self):
        """
        Perform WebSocket Handshake.
        """

        self._send_handshake()
        self._logger.debug('Sent opening handshake response')
    
    def _write(self, bytes):
        """
        Writes given bytes to connection.
        """
        
        self._sendlock.acquire()
        try:
            self._socket.sendall(bytes)
        finally:
            self._sendlock.release()
    
    
    def _parse_message_queue(self):
        """
        Parses for messages in the buffer *buf*. It is assumed that
        the buffer contains the start character for a message, but that it
        may contain only part of the rest of the message.

        Returns an array of messages, and the buffer remainder that
        didn't contain any full messages.
        
        Must be implemented in stream specific child Class
        """
        
        raise NotImplementedError()
    
    
    def _socket_recv(self):
        """
        Gets new data from the socket and try to parse new messages.
        """
        
        delta = self._socket.recv(self._socket_recv_bytes)
        if delta == '':
            return False
        self._buffer += delta
        
        msgs = self._parse_message_queue()
        
        self._message_queue.extend(msgs)
        return True
    
    
    def _wait(self):
        """
        Waits for and deserializes messages. Returns a single message; the
        oldest not yet processed.
        """
        
        while not self._message_queue:
            # Websocket might be closed already.
            if self.closed:
                raise ConnectionTerminatedException('Receiving byte failed. Peer closed connection')
            # no parsed messages, must mean buf needs more data
            bytes = self._socket_recv()
            if not bytes:
                raise ConnectionTerminatedException('Receiving byte failed. Peer closed connection')
        return self._message_queue.popleft()
    
    
    def __iter__(self):
        """
        Use WebSocket as iterator. Iteration only stops when the websocket
        gets closed by the client.
        """
        
        while True:
            try:
                message = self._wait()
            except:
                return
            yield message


"""
const functions and exceptions used by WebSocket opening handshake
processors.
"""

class AbortedByUserException(Exception):
    """
    Exception for aborting a connection intentionally.

    If this exception is raised in do_extra_handshake handler, the connection
    will be abandoned. No other WebSocket or HTTP(S) handler will be invoked.

    If this exception is raised in transfer_data_handler, the connection will
    be closed without closing handshake. No other WebSocket or HTTP(S) handler
    will be invoked.
    """

    pass


class HandshakeException(Exception):
    """
    This exception will be raised when an error occurred while processing
    WebSocket initial handshake.
    """

    def __init__(self, name, status=None):
        super(HandshakeException, self).__init__(name)
        self.status = status


class VersionException(Exception):
    """
    This exception will be raised when a version of client request does not
    match with version the server supports.
    """

    def __init__(self, name, supported_versions=''):
        """
        Construct an instance.

        supported_version is a str object to show supported hybi versions.
        (e.g. '8, 13')
        """
        
        super(VersionException, self).__init__(name)
        self.supported_versions = supported_versions


def build_location(request):
    """
    Build WebSocket location for request.
    """
    location_parts = []
    if request.is_secure():
        location_parts.append(const.WEB_SOCKET_SECURE_SCHEME)
    else:
        location_parts.append(const.WEB_SOCKET_SCHEME)
    location_parts.append('://')
    host = request.get_host()
    location_parts.append(host)
    if request.is_secure():
        location_parts.append(':')
        location_parts.append(str(const.DEFAULT_WEB_SOCKET_SECURE_PORT))
    location_parts.append(request.path)
    return ''.join(location_parts)
