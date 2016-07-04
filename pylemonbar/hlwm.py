#!/usr/bin/env python3

import subprocess
import time
import sys
import select
import os
import math
import struct

from pylemonbar.widgets import Widget
from pylemonbar.widgets import Label
from pylemonbar.widgets import Button
from pylemonbar.widgets import Switcher
from pylemonbar.widgets import StackedLayout
from pylemonbar.core import EventInput
from pylemonbar.core import Painter

def hc(args):
    cmd = [ "herbstclient", "-n" ]
    cmd += args;
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    proc.wait()
    return proc.stdout.read().decode("utf-8")

class HLWMInput(EventInput):
    def __init__(self):
        cmd = [ 'herbstclient', '--idle' ]
        self.hooks = { }
        super(HLWMInput,self).__init__(cmd)
    def enhook(self,name,callback):
        self.hooks.setdefault(name,[]).append(callback)
    def handle_line(self,line):
        args = line.split('\t')
        if len(args) == 0:
            return
        if args[0] in self.hooks:
            for cb in self.hooks[args[0]]:
                cb(args[1:])

class HLWMTagInfo:
    def __init__(self):
        self.name = '?'
        self.occupied = True
        self.focused = False
        self.here = False
        self.urgent = False
        self.visible = True
        self.empty = False
        self.activecolor = '#9fbc00'
        self.emphbg = '#303030'
    def parse(self,string): # parse a tag_status string
        self.name = string[1:]
        self.parse_char(string[0])
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
        painter.fg(None if self.occupied else '#909090')
        if self.urgent:
            painter.bg('#eeD6156C')
            painter.set_flag(Painter.overline, False)
        if self.focused:
            painter.fg('#ffffff')
            painter.ol(self.activecolor)
        else:
            painter.ol('#454545')
        painter += ' %s ' % self.name
        painter.bg()
        painter.ol()
        painter.set_flag(painter.overline, False)

class HLWMTags(Widget):
    def __init__(self,hlwm,monitor):
        super(HLWMTags,self).__init__()
        self.needs_update = True
        self.tags = [ ]
        self.tag_info = [ ]
        self.tag_count = 0
        self.buttons = [4, 5]
        self.monitor = monitor
        self.activecolor = hc('attr theme.tiling.active.color'.split(' '))
        self.emphbg = '#303030'
        self.update_tags()
        hlwm.enhook('tag_changed', lambda a: self.update_tags(args = a))
        hlwm.enhook('tag_flags', lambda a: self.update_tags(args = a))
        hlwm.enhook('tag_added', lambda a: self.update_tags(args = a))
        hlwm.enhook('tag_removed', lambda a: self.update_tags(args = a))

    def update_tags(self, args = None):
        strlist = hc(['tag_status', str(self.monitor)]).strip('\t').split('\t')
        self.tag_count = len(strlist)
        # enlarge the tag button array
        for i in range(len(self.tags),len(strlist)):
            btn = Button('')
            btn.callback = (lambda j: lambda b: self.tag_clicked(j, b))(i)
            tag_info = HLWMTagInfo()
            btn.pre_render = tag_info.render
            self.tags.append(btn)
            self.subwidgets.append(btn)
            self.tag_info.append(tag_info)
        # update names and formatting
        for i in range(0, self.tag_count):
            self.tag_info[i].parse(strlist[i])
        self.needs_update = False
    def tag_clicked(self,tagindex,button):
        cmd = 'chain , focus_monitor %d , use_index %d' % (self.monitor,tagindex)
        cmd = cmd.split(' ')
        #print(cmd)
        hc(cmd)
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
        cmd = 'chain , focus_monitor %d , use_index %+d --skip-visible'
        if b == 4:
            delta = -1
        else:
            delta = +1
        cmd = (cmd % (self.monitor,delta)).split(' ')
        hc(cmd)

class HLWMWindowTitle(Label):
    def __init__(self, hlwm, maxlen = -1):
        self.windowtitle = hc(['attr', 'clients.focus.title'])
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
        if self.maxlen < 0:
            self.label = self.windowtitle
        else:
            self.label = self.windowtitle[:self.maxlen]
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
    def render(self,painter):
        if self.label != '':
            super(HLWMWindowTitle,self).render(painter)

class HLWMLayoutSwitcher(Switcher):
    def __init__(self, hlwm, layouts, command = [ 'setxkbmap' ]):
        # layouts is a list of layout specifications
        # a layout specification is a list containing:
        # [ some internal name, displayed identifier, xkbmap arguments...]
        self.layouts = layouts
        self.command = command
        self.titles = [ l[1] for l in layouts ]
        super(HLWMLayoutSwitcher,self).__init__(self.titles)
        hlwm.enhook('keyboard_layout', (lambda a: self.layoutswitched(a)))
    def choice_clicked(self,idx):
        l = self.layouts[idx]
        hc(['emit_hook', 'keyboard_layout', l[0]])
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
        self.curmonitor = int(hc(['attr', 'monitors.focus.index']))
        super(HLWMMonitorFocusLayout,self).__init__([wpassive, wactive],
            selection = int(self.curmonitor == int(monitor)))
    def anothermonitor(self, args):
        if len(args) >= 2:
            self.curmonitor = int(args[1])
            self.selection = int(self.curmonitor == self.monitor)

