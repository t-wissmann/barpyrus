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

from barpyrus.core import *
from barpyrus.hlwm import *
from barpyrus.widgets import *
from barpyrus.conky import ConkyWidget
from barpyrus import lemonbar

def get_config(filepath):
    with open(filepath) as f:
        code = compile(f.read(), filepath, 'exec')
        exec(code, global_vars, local_vars)

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
    if int(hc(['get', 'smart_frame_surroundings'])) == 0:
        frame_gap = int(hc(['get', 'frame_gap']))
        x += frame_gap
        width -= 2 * frame_gap

    bar = lemonbar.Lemonbar(geometry = (x,y,width,height))
    hc_idle = HLWMInput()
    # import all locales
    locale.setlocale(locale.LC_ALL, '')

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
        #painter.ol('#ffffff' if self.focused else None)
        painter.set_flag(painter.underline, True if self.visible else False)
        painter.fg('#a0a0a0' if self.occupied else '#909090')
        if self.urgent:
            painter.ol('#FF7F27')
            painter.fg('#FF7F27')
            painter.set_flag(Painter.underline, True)
            painter.bg('#57000F')
        elif self.here:
            painter.fg('#ffffff')
            painter.ol(self.activecolor if self.focused else '#ffffff')
            painter.bg(self.emphbg)
        else:
            painter.ol('#454545')
        painter.space(3)
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
        painter.space(3)
        painter.bg()
        painter.ol()
        painter.set_flag(painter.underline, False)
        painter.space(2)

    bat_icons = [
        0xe242, 0xe243, 0xe244, 0xe245, 0xe246,
        0xe247, 0xe248, 0xe249, 0xe24a, 0xe24b,
    ]
    # first icon: 0 percent
    # last icon: 100 percent
    bat_delta = 100 / len(bat_icons)
    conky_text = "${if_existing /sys/class/power_supply/BAT0}"
    conky_text += "%{T2}"
    conky_text += "${if_match \"$battery\" == \"discharging $battery_percent%\"}"
    conky_text += "%{F\\#FFC726}"
    conky_text += "$else"
    conky_text += "%{F\\#9fbc00}"
    conky_text += "$endif"
    for i,icon in enumerate(bat_icons[:-1]):
        conky_text += "${if_match $battery_percent < %d}" % ((i+1)*bat_delta)
        conky_text += chr(icon)
        conky_text += "${else}"
    conky_text += chr(bat_icons[-1]) # icon for 100 percent
    for _ in bat_icons[:-1]:
        conky_text += "${endif}"
    conky_text += "%{T-} $battery_percent% "
    conky_text += "${endif}"
    conky_text += "%{F-}"
    print(conky_text)

    grey_frame = Theme(bg = '#303030', fg = '#EFEFEF', padding = (3,3))
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
                ConkyWidget(text= conky_text),
                ShortLongLayout(
                    RawLabel(''),
                    ListLayout([
                        kbdswitcher,
                        RawLabel(' '),
                    ])),
                    grey_frame(DateTime('%d. %B, %H:%M')),
    ])

    inputs = [ hc_idle,
               bar
             ]

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

