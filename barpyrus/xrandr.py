import subprocess
import collections

from itertools import combinations


class Xrandr:
    def __init__(self):
        self.connected = list()
        self.active_layout = None
        self.active_mode = "+"
        self.disconnected = list()
        self.displayed = None

    def get_layout(self):
        active_layout = list()
        proc = subprocess.run(["xrandr"], capture_output=True)
        for line in proc.stdout.decode().splitlines():
            s = line.split(" ")
            if s[1] == "connected":
                output, state, mode = s[0], s[1], None
                for index, x in enumerate(s[2:], 2):
                    if "x" in x and "+" in x:
                        mode = x
                        active_layout.append(output)
                        infos = line[line.find(s[index + 1]) :]
                        break
                    elif "(" in x:
                        break
                self.connected.append(output)
            elif s[1] == "disconnected":
                output, state = s[0], s[1]
                self.disconnected.append(output)
    
        if self.active_layout is None:
            self.active_layout = self.active_mode.join(tuple(active_layout))
        return self.connected

    def set_combinations(self, connected):
        available = set()
        combinations_map = {}

        for output in range(len(connected)):
            for comb in combinations(connected, output + 1):
                for mode in ["=", "+"]:
                    string = mode.join(comb)
                    if len(comb) == 1:
                        combinations_map[string] = (comb, None)
                    else:
                        combinations_map[string] = (comb, mode)
                    available.add(string)
 
        self.available_combinations = collections.deque(available)
        self.combinations_map = combinations_map

        return self.available_combinations
    
    def choose_what_to_display(self):
        for _ in range(len(self.available_combinations)):
            if self.displayed is None and self.available_combinations[0] == self.active_layout:
                self.displayed = self.available_combinations[0]
                break
            elif self.displayed == self.available_combinations[0]:
                break
            else:
                self.available_combinations.rotate(1)

    def switch_selection(self):
        self.available_combinations.rotate()
        self.displayed = self.available_combinations[0]

    def apply(self):
        print("displayed " + self.displayed)
        print("active " + self.active_layout)
        if self.displayed == self.active_layout:
            return

        combination, mode = self.combinations_map.get(self.displayed, (None, None))

        if combination is None and mode is None:
        # displayed combination cannot be activated, ignore
          return

        cmd = "xrandr"
        outputs = self.connected
        previous_output = None
        for output in outputs:
            cmd += f" --output {output}"
            if output in combination:
                pos = getattr(self, f"{output}_pos", "0x0")
                resolution = getattr(self, f"{output}_mode", None)
                resolution = f"--mode {resolution}" if resolution else "--auto"
                rotation = "normal"
                if mode == "=" and previous_output is not None:
                    cmd += f" {resolution} --same-as {previous_output}"
                else:
                    if (
                        "above" in pos
                        or "below" in pos
                        or "left-of" in pos
                        or "right-of" in pos
                       ):
                        cmd += f" {resolution} --{pos} --rotate {rotation}"
                    else:
                        cmd += " {} --pos {} --rotate {}".format(
                            resolution, pos, rotation
                        )
                previous_output = output
            else:
                cmd += " --off"

        code = subprocess.run(cmd.split())

        if code.returncode == 0:
            self.active_layout = self.displayed
            self.active_mode = mode
        print(cmd)
        print(code)

    def on_click(self, button):
        print(button)

        if button == 1:
          print("before %s", self.available_combinations[0])
          self.switch_selection()
          print("after %s", self.available_combinations[0])
        elif button == 3:
            self.apply()

