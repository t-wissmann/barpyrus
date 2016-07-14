# barpyrus
A python wrapper for lemonbar, targeting to herbstluftwm users.

This is basically a python3-rewrite of my panel.sh for herbstluftwm.

## configuration
The configuration is a python file and is located at
`~/.config/barpyrus/config.py`. There is no documentation yet, but you can find
some example configuratons in the `share/` directory.

## usage in herbstluftwm
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
