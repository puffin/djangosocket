# -*- coding: utf-8 -

from django.http import HttpResponseBadRequest

from gunicorn.workers.async import ALREADY_HANDLED

from djangosocket.conf import settings
from djangosocket.websocket import setup_djangosocket, MalformedWebSocket


class DjangoSocketMiddleware(object):
    """
    "Socket" middleware for taking care of some basic operations:

        - Append "websocket" object to Request
        
        - Ensure that the view is called accept websocket by settings
          DJANGOSOCKET_ACCEPT_ALL or decorating the view with accept_djangosocket
          decorator
         
        - Return Bad Request Response (400) if view require a websocket (require_djangosocket)
          and no websocket object exists in Request
         
        - If "websocket" exists in Request, return a an ALREADY_HANDLED object as
          response to prevent barf on the fact that socket doesn't call response
    """
    def process_request(self, request):
        """
        Append "websocket" object to Request if available, otherwise return
        a Bad Request Response (400)
        """
        try:
            request.websocket = setup_djangosocket(request)
            request.is_websocket = lambda: True
        except MalformedWebSocket, e:
            request.websocket = None
            request.is_websocket = lambda: False
            return HttpResponseBadRequest()

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Ensure that the view is called accept websocket by settings
        DJANGOSOCKET_ACCEPT_ALL or decorating the view with accept_djangosocket
        decorator
        """
        # open websocket if its an accepted request
        if request.is_websocket():
            # deny websocket request if view can't handle websocket
            if not settings.DJANGOSOCKET_ACCEPT_ALL and \
                not getattr(view_func, 'accept_djangosocket', False):
                return HttpResponseBadRequest()
            # everything is fine .. so prepare connection by sending handshake
            request.websocket.do_handshake()
        elif getattr(view_func, 'require_djangosocket', False):
            # websocket was required but not provided
            return HttpResponseBadRequest()

    def process_response(self, request, response):
        if request.is_websocket():
            return ALREADY_HANDLED