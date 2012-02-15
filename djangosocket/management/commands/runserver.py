# -*- coding: utf-8 -

from django.core.management.commands.runserver import Command as _Runserver
from optparse import make_option

class Command(_Runserver):
    
    option_list = _Runserver.option_list + (
        make_option('--multithreaded', action='store_true', dest='multithreaded', default=False,
        help='Run development server with support for concurrent requests.'),
    )
    
    def run(self, *args, **options):
        multithreaded = options.get('multithreaded')
        
        if multithreaded:
            import eventlet
            eventlet.monkey_patch(os=False)
            from eventlet import wsgi
            
            handler = self.get_handler(*args, **options)
            wsgi.server(eventlet.listen((self.addr, int(self.port))), handler)
        else:
            super(Command, self).run(*args, **options)