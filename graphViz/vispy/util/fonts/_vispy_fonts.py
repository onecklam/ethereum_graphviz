# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2015, Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------

from ..fetching import load_data_file
import os
# List the vispy fonts made available online
_vispy_fonts = ('OpenSans', 'Cabin')


def _get_vispy_font_filename(face, bold, italic):
    """Fetch a remote vispy font"""
    name = face + '-'
    name += 'Regular' if not bold and not italic else ''
    name += 'Bold' if bold else ''
    name += 'Italic' if italic else ''
    name += '.ttf'
    currentDir = (os.path.split(os.path.realpath(__file__))[0])
    currentDir = currentDir.replace('wetapy\\util\\fonts','')
    #print (currentDir)
    return load_data_file('fonts/%s' % name,directory=currentDir)
