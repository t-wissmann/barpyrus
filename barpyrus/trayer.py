#!/usr/bin/env python3

from barpyrus.widgets import Widget
from barpyrus.core import EventInput
from Xlib.display import Display, X

class TrayerWatch(EventInput):
    def __init__(self, args = None):
        command = [ 'trayer' ]
        self.default_args = {
            'edge': 'top',
            'align': 'right',
            'widthtype': 'request',
            'expand': 'true',
            'SetDockType': 'true',
            'transparent': 'true',
            'alpha': '0',
            'height': '16',
            'margin': '0',
            'tint': '0x29b2e',
        }
        if args is not None:
            self.default_args.update(args)
        for key,val in self.default_args.items():
            command += ["--%s" % (key), str(val)]

        super(TrayerWatch,self).__init__(command)
        self.proc.stdin.close()
        self.proc.stdout.close()

        # search for running trayer window
        self.display = Display()
        root = self.display.screen().root
        self.trayer = self.find_tray_window(root)
        assert self.trayer is not None, 'Panel not found!'
        
        # activate ConfigureNotify-Events for self.trayer
        self.trayer.change_attributes(event_mask=X.StructureNotifyMask)

    def find_tray_window(self, root, tray_name='trayer'):
        children = root.query_tree().children
        for window in children:
            if window.get_wm_class() and window.get_wm_class()[1] == tray_name:
                return window
            res = self.find_tray_window(window, tray_name)
            if res:
                return res
        return None

    def watch_trayer_non_blocking(self):
        while self.display.pending_events() > 0:
            event = self.display.next_event()
            if event.type != X.ConfigureNotify:
                continue
            if event.window != self.trayer:
                continue

    def get_width(self):
        self.width = self.trayer.get_geometry().width
        return self.width + int(self.default_args['margin'])

    def kill(self):
        self.proc.kill()
        self.display.close()

    def fileno(self):
        return self.display.fileno()

    def process(self):
        self.watch_trayer_non_blocking()


class TrayerWidget(Widget):
    def __init__(self, args = None):
        super(TrayerWidget,self).__init__()
        self.trayer = TrayerWatch(args=args)

    def render(self, painter):
        painter.space(self.trayer.get_width())
