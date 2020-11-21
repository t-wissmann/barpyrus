#!/usr/bin/env python3

import subprocess
import time
import sys
import select
import os
import math
import signal
import struct
import locale
import os

from barpyrus.core import *
from barpyrus import hlwm
from barpyrus.widgets import *
from barpyrus.conky import ConkyWidget
from barpyrus import lemonbar

def get_config(filepath):
    global_vars = {}
    with open(filepath) as f:
        code = compile(f.read(), filepath, 'exec')
        exec(code, global_vars)
    return global_vars

def user_config_path():
    if 'BARPYRUS_CONFIG' in os.environ:
        return os.environ['BARPYRUS_CONFIG']
    if 'XDG_CONFIG_DIR' in os.environ:
        path = os.environ['XDG_CONFIG_DIR']
    elif 'HOME' in os.environ:
        path = os.path.join(os.environ['HOME'], '.config')
    else:
        path = '.'
    return os.path.join(path, 'barpyrus', 'config.py')

def get_user_config():
    return get_config(user_config_path())

def main():
    # import all locales
    locale.setlocale(locale.LC_ALL, '')
    # ---- configuration ---
    conf = get_user_config()
    bar = conf['bar']
    main_loop(bar)

def main_loop(bar, inputs = None):
    # TODO: remove eventinputs again?
    #inputs += bar.widget.eventinputs()
    if inputs == None:
        inputs = global_inputs

    global_update = True
    def signal_quit(signal, frame):
        quit_main_loop()
    signal.signal(signal.SIGINT, signal_quit)
    signal.signal(signal.SIGTERM, signal_quit)

    # main loop
    while not core.shutdown_requested() and bar.is_running():
        now = time.clock_gettime(time.CLOCK_MONOTONIC)
        if bar.widget.maybe_timeout(now):
            global_update = True
        data_ready = []
        if global_update:
            painter = bar.painter()
            painter.widget(bar.widget)
            data_ready = select.select(inputs,[],[], 0.00)[0]
            if not data_ready:
                #print("REDRAW: " + str(time.clock_gettime(time.CLOCK_MONOTONIC)))
                painter.flush()
                global_update = False
            else:
                pass
                #print("more data already ready")
        if not data_ready:
            # wait for new data
            next_timeout = now + 360 # wait for at most one hour until the next bar update
            to = bar.widget.next_timeout()
            if to != None:
                next_timeout = min(next_timeout, to)
            now = time.clock_gettime(time.CLOCK_MONOTONIC)
            next_timeout -= now
            next_timeout = max(next_timeout,0.1)
            #print("next timeout = " + str(next_timeout))
            data_ready = select.select(inputs,[],[], next_timeout)[0]
            if core.shutdown_requested():
                break
        if not data_ready:
            pass #print('timeout!')
        else:
            for x in data_ready:
                try:
                    x.process()
                    global_update = True
                except EOFError:
                    print(f"Received EOF from {x}", file=sys.stderr)
                    quit_main_loop()
                    break
    bar.proc.kill()
    for i in inputs:
        i.kill()
    bar.proc.wait()

