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
from pylemonbar.core import EventInput

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

class HLWMTags(Widget):
    def __init__(self,hlwm,monitor):
        super(HLWMTags,self).__init__()
        self.needs_update = True
        self.tags = [ ]
        self.tag_count = 0
        self.buttons = [4, 5]
        self.pad_right = '%{F-}%{B-}%{-o}'
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
            btn = Button(str(i))
            btn.callback = (lambda j: lambda b: self.tag_clicked(j, b))(i)
            self.tags.append(btn)
        # update names and formatting
        for i in range(0, self.tag_count):
            occupied = True
            focused = False
            here = False
            urgent = False
            visible = True
            ch = strlist[i][0]
            self.tags[i].empty = False
            if ch == '.':
                occupied = False
                visible = False
                self.tags[i].empty = True
            elif ch == '#':
                focused = True
                here = True
            elif ch == '%':
                focused = True
            elif ch == '+':
                here = True
            elif ch == '!':
                urgent = True
            elif ch == ':':
                visible = False
            else:
                print("Unknown hlwm tag modifier >%s<" % ch)
            #if here:
            #    print('tag:        %s' %strlist[i][1:])
            form = ''
            form += '%{B' + self.emphbg + '}' if here else '%{B-}'
            form += '%{+o}' if visible else '%{-o}'
            form += '%{F-}' if occupied else '%{F#909090}'
            form += '%{B#eeD6156C}%{-o}' if urgent else ''
            form += ('%{Fwhite}%{U' + self.activecolor + '}' ) if focused else '%{U#454545}'
            self.tags[i].pad_left = form + ' '
            self.tags[i].label = strlist[i][1:]
        self.needs_update = False
    def tag_clicked(self,tagindex,button):
        cmd = 'chain , focus_monitor %d , use_index %d' % (self.monitor,tagindex)
        cmd = cmd.split(' ')
        #print(cmd)
        hc(cmd)
    def content(self):
        text = ''
        for t in self.tags:
            if t.empty:
                continue
            text += t.render()
        return text
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
    def __init__(self, hlwm):
        super(HLWMWindowTitle,self).__init__(hc(['attr', 'clients.focus.title']))
        hlwm.enhook('focus_changed', (lambda a: self.newtitle(a)))
        hlwm.enhook('window_title_changed', (lambda a: self.newtitle(a)))
    def newtitle(self,args):
        if len(args) >= 2:
            self.label = args[1]
        else:
            self.label = ''
    def render(self):
        if self.label == '':
            return ""
        else:
            return super(HLWMWindowTitle,self).render()

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

