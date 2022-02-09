#!/usr/bin/env python3

from barpyrus.widgets import Widget
from barpyrus.core import EventInput
from Xlib.display import Display, X
import Xlib
import sys

class WindowWatch(EventInput):
    """
    Run an external command that creates a window and then
    watch that window's size.
    """
    def __init__(self, command, is_right_window, kill_old_instance=False):
        """
        - command is a tokinzed command to invoke the process
        - is_right_window is a callback such that
            is_right_window(window) returns 'window' if it is a the window to watch
            and None otherwise.
        - if kill_old_instance is set, then all clients matching
          is_right_window() are killed before 'command' is invoked.
        """

        self.display = Display()
        root = self.display.screen().root

        # get root window's current event mask and replace it in order to wait
        # passively for the trayer window
        old_mask = root.get_attributes().your_event_mask
        root.change_attributes(event_mask=X.SubstructureNotifyMask)
        self.display.sync()

        if kill_old_instance:
            while True:
                old_tray = self.find_tray_window(root, is_right_window)
                if old_tray is None:
                    # no old instance
                    break
                # force shutdown:
                old_tray.kill_client()
                # wait for an event, i.e. any kind of updater from X
                self.display.next_event()

        # start the process:
        super(WindowWatch,self).__init__(command)
        self.proc.stdin.close()
        self.proc.stdout.close()

        # wait passively for trayer to create its window
        while self.proc.poll() is None:
            event = self.display.next_event()
            self.trayer = self.find_tray_window(root, is_right_window)
            if self.trayer is not None:
                break

        if self.proc.poll() is not None:
            print("command »{}« exited unexpectedly.".format(' '.join(command)), file=sys.stderr)
            return

        # revert root window event_mask to remove unnecessary wakeups
        root.change_attributes(event_mask=old_mask)

        # activate ConfigureNotify-Events for self.trayer
        self.trayer.change_attributes(event_mask=X.StructureNotifyMask)

    def find_tray_window(self, root, is_right_window):
        children = root.query_tree().children
        for window in children:
            try:
                found = is_right_window(window)
                if found is not None:
                    return found
                res = self.find_tray_window(window, is_right_window)
                if res:
                    return res
            except Xlib.error.BadWindow as e:
                # if a window disappeared while inspecting it,
                # just skip it.
                pass
        return None

    def watch_trayer_non_blocking(self):
        while self.display.pending_events() > 0:
            event = self.display.next_event()
            if event.type != X.ConfigureNotify:
                continue
            if event.window != self.trayer:
                continue

    def get_width(self):
        try:
            self.width = self.trayer.get_geometry().width
        except Xlib.error.BadWindow:
            self.width = 0
        except Xlib.error.BadDrawable:
            self.width = 0
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
    def __init__(self, panel_geometry, cmd='stalonetray', args=[], width_factor=1):
        """
        a widget that starts stalonetray and reserves space for it in
        the panel.
        panel_geometry is the geometry (x,y,width,height) of the panel
        if the stalonetray window has width n, then
        this will reserve width_factor*n spaces on the bar
        """
        super(StalonetrayWidget,self).__init__()
        self.width_factor = width_factor

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
            '--kludges=force_icons_size,fix_window_pos',  # force icon size in apps like steam
        ]
        command += args
        self.tray = WindowWatch(command, is_tray_window, kill_old_instance=True)

    def render(self, painter):
        width = int(self.tray.get_width() * self.width_factor)
        painter.space(width)
