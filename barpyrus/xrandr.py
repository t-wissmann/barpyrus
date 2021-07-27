import subprocess
import collections

from itertools import combinations


class Xrandr:
    def __init__(self):
        self.connected = list()
        self.active_layout = list()
        self.disconnected = list()
        setattr(self, 'DP2-1_pos', 'left-of eDP1')
        setattr(self, 'DP2-1_resolution', '1920x1080')

    def get_layout(self):
        proc = subprocess.run(["xrandr"], capture_output=True)
        for line in proc.stdout.decode().splitlines():
            s = line.split(" ")
            if s[1] == "connected":
                output, state, mode = s[0], s[1], None
                for index, x in enumerate(s[2:], 2):
                    if "x" in x and "+" in x:
                        mode = x
                        self.active_layout.append(output)
                        infos = line[line.find(s[index + 1]) :]
                        break
                    elif "(" in x:
                        break
                self.connected.append(output)
            elif s[1] == "disconnected":
                output, state = s[0], s[1]
                self.disconnected.append(output)
    
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
    
    def on_click(self, button):
        print(button)

        if button == 1:
          print("before %s", self.available_combinations[0])
          self.available_combinations.rotate()
          print("after %s", self.available_combinations[0])
        elif button == 3:
            displayed = self.available_combinations[0]
            combination, mode = self.combinations_map.get(displayed, (None, None))

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
            print(cmd)
            print(code)

