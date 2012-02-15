def setup_djangosocket(request):
    
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