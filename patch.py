#!/usr/bin/python
"""
libsmashhit patcher tool
"""

import tkinter
import tkinter.ttk as ttk
import tkinter.messagebox
import tkinter.filedialog
import json
import os
import sys
import struct

class File():
	"""
	A libsmashhit.so file
	"""
	
	def __init__(self, path):
		"""
		Initialise the file
		"""
		
		self.file = open(path, "rb+")
	
	def read(self, location):
		"""
		Read 32 bits from the given location
		"""
		
		self.file.seek(location, 0)
		return self.file.read(4)
	
	def patch(self, location, data):
		"""
		Write patched data to the file
		"""
		
		self.file.seek(location, 0)
		self.file.write(data)
	
	def __del__(self):
		"""
		Destroy the file
		"""
		
		self.file.close()

def patch_const_mov_instruction_arm64(old, value):
	mask = 0b11100000111111110001111100000000
	
	old = old & (~mask)
	
	last = (value & 0b111) << 29
	first = ((value >> 3) & 0b11111111) << 16
	new = last | first
	
	return (old | new)

def patch_antitamper(f, value):
	f.patch(0x47130, b"\x1f\x20\x03\xd5")
	f.patch(0x474b8, b"\x3e\xfe\xff\x17")
	f.patch(0x47464, b"\x3a\x00\x00\x14")
	f.patch(0x47744, b"\x0a\x00\x00\x14")
	f.patch(0x4779c, b"\x1f\x20\x03\xd5")
	f.patch(0x475b4, b"\xff\xfd\xff\x17")
	f.patch(0x46360, b"\x13\x00\x00\x14")

def patch_premium(f, value):
	tkinter.messagebox.showwarning("Software copyright notice", "APKs where premium is patched should NOT be distrubuted, and this functionality is only available for users to extercise their right to modify software that they own for private use. If you do not own premium, you should delete the patched file immediately.")
	
	f.patch(0x5ace0, b"\x1f\x20\x03\xd5")
	f.patch(0x598cc, b"\x14\x00\x00\x14")
	f.patch(0x59720, b"\xa0\xc2\x22\x39")
	f.patch(0x58da8, b"\x36\x00\x00\x14")
	f.patch(0x57864, b"\xbc\x00\x00\x14")
	f.patch(0x566ec, b"\x04\x00\x00\x14")

def patch_encryption(f, value):
	f.patch(0x567e8, b"\xc0\x03\x5f\xd6")
	f.patch(0x5672c, b"\xc0\x03\x5f\xd6")

def patch_balls(f, value):
	if (not value):
		tkinter.messagebox.showerror("Patch balls error", "You didn't put in a value for how many balls you want to start with. Balls won't be patched!")
		return
	
	value = int(value)
	
	# Somehow, this works.
	d = struct.unpack(">I", f.read(0x57cf4))[0]
	f.patch(0x57cf4, struct.pack(">I", patch_const_mov_instruction_arm64(d, value)))
	
	f.patch(0x57ff8, struct.pack("<I", value))

def patch_fov(f, value):
	if (not value):
		tkinter.messagebox.showerror("Patch FoV error", "You didn't put in a value for the FoV you want. FoV won't be patched!")
		return
	
	f.patch(0x1c945c, struct.pack("<f", float(value)))

PATCH_LIST = {
	"antitamper": patch_antitamper,
	"premium": patch_premium,
	"encryption": patch_encryption,
	"balls": patch_balls,
	"fov": patch_fov,
}

def applyPatches(location, patches):
	"""
	Apply patches to a given libsmashhit.so file
	"""
	
	f = File(location)
	
	ver = (f.read(0x1f38a0) + f.read(0x1f38a4))[:5].decode("utf-8")
	
	if (ver != '1.4.2'):
		raise Exception(f"Not version 1.4.2 for ARM64. Got {ver} instead!")
	
	# For each patch ...
	for p in patches:
		# ... that is actually a patch and is wanted ...
		if (not p.endswith("_val") and patches[p] == True):
			# ... do the patch, also passing (PATCHNAME) + "_val" if it exists.
			(PATCH_LIST[p])(f, patches.get(p + "_val", None))

# ==============================================================================
# ==============================================================================

class Window():
	"""
	Window thing
	"""
	
	def __init__(self, title, size, class_name = "Application"):
		"""
		Initialise the window
		"""
		
		self.window = tkinter.Tk(className = class_name)
		self.window.title(title)
		self.window.geometry(size)
		
		self.position = -25
		self.gap = 35
		
		# Main frame
		ttk.Frame(self.window)
	
	def getYPos(self, flush = False):
		self.position += self.gap if not flush else 0
		
		return self.position
	
	def label(self, content):
		"""
		Create a label
		"""
		
		label = tkinter.Label(self.window, text = content)
		label.place(x = 10, y = self.getYPos())
		
		return label
	
	def button(self, content, action):
		button = tkinter.Button(self.window, text = content, command = action)
		button.place(x = 10, y = self.getYPos())
		
		return button
	
	def textbox(self, inline = False):
		"""
		Create a textbox
		"""
		
		entry = tkinter.Entry(self.window, width = (70 if not inline else 28))
		
		if (not inline):
			entry.place(x = 10, y = self.getYPos())
		else:
			entry.place(x = 300, y = self.getYPos(True))
		
		return entry
	
	def checkbox(self, content, default = False):
		"""
		Create a tickbox
		"""
		
		var = tkinter.IntVar()
		
		tick = tkinter.Checkbutton(self.window, text = content, variable = var, onvalue = 1, offvalue = 0)
		tick.place(x = 10, y = self.getYPos())
		
		var.set(1 if default else 0)
		
		return var
	
	def main(self):
		self.window.mainloop()

def gui(default_path = None):
	w = Window("Smash Hit Binary Modification Tool", "520x560")
	
	w.label("This tool will let you add common patches to Smash Hit's main binary.")
	
	location = default_path
	
	if (not location):
		#w.label("Where is your libsmashhit.so located? (Note: It will be overwitten.)")
		#location = w.textbox()
		
		location = tkinter.filedialog.askopenfilename(title = "Pick libsmashhit.so", filetypes = (("Shared objects", "*.so"), ("All files", "*.*")))
		w.label("Path: " + location)
	else:
		w.label("Path: " + location)
	
	w.label("What patches would you like to apply?")
	
	antitamper = w.checkbox("Disable anti-tamper protection (required)", default = True)
	premium = w.checkbox("Enable premium by default")
	encryption = w.checkbox("Disable save encryption")
	balls = w.checkbox("Change starting ballcount to:")
	balls_val = w.textbox(True)
	fov = w.checkbox("Change the feild of view to:")
	fov_val = w.textbox(True)
	
	def x():
		"""
		Callback to run when the "Patch libsmashhit.so!" button is clicked
		"""
		
		try:
			patches = {
				"antitamper": antitamper.get(),
				"premium": premium.get(),
				"encryption": encryption.get(),
				"balls": balls.get(),
				"balls_val": balls_val.get(),
				"fov": fov.get(),
				"fov_val": fov_val.get(),
			}
			
			applyPatches(location.get() if type(location) != str else location, patches)
			
			tkinter.messagebox.showinfo("Success", "Your libsmashhit has been patched succesfully!")
		
		except Exception as e:
			tkinter.messagebox.showerror("Error", str(e))
	
	w.button("Patch libsmashhit.so!", x)
	
	w.main()

def main():
	try:
		gui(sys.argv[1] if len(sys.argv) >= 2 else None)
	except Exception as e:
		tkinter.messagebox.showerror("Fatal error", str(e))

if (__name__ == "__main__"):
	main()
