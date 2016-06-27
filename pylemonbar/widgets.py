#!/usr/bin/env python3

import subprocess
import time
import sys
import select
import os
import math
import struct

class Widget:
    def __init__(self):
        self.timer_interval = None
        self.buttons = [ ]
        self.click_id = 'w' + str(id(self))
        self.pad_left = ''
        self.pad_right = ''
        self.last_timeout = 0.0 # timestamp of the last timeout
    def timeout(self):
        return False
    def eventinput(self):
        return None
    def next_timeout(self):
        if self.timer_interval:
            return self.last_timeout + self.timer_interval
        else:
            return math.inf
    def maybe_timeout(self, now):
        if not self.timer_interval:
            return False
        if self.last_timeout + self.timer_interval <= now:
            self.last_timeout = now
            return self.timeout()
        return False
    def render(self):
        begin = ''
        end = self.pad_right
        for b in self.buttons:
            clickname = self.click_id + '_' + str(b)
            begin += '%%{A%d:%s:}' % (b,clickname)
            end += '%{A}'
        begin += self.pad_left
        return begin + self.content() + end
    def content(self):
        return 'widget'
    def can_handle_input(self, click_id, btn):
        if click_id == self.click_id:
            self.on_click(btn)
            return True
        else:
            return False
    def on_click(self, button):
        pass

class RawLabel(Widget):
    def __init__(self,label):
        super(RawLabel,self).__init__()
        self.label = label
    def render(self):
        return self.label

class Label(Widget):
    def __init__(self,label):
        super(Label,self).__init__()
        self.label = label
    def content(self):
        return self.label.replace('%', '%%')

class Button(Widget):
    def __init__(self,label):
        super(Button,self).__init__()
        self.label = label
        self.pad_left = ' '
        self.pad_right = ' '
        self.buttons = [ 1 ]
        self.callback = None
    def content(self):
        return self.label
    def on_click(self, button):
        #print("btn %d" % button)
        if self.callback:
            self.callback(button)

class DateTime(Label):
    def __init__(self,time_format = '%H:%M, %Y-%m-%d'):
        super(DateTime,self).__init__('')
        self.timer_interval = 1
        self.time_format = time_format
        self.last_time = ''
        self.timeout()
    def timeout(self):
        self.label = time.strftime(self.time_format)
        if_changed = (self.label != self.last_time)
        self.last_time = self.label
        return if_changed

class Switcher(Widget):
    def __init__(self,choices,selection=0):
        super(Switcher,self).__init__()
        self.buttons = [ Button(x) for x in choices ]
        for i,btn in enumerate(self.buttons):
            btn.callback = (lambda j: lambda buttonnr: self.choice_clicked(j))(i)
        self.normalbg = '#303030'
        self.normalfg = 'white'
        self.focusfg = 'black'
        self.focusbg = '#9fbc00'
        self.selection = selection
    def choice_clicked(self, idx):
        self.selection = idx
    def render(self):
        buf = self.pad_left
        buf += '%{B' + self.normalbg + '}%{+o}%{+u}%{U' + self.normalbg + '} '
        for i, btn in enumerate(self.buttons):
            if i == self.selection:
                buf += '%%{B%s}%%{F%s}' % (self.focusbg, self.focusfg)
            buf += btn.render()
            if i == self.selection:
                buf += '%%{B%s}%%{F%s}' % (self.normalbg, self.normalfg)
        buf += ' %{B-}%{-o}%{-u}%{F-}'
        buf += self.pad_right
        return buf
    def can_handle_input(self, click_id, btn):
        if super(Switcher,self).can_handle_input(click_id, btn):
            return True
        for btn in self.buttons:
            if btn.can_handle_input(click_id, btn):
                return True
        return False

class StackedLayout(Widget):
    def __init__(self, widgets, selection=0):
        super(StackedLayout,self).__init__()
        self.widgets = widgets
        self.selection = selection
    def can_handle_input(self, click_id, btn):
        for w in self.widgets:
            if w.can_handle_input(click_id, btn):
                return True
        if super(StackedLayout,self).can_handle_input(click_id, btn):
            return True
        return False
    def render(self):
        buf = ""
        buf += self.pad_left
        buf += self.widgets[self.selection].render()
        buf += self.pad_right
        return buf
    def can_handle_input(self, click_id, btn):
        return self.widgets[self.selection].can_handle_input(click_id, btn)

class TabbedLayout(StackedLayout):
    def __init__(self, tabs, selection = 0):
        # tabs is a list of paris, where the first element is the title
        # and the second element is the widget
        self.tabs = tabs
        super(TabbedLayout,self).__init__([w[1] for w in tabs], selection)
        self.tab_label = Button(tabs[selection][0])
        self.tab_label.callback = lambda buttonnr: self.on_click()
    def on_click(self):
        self.selection += 1
        self.selection %= len(self.tabs)
        self.tab_label.label = self.tabs[self.selection][0]
    def can_handle_input(self, click_id, btn):
        if self.tab_label.can_handle_input(click_id, btn):
            return True
        return super(TabbedLayout,self).can_handle_input(click_id, btn)
    def render(self):
        buf = ""
        buf += self.tab_label.render()
        buf += super(TabbedLayout,self).render()
        return buf

class ShortLongLayout(TabbedLayout):
    def __init__(self, shortwidget, longwidget, longdefault = False):
        # tabs is a list of paris, where the first element is the title
        # and the second element is the widget
        tabs = [
            ('%{F#A0A0A0}+%{F-}', shortwidget),
            ('%{F#A0A0A0}-%{F-}', longwidget),
        ]
        super(ShortLongLayout,self).__init__(tabs, selection = (1 if longdefault else 0))

class ListLayout(Widget):
    def __init__(self, widgets):
        # just show a couple of widgets side by side
        super(ListLayout,self).__init__()
        self.widgets = widgets
    def render(self):
        buf = ''
        for w in self.widgets:
            buf += w.render()
        return buf
    def can_handle_input(self, click_id, btn):
        for w in self.widgets:
            if w.can_handle_input(click_id, btn):
                return True
        return False
