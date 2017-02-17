#!/usr/bin/env python3

import sys
import os

# Change path so we find Xlib
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from Xlib import X, display, Xutil
from Xlib.protocol import request

def setborder(winid_int, border_width, border_color):
	d = display.Display();
	window = d.create_resource_object('window',winid_int)
	keys = {
		'border_pixel' : 0
	}
	attributes = window.get_attributes()
	geometry = window.get_geometry()
	colormap = attributes.colormap
	pixel_value = colormap.alloc_named_color(border_color).pixel
	#window.change_attributes(
	window.configure(
		border_width = border_width,
		# if we want to keep the window content in place
		# we have to move it
		x = geometry.x - border_width + geometry.border_width,
		y = geometry.y - border_width + geometry.border_width,
		)
	window.change_attributes(border_pixel = pixel_value)
	d.flush()
	#request.SetWindowBorderWidth(
	#	display = d,
	#	window = window,
	#	width = 3)
	#print ()

def print_usage(name, outfile):
	usage = """Usage: %s WindowId BorderWidth BorderColor

Set the window border of the given WindowId to the specified width and color.

Example: %s 0xc00004 2 '#9fbc00'""" % (name,name)
	print(usage,file=outfile)

def main(args):
	if len(args) < 4:
		print_usage(args[0], sys.stderr)
	else:
		setborder(int(args[1], 0),
			int(args[2], 0),
			args[3])

if __name__ == '__main__':
	main(sys.argv)

# vim: noet ts=4
