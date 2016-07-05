#!/usr/bin/env python3

import subprocess
import time
import sys
import select
import os
import math
import struct

from barpyrus import core
from barpyrus import core

class Widget:
    def __init__(self):
        self.timer_interval = None
        self.buttons = [ ]
        self.click_id = 'w' + str(id(self))
        self.pre_render = None
        self.post_render = None
        self.last_timeout = 0.0 # timestamp of the last timeout
        self.subwidgets = []
        self.theme = None
    def timeout(self):
        # called on timeout. Return true if an update is needed
        return False
    def eventinputs(self): # returns a list of Core.EventInput objects
        inputs = []
        for w in self.subwidgets:
            inputs += w.eventinputs()
        return inputs
    def next_timeout(self):
        next_to = None
        for w in self.subwidgets:
            to = w.next_timeout()
            next_to = min(next_to, to) if next_to != None else to
        if self.timer_interval:
            to = self.last_timeout + self.timer_interval
            next_to = min(next_to, to) if next_to != None else to
        return next_to
    def maybe_timeout(self, now):
        some_timeout = False
        for w in self.subwidgets:
            some_timeout = w.maybe_timeout(now) or some_timeout
        if self.timer_interval and self.last_timeout + self.timer_interval <= now:
            self.last_timeout = now
            #print("timeout for " + str(self))
            some_timeout = self.timeout() or some_timeout
        return some_timeout
    def render(self, painter):
        painter += 'widget'
    def can_handle_input(self, click_id, btn):
        for w in self.subwidgets:
            if w.can_handle_input(click_id, btn):
                return True
        if click_id == self.click_id:
            self.on_click(btn)
            return True
        else:
            return False
    def on_click(self, button):
        pass

    def render_themed(self,painter):
        clickable = None
        if self.buttons:
            clickable = core.Painter.Clickable(self.buttons, self, self.on_click)
            painter._enter_clickable(clickable)
        if self.theme:
            self.theme.begin_with_attributes(painter, self)
        if self.pre_render:
            self.pre_render(painter)
        self.render(painter)
        if self.post_render:
            self.post_render(painter)
        if self.theme:
            self.theme.end_with_attributes(painter, self)
        if self.buttons:
            painter._exit_clickable(clickable)

class RawLabel(Widget):
    def __init__(self,label):
        super(RawLabel,self).__init__()
        self.label = label
    def render(self, p):
        p.drawRaw(self.label)

class Label(Widget):
    def __init__(self,label):
        super(Label,self).__init__()
        self.label = label
    def render(self, p):
        p += self.label

class Button(Widget):
    def __init__(self,label):
        super(Button,self).__init__()
        self.label = label
        self.buttons = [ 1 ]
        self.callback = None
    def render(self, p):
        p += self.label
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
        self.option_buttons = [ Button(x) for x in choices ]
        self.subwidgets += self.option_buttons
        for i,btn in enumerate(self.option_buttons):
            btn.callback = (lambda j: lambda buttonnr: self.choice_clicked(j))(i)
        self.normalbg = '#303030'
        self.normalfg = '#ffffff'
        self.focusfg = '#000000'
        self.focusbg = '#9fbc00'
        self.selection = selection
    def choice_clicked(self, idx):
        self.selection = idx
    def render(self, p):
        p.fg(self.normalfg)
        p.bg(self.normalbg)
        p.ul(self.normalbg)
        p.set_flag(p.overline | p.underline, True)
        p.space(3)
        for i, btn in enumerate(self.option_buttons):
            if i == self.selection:
                p.fg(self.focusfg)
                p.bg(self.focusbg)
            p.space(3)
            p.widget(btn)
            p.space(3)
            if i == self.selection:
                p.fg(self.normalfg)
                p.bg(self.normalbg)
                p.ul(self.normalbg)
        p.space(3)
        p.bg()
        p.fg()
        p.ul()
        p.set_flag(p.overline | p.underline, False)

class StackedLayout(Widget):
    def __init__(self, widgets, selection=0):
        super(StackedLayout,self).__init__()
        self.widgets = widgets
        self.selection = selection
        self.subwidgets += widgets
    def render(self,painter):
        painter.widget(self.widgets[self.selection])
    def can_handle_input(self, click_id, btn):
        return self.widgets[self.selection].can_handle_input(click_id, btn)

class TabbedLayout(StackedLayout):
    def __init__(self, tabs, selection = 0):
        # tabs is a list of pairs, where the first element is the title
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
    def render(self,painter):
        painter.widget(self.tab_label)
        super(TabbedLayout,self).render(painter)

class ShortLongLayout(TabbedLayout):
    def __init__(self, shortwidget, longwidget, longdefault = False):
        # tabs is a list of paris, where the first element is the title
        # and the second element is the widget
        tabs = [
            ('< ', shortwidget),
            ('> ', longwidget),
        ]
        super(ShortLongLayout,self).__init__(tabs, selection = (1 if longdefault else 0))

class ListLayout(Widget):
    def __init__(self, widgets):
        # just show a couple of widgets side by side
        super(ListLayout,self).__init__()
        self.widgets = widgets
        self.subwidgets = widgets
    def render(self, painter):
        for w in self.widgets:
            painter.widget(w)
