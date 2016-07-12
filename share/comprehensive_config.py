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

# An example conky-section:
# icons
bat_icons = [
    0xe242, 0xe243, 0xe244, 0xe245, 0xe246,
    0xe247, 0xe248, 0xe249, 0xe24a, 0xe24b,
]
# first icon: 0 percent
# last icon: 100 percent
bat_delta = 100 / len(bat_icons)
conky_text = '%{F\\#9fbc00}%{T2}\ue026%{T-}%{F\\#989898}${cpu}% '
conky_text += '%{F\\#9fbc00}%{T2}\ue021%{T-}%{F\\#989898}${memperc}% '
conky_text += '%{F\\#9fbc00}%{T2}\ue13c%{T-}%{F\\#989898}${downspeedf}K '
conky_text += '%{F\\#9fbc00}%{T2}\ue13b%{T-}%{F\\#989898}${upspeedf}K '
conky_text += "${if_existing /sys/class/power_supply/BAT0}"
conky_text += "%{T2}"
conky_text += "${if_match \"$battery\" == \"discharging $battery_percent%\"}"
conky_text += "%{F\\#FFC726}"
conky_text += "$else"
conky_text += "%{F\\#9fbc00}"
conky_text += "$endif"
for i,icon in enumerate(bat_icons[:-1]):
    conky_text += "${if_match $battery_percent < %d}" % ((i+1)*bat_delta)
    conky_text += chr(icon)
    conky_text += "${else}"
conky_text += chr(bat_icons[-1]) # icon for 100 percent
for _ in bat_icons[:-1]:
    conky_text += "${endif}"
conky_text += "%{T-} $battery_percent% "
conky_text += "${endif}"
conky_text += "%{F-}"

# example options for the hlwm.HLWMLayoutSwitcher widget
xkblayouts = [
    'us us -variant altgr-intl us'.split(' '),
    'de de de'.split(' '),
]
setxkbmap = 'setxkbmap -option compose:menu -option ctrl:nocaps'
setxkbmap += ' -option compose:ralt -option compose:rctrl'

# you can define custom themes
grey_frame = Theme(bg = '#303030', fg = '#EFEFEF', padding = (3,3))

# Widget configuration:
bar = lemonbar.Lemonbar(geometry = (x,y,width,height))
bar.widget = W.ListLayout([
    W.RawLabel('%{l}'),
    hlwm.HLWMTags(hc, monitor, tag_renderer = hlwm.underlined_tags),
    W.RawLabel('%{c}'),
    hlwm.HLWMMonitorFocusLayout(hc, monitor,
           # this widget is shown on the focused monitor:
           grey_frame(hlwm.HLWMWindowTitle(hc)),
           # this widget is shown on all unfocused monitors:
           conky.ConkyWidget('df /: ${fs_used_perc /}%')
                                    ),
    W.RawLabel('%{r}'),
    conky.ConkyWidget(text= conky_text),
    # something like a tabbed widget with the tab labels '>' and '<'
    W.ShortLongLayout(
        W.RawLabel(''),
        W.ListLayout([
            hlwm.HLWMLayoutSwitcher(hc, xkblayouts, command = setxkbmap.split(' ')),
            W.RawLabel(' '),
        ])),
        grey_frame(W.DateTime('%d. %B, %H:%M')),
])


