#!/usr/bin/env python3

import subprocess
import time
import sys
import select
import os
import math


def hc(args):
    cmd = [ "herbstclient", "-n" ]
    cmd += args;
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    proc.wait()
    return proc.stdout.read().decode("utf-8")

def spawn_bar(geometry = None):
    lemonbar_args = '-u 2 -B #ee121212 -f -*-fixed-medium-*-*-*-12-*-*-*-*-*-*-*'.split(' ')
    command = [ "lemonbar" ]
    if geometry:
        (x,y,w,h) = geometry
        command += [ '-g', "%dx%d%+d%+d" % (w,h,x,y)  ]
    command += lemonbar_args
    (x,y,w,h)
    lemonbar = subprocess.Popen(command,
                                stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE)
    return lemonbar

def spawn_hc_idle():
    cmd = [ 'herbstclient', '--idle' ]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE)

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
    def __init__(self):
        super(HLWMTags,self).__init__()
        self.needs_update = True
        self.tags = [ ]
        self.tag_count = 0
        self.buttons = [4, 5]
        self.pad_right = '%{F-}%{B-}%{-o}'
        self.update_tags()

    def update_tags(self):
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


class LineReader(object):
    # thanks to http://stackoverflow.com/questions/5486717/python-select-doesnt-signal-all-input-from-pipe
    def __init__(self, fd, callback):
        # read all available lines from fd and call
        # the callback for each complete line
        self._fd = fd
        self._buf = ''
        self.callback = callback
    def fileno(self):
        return self._fd
    def readlines(self):
        data = os.read(self._fd, 4096).decode('utf-8')
        if not data:
            # EOF
            return None
        self._buf += data
        if '\n' not in data:
            return []
        tmp = self._buf.split('\n')
        lines, self._buf = tmp[:-1], tmp[-1]
        return lines
    def handle_lines(self):
        for line in self.readlines():
            self.callback(line)

def bar_handle_input(line):
    line = line.split('_')
    if len(line) != 2:
        print("invalid event name: %s" % '_'.join(line))
    else:
        #print("bar event: %s" % '_'.join(line))
        name = line[0]
        btn = int(line[1])
        for w in widgets:
            if w.can_handle_input(name, btn):
                break

hlwm_hooks = { }

def hlwm_handle_input(line):
    args = line.split('\t')
    #print('event: ' + ' , '.join(args))
    if len(args) == 0:
        return
    if args[0] in hlwm_hooks:
        #print("hlwm event: %s" % line)
        hlwm_hooks[args[0]](args[1:])

# some more example widgets:
class Counter(Button):
    def __init__(self):
        super(Counter,self).__init__('x')
        self.c = 0
    def on_click(self,btn):
        self.c += 1
        self.c %= 5
    def content(self):
        return ('c=%d' % self.c)

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
height = 16

bar = spawn_bar(geometry = (x,y,monitor_w,height))
hc_idle = spawn_hc_idle()

# widgets
hlwm_windowtitle = Label(hc(['attr', 'clients.focus.title']))
def update_window_title(args):
    if len(args) >= 2:
        hlwm_windowtitle.label = args[1]
    else:
        hlwm_windowtitle.label = ''
hlwm_hooks['focus_changed'] = update_window_title
hlwm_hooks['window_title_changed'] = update_window_title

hlwm_tags = HLWMTags()
def update_tags(args):
    hlwm_tags.update_tags()
hlwm_hooks['tag_changed'] = update_tags
hlwm_hooks['tag_flags'] = update_tags
hlwm_hooks['tag_added'] = update_tags
hlwm_hooks['tag_removed'] = update_tags

time_widget = DateTime()

widgets = [ RawLabel('%{l}'),
            hlwm_tags,
            #Counter(),
            RawLabel('%{c}'),
            hlwm_windowtitle,
            RawLabel('%{r}'),
            time_widget,
]
inputs = [ LineReader(bar.stdout.fileno(), bar_handle_input),
           LineReader(hc_idle.stdout.fileno(), hlwm_handle_input),
         ]

def nice_theme(widget):
    widget.pad_left  = '%{-o}%{U' + activecolor + '}%{B' + emphbg + '} '
    widget.pad_right = ' %{-o}%{B-}'

nice_theme(hlwm_windowtitle)
nice_theme(time_widget)

global_update = True

# main loop
while bar.pid != None:
    now = time.clock_gettime(time.CLOCK_MONOTONIC)
    for w in widgets:
        if w.maybe_timeout(now):
            global_update = True
    if global_update:
        text = ''
        for w in widgets:
            text += w.render()
        text += '\n'
        #print(text, end='')
        bar.stdin.write(text.encode('utf-8'))
        bar.stdin.flush()
        global_update = False
    # wait for new data
    next_timeout = math.inf
    for w in widgets:
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
            x.handle_lines()
            global_update = True
bar.wait()

