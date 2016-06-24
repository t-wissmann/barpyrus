#!/usr/bin/env python3

import subprocess
import time
import sys
import select
import os
import math
import struct


def hc(args):
    cmd = [ "herbstclient", "-n" ]
    cmd += args;
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    proc.wait()
    return proc.stdout.read().decode("utf-8")

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
    def is_running(self):
        return self.proc.pid != None
    def handle_line(self):
        if self.callback != None:
            self.callback(line)
    def write_flushed(self, text):
        self.proc.stdin.write(text.encode('utf-8'))
        self.proc.stdin.flush()

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

class Lemonbar(EventInput):
    def __init__(self, geometry = None):
        command = [ "lemonbar" ]
        if geometry:
            (x,y,w,h) = geometry
            command += [ '-g', "%dx%d%+d%+d" % (w,h,x,y)  ]
        command += '-u 2 -B #ee121212 -f -*-fixed-medium-*-*-*-12-*-*-*-*-*-*-*'.split(' ')
        super(Lemonbar,self).__init__(command)
        self.widgets = None

    def handle_line(self,line):
        line = line.split('_')
        if len(line) != 2:
            print("invalid event name: %s" % '_'.join(line))
        else:
            name = line[0]
            btn = int(line[1])
            for w in self.widgets:
                if w.can_handle_input(name, btn):
                    break


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

activecolor = hc('attr theme.tiling.active.color'.split(' '))
emphbg = '#303030'

class HLWMTags(Widget):
    def __init__(self,hlwm):
        super(HLWMTags,self).__init__()
        self.needs_update = True
        self.tags = [ ]
        self.tag_count = 0
        self.buttons = [4, 5]
        self.pad_right = '%{F-}%{B-}%{-o}'
        self.update_tags()
        hlwm.enhook('tag_changed', lambda a: self.update_tags(args = a))
        hlwm.enhook('tag_flags', lambda a: self.update_tags(args = a))
        hlwm.enhook('tag_added', lambda a: self.update_tags(args = a))
        hlwm.enhook('tag_removed', lambda a: self.update_tags(args = a))

    def update_tags(self, args = None):
        global monitor
        strlist = hc(['tag_status', str(monitor)]).strip('\t').split('\t')
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
            form += '%{B' + emphbg + '}' if here else '%{B-}'
            form += '%{+o}' if visible else '%{-o}'
            form += '%{F-}' if occupied else '%{F#909090}'
            form += '%{B#eeD6156C}%{-o}' if urgent else ''
            form += ('%{Fwhite}%{U' + activecolor + '}' ) if focused else '%{U#454545}'
            self.tags[i].pad_left = form + ' '
            self.tags[i].label = strlist[i][1:]
        self.needs_update = False
    def tag_clicked(self,tagindex,button):
        cmd = 'chain , focus_monitor %d , use_index %d' % (monitor,tagindex)
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
        cmd = (cmd % (monitor,delta)).split(' ')
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

# ---- configuration ---
if len(sys.argv) >= 2:
    monitor = int(sys.argv[1])
else:
    monitor = 0
geometry = hc(['monitor_rect', str(monitor)]).split(' ')
x = int(geometry[0])
y = int(geometry[1])
monitor_w = int(geometry[2])
monitor_h = int(geometry[3])
width = monitor_w
height = 16

bar = Lemonbar(geometry = (x,y,width,height))
hc_idle = HLWMInput()

# widgets
#rofi = DropdownRofi(y+height,x,width)
#
#def session_menu(btn):
#    rofi.spawn(['Switch User', 'Suspend', 'Logout'])
#
#session_button = Button('V')
#session_button.callback = session_menu

time_widget = DateTime()
hlwm_windowtitle = HLWMWindowTitle(hc_idle)

bar.widgets = [ RawLabel('%{l}'),
            HLWMTags(hc_idle),
            #Counter(),
            RawLabel('%{c}'),
            hlwm_windowtitle,
            RawLabel('%{r}'),
            time_widget,
]

inputs = [ hc_idle,
           bar
         ]

procwatch = [ ]

def nice_theme(widget):
    widget.pad_left  = '%{-o}%{U' + activecolor + '}%{B' + emphbg + '} '
    widget.pad_right = ' %{-o}%{B-}'

nice_theme(hlwm_windowtitle)
nice_theme(time_widget)

global_update = True

# main loop
while bar.is_running():
    now = time.clock_gettime(time.CLOCK_MONOTONIC)
    for w in bar.widgets:
        if w.maybe_timeout(now):
            global_update = True
    if global_update:
        text = ''
        for w in bar.widgets:
            text += w.render()
        text += '\n'
        #print(text, end='')
        bar.write_flushed(text)
        global_update = False
    # wait for new data
    next_timeout = math.inf
    for w in bar.widgets:
        next_timeout = min(next_timeout, w.next_timeout())
    now = time.clock_gettime(time.CLOCK_MONOTONIC)
    next_timeout -= now
    next_timeout = max(next_timeout,0.1)
    #print("next timeout = " + str(next_timeout))
    if next_timeout != math.inf:
        ready = select.select(inputs,[],[], next_timeout)[0]
    else:
        ready = select.select(inputs,[],[], 18)[0]
    if not ready:
        pass #print('timeout!')
    else:
        for x in ready:
            x.process()
            global_update = True
bar.proc.wait()

