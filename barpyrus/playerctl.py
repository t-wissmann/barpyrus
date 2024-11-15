import sys
import html
from barpyrus.widgets import Widget
from barpyrus.core import EventInput, Painter
import barpyrus.colors
import subprocess

class PlayerctlFollow(EventInput):
    def __init__(self, playerctl_prefix, variables):
        self.variables = variables
        format_str = '<>'.join(['{{markup_escape(' + v + ')}}' for v in variables])
        self.full_cmd = playerctl_prefix + [
            '--follow',
            '--format=' + format_str,
            'metadata'
        ]
        super(PlayerctlFollow,self).__init__(self.full_cmd)
        self.proc.stdin.close()
        self.callback = lambda line: self.parse_line(line)
        self.values = {}

    def parse_line(self, line):
        if line == '':
            # clear all metadata on empty line
            self.values = { key: '' for key in self.variables }
        else:
            fields = line.split('<>')
            if len(fields) != len(self.variables):
                print("Error: requested {} fields from playerctl but obtained {} fields"
                      .format(len(self.variables), len(fields)),
                      file=sys.stderr)
            for key, value in zip(self.variables, fields):
                self.values[key] = html.unescape(value)

    def __getitem__(self, key):
        return self.values.get(key, '')


class Playerctl(Widget):
    def __init__(self, player=None, playerctl='playerctl'):
        """
        Show the current media player status
        using `playerctl`
        """
        super(Playerctl,self).__init__()
        playerctl_prefix = [
            playerctl,
        ]
        if player is not None:
            playerctl_prefix.append('--player=' + player)
        variables = [
            'playerName',
            'artist',
            'title',
            'status',
            'album',
            'mpris:trackid',
            'xesam:artist',
            'xesam:title',
        ]
        self.playerctl = PlayerctlFollow(playerctl_prefix, variables)
        # save the command without --player, because we take the player
        # name from the most recent output of 'playerctl metadata'
        self.playerctl_command = [playerctl]

    def __getitem__(self, key):
        return self.playerctl.values.get(key, '')

    def call(self, *command):
        # always send commands to the player whose status is displayed:
        playerName = self.playerctl['playerName']
        if len(playerName) > 0:
            playerArg = ['--player=' + playerName]
        else:
            playerArg = []
        full_cmd = self.playerctl_command + playerArg + list(command)
        subprocess.call(full_cmd)

    def is_empty(self):
        return self.playerctl['playerName'] == ''

    def render(self, p):
        # music_notes = [
        #     0xe270,
        #     0xe271,
        #     0xe272,
        #     0xe273,
        # ]
        # p.fg(barpyrus.colors.GRAY_LIGHT)
        # p.symbol(music_notes[1])
        if self.playerctl['playerName'] == '':
            return
        artist = self.playerctl['artist']
        if len(artist) == 0:
            artist = self.playerctl['xesam:artist']
        artist = artist[0:30]
        title = self.playerctl['title']
        if len(title) == 0:
            title = self.playerctl['xesam:title']
        title = title[0:30]
        # buttons don't work correctly
        # in the centered area of lemonbar-xft
        with p.clickable(1, lambda b: self.call('previous')):
            p.fg(barpyrus.colors.PURPLE_DARK)
            p.symbol(0xe096)  # prev icon
        p.fg(barpyrus.colors.PURPLE_DARK)
        with p.clickable(1, lambda b: self.call('play-pause')):
            if self['status'] == 'Playing':
                p.symbol(0xe059)  # Pause icon
            else:
                p.symbol(0xe058)  # Play icon
        with p.clickable(1, lambda b: self.call('next')):
            p.symbol(0xe09c)  # next icon
        p += ' '
        p.fg(barpyrus.colors.GRAY_LIGHT)
        p.fg(barpyrus.colors.GREEN_LIGHT)
        if len(artist) > 0:
            p += artist
            p.fg(barpyrus.colors.GRAY_LIGHT)
            p += ': '
        p.fg(barpyrus.colors.ORANGE_LIGHT)
        p += title
        p.fg(barpyrus.colors.GRAY_LIGHT)
        if self['album'] != '':
            p += ' ('
            p.fg(barpyrus.colors.YELLOW_LIGHT)
            p += self.playerctl['album']
            p.fg(barpyrus.colors.GRAY_LIGHT)
            p += ')'
        # p.space(1)
        # p.symbol(music_notes[2])

    def eventinputs(self):
        return [ self.playerctl ]
