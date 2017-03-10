import sys
import os

# Change path so we find Xlib
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from Xlib import X, display, Xutil
from Xlib.protocol import request

# Application window (only one)
class WindowFrame():
    def __init__(self, outer_geometry, border_width):
        self.d = display.Display()
        (x,y,w,h) = outer_geometry
        w -= 2 * border_width
        h -= 2 * border_width

        # Find which screen to open the window on
        self.screen = self.d.screen()

        self.window = self.screen.root.create_window(
            x, y, w, h, border_width,
            self.screen.root_depth,
            X.InputOutput,
            X.CopyFromParent,

            # special attribute values
            background_pixel = self.screen.white_pixel,
            event_mask = (X.ExposureMask |
                          X.StructureNotifyMask |
                          X.ButtonPressMask |
                          X.ButtonReleaseMask |
                          X.Button1MotionMask),
            colormap = X.CopyFromParent,
            override_redirect = True,
            )

        self.gc = self.window.create_gc(
            foreground = self.screen.black_pixel,
            background = self.screen.white_pixel,
            )

        # Set some WM info

        self.WM_DELETE_WINDOW = self.d.intern_atom('WM_DELETE_WINDOW')
        self.WM_PROTOCOLS = self.d.intern_atom('WM_PROTOCOLS')

        self.window.set_wm_name('Xlib example: draw.py')
        self.window.set_wm_icon_name('draw.py')
        self.window.set_wm_class('draw', 'XlibExample')

        self.window.set_wm_protocols([self.WM_DELETE_WINDOW])
        self.window.set_wm_hints(flags = Xutil.StateHint,
                                 initial_state = Xutil.NormalState)

        self.window.set_wm_normal_hints(flags = (Xutil.PPosition | Xutil.PSize
                                                 | Xutil.PMinSize),
                                        min_width = 20,
                                        min_height = 20)

        # Map the window, making it visible
        self.window.map()
        while self.d.pending_events() >= 1:
            self.handle_event(self.d.next_event())


    # Main loop, handling events
    def handle_event(self, e):
        # Window has been destroyed, quit
        if e.type == X.DestroyNotify:
            sys.exit(0)


        # Mouse movement with button pressed, draw
        if e.type == X.MotionNotify and current:
            current.motion(e)

        if e.type == X.ClientMessage:
            if e.client_type == self.WM_PROTOCOLS:
                fmt, data = e.data
                if fmt == 32 and data[0] == self.WM_DELETE_WINDOW:
                    sys.exit(0)

    def swallow(self, other):
        request.ReparentWindow(display = self.display,
                               onerror = None,
                               window = other,
                               parent = self.id,
                               x = 0,
                               y = 0)


