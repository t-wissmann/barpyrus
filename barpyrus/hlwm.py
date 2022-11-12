#!/usr/bin/env python3

import subprocess
import time
import sys
import select
import os
import math
import struct

from barpyrus.widgets import Widget
from barpyrus.widgets import Label
from barpyrus.widgets import Button
from barpyrus.widgets import Switcher
from barpyrus.widgets import StackedLayout
from barpyrus.core import EventInput
from barpyrus.core import Painter
from barpyrus.core import quit_main_loop
from barpyrus.colors import (
    PURPLE_DARK,
    GREEN_DARK,
    ORANGE_LIGHT,
    RED_DARK,
    FG,
    FG2,
    FG4,
    BG,
    BG2,
)

class HLWMInput(EventInput):
    def __init__(self):
        cmd = [ 'herbstclient', '--idle' ]
        self.hooks = { }
        super(HLWMInput,self).__init__(cmd)
        self.enhook('quit_panel', lambda args: quit_main_loop())
        self.enhook('reload', lambda args: quit_main_loop())
    def enhook(self,name,callback):
        self.hooks.setdefault(name,[]).append(callback)
    def handle_line(self,line):
        args = line.split('\t')
        if len(args) == 0:
            return
        if args[0] in self.hooks:
            for cb in self.hooks[args[0]]:
                cb(args[1:])

    def __call__(self, args, check=True):
        cmd = [ "herbstclient", "-n" ]
        cmd += args;
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        exit_code = proc.wait()
        stdout = proc.stdout.read().decode()
        if check:
            assert exit_code == 0, \
                f'Error: command {args} exited with non-success code {exit_code} (and stdout "{stdout}")'
        return stdout

    def monitor_rect(hc, monitor=None):
        if monitor == None:
            if len(sys.argv) >= 2:
                monitor = int(sys.argv[1])
            else:
                monitor = 0
        geometry = hc(['monitor_rect', str(monitor)]).split(' ')
        x = int(geometry[0])
        y = int(geometry[1])
        monitor_w = int(geometry[2])
        monitor_h = int(geometry[3])
        return (x,y, monitor_w, monitor_h)

def connect():
    return HLWMInput()

def underlined_tags(self, painter): # self is a HLWMTagInfo object
    if self.empty:
        return
    #painter.ol('#ffffff' if self.focused else None)
    painter.set_flag(painter.underline, True if self.visible else False)
    painter.fg(FG2 if self.occupied else FG4)
    if self.urgent:
        painter.ol(ORANGE_LIGHT)
        painter.fg(ORANGE_LIGHT)
        painter.set_flag(Painter.underline, True)
        painter.bg(RED_DARK)
    elif self.here:
        painter.fg(FG)
        painter.ol(self.activecolor if self.focused else FG)
        painter.bg(self.emphbg)
    else:
        painter.ol(BG2)
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
    elif self.name == 'music':
        painter.symbol(0xe05c)
    else:
        painter += self.name
    painter.space(3)
    painter.bg()
    painter.ol()
    painter.set_flag(painter.underline, False)
    painter.space(2)

class HLWMTagInfo:
    def __init__(self):
        self.name = '?'
        self.occupied = True
        self.focused = False
        self.here = False
        self.urgent = False
        self.visible = True
        self.empty = False
        self.activecolor = GREEN_DARK
        self.emphbg = BG
        self.index = 0
    def parse(self, string, index): # parse a tag_status string
        self.name = string[1:]
        self.parse_char(string[0])
        self.index = index
    def parse_char(self,ch): # parse a tag_status char
        self.occupied = True
        self.focused = False
        self.here = False
        self.urgent = False
        self.visible = True
        self.empty = False
        if ch == '.':
            self.occupied = False
            self.visible = False
            self.empty = True
        elif ch == '#':
            self.focused = True
            self.here = True
        elif ch == '%':
            self.focused = True
        elif ch == '+':
            self.here = True
        elif ch == '!':
            self.urgent = True
        elif ch == ':':
            self.visible = False
        elif ch == '-':
            pass
        else:
            print("Unknown hlwm tag modifier >%s<" % ch)

    def render(self, painter):
        if self.empty:
            return
        painter.bg(self.emphbg if self.here else None)
        painter.set_flag(painter.overline, True if self.visible else False)
        painter.fg(None if self.occupied else FG4)
        if self.urgent:
            painter.fg(FG)
            painter.bg(PURPLE_DARK)
            painter.set_flag(Painter.overline, False)
        if self.focused:
            painter.fg(FG)
            painter.ol(self.activecolor)
        else:
            painter.ol(BG2)
        painter.space(4)
        painter += self.name
        painter.space(4)
        painter.bg()
        painter.ol()
        painter.set_flag(painter.overline, False)

class HLWMTags(Widget):
    def __init__(self,hlwm,monitor, tag_renderer = None):
        super(HLWMTags,self).__init__()
        self.hc = hlwm
        self.needs_update = True
        self.tags = [ ]
        self.tag_info = [ ]
        self.tag_count = 0
        self.buttons = [4, 5]
        self.tag_renderer = tag_renderer
        self.monitor = monitor
        self.activecolor = hlwm('attr theme.tiling.active.color'.split(' '))
        self.emphbg = GREEN_DARK
        self.update_tags()
        for event in ['tag_changed', 'tag_flags', 'tag_added', 'tag_removed', 'tag_renamed']:
            hlwm.enhook(event, self.update_tags)

    def update_tags(self, args = None):
        strlist = self.hc(['tag_status', str(self.monitor)]).strip('\t').split('\t')
        # remove buttons if tags have been deleted
        if len(strlist) < self.tag_count:
            del self.tags[len(strlist):]
            del self.subwidgets[len(strlist):]
            del self.tag_info[len(strlist):]
        self.tag_count = len(strlist)
        # enlarge the tag button array
        for i in range(len(self.tags),len(strlist)):
            btn = Button('')
            btn.callback = (lambda j: lambda b: self.tag_clicked(j, b))(i)
            tag_info = HLWMTagInfo()
            if self.tag_renderer:
                btn.pre_render = (lambda t: lambda p: self.tag_renderer(t,p))(tag_info)
            else:
                btn.pre_render = tag_info.render
            self.tags.append(btn)
            self.subwidgets.append(btn)
            self.tag_info.append(tag_info)
        # update names and formatting
        for i in range(0, self.tag_count):
            self.tag_info[i].parse(strlist[i], i)
        self.needs_update = False
    def tag_clicked(self,tagindex,button):
        cmd = 'chain , focus_monitor %s , use_index %s' % (str(self.monitor),str(tagindex))
        cmd = cmd.split(' ')
        #print(cmd)
        self.hc(cmd)
    def render(self,painter):
        for t in self.tags:
            painter.widget(t)
    def can_handle_input(self, click_id, btn):
        if super(HLWMTags,self).can_handle_input(click_id,btn):
            return True
        else:
            for t in self.tags:
                if t.can_handle_input(click_id,btn):
                    return True
            return False
        return False
    def on_click(self, b):
        cmd = 'chain , focus_monitor %s , use_index %+d --skip-visible'
        if b == 4:
            delta = -1
        else:
            delta = +1
        cmd = (cmd % (str(self.monitor),delta)).split(' ')
        self.hc(cmd)

class HLWMWindowTitle(Label):
    def __init__(self, hlwm, maxlen = -1):
        self.windowtitle = hlwm(['attr', 'clients.focus.title'], check=False)
        self.maxlen = maxlen
        super(HLWMWindowTitle,self).__init__('')
        self.buttons = [4 , 5]
        self.reset_label()
        hlwm.enhook('focus_changed', (lambda a: self.newtitle(a)))
        hlwm.enhook('window_title_changed', (lambda a: self.newtitle(a)))
    def newtitle(self,args):
        self.windowtitle = args[1] if len(args) >= 2 else ''
        self.reset_label()
    def reset_label(self):
        if self.maxlen < 0 or len(self.windowtitle) <= self.maxlen:
            self.label = self.windowtitle
        else:
            self.label = self.windowtitle[:self.maxlen-1] + '…'
    def on_click(self, b):
        if self.maxlen > len(self.windowtitle) or self.maxlen < 0:
            self.maxlen = len(self.windowtitle)
        if b == 5:
            self.maxlen = max(1, self.maxlen - 1)
        elif b == 4:
            self.maxlen = self.maxlen + 1
        if self.maxlen > len(self.windowtitle):
            self.maxlen = -1
        self.reset_label()
    def render_themed(self,painter):
        if self.label != '':
            super(HLWMWindowTitle,self).render_themed(painter)

class HLWMLayoutSwitcher(Switcher):
    def __init__(self, hlwm, layouts, command = [ 'setxkbmap' ]):
        # layouts is a list of layout specifications
        # a layout specification is a list containing:
        # [ some internal name, displayed identifier, xkbmap arguments...]
        self.layouts = layouts
        self.command = command
        self.titles = [ l[1] for l in layouts ]
        self.hc = hlwm
        super(HLWMLayoutSwitcher,self).__init__(self.titles)
        hlwm.enhook('keyboard_layout', (lambda a: self.layoutswitched(a)))
    def choice_clicked(self,idx):
        l = self.layouts[idx]
        self.hc(['emit_hook', 'keyboard_layout', l[0]])
        cmd = []
        cmd += self.command
        cmd += l[2:]
        subprocess.Popen(cmd)
    def layoutswitched(self,args):
        for idx, l in enumerate(self.layouts):
            if args[0] == l[0]:
                self.selection = idx

class HLWMMonitorFocusLayout(StackedLayout):
    def __init__(self, hlwm, monitor, wactive, wpassive):
        self.hlwm = hlwm # the hlwm connection
        self.wactive = wactive # widget that is shown if the monitor is focused
        self.wpassive = wpassive # widget that is shown if the monitor is not focused
        self.monitor = int(monitor) # monitor index to watch
        hlwm.enhook('tag_changed', (lambda a: self.anothermonitor(a)))
        self.curmonitor = int(hlwm(['attr', 'monitors.focus.index']))
        super(HLWMMonitorFocusLayout,self).__init__([wpassive, wactive],
            selection = int(self.curmonitor == int(monitor)))
    def anothermonitor(self, args):
        if len(args) >= 2:
            self.curmonitor = int(args[1])
            self.selection = int(self.curmonitor == self.monitor)

