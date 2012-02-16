# -*- coding: utf-8 -

"""
WebSocket protocol with the framing used by Hixie 76 protocol.
"""

import re
import logging
import struct
import string
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

from djangosocket.stream import const
from djangosocket.stream.base import BadOperationException
from djangosocket.stream.base import ConnectionTerminatedException
from djangosocket.stream.base import InvalidFrameException
from djangosocket.stream.base import UnsupportedFrameException
from djangosocket.stream.base import StreamBase
from djangosocket.stream.base import HandshakeException
from djangosocket.stream.base import build_location


class WebSocket(StreamBase):
    """
    This class performs WebSocket handshake for Hixie76 protocol.
    """
    
    def __init__(self, request, socket):
        """
        Construct an instance of WebSocket.

        request: django request.
        socket: django request websocket object.
        """
        super(WebSocket, self).__init__(socket)
        
        self._logger = logging.getLogger('djangosocket.websocket')
        self._request = request
        self._origin = request.META.get('HTTP_ORIGIN', '')
        self._location = build_location(request)
        self._protocol = request.META.get('HTTP_SEC_WEBSOCKET_PROTOCOL', 'default')
        self._version = const.VERSION_HIXIE76
    
    def gen_challenge(self):
        """
        Generate hash value for WebSockets hixie-76.
        """
        
        def _get_key_value(value):
            """
            Utility function which, given a string like 'g98sd  5[]221@1', will
            return 9852211. Used to parse the Sec-WebSocket-Key headers.
            """
            out = ""
            spaces = 0
            for char in value:
                if char in string.digits:
                    out += char
                elif char == " ":
                    spaces += 1
            return int(out) / spaces
        
        key1 = self._request.META.get('HTTP_SEC_WEBSOCKET_KEY1', None)
        key2 = self._request.META.get('HTTP_SEC_WEBSOCKET_KEY2', None)
        key3 = self._request.META['wsgi.input'].read()
        
        return md5(struct.pack(">II", _get_key_value(key1), _get_key_value(key2)) + key3).digest()
    
    def _send_handshake(self):
        
        handshake_parts = []
        handshake_parts.append('HTTP/1.1 101 Web Socket Protocol Handshake\r\n')
        handshake_parts.append('%s: %s\r\n' %(const.UPGRADE_HEADER, const.WEBSOCKET_UPGRADE_TYPE_HIXIE76))
        handshake_parts.append('%s: %s\r\n' % (const.CONNECTION_HEADER, const.UPGRADE_CONNECTION_TYPE))
        handshake_parts.append('%s: %s\r\n' % (const.SEC_WEBSOCKET_ORIGIN_HEADER, self._origin))
        handshake_parts.append('%s: %s\r\n' % (const.SEC_WEBSOCKET_LOCATION_HEADER, self._location))
        handshake_parts.append('%s: %s\r\n' % (const.SEC_WEBSOCKET_PROTOCOL_HEADER, self._protocol))
        handshake_parts.append('\r\n')
        handshake_reply = str(''.join(handshake_parts)) + self.gen_challenge()
        
        self._write(handshake_reply)
    
    def _send_closing_handshake(self):
        self.closed = True

        # 5.3 the server may decide to terminate the WebSocket connection by
        # running through the following steps:
        # 1. send a 0xFF byte and a 0x00 byte to the client to indicate the
        # start of the closing handshake.
        self._write('\xff\x00')
    
    def send(self, message):
        """
        Send message.

        message: unicode string to send.

        Raises BadOperationException when called on a server-terminated
        connection.
        """

        if self.closed:
            raise BadOperationException('Requested send after sending out a closing handshake')

        if isinstance(message, unicode):
            message = message.encode('utf-8')
        elif not isinstance(message, str): # Message for binary frame must be instance of str
            message = str(message)

        self._write(''.join(['\x00', message, '\xff']))

    def _parse_message_queue(self):
        """
        Parses for messages in the buffer *buf*.  It is assumed that
        the buffer contains the start character for a message, but that it
        may contain only part of the rest of the message.

        Returns an array of messages, and the buffer remainder that
        didn't contain any full messages.
        """

        if self.closed:
            raise BadOperationException(
                'Requested receive_message after receiving a closing '
                'handshake')

        msgs = []
        end_idx = 0
        buf = self._buffer
        while buf:
            frame_type = ord(buf[0])
            if frame_type == 0:
                # Normal message.
                end_idx = buf.find("\xFF")
                if end_idx == -1: #pragma NO COVER
                    break
                msgs.append(buf[1:end_idx].decode('utf-8', 'replace'))
                buf = buf[end_idx+1:]
            elif frame_type == 255:
                # Closing handshake.
                assert ord(buf[1]) == 0, "Unexpected closing handshake: %r" % buf
                self._logger.debug('Received client-initiated closing handshake')
                self._send_closing_handshake()
                self._logger.debug('Sent ack for client-initiated closing handshake')
                break
            else:
                raise ValueError("Don't understand how to parse this type of message: %r" % buf)
        self._buffer = buf
        return msgs
        