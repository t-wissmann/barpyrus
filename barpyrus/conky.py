#!/usr/bin/env python3

import subprocess
import time
import sys
import select
import os
from barpyrus.widgets import RawLabel
from barpyrus.core import EventInput

class Conky(EventInput):
    def __init__(self, text='Conky $conky_version'):
        command = [ 'conky', '-c' , '-' ]
        super(Conky,self).__init__(command)
        config = """
conky.config = {
    out_to_console = true,
    out_to_x = false,
    update_interval = 20,
    background = false,
    default_bar_width = 5,
};

conky.text = [[
%s
]];
""" % text
        self.write_flushed(config);
        self.proc.stdin.close()

class ConkyWidget(RawLabel):
    def __init__(self, text='Conky $conky_version'):
        super(ConkyWidget,self).__init__("")
        self.conky = Conky(text=text)
        self.conky.callback = lambda line: self.update_label(line)
    def update_label(self, line):
        self.label = line
    def eventinputs(self):
        return [ self.conky ]

