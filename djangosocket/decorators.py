from django.http import HttpResponse
from django.utils.decorators import decorator_from_middleware

from djangosocket.conf import settings
from djangosocket.middleware import DjangoSocketMiddleware

__all__ = ('accept_djangosocket', 'require_djangosocket')


def _setup_djangosocket(func):
    from functools import wraps
    @wraps(func)
    def new_func(request, *args, **kwargs):
        response = func(request, *args, **kwargs)
        if response is None and request.is_websocket():
            return HttpResponse()
        return response
    if not settings.DJANGOSOCKET_MIDDLEWARE_INSTALLED:
        decorator = decorator_from_middleware(DjangoSocketMiddleware)
        new_func = decorator(new_func)
    return new_func


def accept_djangosocket(func):
    func.accept_djangosocket = True
    func.require_djangosocket = getattr(func, 'require_djangosocket', False)
    func = _setup_djangosocket(func)
    return func


def require_djangosocket(func):
    func.accept_djangosocket = True
    func.require_djangosocket = True
    func = _setup_djangosocket(func)
    return func
