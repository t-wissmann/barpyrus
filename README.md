# barpyrus
A python wrapper for lemonbar, targeting to herbstluftwm users.

This is basically a python3-rewrite of my panel.sh for herbstluftwm.

## Configuration
The configuration is a python file and is located at
`~/.config/barpyrus/config.py`. There is no documentation yet, but you can find
some example configuratons in the `share/` directory.

## Requirements
You need to have the following things installed:

- [lemonbar](https://github.com/lemonboy/bar)

Optional:

- [siji font](https://github.com/stark/siji) (default `symbol_font` used)
- [herbstluftwm](https://github.com/herbstluftwm/herbstluftwm) (for the `hlwm` integration)
- conky (to use the conky widget)
- setuptools (if installing via `setup.py`)
- pytz (if using `tz_name` for `widgets.DateTime`)
- python-xlib (to use the `trayer` integration)
- trayer (to use the `trayer` integration)
- playerctl (to use the `playerctl` integration)

## Usage in herbstluftwm
To install it type:
```
# first back up your old panel.sh
mv -f ~/.config/herbstluftwm/panel.sh ~/.config/herbstluftwm/backup_panel.sh
# link barpyrus:
ln -s ~/path/to/barpyrus.py ~/.config/herbstluftwm/panel.sh
```

If you just want to have a quick look, you can run it directly:
```
./barpyrus.py
```

## License
barpyrus is licensed under the [simplified BSD license](LICENSE).

## Examples

[![image](https://user-images.githubusercontent.com/9048813/143689969-e92fe9ab-9390-4726-bed2-b80192f591e3.png)](https://user-images.githubusercontent.com/9048813/143689969-e92fe9ab-9390-4726-bed2-b80192f591e3.png)
