"""
    Wirepas Gateway Client
    ======================

    Installation script

    .. Copyright:
        Wirepas Oy licensed under Apache License, Version 2.0
        See file LICENSE for full license details.

"""

import os
import re

import wirepas_gateway
from setuptools import setup, find_packages, Extension

readme_file = "README.md"
license_file = "LICENSE"

with open(readme_file) as f:
    long_description = f.read()


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
            line = re.sub(r"^#.*|\s#.*", "", line)
            # Ignore empty lines
            if line and not line.isspace():
                requirements.add(re.sub(r"\s+", "", line))
    return sorted(requirements)


setup(
    name=wirepas_gateway.__name__,
    version=wirepas_gateway.__version__,
    description=wirepas_gateway.__description__,
    long_description=long_description,
    author=wirepas_gateway.__author__,
    author_email=wirepas_gateway.__author_email__,
    url=wirepas_gateway.__url__,
    license=wirepas_gateway.__license__,
    classifiers=wirepas_gateway.__classifiers__,
    keywords=wirepas_gateway.__keywords__,
    packages=find_packages(exclude=["contrib", "docs", "tests", "examples"]),
    install_requires=get_requirements("requirements.txt"),
    ext_modules=[
        Extension(
            "dbusCExtension",
            sources=["wirepas_gateway/dbus/c-extension/dbus_c.c"],
            libraries=["systemd"],
        )
    ],
    include_package_data=True,
    package_data={"wirepas_gateway": ["wirepas_gateway/wirepas_certs/extwirepas.pem"]},
    data_files=[
        (
            "./wirepas_gateway-extras/package",
            [
                readme_file,
                license_file,
                "requirements.txt",
                "wirepas_gateway/wirepas_certs/extwirepas.pem",
                "setup.py",
            ],
        )
    ],
    entry_points={
        "console_scripts": [
            "wm-gw=wirepas_gateway.transport_service:main",
            "wm-dbus-print=wirepas_gateway.dbus_print_client:main",
        ]
    },
)
