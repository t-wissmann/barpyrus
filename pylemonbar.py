#!/usr/bin/env python3

import subprocess
import time # only for sleep()
import sys
import select


def hc(args):
    cmd = [ "herbstclient", "-n" ]
    cmd += args;
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    proc.wait()
    return proc.stdout.read().decode("utf-8")

def spawn_bar(geometry = None):
    lemonbar_args = [ ]
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

widget_nr = 0
class Widget:
    def __init__(self):
        self.interval = None
        self.timeout = None
        self.buttons = [ ]
        global widget_nr
        widget_nr += 1
        self.click_id = 'widget' + str(widget_nr)
    def timeout(self):
        pass
    def render(self):
        begin = ''
        end = ''
        for b in self.buttons:
            clickname = self.click_id + '_' + str(b)
            begin += '%%{A%d:%s:}' % (b,clickname)
            end += '%{A}'
        return begin + self.content() + end
    def content(self):
        return 'widget'
    def can_handle_input(self, click_id, btn):
        if click_id == self.click_id:
            self.on_click(btn)
            return True
    def on_click(self, button):
        pass

class Button(Widget):
    def __init__(self,label):
        super(Button,self).__init__()
        self.label = label
        self.pad_left = ' '
        self.pad_right = ' '
        self.buttons = [ 1 ]
    def content(self):
        return self.pad_left + self.label + self.pad_right
    def on_click(self, button):
        print("click %d!" % button)

class BarEventReader:
    def fileno(self):
        return bar.stdout.fileno()
    def handle_input(self):
        line = bar.stdout.readline().decode('utf-8').split('_')
        if len(line) != 2:
            print("invalid event name: %s" % '_'.join(line))
        else:
            name = line[0]
            btn = int(line[1])
            for w in widgets:
                if w.can_handle_input(name, btn):
                    break


class HLWMEventReader:
    def fileno(self):
        return hc_idle.stdout.fileno()
    def handle_input(self):
        line = hc_idle.stdout.readline().decode('utf-8').rstrip('\n')
        args = line.split('\t')
        print('event: ' + ' , '.join(args))

# ---- configuration ---
monitor = 0
geometry = hc(['monitor_rect', str(monitor)]).split(' ')
x = int(geometry[0])
y = int(geometry[1])
monitor_w = int(geometry[2])
monitor_h = int(geometry[3])
height = 16

bar = spawn_bar(geometry = (x,y,monitor_w,height))
hc_idle = spawn_hc_idle()
widgets = [ Button('click me') ]
inputs = [ BarEventReader(), HLWMEventReader() ]


# main loop
while bar.pid != None:
    text = ''
    for w in widgets:
        text += w.render()
    text += '\n'
    bar.stdin.write(text.encode('utf-8'))
    bar.stdin.flush()
    # wait for new data
    (ready,_,_) = select.select(inputs,[],[], 1)
    if not ready:
        print('timeout!')
    else:
        for x in ready:
            x.handle_input()
bar.wait()

