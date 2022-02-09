#!/usr/bin/env python3

import subprocess
import time
import sys
import select
import os
import math
import struct
import contextlib


global_inputs = [ ]

# ask the main loop to quit soon
def quit_main_loop():
    shutdown_requested.value = True

# returns whether the shutdown of the main loop has been requested
def shutdown_requested():
    return shutdown_requested.value
shutdown_requested.value = False

def add_global_input(inp):
    global_inputs.append(inp)

class EventInput:
    def __init__(self, command):
        self.command = command
        self.proc = subprocess.Popen(command, stdout=subprocess.PIPE,
                                              stdin=subprocess.PIPE)
        self._buf = ''
        self.callback = None;
        add_global_input(self)

    def __str__(self):
        cmd = ' '.join([f"'{word}'" for word in self.command])
        return f'<EventInput pid={self.proc.pid} {cmd}>'

    def fileno(self):
        return self.proc.stdout.fileno()
    # thanks to http://stackoverflow.com/questions/5486717/python-select-doesnt-signal-all-input-from-pipe
    def readlines(self):
        data = os.read(self.proc.stdout.fileno(), 4096).decode('utf-8')
        if not data:
            raise EOFError
        self._buf += data
        if '\n' not in data:
            return []
        tmp = self._buf.split('\n')
        lines, self._buf = tmp[:-1], tmp[-1]
        return lines
    def process(self):
        for line in self.readlines():
            self.handle_line(line)
    def kill(self):
        self.proc.kill()
    def is_running(self):
        return self.proc.pid != None
    def handle_line(self,line):
        if self.callback != None:
            self.callback(line)
    def write_flushed(self, text):
        self.proc.stdin.write(text.encode('utf-8'))
        self.proc.stdin.flush()

class Theme:
    def __init__(self, bg = None, fg = None, padding = (0,0), margin = (0,0), begin = None, end = None):
        self.bg = bg
        self.fg = fg
        self.padding = padding
        self.margin = margin
        self.begin_cb = begin
        self.end_cb = end
    def begin_with_attributes(self, painter, widget):
        if self.margin[0] != 0:
            painter.space(self.margin[0])
        painter.push()
        if self.bg:
            painter.bg(self.bg)
        if self.fg:
            painter.fg(self.fg)
        if self.padding[0] != 0:
            painter.space(self.padding[0])
        self.begin(painter, widget)
    def end_with_attributes(self, painter, widget):
        self.end(painter,widget)
        if self.padding[1] != 0:
            painter.space(self.padding[1])
        painter.pop()
        if self.margin[1] != 0:
            painter.space(self.margin[1])
    def begin(self, painter, widget):
        if self.begin_cb:
            self.begin_cb(self, painter, widget)
    def end(self, painter, widget):
        if self.end_cb:
            self.end_cb(self, painter, widget)
    def __call__(self, widget):
        widget.theme = self
        return widget

class Painter:
    underline = 0x01
    overline  = 0x02
    def __init__(self):
        self.flags = 0
        self.stack = []
    def push(self):
        pass
    def pop(self):
        self.fg(None)
        self.bg(None)
        pass
    def drawRaw(self, text): # draw text and possibly interpret them as control characters
        pass
    def text(self,text): # draw a text savely
        pass
    def __iadd__(self, text):
        self.text(text)
        return self
    def fg(self, color = None): # sets the foreground color (None resets it to the default)
        pass

    @contextlib.contextmanager
    def temp_fg(self, color):
        self.fg(color)
        yield
        self.fg(None)

    def bg(self, color = None): # sets the background color (None resets it to the default)
        pass
    def ul(self, color = None): # sets the underline color (None resets it to the default)
        pass
    def ol(self, color = None): # sets the overline color (None resets it to the default)
        pass
    def set_flag(self, flag, value):
        if value:
            self.set_flags(self.flags | flag)
        else:
            self.set_flags(self.flags & ~flag)
    def set_flags(self,flags):
        oldflags = self.flags
        self.flags = flags
        if (oldflags & Painter.underline) != (flags & Painter.underline):
            self.set_ul((flags & Painter.underline) != 0x0)
        if (oldflags & Painter.overline) != (flags & Painter.overline):
            self.set_ol((flags & Painter.overline) != 0x0)
    def __ior__(self, flags): # add the given flags
        self.set_flags(flags | self.flags)
        return self
    def set_ul(self, enabled):
        pass
    def set_ol(self, enabled):
        pass
    def symbol(self, symbol):
        pass
    def flush(self):
        pass
    def space(self, width): # insert some space of 'width' many units
        pass

    class Clickable:
        def __init__(self, buttons, obj, callback):
            # buttons = a list of mouse button numbers
            # callback = a function with the paramters: callback(object, button)
            #           object = the given object obj
            #           button = the number of the button that was clicked
            self.buttons = buttons
            self.obj = obj
            self.callback = callback

    def widget(self, widget):
        widget.render_themed(self)

    @contextlib.contextmanager
    def clickable(self, buttons, callback):
        if isinstance(buttons, int):
            buttons = [buttons]
        click = Painter.Clickable(buttons, None, callback)
        self._enter_clickable(click)
        yield
        self._exit_clickable(click)

    # draw the start of a clickable area
    def _enter_clickable(self, clickable):
        pass
    # draw the end of a clickable area
    def _exit_clickable(self, clickable):
        pass

class TextPainter(Painter):
    # like a painter, but additionally supports encoding the formatting
    # information within text
    def __str__(self):
        pass

def get_mouse_location():
    cmd = 'xdotool getmouselocation'.split(' ')
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    proc.wait()
    lines = proc.stdout.read().decode("utf-8").split(' ')
    x = int(lines[0].replace('x:', '', 1))
    y = int(lines[1].replace('y:', '', 1))
    return (x,y)

class DropdownRofi:
    def __init__(self, y, x, panel_width, direction_down = True):
        self.y = y
        self.x = x
        self.panel_width = panel_width
        self.direction_down = direction_down
        self.rofi_args = [ ]
        self.default_width = 40
    def spawn(self, lines, additional_args = [ '-p', ''], width = None):
        (mouse_x, mouse_y) = get_mouse_location()
        if not width:
            width = 100 # some default width
        width = max(width, 101) # width has to be 100 at least (rofi restriction)
        # first, compute the top left corner of the menu
        menu_x = min(max(mouse_x - width/2, self.x), self.x + self.panel_width - width)
        menu_y = self.y
        # then, specify these coordinates relative to the mouse cursor
        menu_x -= mouse_x
        menu_y -= mouse_y
        # compile rofi arguments
        cmd = ['rofi', '-dmenu', '-sep' , '\\0' ]
        cmd += ['-monitor', '-3' ] # position relative to mouse cursor
        cmd += ['-layout', '1' ] # specify top left corner of the menu
        cmd += ['-width', str(width) ]
        cmd += ['-xoffset', str(menu_x), '-yoffset', str(menu_y) ]
        cmd += self.rofi_args
        cmd += additional_args
        rofi = subprocess.Popen(cmd,stdout=subprocess.PIPE,stdin=subprocess.PIPE)
        for i in lines:
            rofi.stdin.write(i.encode('utf-8'))
            rofi.stdin.write(struct.pack('B', 0))
        rofi.stdin.close()
        rofi.wait()

