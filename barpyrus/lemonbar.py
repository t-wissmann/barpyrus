
from barpyrus.core import EventInput
from barpyrus.core import TextPainter

def textpainter():
    return Lemonbar.LBPainter(None)


class Lemonbar(EventInput):
    def __init__(self, geometry = None,
                 cmd = 'lemonbar',
                 font = '-*-fixed-medium-*-*-*-12-*-*-*-*-*-iso10646-1',
                 symbol_font = '-wuncon-siji-medium-r-normal--10-100-75-75-c-80-iso10646-1',
                 background = '#ee121212',
                 foreground = '#989898',
                 lemonbar_old_percent_escapes = False,
                 args = []):
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
        command += [ '-f', font  ]
        command += '-f -*-*-*-*-*-*-2-*-*-*-*-*-*-*'.split(' ')
        if symbol_font != None:
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
            self.buf += '%{T2}' + (' ' * width) + '%{T-}'
        def _enter_clickable(self, clickable):
            for b in clickable.buttons:
                clickname = str(id(clickable.obj)) + '_' + str(b)
                self.buf += '%%{A%d:%s:}' % (b,clickname)
                self.lemonbar.clickareas[clickname] = (clickable.callback, b)
        def _exit_clickable(self, clickable):
            for b in clickable.buttons:
                self.buf += '%{A}'
    def painter(self):
        return Lemonbar.LBPainter(self)

