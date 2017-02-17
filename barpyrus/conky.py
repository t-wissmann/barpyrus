#!/usr/bin/env python3

import contextlib
import subprocess
import time
import sys
import select
import os
from barpyrus.widgets import RawLabel
from barpyrus.core import EventInput
from barpyrus.core import TextPainter

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

    def __init__(self, textpainter):
        self._painter = textpainter
        self._in_if = False
        self._cases = None

    def __str__(self):
        # conky treats '#' as comment indicators
        # we want each '#' to be treated literally
        return str(self._painter).replace('#', '\\#')

    @contextlib.contextmanager
    def if_(self, text):
        self._painter.drawRaw('${if_%s}' % text)
        self._in_if = True
        yield
        self._in_if = False
        self._painter.drawRaw('${endif}')

    def else_(self):
        if not self._in_if and self._cases is None:
            raise ValueError("else without if/cases!")
        self._painter.drawRaw('${else}')

    @contextlib.contextmanager
    def cases(self):
        if self._cases is not None:
            raise ValueError("Nesting cases is not supported!")
        self._cases = 0
        yield
        for _ in range(self._cases):
            self._painter.drawRaw('${endif}')
        self._cases = None

    def case(self, text):
        if self._cases is None:
            raise ValueError("Got case without cases!")
        if self._cases != 0:
            self._painter.drawRaw('${else}')
        self._painter.drawRaw('${if_%s}' % text)
        self._cases += 1

    def var(self, text):
        self._painter.drawRaw('${%s}' % text)

    def __iadd__(self,string):
        self._painter += string
        return self

    def __getattr__(self, name):
        return self._painter.__getattribute__(name)
