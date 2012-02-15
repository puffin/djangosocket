#!/usr/bin/env python
from setuptools import setup, find_packages
from os.path import join, dirname

try:
    long_description = open(join(dirname(__file__), 'README.rst')).read()
except Exception:
    long_description = None

setup(
    name='django-socket',
    version='1.0',
    description='Django Socket Webserver.',
    author='David Michon',
    author_email='david.michon@gmail.com',
    url='https://github.com/puffin/django-socket',

    long_description=long_description,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ],

    packages = find_packages(),
    provides=['djangosocket'],
    include_package_data=True,
    zip_safe=True,
    requires=['Django(>=1.3)', 'eventlet(>=0.9)', 'numpy',],
)
