#!/usr/bin/env python3

import subprocess
import time
import datetime
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
        self.custom_render = None # here the user can override a widgets render()
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
            if to == None:
                continue
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

    def is_empty(self):
        """tell, whether the widget has empty contents"""
        return False

    def render_themed(self,painter):
        clickable = None
        if self.buttons:
            clickable = core.Painter.Clickable(self.buttons, self, self.on_click)
            painter._enter_clickable(clickable)
        if self.theme:
            self.theme.begin_with_attributes(painter, self)
        if self.pre_render:
            self.pre_render(painter)
        if self.custom_render:
            self.custom_render(self, painter)
        else:
            self.render(painter)
        if self.post_render:
            self.post_render(painter)
        if self.theme:
            self.theme.end_with_attributes(painter, self)
        if self.buttons:
            painter._exit_clickable(clickable)

    def print_widget_tree(self, indent='', file=sys.stderr):
        print('{}- Widget "{}" has {} subwidgets'
              .format(indent, type(self).__name__, len(self.subwidgets)),
              file=file)
        for sub in self.subwidgets:
            sub.print_widget_tree(indent=(indent + '  '), file=file)


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


class ColorLabel(RawLabel):
    def __init__(self, label, color):
        super().__init__(label=label)
        self.color = color
    def render(self, p):
        p.fg(self.color)
        super().render(p)

class Button(Widget):
    def __init__(self, label):
        super(Button,self).__init__()
        self.label = label
        self.buttons = [ 1 ]
        self.callback = None
    def render(self, p):
        if isinstance(self.label, Widget):
            self.label.render(p)
        else:
            p += self.label
    def on_click(self, button):
        if self.callback:
            self.callback(button)


class DateTime(Label):
    """
    This is a label widget that displays the current date/time
    in the specified format. The optional parameter 'timezone'
    expects the string representation of a timezone (e.g.
    'Europe/Berlin'), and requires that the pytz library is installed.
    """
    def __init__(self, time_format = '%H:%M, %Y-%m-%d', timezone=None):
        super(DateTime,self).__init__('')
        self.timer_interval = 1
        self.time_format = time_format
        self.last_time = ''
        self.tz_name = timezone
        self.tz = None
        if self.tz_name:
            # if tz_name is provided, we need the 'pytz' library:
            import pytz
            self.tz = pytz.timezone(self.tz_name)
        # set label
        self.timeout()

    def timeout(self):
        if self.tz:
            t = datetime.datetime.now(self.tz)
        else:
            t = datetime.datetime.now()
        self.label = t.strftime(self.time_format)
        if_changed = (self.label != self.last_time)
        self.last_time = self.label
        return if_changed


class ExButton(Button):
    def __init__(self, label, cmd):
        super().__init__(label=label)
        self._cmd = cmd
        self.callback = self.execute_cmd

    def execute_cmd(self, button):
        subprocess.Popen(self._cmd, shell=True)


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
    """Switch between multiple widgets. If the selected widget is_empty(), then
    the first non-empty next is shown instead."""
    def __init__(self, widgets, selection=0, find_nonempty=True):
        super(StackedLayout,self).__init__()
        self.widgets = widgets
        self.selection = selection
        self.subwidgets += widgets
        self.find_nonempty = find_nonempty

    def render(self,painter):
        # starting at the current selection, find the first non-empty widget:
        first_nonempty = self.selection
        if self.find_nonempty:
            count = len(self.widgets)
            for i in range(0, count):
                abs_idx = (self.selection +  i) % count
                if not self.widgets[abs_idx].is_empty():
                    first_nonempty = abs_idx
                    break
        painter.widget(self.widgets[abs_idx])

    def can_handle_input(self, click_id, btn):
        return self.widgets[self.selection].can_handle_input(click_id, btn)

class TabbedLayout(StackedLayout):
    def __init__(self, tabs, selection = 0, tab_renderer = None):
        # tabs is a list of pairs, where the first element is the title
        # and the second element is the widget
        self.tabs = tabs
        super(TabbedLayout,self).__init__([w[1] for w in tabs], selection)
        self.tab_label = Button(tabs[selection][0])
        if tab_renderer != None:
            self.tab_label.custom_render = tab_renderer
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
