"""
    Wirepas Gateway Client
    ======================

    Installation script

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0
        See file LICENSE for full license details.

"""
import codecs
import os
import re
import glob

from setuptools import setup, find_packages, Extension


with open('README.rst') as f:
    long_description = f.read()

with open('LICENSE') as f:
    license = f.read()


def filter(flist, rules=['private', '.out']):
    for f in flist:
        for rule in rules:
            if rule in f:
                flist.pop(flist.index(f))
    return flist


def get_list_files(root, flist=None):
    if flist is None:
        flist = list()

    for path, subdirs, files in os.walk(root):
        for name in files:
            flist.append(os.path.join(path, name))
    return flist


def get_absolute_path(*args):
    """ Transform relative pathnames into absolute pathnames """
    directory = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(directory, *args)


def get_requirements(*args):
    """ Get requirements requirements.txt """
    requirements = set()
    with open(get_absolute_path(*args)) as handle:
        for line in handle:
            # Strip comments.
            line = re.sub(r'^#.*|\s#.*', '', line)
            # Ignore empty lines
            if line and not line.isspace():
                requirements.add(re.sub(r'\s+', '', line))
    return sorted(requirements)

setup(
    name='wirepas_gateway',
    version='1.1.0',
    description='Wirepas gateway client',
    long_description=long_description,
    author='Wirepas Ltd',
    author_email='techsupport@wirepas.com',
    url='https://wirepas.com',
    license=license,
    classifiers=[
        'Development Status :: 5 - Stable',
        'Intended Audience :: Developers',
        'Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3',
    ],
    keywords='wirepas connectivity iot mesh',
    packages=find_packages(exclude=['contrib', 'docs', 'tests', 'examples']),
    install_requires=get_requirements('requirements.txt'),
    ext_modules=[Extension('dbusCExtension', sources=[
                           'wirepas_gateway/dbus/c-extension/dbus_c.c'],
                           libraries=['systemd'])],
    include_package_data=True,
    package_data={
        'wirepas_gateway':
        ['wirepas_gateway/wirepas_certs/extwirepas.pem']
    },
    data_files=[
        ('./wirepas_gateway-extras/package',
         ['LICENSE',
          'README.rst',
          'requirements.txt',
          'wirepas_gateway/wirepas_certs/extwirepas.pem',
          'setup.py'])],
    entry_points={
        'console_scripts': ['wm-gw=wirepas_gateway.transport_service:main',
                            'wm-dbus-print=wirepas_gateway.dbus_print_client:main']
    },
)
