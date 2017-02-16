#!/usr/bin/env python3

import contextlib
import subprocess
import time
import sys
import select
import os
from barpyrus.widgets import RawLabel
from barpyrus.core import EventInput

class Conky(EventInput):
    def __init__(self, text='Conky $conky_version', config = { }, lua = ""):
        command = [ 'conky', '-c' , '-' ]
        super(Conky,self).__init__(command)
        default_config = {
            'out_to_console': 'true',
            'out_to_x': 'false',
            'update_interval': '20',
            'background': 'false',
            'default_bar_width': '5',
            'use_spacer': 'none',
        }
        for key,val in config.items():
            default_config[key] = val
        config_str = "conky.config = {\n"
        for key,val in default_config.items():
            config_str += "    %s = %s,\n" % (key,str(val))
        config_str += "};\n"
        config_str += lua + "\n"
        config_str += "conky.text = [[\n"
        config_str += text
        config_str += "\n]];\n"
        self.write_flushed(config_str);
        self.proc.stdin.close()

class ConkyWidget(RawLabel):
    def __init__(self, text='Conky $conky_version', config = { }, lua = ""):
        super(ConkyWidget,self).__init__("")
        self.conky = Conky(text=text, config=config, lua=lua)
        self.conky.callback = lambda line: self.update_label(line)
    def update_label(self, line):
        self.label = line
    def eventinputs(self):
        return [ self.conky ]

class ConkyGenerator:

    def __init__(self):
        self._text = ""
        self._in_if = False
        self._cases = None

    def __str__(self):
        return self._text

    @contextlib.contextmanager
    def if_(self, text):
        self._text += '${if_%s}' % text
        self._in_if = True
        yield
        self._in_if = False
        self._text += '$endif'

    def else_(self):
        if not self._in_if and self._cases is None:
            raise ValueError("else without if/cases!")
        self._text += '$else'

    @contextlib.contextmanager
    def cases(self):
        if self._cases is not None:
            raise ValueError("Nesting cases is not supported!")
        self._cases = 0
        yield
        for _ in range(self._cases):
            self._text += '$endif'
        self._cases = None

    def case(self, text):
        if self._cases is None:
            raise ValueError("Got case without cases!")
        if self._cases != 0:
            self._text += '$else'
        self._text += '${if_%s}' % text
        self._cases += 1

    def text(self, text):
        self._text += text

    def var(self, text):
        self._text += '${%s}' % text

    @contextlib.contextmanager
    def temp_fg(self, color):
        self.fg(color)
        yield
        self.fg(None)

    def fg(self, color):
        if color is None:
            self._text += '%{F-}'
        else:
            self._text += '%%{F\\#%x}' % color

    def symbol(self, ch):
        self._text += '%%{T2}%s%%{T-}' % chr(ch)

    def space(self):
        self._text += ' '
