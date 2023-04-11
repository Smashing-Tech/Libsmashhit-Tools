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

VERSION = (0, 3, 1)

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

def patch_const_subs_instruction_arm64(old, value):
	mask = 0b00000000111111000011111100000000
	
	old = old & (~mask)
	
	last = (value & 0b111111) << 18
	first = ((value >> 6) & 0b111111) << 8
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

def patch_key(f, value):
	if (not value):
		tkinter.messagebox.showwarning("Change key warning", "The encryption key will be set to Smash Hit's default key, 5m45hh1t41ght, since you did not set one.")
		value = "5m45hh1t41ght"
	
	key = value.encode('utf-8')
	
	if (len(key) >= 24):
		tkinter.messagebox.showwarning("Change key warning", "Your encryption key is longer than 23 bytes, so it has been truncated.")
		key = key[:23]
	
	f.patch(0x1f3ca8, key + (b"\x00" * (24 - len(key))))

def patch_balls(f, value):
	if (not value):
		tkinter.messagebox.showerror("Patch balls error", "You didn't put in a value for how many balls you want to start with. Balls won't be patched!")
		return
	
	value = int(value)
	
	# Somehow, this works.
	d = struct.unpack(">I", f.read(0x57cf4))[0]
	f.patch(0x57cf4, struct.pack(">I", patch_const_mov_instruction_arm64(d, value)))
	
	f.patch(0x57ff8, struct.pack("<I", value))

def patch_hit(f, value):
	if (not value):
		tkinter.messagebox.showerror("Patch drop balls error", "You didn't put in a value for how many balls you want to drop when you hit something. Dropping balls won't be patched!")
		return
	
	value = int(value)
	
	# Patch the number of balls to subtract from the score
	d = struct.unpack(">I", f.read(0x715f0))[0]
	f.patch(0x715f0, struct.pack(">I", patch_const_subs_instruction_arm64(d, value)))
	
	# Patch the number of balls to drop
	d = struct.unpack(">I", f.read(0x71624))[0]
	f.patch(0x71624, struct.pack(">I", patch_const_mov_instruction_arm64(d, value)))
	
	# This changes from "cmp w23,#0xa" to "cmp w23,w1" so that we don't
	# need to make a specific patch for the comparision.
	f.patch(0x7162c, b"\xff\x02\x01\x6b")

def patch_fov(f, value):
	if (not value):
		tkinter.messagebox.showerror("Patch FoV error", "You didn't put in a value for the FoV you want. FoV won't be patched!")
		return
	
	f.patch(0x1c945c, struct.pack("<f", float(value)))

def patch_seconds(f, value):
	value = float(value) if value else ""
	
	if (not value):
		tkinter.messagebox.showwarning("Patch room length in seconds warning", "You didn't put in a room length in seconds. Room length in seconds will be set to the default! (32)")
		value = 32.0
	
	tkinter.messagebox.showwarning("Patch room length in seconds warning", f"Changing the time a room takes breaks the game if you have improperly lengthed music. Music tracks must now be {value + 4} seconds long.")
	
	# Smash Hit normalises the value to the range [0.0, 1.0] so we need to take the inverse
	f.patch(0x73f80, struct.pack("<f", 1 / value))

def patch_realpaths_segments(f, value):
	f.patch(0x2119f8, b"\x00")

def patch_realpaths(f, value):
	f.patch(0x2118e8, b"\x00")
	f.patch(0x1f48c0, b"\x00")

def patch_package(f, value):
	### This was the THIRD ATTEMPT to make it work.
	# It works by chaining it on after luaopen_base
	# This one worked, even if its the worst hack :D
	
	f.patch(0xa71b8, b"\xe0\x03\x13\xaa") # Preserve param_1
	f.patch(0xa71c8, b"\xb8\x0e\x00\x14") # Chain to luaopen_package
	f.patch(0xaaef4, b"\xe0\x03\x13\xaa") # Preserve param_1
	f.patch(0xaaf08, b"\xb1\xf0\xff\x17") # Chain to luaopen_io
	f.patch(0xa748c, b"\xe0\x03\x13\xaa") # Preserve param_1
	f.patch(0xa74a0, b"\xd1\xfe\xff\x17") # Chain to luaopen_os
	f.patch(0xa7004, b"\xa0\x00\x80\x52") # Set return to 5 (2 + 1 + 1 + 1 = 5)
	f.patch(0xa7010, b"\xc0\x03\x5f\xd6") # Make sure last is return (not really needed)

def patch_vertical(f, value):
	f.patch(0x46828, b"\x47\x00\x00\x14") # Patch an if (gWidth < gHeight)
	f.patch(0x4693c, b"\x71\x00\x00\x14") # Another if ...
	f.patch(0x46a48, b"\x1f\x20\x03\xd5")

PATCH_LIST = {
	"antitamper": patch_antitamper,
	"premium": patch_premium,
	"encryption": patch_encryption,
	"key": patch_key,
	"balls": patch_balls,
	"hit": patch_hit,
	"fov": patch_fov,
	"seconds": patch_seconds,
	"realpaths_segments": patch_realpaths_segments,
	"realpaths": patch_realpaths,
	"package": patch_package,
	"vertical": patch_vertical,
}

def applyPatches(location, patches):
	"""
	Apply patches to a given libsmashhit.so file
	"""
	
	f = File(location)
	
	ver = (f.read(0x1f38a0) + f.read(0x1f38a4))[:5].decode("utf-8")
	
	if (ver != '1.4.2' and ver != '1.4.3'):
		raise Exception(f"Sorry, this doesn't seem to be version 1.4.2 or version 1.4.3 for ARM64 devices. Make sure you have selected the ARM64 libsmashhit.so from 1.4.2 or 1.4.3 and try again.")
	
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
	w = Window(f"Smash Hit Binary Modification Tool v{VERSION[0]}.{VERSION[1]}.{VERSION[2]} (by Knot126)", "510x640")
	
	w.label("This tool will let you add common patches to Smash Hit's main binary.")
	
	location = default_path
	
	if (not location):
		location = tkinter.filedialog.askopenfilename(title = "Pick libsmashhit.so", filetypes = (("Shared objects", "*.so"), ("All files", "*.*")))
	
	w.label("(Note: If you have issues typing in boxes, try clicking off and on the window first.)")
	w.label("Please select what patches you would like to apply:")
	
	antitamper = w.checkbox("Disable anti-tamper protection (required)", default = True)
	premium = w.checkbox("Enable premium by default")
	encryption = w.checkbox("Nop out save encryption functions")
	key = w.checkbox("Set encryption key to (string):")
	key_val = w.textbox(True)
	balls = w.checkbox("Set the starting ball count to (integer):")
	balls_val = w.textbox(True)
	hit = w.checkbox("Change dropped balls when hit to (integer):")
	hit_val = w.textbox(True)
	fov = w.checkbox("Set the field of view to (float):")
	fov_val = w.textbox(True)
	seconds = w.checkbox("Set the room time in seconds to (float):")
	seconds_val = w.textbox(True)
	realpaths_segments = w.checkbox("Use absolute paths for segments")
	realpaths = w.checkbox("Use absolute paths for rooms and levels")
	package = w.checkbox("Load package, io and os modules in scripts")
	vertical = w.checkbox("Allow running in vertical resolutions")
	
	def x():
		"""
		Callback to run when the "Patch libsmashhit.so!" button is clicked
		"""
		
		try:
			patches = {
				"antitamper": antitamper.get(),
				"premium": premium.get(),
				"encryption": encryption.get(),
				"key": key.get(),
				"key_val": key_val.get(),
				"balls": balls.get(),
				"balls_val": balls_val.get(),
				"fov": fov.get(),
				"fov_val": fov_val.get(),
				"hit": hit.get(),
				"hit_val": hit_val.get(),
				"seconds": seconds.get(),
				"seconds_val": seconds_val.get(),
				"realpaths_segments": realpaths_segments.get(),
				"realpaths": realpaths.get(),
				"package": package.get(),
				"vertical": vertical.get(),
			}
			
			applyPatches(location.get() if type(location) != str else location, patches)
			
			tkinter.messagebox.showinfo("Success", "Your libsmashhit has been patched succesfully!")
		
		except Exception as e:
			tkinter.messagebox.showerror("Error", str(e))
	
	w.button("Patch game binary!", x)
	
	w.main()

def main():
	try:
		gui(sys.argv[1] if len(sys.argv) >= 2 else None)
	except Exception as e:
		tkinter.messagebox.showerror("Fatal error", str(e))

if (__name__ == "__main__"):
	main()
