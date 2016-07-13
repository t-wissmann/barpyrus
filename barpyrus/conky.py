#!/usr/bin/env python3

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

