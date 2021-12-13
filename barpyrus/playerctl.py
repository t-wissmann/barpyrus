import sys
import html
from barpyrus.widgets import Widget
from barpyrus.core import EventInput, Painter
import barpyrus.colors

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
        fields = line.split('<>')
        if len(fields) != len(self.variables):
            print("Error: requested {} fields from playerctl but obtained {} fields"
                  .format(len(fields), len(self.variables)),
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
            'artist',
            'title',
            'status',
            'album',
        ]
        self.playerctl = PlayerctlFollow(playerctl_prefix, variables)

    def __getitem__(self, key):
        return self.playerctl.values.get(key, '')

    def render(self, p):
        # music_notes = [
        #     0xe270,
        #     0xe271,
        #     0xe272,
        #     0xe273,
        # ]
        # p.fg(barpyrus.colors.GRAY_LIGHT)
        # p.symbol(music_notes[1])
        p.fg(barpyrus.colors.PURPLE_DARK)
        if self['status'] == 'Playing':
            p.symbol(0xe058)  # Play
        else:
            p.symbol(0xe059)  # Pause
        p.space(3)
        p.fg(barpyrus.colors.GRAY_LIGHT)
        p.fg(barpyrus.colors.GREEN_LIGHT)
        p += self.playerctl['artist']
        p.fg(barpyrus.colors.GRAY_LIGHT)
        p += ': '
        p.fg(barpyrus.colors.ORANGE_LIGHT)
        p += self.playerctl['title']
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
