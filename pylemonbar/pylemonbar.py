#!/usr/bin/env python3

import subprocess
import time
import sys
import select
import os
import math
import struct

from pylemonbar.core import *
from pylemonbar.hlwm import *
from pylemonbar.widgets import *

def main(argv):
    # ---- configuration ---
    if len(argv) >= 2:
        monitor = int(argv[1])
    else:
        monitor = 0
    geometry = hc(['monitor_rect', str(monitor)]).split(' ')
    x = int(geometry[0])
    y = int(geometry[1])
    monitor_w = int(geometry[2])
    monitor_h = int(geometry[3])
    width = monitor_w
    height = 16

    bar = Lemonbar(geometry = (x,y,width,height))
    hc_idle = HLWMInput()

    # widgets
    #rofi = DropdownRofi(y+height,x,width)
    #
    #def session_menu(btn):
    #    rofi.spawn(['Switch User', 'Suspend', 'Logout'])
    #
    #session_button = Button('V')
    #session_button.callback = session_menu

    time_widget = DateTime()
    hlwm_windowtitle = HLWMWindowTitle(hc_idle)

    bar.widgets = [ RawLabel('%{l}'),
                HLWMTags(hc_idle, monitor),
                #Counter(),
                RawLabel('%{c}'),
                hlwm_windowtitle,
                RawLabel('%{r}'),
                time_widget,
    ]

    inputs = [ hc_idle,
               bar
             ]

    procwatch = [ ]

    def nice_theme(widget):
        widget.pad_left  = '%{-o}%{B#303030} '
        widget.pad_right = ' %{-o}%{B-}'

    nice_theme(hlwm_windowtitle)
    nice_theme(time_widget)

    global_update = True

    # main loop
    while bar.is_running():
        now = time.clock_gettime(time.CLOCK_MONOTONIC)
        for w in bar.widgets:
            if w.maybe_timeout(now):
                global_update = True
        if global_update:
            text = ''
            for w in bar.widgets:
                text += w.render()
            text += '\n'
            #print(text, end='')
            bar.write_flushed(text)
            global_update = False
        # wait for new data
        next_timeout = math.inf
        for w in bar.widgets:
            next_timeout = min(next_timeout, w.next_timeout())
        now = time.clock_gettime(time.CLOCK_MONOTONIC)
        next_timeout -= now
        next_timeout = max(next_timeout,0.1)
        #print("next timeout = " + str(next_timeout))
        if next_timeout != math.inf:
            ready = select.select(inputs,[],[], next_timeout)[0]
        else:
            ready = select.select(inputs,[],[], 18)[0]
        if not ready:
            pass #print('timeout!')
        else:
            for x in ready:
                x.process()
                global_update = True
    bar.proc.wait()

