#! python
# -*- coding: UTF-8 -*-
#
# Copyright 2015-2017 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

import sys
import unittest

import transitions

import os.path as osp


mydir = osp.dirname(__file__)
proj_path = osp.join(mydir, '..')
readme_path = osp.join(proj_path, 'README.md')


@unittest.skipIf(sys.version_info < (3, ),
                 "fopen(encoding) unsupported, besides, 1 python is enough.")
class VersionTest(unittest.TestCase):

    def _check_text_in_README_opening(self, text):
        header_len = 20
        mydir = osp.dirname(__file__)
        with open(readme_path, encoding='utf-8') as fd:
            for i, l in enumerate(fd):
                if text in l:
                    break
                elif i >= header_len:
                    msg = "%s not found in README %s header-lines!"
                    raise AssertionError(msg % (text, header_len))

    def test_README_version(self):
        self._check_text_in_README_opening(transitions.__version__)

    def test_README_updated(self):
        self._check_text_in_README_opening(transitions.__updated__)
