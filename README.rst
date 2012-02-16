About
-----

Djangosocket is a Python Websocket plugin for Django webframework.

The Djangosocket is meant to be plugged behind a WSGI HTTP Server (Actually
the middleware and decorators are meant to be used with Gunicorn)


Installation
------------

Djangosocket requires **Python 2.x >= 2.6**.

Install from sources::

  $ python setup.py install

As Djangosocket expect that your application code may need to pause for extended
periods of time during request processing. Djangosocket depends on Eventlet for
non-blocking I/O.

To install eventlet::

    $ easy_install -U eventlet


Basic Usage
-----------

After installing Djangosocket you will have access to one middleware "DjangoSocketMiddleware" 
that you can install in your django settings file if you want project-wide websocket
handling.

Djangosocket add a websocket object to the django HTTPRequest that you can access in your view
by calling: request.websocket

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    ...
    ...
    'djangosocket.middleware.DjangoSocketMiddleware',
)

If your project mix standard Django views with websocket views, Djangosocket provides
two decorators for your views: "accept_djangosocket" and "require_djangosocket".

from djangosocket.decorator import require_djangosocket

@require_djangosocket
def your_view(request):
    request.websocket