#!/usr/bin/env python
# -*- coding: utf-8 -*-
# setup.py
from distutils.core import setup
import py2exe

setup(
    options={
        "py2exe": {
            "compressed": 1,
            "optimize": 2,
            # "ascii": 1,
            "bundle_files": 1
        }
    },
    windows=['copyer.py'],
    # console=['copyer.py'],
    zipfile = None
)
