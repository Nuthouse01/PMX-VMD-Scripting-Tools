
''' tk_scrolledtext101.py
explore Tkinter's ScrolledText widget
inside the edit_space use
ctrl+c to copy, ctrl+x to cut selected text,
ctrl+v to paste, and ctrl+a to select all
uses the same methods as the Text() widget
'''




# one/two buttons for load PMX/VMD

# "RUN" button

# bigass scrolltext where I print everything

# translate: build an actual grid within a popup containing editable text fields?
# input: translate confirm/deny (buttons below popup)
# input: morph winnow threshold
# debug checkbox


# button invokes begin: prompt for name & load
# "run" invokes the meat of the script
# "help" button prints all the help info... or opens a popup?


# how do I make this look good?

#############################
# basic size = ~6k
# size with translate ~10k
# size with translate + gui ~12k
# size with just gui ~9k

# re-investigate compression with UPK?
#############################


# TODO: config pyinstaller to launch without console so it cannot unexpectedly die

# TODO: completely rethink all error cases, convert to throwing errors which are caught at higher level(s)


# todo: its obviously better to handle the translations with a grid of text boxes, instead of ugly printing and seneding to file... but its harder and less generalized...
# what was the thing Tristan did that I was interested in? aligning the text!!

# TODO: handle "mode-choice" inputs, maybe another function variable in Core that i can override?
# TODO: handle grid presentation in translate

# TODO: restructure the original 5 scripts to use the "begin/middle/end/main" structure
# TODO: error wrappers in PMX parser? ugh

# eventual todo: how to make this system work for the other major scripts that take different inputs? different number/type of inputs

try:
	# for Python2
	import Tkinter as tk
	import ScrolledText as tkst
except ImportError:
	# for Python3
	import tkinter as tk
	import tkinter.scrolledtext as tkst
import tkinter.filedialog as fdg

import nuthouse01_core as core
import nuthouse01_pmx_parser as pmxlib
from os import path
import time
import sys
# import pmx_overall_cleanup


# d = {}
# d[4] = "asdf"
# try:
# 	print(d[2])
# except Exception as e:
# 	print(e)
# 	print(sys.exc_info())




class Application(tk.Frame):
	def __init__(self, master):
		tk.Frame.__init__(self, master)
		
		# paramaters: payload function, output filename suffix, what kind of input buttons,
		
		# # frame = tk.Frame(master, bg='brown')
		# frame = tk.Frame(master)
		# frame.pack(fill='both', expand='yes')
		
		self.last_print_was_progress = False
		
		self.payload_func = None

		self.basename = ""
		self.pmx = []
		self.is_debug = 0
		self.out_suffix = "better"
		
		# build the "scrolledtext" object to serve as my output terminal
		self.edit_space = tkst.ScrolledText(
			master=master,
			wrap='word',  # wrap text at full words only
			width=25,  # characters
			height=10,  # text lines
			bg='beige'  # background color of edit area
		)
		self.edit_space.pack(fill='both', expand=True, padx=8, pady=8)
		self.edit_space.configure(state='disabled')
		
		# VERY IMPORTANT: overwrite the default print function with one that goes to the GUI
		core.MY_PRINT_FUNC = self.my_write
		
		core.MY_PRINT_FUNC("Nuthouse01 - 03/30/2020 - v3.51")
		
		mytext = '''\
		Man who drive like hell, bound to get there.
		Man who run in front of car, get tired.
		Man who run behind car, get exhausted. 全ての親
		The Internet: where men are men, women are men, and children are FBI agents.
		'''
		core.MY_PRINT_FUNC(mytext)
		
		# "run" button is disabled until a valid PMX is loaded
		self.run_butt = tk.Button(master, text="RUN", width=10, command=self.do_the_thing)
		self.run_butt.pack(side=tk.LEFT, padx=10, pady=10)
		self.run_butt.configure(state='disabled')
		
		self.load_butt = tk.Button(master, text="Load", width=10, command=self.get_pmx_file)
		self.load_butt.pack(side=tk.LEFT, padx=10, pady=10)
		
		self.load_label = tk.Label(master, text="PMX: ----")
		self.load_label.pack()
		
		self.help_butt = tk.Button(master, text="help", width=10, command=self.get_pmx_file)
		self.help_butt.pack(side=tk.LEFT, padx=10, pady=10)
		
		
		self.debug_check_var = tk.IntVar()
		self.debug_check = tk.Checkbutton(master, text="debug", variable=self.debug_check_var)
		self.debug_check.pack(side=tk.LEFT, padx=10, pady=10)
		# self.debug_check.
	
	# replacement for core.basic_print function, print to text thingy instead of to console
	def my_write(self, *args, is_progress=False):
		the_string = ' '.join([str(x) for x in args])
		# todo remove this probably?
		core.basic_print(the_string, is_progress=is_progress)
		# if last print was a progress update, then overwrite it with next print
		if self.last_print_was_progress:	self._overwrite(the_string)
		# if last print was a normal print, then print normally
		else: 								self._write(the_string)
		# don't force scrolling down for progress update printouts
		if not is_progress: 				self.edit_space.see(tk.END)
		# at the end, store this value for next time
		self.last_print_was_progress = is_progress
	def _write(self, the_string):
		self.edit_space.configure(state="normal")  # enable
		self.edit_space.tag_remove("last_insert", "1.0", tk.END)  # wipe old tag
		self.edit_space.insert(tk.END, the_string + '\n', "last_insert")  # write and label with tag
		self.edit_space.configure(state="disabled")  # disable
		self.update_idletasks()  # actually refresh the screen
	def _overwrite(self, the_string):
		self.edit_space.configure(state="normal")  # enable
		last_insert = self.edit_space.tag_ranges("last_insert")  # get tag range
		self.edit_space.delete(last_insert[0], last_insert[1])  # delete
		self._write(the_string)
	
	def do_the_thing(self):
		# run the actual processing code
		# give it self.pmx
		self.payload_func(self.pmx)
		# give it self.debug_check_var.get()
		# get pmx, bool
		pass
		
	def dummy(self):
		return
	def get_pmx_file(self):
		# attached to "load PMX" button
		# get filename:	start in the last directory they opened from
		# if not "" then open with pmx reader
		# load a file & store it into the self.pmx object
		#
		print("get file")
		
		# file dialog automatically remembers the last path it succesfully opened!! neat!!
		newpath = fdg.askopenfilename(title="Select input file", filetypes=(("PMX files", "*.pmx"),))
		
		# if user closed the prompt before giving a file path, quit here
		if newpath == "": return
		
		try:
			newpmx = pmxlib.read_pmx(newpath)
		except Exception as e:
			# todo rearchitect error handling
			print("oops", e)
			return
			
		# if parsed without crashing, hooray!
		# save the name for displaying under the button
		basename = path.basename(newpath)
		self.basename = basename
		# write name into label widget
		self.load_label.config(text='PMX: "%s"' % basename)
		
		# save the PMX for giving to the actual processing later
		self.pmx = newpmx
		
		# unlock the "run" button once a valid PMX is loaded in
		self.run_butt.configure(state='normal')
		return

def launch_gui():
	root = tk.Tk()
	root.title('ScrolledText test')
	app = Application(root)
	app.mainloop()


if __name__ == '__main__':
	launch_gui()

'''
# this is the function to run when something changes and its time to send a message to ROS or inmoov
# this is a function that takes a single string
self.on_change_callback = on_change_callback

self.mode = 0  # mode 0=left, 1=center, 2=right

self.maxtablistlength = 0  # the most servos in a tab
for namelist in names_all:
	self.maxtablistlength = max(self.maxtablistlength, len(namelist))
# current_values is initiallized with all zeros, in the same shape as names_all
# used to determine which changed when something changed, also to know what to display when loading a tab
self.current_values = []
for p in names_all:
	self.current_values.append([0] * len(p))
# current_checkbox_states is same as current_values but for the checkboxes_vars
# disabled servos begin with this checkbox off
self.pose_init = {}
self.current_checkbox_states = []
self.current_onoff_states = []
for p in names_all:
	boxes = []
	onoff = []
	for n in p:
		s = my_inmoov.find_servo_by_name(n)
		self.pose_init[n] = s.default_angle
		boxes.append(int(not s.disabled))
		onoff.append(0)
	self.current_checkbox_states.append(boxes)
	self.current_onoff_states.append(onoff)

# applying an "empty pose" doesn't change any sliders, but it unchecks all checkboxes
self.pose_off = {}

#####################################
# begin GUI setup
# structure:
# one frame for all buttons stacked vertically with one frame for the scrollbar stuff
# inside buttons frame, everything packed horizontally
# buttons grouped with visible borders to show things that are related:
# left/right/center buttons inside a frame with a visible border
# init/off buttons inside a frame with a visible border
# name/save field/button inside a frame with a visible border

# buttons for control & stuff
self.frame_biggroup1 = tk.Frame(master)
self.frame_biggroup1.pack(side=tk.TOP)

# self.frame_tab_buttons = tk.Frame(self.frame_biggroup1, highlightbackground="black", highlightthickness=1)
self.frame_tab_buttons = tk.Frame(self.frame_biggroup1, relief=tk.RAISED, borderwidth=1)
self.frame_tab_buttons.pack(side=tk.LEFT, padx=10, pady=10)
self.butt_left = tk.Button(self.frame_tab_buttons, text="Left", width=button_width,
						   command=lambda: self.change_tab(0))
self.butt_left.pack(side=tk.LEFT, padx=button_padx, pady=button_pady)
self.butt_center = tk.Button(self.frame_tab_buttons, text="Center", width=button_width,
							 command=lambda: self.change_tab(1))
self.butt_center.pack(side=tk.LEFT, padx=button_padx, pady=button_pady)
self.butt_right = tk.Button(self.frame_tab_buttons, text="Right", width=button_width,
							command=lambda: self.change_tab(2))
self.butt_right.pack(side=tk.LEFT, padx=button_padx, pady=button_pady)

self.frame_command_buttons = tk.Frame(self.frame_biggroup1, relief=tk.RAISED, borderwidth=1)
self.frame_command_buttons.pack(side=tk.LEFT, pady=10)
self.butt_init = tk.Button(self.frame_command_buttons, text="INIT", width=button_width,
						   command=self.allservos_init)
self.butt_init.pack(side=tk.LEFT, padx=button_padx, pady=button_pady)
self.butt_off = tk.Button(self.frame_command_buttons, text="OFF", width=button_width,
						  command=self.allservos_off)
self.butt_off.pack(side=tk.LEFT, padx=button_padx, pady=button_pady)

self.frame_posesave_widgets = tk.Frame(self.frame_biggroup1, relief=tk.RAISED, borderwidth=1)
self.frame_posesave_widgets.pack(side=tk.LEFT, padx=10, pady=10)
self.name_entry = tk.Entry(self.frame_posesave_widgets, width=textentry_width)
self.name_entry.pack(side=tk.LEFT, padx=button_padx, pady=button_pady)
self.butt_save = tk.Button(self.frame_posesave_widgets, text="Save", width=button_width,
						   command=self.save_values)
self.butt_save.pack(side=tk.LEFT, pady=button_pady)
self.butt_load = tk.Button(self.frame_posesave_widgets, text="Load", width=button_width,
						   command=self.load_values)
self.butt_load.pack(side=tk.LEFT, padx=button_padx, pady=button_pady)

# the default color always looks the same but has different names on different platforms
self.defaultcolor_buttonback = self.butt_off.cget("background")
print(self.defaultcolor_buttonback)

# Scale.config(state=tk.DISABLED)
# Scale.config(state=tk.NORMAL)
# Label.config(text="asdf")

###########################################################################
# build & fill the scrollbar region

# frame that contains everything that isn't the above buttons
self.frame_biggroup2 = tk.Frame(master)
self.frame_biggroup2.pack(fill=tk.BOTH, expand=True)

# canvas holds a frame widget
canvas_width = int(slider_width + (7.5 * label_width) + 23)  # set the default and minimum width
self.canvas = tk.Canvas(self.frame_biggroup2, height=canvas_height, width=canvas_width)
self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# scrollbar
# change the canvas when the scrollbar is scrolled
self.scrollbar = tk.Scrollbar(self.frame_biggroup2, command=self.canvas.yview)
self.scrollbar.pack(side=tk.LEFT, fill='y')
# set the scrollbar when something changes the canvas (window resizing)
self.canvas.configure(yscrollcommand=self.scrollbar.set)
# not totally sure what this does, gets called when the canvas is resized (window resizing)
self.canvas.bind('<Configure>', self.update_canvas_size)

# --- put frame in canvas ---
self.frame_servolist = tk.Frame(self.canvas)
self.canvas.create_window((0, 0), window=self.frame_servolist, anchor='nw')

# --- add widgets in frame ---
self.sliders = []
self.labels = []
self.checkboxes = []
self.checkboxes_vars = []
for i in range(self.maxtablistlength):
	w = tk.Label(self.frame_servolist, text="Hello Tkinter!" + str(i), width=label_width)
	w.grid(row=i, column=0)
	self.labels.append(w)

	s = tk.Scale(self.frame_servolist, from_=0, to=200, length=slider_width, tickinterval=30,
				 orient=tk.HORIZONTAL, command=self.get_changed_sliders)
	s.grid(row=i, column=1)
	self.sliders.append(s)

	var = tk.IntVar()
	c = tk.Checkbutton(self.frame_servolist, variable=var, text="", command=self.get_changed_checkbox)
	# var.set(1) # turn the button on by default
	c.grid(row=i, column=2)
	self.checkboxes.append(c)
	self.checkboxes_vars.append(var)

# w.get() to return current slider val
# w.set(x) to set initial value
# resolution: default 1, set lower for floatingpoint
# command: callback, gets value as only arg

# the default color always looks the same but has different names on different platforms
self.defaultcolor_font = self.labels[0].cget("fg")
print(self.defaultcolor_font)

self.change_tab(0)
# DONE WITH GUI INIT
pass
'''

# root > app(frame)? > everything



# optiona info
# help(tkst.ScrolledText)


