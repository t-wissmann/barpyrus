#!/usr/bin/env python3

import subprocess
import time
import sys
import select
import os
import math
import struct

class EventInput:
    def __init__(self, command):
        self.command = command
        self.proc = subprocess.Popen(command, stdout=subprocess.PIPE,
                                              stdin=subprocess.PIPE)
        self._buf = ''
        self.callback = None;
    def fileno(self):
        return self.proc.stdout.fileno()
    # thanks to http://stackoverflow.com/questions/5486717/python-select-doesnt-signal-all-input-from-pipe
    def readlines(self):
        data = os.read(self.proc.stdout.fileno(), 4096).decode('utf-8')
        if not data:
            # EOF
            return None
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

class Painter:
    def __init__(self):
        self.flags = 0
    def drawRaw(self, text): # draw text and possibly interpret them as control characters
        pass
    def __iadd__(self, text): # draw a text savely
        pass
    def fg(self, color = None): # sets the foreground color (None resets it to the default)
        pass
    def bg(self, color = None): # sets the background color (None resets it to the default)
        pass
    def ul(self, color = None): # sets the underline color (None resets it to the default)
        pass
    def ol(self, color = None): # sets the overline color (None resets it to the default)
        pass
    def __ior__(self, flags): # set the flags to a fixed set using: |=
        pass
    def __ixor__(self, flags): # set the flags to a fixed set using: |=
        pass
    def symbol(self, symbol):
        pass
    def flush(self):
        pass
    def clickable(self, buttons, obj, callback):
        # render a clickable area
        # buttons = a list of mouse button numbers
        # callback = a function with the paramters: callback(object, button)
        #           object = the given object obj
        #           button = the number of the button that was clicked
        class Clickable:
            def __init__(self,painter):
                self.p = painter
            def __enter__(self):
                self.p._enter_clickable()
            def __exit__(self):
                self.p._exit_clickable()
        c = Clickable(self)
        c.buttons = buttons
        c.obj = obj
        c.callback = callback
        return c
    # draw the start of a clickable area
    def _enter_clickable(self, clickable):
        pass
    # draw the end of a clickable area
    def _exit_clickable(self, clickable):
        pass

class Lemonbar(EventInput):
    def __init__(self, geometry = None):
        command = [ "lemonbar" ]
        if geometry:
            (x,y,w,h) = geometry
            command += [ '-g', "%dx%d%+d%+d" % (w,h,x,y)  ]
        command += '-a 100 -d -u 2 -B #ee121212 -f -*-fixed-medium-*-*-*-12-*-*-*-*-*-*-*'.split(' ')
        command += '-f -wuncon-siji-medium-r-normal--10-100-75-75-c-80-iso10646-1'.split(' ')
        super(Lemonbar,self).__init__(command)
        self.widget = None
        self.clickareas = { }

    def handle_line(self,line):
        if line in self.clickareas:
            (callback, obj, b) = self.clickareas[line]
            callback(obj, b)
        elif len(line.split('_')) == 2 and self.widget != None:
            # temporary workaround during dransition to painters
            line = line.split('_')
            name = line[0]
            btn = int(line[1])
            self.widget.can_handle_input(name, btn)
        else:
            print("invalid event name: %s" % line)
    class LBPainter(Painter):
        def __init__(self,lemonbar):
            super(LBPainter,self).__init__()
            self.buf = ""
            self.lemonbar = lemonbar
        def drawRaw(self, text):
            self.buf += text
        def __iadd__(self, text):
            self.buf += text.replace('%', '%%')
        def fg(self, color = None):
            self.buf += '%{F' + color + '}' if color else '%{F-}'
        def bg(self, color = None):
            self.buf += '%{B' + color + '}' if color else '%{B-}'
        def linecolor(self, color = None):
            self.buf += '%{U' + color + '}' if color else '%{U-}'
        def ul(self, color = None):
            self.linecolor(color)
        def ol(self, color = None):
            self.linecolor(color)
        def symbol(self, symbol):
            self.buf += '%{T1}' + chr(symbol) + '%{T-}'
        def flush(self):
            lemonbar.write_flushed(text)
        def _enter_clickable(self, clickable):
            for b in clickable.buttons:
                clickname = str(clickable.obj) + '_' + str(b)
                self.buf += '%%{A%d:%s:}' % (b,clickname)
                self.lemonbar.clickareas[clickname] = (clickable.callback, clickable.obj, b)
        def _exit_clickable(self, clickable):
            clickname = str(clickable.obj) + '_' + str(b)
            for b in clickable.buttons:
                self.buf += '%{A}'
    def painter(self):
        return LBPainter(self)
    def textpainter(self, actions):
        p = LBPainter(None)
        actions(p)
        return p.buf

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

