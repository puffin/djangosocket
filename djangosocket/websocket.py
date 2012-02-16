# -*- coding: utf-8 -

class MalformedWebSocket(ValueError):
    pass
    
    
def setup_djangosocket(request):
    """
    Helper function that return a websocket object based on the protocol
    used by the client. Actually support:
    
    - hixie76 protocol (Safari 5+)
    - hybi protocol (Chrome 13+)
    """
    
    if request.META.get('HTTP_CONNECTION', '').lower() == 'upgrade' and \
        request.META.get('HTTP_UPGRADE', '').lower() == 'websocket':
        
        socket = request.META['gunicorn.socket']
        try:
            ver = request.META.get('HTTP_SEC_WEBSOCKET_VERSION')
            
            if ver:
                from djangosocket.stream.hybi import WebSocket
            else:
                from djangosocket.stream.hixie76 import WebSocket
            
            ws = WebSocket(request, socket)
            return ws
        except Exception, e:
            print e
    return []