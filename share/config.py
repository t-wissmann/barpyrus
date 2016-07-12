from barpyrus import hlwm
from barpyrus import widgets as W
from barpyrus.core import Theme
from barpyrus import lemonbar
from barpyrus import conky
import sys

# Copy this config to ~/.config/barpyrus/config.py

# set up a connection to herbstluftwm in order to get events
# and in order to call herbstclient commands
hc = hlwm.connect()

# get the geometry of the monitor
monitor = sys.argv[1] if len(sys.argv) >= 2 else 0
(x, y, monitor_w, monitor_h) = hc.monitor_rect(monitor)
height = 16 # height of the panel
width = monitor_w # width of the panel
hc(['pad', str(monitor), str(height)]) # get space for the panel

# you can define custom themes
grey_frame = Theme(bg = '#303030', fg = '#EFEFEF', padding = (3,3))

# Widget configuration:
bar = lemonbar.Lemonbar(geometry = (x,y,width,height))
bar.widget = W.ListLayout([
    W.RawLabel('%{l}'),
    hlwm.HLWMTags(hc, monitor),
    W.RawLabel('%{c}'),
    grey_frame(hlwm.HLWMWindowTitle(hc)),
    W.RawLabel('%{r}'),
    conky.ConkyWidget('df /: ${fs_used_perc /}%'),
    grey_frame(W.DateTime('%d. %B, %H:%M')),
])


