# -*- coding: utf-8 -

"""
WebSocket protocol with the framing used by Hixie 76.
"""

import re
import logging
import struct
import string
from base64 import b64encode, b64decode
import array

try:
    import numpy
except:
    pass

try:
    from hashlib import sha1
except:
    from sha import sha as sha1

from djangosocket.stream import const
from djangosocket.stream.base import BadOperationException
from djangosocket.stream.base import ConnectionTerminatedException
from djangosocket.stream.base import InvalidFrameException
from djangosocket.stream.base import UnsupportedFrameException
from djangosocket.stream.base import UnsupportedProtocolException
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
        self._version = const.VERSION_HYBI_LATEST
        self.recv_part = ''
        
        protocols = self._protocol.split(',')
        if 'binary' in protocols:
            self.base64 = False
        else:
            self.base64 = True
        
    def gen_challenge(self):
        """
        Generate hash value for WebSockets hybi.
        """
        
        key = self._request.META.get('HTTP_SEC_WEBSOCKET_KEY', None)
        
        challenge = sha1()
        challenge.update(key + const.WEBSOCKET_ACCEPT_UUID)
        return b64encode(challenge.digest())
    
    def _send_handshake(self):
        
        handshake_parts = []
        handshake_parts.append('HTTP/1.1 101 Switching Protocols\r\n')
        handshake_parts.append('%s: %s\r\n' %(const.UPGRADE_HEADER, const.WEBSOCKET_UPGRADE_TYPE))
        handshake_parts.append('%s: %s\r\n' % (const.CONNECTION_HEADER, const.UPGRADE_CONNECTION_TYPE))
        handshake_parts.append('%s: %s\r\n' % (const.SEC_WEBSOCKET_ORIGIN_HEADER, self._origin))
        handshake_parts.append('%s: %s\r\n' % (const.SEC_WEBSOCKET_LOCATION_HEADER, self._location))
        handshake_parts.append('%s: %s\r\n' % (const.SEC_WEBSOCKET_PROTOCOL_HEADER, self._protocol))
        handshake_parts.append('%s: %s\r\n' % (const.SEC_WEBSOCKET_ACCEPT_HEADER, self.gen_challenge()))
        handshake_parts.append('\r\n')
        handshake_reply = str(''.join(handshake_parts))
        
        self._write(handshake_reply)
    
    def _send_closing_handshake(self):
        self.closed = True

        # 5.3 the server may decide to terminate the WebSocket connection by
        # running through the following steps:
        # 1. send a 0xFF byte and a 0x00 byte to the client to indicate the
        # start of the closing handshake.
        buf, h, t = self.encode_hybi('', opcode=0x08)
        self._write(buf)
    
    @staticmethod
    def unmask(buf, f):
        s2a = lambda s: [ord(c) for c in s]
        s2b = lambda s: s
        
        pstart = f['hlen'] + 4
        pend = pstart + f['length']
        
        if numpy:
            b = c = s2b('')
            if f['length'] >= 4:
                mask = numpy.frombuffer(buf, dtype=numpy.dtype('<u4'),
                        offset=f['hlen'], count=1)
                data = numpy.frombuffer(buf, dtype=numpy.dtype('<u4'),
                        offset=pstart, count=int(f['length'] / 4))
                b = numpy.bitwise_xor(data, mask).tostring()

            if f['length'] % 4:
                mask = numpy.frombuffer(buf, dtype=numpy.dtype('B'),
                        offset=f['hlen'], count=(f['length'] % 4))
                data = numpy.frombuffer(buf, dtype=numpy.dtype('B'),
                        offset=pend - (f['length'] % 4),
                        count=(f['length'] % 4))
                c = numpy.bitwise_xor(data, mask).tostring()
            return b + c
        else:
            data = array.array('B')
            mask = s2a(f['mask'])
        
            data.fromstring(buf[pstart:pend])
            for i in range(len(data)):
                data[i] ^= mask[i % 4]
            return data.tostring()
    
    @staticmethod
    def encode_hybi(buf, opcode):
        """
        Encode a HyBi style WebSocket frame.
        Optional opcode:
            0x0 - continuation
            0x1 - text frame (base64 encode buf)
            0x2 - binary frame (use raw buf)
            0x8 - connection close
            0x9 - ping
            0xA - pong
        """
        
        b1 = 0x80 | (opcode & 0x0f) # FIN + opcode
        payload_len = len(buf)
        if payload_len <= 125:
            header = struct.pack('>BB', b1, payload_len)
        elif payload_len > 125 and payload_len < 65536:
            header = struct.pack('>BBH', b1, 126, payload_len)
        elif payload_len >= 65536:
            header = struct.pack('>BBQ', b1, 127, payload_len)

        return header + buf, len(header), 0
    
    @staticmethod
    def decode_hybi(buf):
        """
        Decode HyBi style WebSocket packets.
        
        Returns:
            {'fin'          : 0_or_1,
             'opcode'       : number,
             'mask'         : 32_bit_number,
             'hlen'         : header_bytes_number,
             'length'       : payload_bytes_number,
             'payload'      : decoded_buffer,
             'left'         : bytes_left_number,
             'close_code'   : number,
             'close_reason' : string}
        """

        f = {'fin'          : 0,
             'opcode'       : 0,
             'mask'         : 0,
             'hlen'         : 2,
             'length'       : 0,
             'payload'      : None,
             'left'         : 0,
             'close_code'   : None,
             'close_reason' : None}

        blen = len(buf)
        f['left'] = blen

        if blen < f['hlen']:
            return f # Incomplete frame header
        
        b1, b2 = struct.unpack_from(">BB", buf)
        f['opcode'] = b1 & 0x0f
        f['fin'] = (b1 & 0x80) >> 7
        has_mask = (b2 & 0x80) >> 7
        
        f['length'] = b2 & 0x7f
        
        if f['length'] == 126:
            f['hlen'] = 4
            if blen < f['hlen']:
                return f # Incomplete frame header
            (f['length'],) = struct.unpack_from('>xxH', buf)
        elif f['length'] == 127:
            f['hlen'] = 10
            if blen < f['hlen']:
                return f # Incomplete frame header
            (f['length'],) = struct.unpack_from('>xxQ', buf)

        full_len = f['hlen'] + has_mask * 4 + f['length']

        if blen < full_len: # Incomplete frame
            return f # Incomplete frame header

        # Number of bytes that are part of the next frame(s)
        f['left'] = blen - full_len

        # Process 1 frame
        if has_mask:
            # unmask payload
            f['mask'] = buf[f['hlen']:f['hlen']+4]
            f['payload'] = WebSocket.unmask(buf, f)
        else:
            print("Unmasked frame: %s" % repr(buf))
            f['payload'] = buf[(f['hlen'] + has_mask * 4):full_len]
        
        if f['opcode'] == 0x08:
            if f['length'] >= 2:
                f['close_code'] = struct.unpack_from(">H", f['payload'])
            if f['length'] > 3:
                f['close_reason'] = f['payload'][2:]

        return f
    
    def send(self, message):
        """
        Send message.

        message: unicode string to send.

        Raises BadOperationException when called on a server-terminated
        connection.
        """
        
        if self.closed:
            raise BadOperationException(
                'Requested send after sending out a closing handshake')
        
        if self.base64:
            encbuf, lenhead, lentail = self.encode_hybi(message, opcode=1)
        else:
            encbuf, lenhead, lentail = self.encode_hybi(message, opcode=2)
        
        self._write(encbuf)

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
        buf = self._buffer
        
        while buf:
            
            try:
                frame = self.decode_hybi(buf)
            except Exception, e:
                print e
            
            if frame['payload'] == None:
                # Incomplete/partial frame
                if frame['left'] > 0:
                    break;
            elif frame['opcode'] == 0x8: # connection close
                self._logger.debug('Received client-initiated closing handshake')
                break
            else:
                msgs.append(frame['payload'])
            
            if frame['left']:
                buf = buf[-frame['left']:]
            else:
                buf = ''
                
        self._buffer = buf
        return msgs
