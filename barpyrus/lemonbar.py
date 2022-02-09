
from barpyrus.core import EventInput
from barpyrus.core import TextPainter

def textpainter():
    return Lemonbar.LBPainter(None)


class Lemonbar(EventInput):
    def __init__(self, geometry = None,
                 cmd = 'lemonbar',
                 font = '-*-fixed-medium-*-*-*-12-*-*-*-*-*-iso10646-1',
                 symbol_font = '-wuncon-siji-medium-r-normal--10-100-75-75-c-80-iso10646-1',
                 # Setting symbol_vert_offset only works if the underlying lemonbar takes the flag `-o`
                 # for adding a vertical offset for the text. E.g lemonbar-xft does this
                 # https://github.com/drscream/lemonbar-xft
                 symbol_vert_offset=None,
                 background = '#ee121212',
                 foreground = '#989898',
                 spacing_font=(1, '-*-*-*-*-*-*-2-*-*-*-*-*-*-*'),
                 lemonbar_old_percent_escapes = False,
                 args = []):
        """
        the spacing_font=(n,font) is a font for which the space character
        has the width of n pixels
        """
        # since https://github.com/LemonBoy/bar/commit/1411d260a4c6956ff5a3699ee9bfd5b275209fe3
        # lemonbar handles the escaping of % symbols correctly. If you have an
        # old lemonbar installation, you must set
        #
        #   lemonbar_old_percent_escapes = True
        #
        command = [ cmd ]
        if geometry:
            (x,y,w,h) = geometry
            command += [ '-g', "%dx%d%+d%+d" % (w,h,x,y)  ]
        command += '-a 100 -d -u 2'.split(' ')
        command += [ '-B', background  ]
        command += [ '-F', foreground  ]
        if symbol_vert_offset is not None:
            command += [ '-o 0' ]
        command += [ '-f', font  ]
        if symbol_vert_offset is not None:
            command += [ '-o 0' ]
        command += ['-f', spacing_font[1]]
        self.spacing_font_width = spacing_font[0]
        if symbol_font != None:
            if symbol_vert_offset is not None:
                command += [ '-o -%d' % symbol_vert_offset ]
            command += [ '-f', symbol_font ]
        command += args
        super(Lemonbar,self).__init__(command)
        self.widget = None
        self.lemonbar_old_percent_escapes = lemonbar_old_percent_escapes
        self.clickareas = { }

    def handle_line(self,line):
        if line in self.clickareas:
            (callback, b) = self.clickareas[line]
            callback(b)
        #elif len(line.split('_')) == 2 and self.widget != None:
        #    # temporary workaround during dransition to painters
        #    line = line.split('_')
        #    name = line[0]
        #    btn = int(line[1])
        #    self.widget.can_handle_input(name, btn)
        else:
            print("invalid event name: %s" % line)
    class LBPainter(TextPainter):
        def __init__(self,lemonbar):
            super(Lemonbar.LBPainter,self).__init__()
            self.buf = ""
            self.lemonbar = lemonbar
            self.next_click_id = 0
        def drawRaw(self, text):
            self.buf += text
        def text(self, text):
            if self.lemonbar is None or \
                not self.lemonbar .lemonbar_old_percent_escapes:
                self.buf += text.replace('%', '%%')
            else:
                self.buf += text.replace('%', '%%{}')
        def set_ul(self, enabled):
            self.buf += '%{+u}' if enabled else '%{-u}'
        def set_ol(self, enabled):
            self.buf += '%{+o}' if enabled else '%{-o}'
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
            self.buf += '%{T3}' + chr(symbol) + '%{T-}'
        def flush(self):
            self.lemonbar.write_flushed(self.buf + '\n')
        def __str__(self):
            return self.buf
        def space(self, width):
            if hasattr(self.lemonbar, 'spacing_font_width'):
                factor = self.lemonbar.spacing_font_width
            else:
                factor = 1
            self.buf += '%{T2}' + (' ' * int(width / factor)) + '%{T-}'
        def _enter_clickable(self, clickable):
            click_id = self.next_click_id
            self.next_click_id += 1
            for b in clickable.buttons:
                clickname = f'{click_id}_{b}'
                self.buf += '%%{A%d:%s:}' % (b, clickname)
                self.lemonbar.clickareas[clickname] = (clickable.callback, b)
        def _exit_clickable(self, clickable):
            for b in clickable.buttons:
                self.buf += '%{A}'
    def painter(self):
        return Lemonbar.LBPainter(self)

