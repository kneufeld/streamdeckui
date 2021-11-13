# -*- coding: utf-8 -*-

import os
from setuptools import setup

base_dir = os.path.dirname(os.path.abspath(__file__))
pkg_name = 'streamdeckui'

# adapted from: http://code.activestate.com/recipes/82234-importing-a-dynamically-generated-module/
# adapted from: https://newbedev.com/python-dynamically-import-module-s-code-from-string-with-importlib
def pseudo_import(pkg_name):
    """
    return a new module that contains the variables of pkg_name.__init__
    """
    init = os.path.join( pkg_name, '__init__.py' )

    # only keep lines that start with '__'. eg. __title__ = 'foo'
    lines = open(init, 'r').readlines()
    lines = filter(lambda l: l.startswith('__'), lines)
    lines = '\n'.join(lines)

    import types
    module = types.ModuleType(pkg_name)

    exec(lines, module.__dict__)
    return module

# trying to make this setup.py as generic as possible
module = pseudo_import(pkg_name)

setup(
    name = pkg_name,
    packages = [pkg_name],

    # I think pep deprecated dependency_links
    # dependency_links = []

    install_requires = [
        'streamdeck',
        'pillow',
        'blinker-async',
        # https://github.com/gomymove/blinker has code examples for async
        # jek/blinker is the official version of blinker and
        # the latest version has async support but not in pypi yet
        # 'blinker @ git+https://github.com/jek/blinker.git@b5e9f0629200d2b2f62e13e595b802948bb4fefb#egg=blinker',
    ],

    extras_require = {},

    include_package_data = True,

    # metadata for upload to PyPI
    description      = "gui framework for an elgato stream deck",
    long_description = __doc__,
    version          = module.__version__,
    author           = module.__author__,
    author_email     = module.__author_email__,
    license          = module.__license__,
    keywords         = "streamdeck ui gui".split(),
    url              = module.__url__,

    # https://pypi.org/classifiers/
    classifiers      = [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Hardware",
        "Topic :: System :: Hardware :: Universal Serial Bus (USB) :: Human Interface Device (HID)",
        ],

    data_files       = [],
)
