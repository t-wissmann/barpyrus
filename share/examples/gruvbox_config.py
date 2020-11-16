import os
import sys

from barpyrus import hlwm
from barpyrus import widgets as W
from barpyrus.core import Theme
from barpyrus import lemonbar
from barpyrus import conky
from barpyrus.colors import (
    AQUA_LIGHT,
    GREEN_LIGHT,
    YELLOW_LIGHT,
    PURPLE_LIGHT,
    BLUE_LIGHT,
    ORANGE_LIGHT,
    RED_LIGHT,
    FG,
    BG,
)
from barpyrus.conky import col_fmt
# Copy this config to ~/.config/barpyrus/config.py

# set up a connection to herbstluftwm in order to get events
# and in order to call herbstclient commands
hc = hlwm.connect()

# get the geometry of the monitor
monitor = sys.argv[1] if len(sys.argv) >= 2 else 0
(x, y, monitor_w, monitor_h) = hc.monitor_rect(monitor)
height = 14  # height of the panel
width = monitor_w  # width of the panel
hc(['pad', str(monitor), str(height)])  # get space for the panel

# Conky setup
custom = ''

mail_symb = '\ue1a8'
inbox = os.path.expanduser('~/.mail/INBOX')
mail = col_fmt(AQUA_LIGHT) + mail_symb + col_fmt(FG) + ' ${new_mails %s}/${mails %s}' % (inbox, inbox)

disk_symb = '\ue1bb'
disk_usage = col_fmt(GREEN_LIGHT) + disk_symb + col_fmt(FG) + '${fs_free}/${fs_size}'

on_symb = '\ue10c'
uptime = col_fmt(GREEN_LIGHT) + on_symb + col_fmt(FG) + '${uptime_short}'

##########
# volume #
##########
vol_off_symb = col_fmt(FG) + '\ue202'
speaker_symb = col_fmt(YELLOW_LIGHT) + '\ue203'
headphone_symb = col_fmt(YELLOW_LIGHT) + '\ue0fd'
bluetooth_symb = col_fmt(BLUE_LIGHT) + '\ue1b5'
vol_on_symb = '${if_match \"$pa_sink_active_port_name\" == \"analog-output-headphones\"}'
vol_on_symb += headphone_symb
vol_on_symb += '${else}'

vol_on_symb += '${if_match \"$pa_sink_active_port_name\" == \"headset-output\"}'
vol_on_symb += headphone_symb + bluetooth_symb
vol_on_symb += '${else}'
vol_on_symb += speaker_symb
vol_on_symb += '${endif}'

vol_on_symb += '${endif}'

volume = '${if_pa_sink_muted}' + vol_off_symb + '${else}' + vol_on_symb + '${endif}'
volume += col_fmt(FG) + '${pa_sink_volume}%'

###########
# various #
###########
cpu_symb = '\ue026'
cpu = col_fmt(PURPLE_LIGHT) + cpu_symb + col_fmt(FG) + '${cpu}%'
ram_symb = '\ue021'
ram = col_fmt(PURPLE_LIGHT) + ram_symb + col_fmt(FG) + '${memperc}%'
net_down_speed_symb = '\ue13c'
net_down_speed = col_fmt(RED_LIGHT) + net_down_speed_symb + col_fmt(FG) + '${downspeedf}K'
net_up_speed_symb = '\ue13b'
net_down_speed = col_fmt(GREEN_LIGHT) + net_up_speed_symb + col_fmt(FG) + '${upspeedf}K'

########
# wifi #
########
no_wifi_symb = '\ue217'
wifi_icons = ['\ue218', '\ue219', '\ue21a']
wifi_delta = 100 / len(wifi_icons)
# Find the wifi name
wifi_name = None
for net in os.listdir('/sys/class/net'):
    if net[0] == 'w':
        wifi_name = net
        break
if wifi_name is None:
    wifi = col_fmt(FG) + no_wifi_symb
else:
    wifi_qual = '${wireless_link_qual_perc %s}' % wifi_name
    wifi = ''
    for i, icon in enumerate(wifi_icons[:-1]):
        wifi += '${if_match ' + wifi_qual + ' < %d}' % ((i + 1) * wifi_delta)
        wifi += col_fmt(BLUE_LIGHT) + icon
        wifi += '${else}'
    wifi += col_fmt(BLUE_LIGHT) + wifi_icons[-1]  # 100 %
    for _ in range(len(wifi_icons) - 1):
        wifi += '${endif}'
    wifi += col_fmt(FG) + ' ' + wifi_qual + '%'

###########
# battery #
###########
battery = "${if_existing /sys/class/power_supply/BAT0}"
battery += "%{T2}"
battery += "${if_match \"$battery\" == \"discharging $battery_percent%\"}"
battery += col_fmt(ORANGE_LIGHT)
battery += "$else"
battery += col_fmt(GREEN_LIGHT)
battery += "$endif"
bat_icons = [
    0xe242, 0xe243, 0xe244, 0xe245, 0xe246,
    0xe247, 0xe248, 0xe249, 0xe24a, 0xe24b,
]
# first icon: 0 percent
# last icon: 100 percent
bat_delta = 100 / len(bat_icons)
for i, icon in enumerate(bat_icons[:-1]):
    battery += "${if_match $battery_percent < %d}" % ((i+1)*bat_delta)
    battery += chr(icon)
    battery += "${else}"
battery += chr(bat_icons[-1])  # icon for 100 percent
for _ in bat_icons[:-1]:
    battery += "${endif}"
battery += "%{T-} $battery_percent%"
battery += "${endif}"

conky_elements = [
    custom,
    mail,
    wifi,
    volume,
    disk_usage,
    cpu,
    ram,
    # net_down_speed,
    # net_up_speed,
    battery,
    uptime,
]

conky_text = ' '.join(conky_elements) + ' '


# example options for the hlwm.HLWMLayoutSwitcher widget
xkblayouts = [
    'us us -variant altgr-intl us'.split(' '),
    'de de de'.split(' '),
]
setxkbmap = 'setxkbmap -option compose:menu -option ctrl:nocaps'
setxkbmap += ' -option compose:ralt -option compose:rctrl'

# you can define custom themes
grey_frame = Theme(bg=BG, fg=FG, padding=(3, 3))

# Widget configuration:
font = '-*-fixed-medium-*-*-*-15-*-*-*-*-*-iso10646-1'
symbol_font = '-wuncon-siji-medium-r-normal--10-100-75-75-c-80-iso10646-1'
bar = lemonbar.Lemonbar(
    geometry=(x, y, width, height),
    font=font,
    symbol_font=symbol_font,
)
update_interval = '1'
bar.widget = W.ListLayout([
    W.RawLabel('%{l}'),
    # hlwm.HLWMTags(hc, monitor, tag_renderer=hlwm.underlined_tags),
    hlwm.HLWMTags(hc, monitor),
    W.RawLabel('%{c}'),
    grey_frame(hlwm.HLWMWindowTitle(hc)),
    # hlwm.HLWMMonitorFocusLayout(hc, monitor,
    #        # this widget is shown on the focused monitor:
    #        grey_frame(hlwm.HLWMWindowTitle(hc)),
    #        # this widget is shown on all unfocused monitors:
    #        conky.ConkyWidget('df /: ${fs_used_perc /}%'),
    #        # conky.ConkyWidget(' '),
    # ),
    W.RawLabel('%{r}'),
    conky.ConkyWidget(
        text=conky_text,
        config={'update_interval': update_interval},
    ),
    # something like a tabbed widget with the tab labels '>' and '<'
    W.ShortLongLayout(
        W.RawLabel(''),
        W.ListLayout([
            hlwm.HLWMLayoutSwitcher(hc, xkblayouts, command=setxkbmap.split(' ')),
            W.RawLabel(' '),
        ]),
    ),
    grey_frame(W.DateTime('%d. %B, %H:%M')),
])
