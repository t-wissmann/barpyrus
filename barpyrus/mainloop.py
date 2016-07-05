#!/usr/bin/env python3

import subprocess
import time
import sys
import select
import os
import math
import signal
import struct

from barpyrus.core import *
from barpyrus.hlwm import *
from barpyrus.widgets import *
from barpyrus.conky import ConkyWidget
from barpyrus import lemonbar

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
    hc(['pad', str(monitor), str(height)])

    bar = lemonbar.Lemonbar(geometry = (x,y,width,height))
    hc_idle = HLWMInput()

    # widgets
    #rofi = DropdownRofi(y+height,x,width)
    #
    #def session_menu(btn):
    #    rofi.spawn(['Switch User', 'Suspend', 'Logout'])
    #
    #session_button = Button('V')
    #session_button.callback = session_menu

    def tag_renderer(self, painter): # self is a HLWMTagInfo object
        if self.empty:
            return
        painter.bg(self.emphbg if self.here else None)
        painter.set_flag(painter.overline, True if self.visible else False)
        painter.fg('#a0a0a0' if self.occupied else '#909090')
        if self.urgent:
            painter.bg('#eeD6156C')
            painter.set_flag(Painter.overline, False)
        if self.focused:
            painter.fg('#ffffff')
            painter.ol(self.activecolor)
        else:
            painter.ol('#454545')
        painter.space(4)
        if self.name == 'irc':
            #painter.symbol(0xe1ec)
            #painter.symbol(0xe1a1)
            painter.symbol(0xe1ef)
        elif self.name == 'vim':
            painter.symbol(0xe1cf)
        elif self.name == 'web':
            painter.symbol(0xe19c)
        elif self.name == 'mail':
            #painter.symbol(0xe1a8)
            painter.symbol(0xe071)
        elif self.name == 'scratchpad':
            painter.symbol(0xe022)
        elif self.name == '5':
            painter.symbol(0xe05c)
        else:
            painter += self.name
        painter.space(4)
        painter.bg()
        painter.ol()
        painter.set_flag(painter.overline, False)

    grey_frame = Theme(bg = '#303030', fg = '#EFEFEF', padding = (3,3))
    time_widget = DateTime()
    short_time = DateTime('%H:%M')
    hlwm_windowtitle = HLWMWindowTitle(hc_idle)
    xkblayouts = [
        'us us -variant altgr-intl us'.split(' '),
        'de de de'.split(' '),
    ]
    setxkbmap = 'setxkbmap -option compose:menu -option ctrl:nocaps'
    setxkbmap += ' -option compose:ralt -option compose:rctrl'

    kbdswitcher = HLWMLayoutSwitcher(hc_idle, xkblayouts, command = setxkbmap.split(' '))
    bar.widget = ListLayout([
                RawLabel('%{l}'),
                HLWMTags(hc_idle, monitor, tag_renderer = tag_renderer),
                #Counter(),
                RawLabel('%{c}'),
                HLWMMonitorFocusLayout(hc_idle, monitor,
                                       grey_frame(hlwm_windowtitle),
                                       ConkyWidget('df /: ${fs_used_perc /}%')
                                                ),
                RawLabel('%{r}'),
                ConkyWidget('${if_existing /sys/class/power_supply/BAT0}B: ${battery_percent} $endif'),
                ShortLongLayout(
                    grey_frame(short_time),
                    ListLayout([
                        kbdswitcher,
                        RawLabel(' '),
                        grey_frame(time_widget),
                    ])),
    ])

    inputs = [ hc_idle,
               bar
             ]

    def nice_theme(widget):
        #widget.pad_left  = '%{-o}%{B#303030} '
        #widget.pad_right = ' %{-o}%{B-}'
        pass

    nice_theme(hlwm_windowtitle)
    nice_theme(time_widget)
    nice_theme(short_time)
    #short_time.pad_left += '%{T1}%{F#9fbc00}\ue016%{T-}%{F-} '
    #time_widget.pad_left += '%{T1}%{F#9fbc00}\ue016%{T-}%{F-} '
    #kbdswitcher.pad_left += '%{B#303030}%{T1} %{F#9fbc00}\ue26f%{T-}%{F-}'
    def request_shutdown(args):
        quit_main_loop()
    hc_idle.enhook('quit_panel', request_shutdown)
    main_loop(bar, inputs)

def quit_main_loop():
    main_loop.shutdown_requested = True

def main_loop(bar, inputs):
    inputs += bar.widget.eventinputs()

    global_update = True
    main_loop.shutdown_requested = False
    def signal_quit(signal, frame):
        quit_main_loop()
    signal.signal(signal.SIGINT, signal_quit)
    signal.signal(signal.SIGTERM, signal_quit)

    # main loop
    while not main_loop.shutdown_requested and bar.is_running():
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
            if main_loop.shutdown_requested:
                break
        if not data_ready:
            pass #print('timeout!')
        else:
            for x in data_ready:
                x.process()
                global_update = True
    bar.proc.kill()
    for i in inputs:
        i.kill()
    bar.proc.wait()

