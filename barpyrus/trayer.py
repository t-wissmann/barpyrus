#!/usr/bin/env python3

from barpyrus.widgets import Widget
from barpyrus.core import EventInput
from Xlib.display import Display, X

class WindowWatch(EventInput):
    """
    Run an external command that creates a window and then
    watch that window's size.
    """
    def __init__(self, command, is_right_window):
        """
        - command is a tokinzed command to invoke the process
        - is_right_window is a callback such that
            is_right_window(window) returns 'window' if it is a the window to watch
            and None otherwise.
        """

        self.display = Display()
        root = self.display.screen().root

        # get root window's current event mask and replace it in order to wait
        # passively for the trayer window
        old_mask = root.get_attributes().your_event_mask
        root.change_attributes(event_mask=X.SubstructureNotifyMask)
        self.display.sync()

        super(WindowWatch,self).__init__(command)
        self.proc.stdin.close()
        self.proc.stdout.close()

        # wait passively for trayer to create its window
        while True:
            event = self.display.next_event()
            self.trayer = self.find_tray_window(root, is_right_window)
            if self.trayer is not None:
                break

        # revert root window event_mask to remove unnecessary wakeups
        root.change_attributes(event_mask=old_mask)

        # activate ConfigureNotify-Events for self.trayer
        self.trayer.change_attributes(event_mask=X.StructureNotifyMask)

    def find_tray_window(self, root, is_right_window):
        children = root.query_tree().children
        for window in children:
            found = is_right_window(window)
            if found is not None:
                return found
            res = self.find_tray_window(window, is_right_window)
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
        return self.width

    def kill(self):
        self.proc.kill()
        self.display.close()

    def fileno(self):
        return self.display.fileno()

    def process(self):
        self.watch_trayer_non_blocking()


class TrayerWidget(Widget):
    def __init__(self, cmd = 'trayer', args = None):
        super(TrayerWidget,self).__init__()

        command = [ cmd ]
        self.default_args = {
            'edge': 'top',
            'align': 'right',
            'widthtype': 'request',
            'expand': 'true',
            'SetDockType': 'true',
            'SetPartialStrut': 'false',
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

        def is_trayer_window(window):
            if window.get_wm_class() and window.get_wm_class()[1] == 'trayer':
                return window
            else:
                return None

        self.trayer = WindowWatch(command, is_trayer_window)

    def render(self, painter):
        width = self.trayer.get_width() + int(self.default_args['margin'])
        painter.space(width)


class StalonetrayWidget(Widget):
    def __init__(self, panel_geometry, cmd='stalonetray', args=[]):
        """
        a widget that starts stalonetray and reserves space for it in
        the panel.
        panel_geometry is the geometry (x,y,width,height) of the panel
        """
        super(StalonetrayWidget,self).__init__()

        def is_tray_window(window):
            if window.get_wm_class() and window.get_wm_class()[1] == 'stalonetray':
                return window
            else:
                return None

        (panel_x, panel_y, panel_width, panel_height) = panel_geometry
        icon_size = panel_height

        command = [
            cmd,
            '--geometry', '1x1+{}+{}'.format(panel_x + panel_width - icon_size, panel_y),
            '--icon-size', str(icon_size),
            '--grow-gravity', 'E',
        ]
        command += args
        self.tray = WindowWatch(command, is_tray_window)

    def render(self, painter):
        width = self.tray.get_width()
        painter.space(width)
