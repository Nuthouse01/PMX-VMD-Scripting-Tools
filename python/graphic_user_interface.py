
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


# todo: its obviously better to handle the translations with a grid of text boxes, instead of ugly printing and seneding to file... but its harder and less generalized...
# what was the thing Tristan did that I was interested in? aligning the text!!

# TODO: handle "mode-choice" inputs, maybe another function variable in Core that i can override?
# TODO: handle grid presentation in translate

# TODO: restructure the original 5 scripts to use the "begin/middle/end/main" structure
# TODO: error wrappers in PMX parser? ugh

# eventual todo: how to make this system work for the other major scripts that take different inputs? different number/type of inputs


# execute must be separate from write so that they can be chained!

# standalone main:
# help
# prompt
# execute
# write
# pause_and_quit

# gui help:
# help

# gui run:
# execute
# write






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
import pmx_overall_cleanup
import copy




# # a popupwindow to replace the stock "input()" function
# def gui_input(prompt=''):
# 	win = tk.Toplevel()
#
# 	# normally when x button is pressed, it calls "destroy". this replaces that with "quit", to break mainloop
# 	# that way the x button resumes executing below win.mainloop and the script continues
# 	win.protocol("WM_DELETE_WINDOW", win.quit)
#
# 	label= tk.Label(win, text=prompt)
# 	label.pack()
#
# 	userinput= tk.StringVar(win)
# 	entry= tk.Entry(win, textvariable=userinput)
# 	entry.pack()
#
# 	# pressing the button should stop the mainloop
# 	button= tk.Button(win, text="ok", command=win.quit)
# 	button.pack()
#
# 	# block execution until the user presses the OK button
# 	win.mainloop()
#
# 	# mainloop has ended. Read the value of the Entry, then destroy the GUI.
# 	userinput= userinput.get()
# 	win.destroy()
#
# 	return userinput





class Application(tk.Frame):
	def __init__(self, master, help_func, run_func, writeout_func, UIconfig):
		tk.Frame.__init__(self, master)
		
		###############################################
		# first, handle input parameters
		# parameters: help function, payload function, writeout function, what kind of input buttons (pmx, vmd, txt)
		
		self.help_func =     help_func
		self.run_func =      run_func
		self.writeout_func = writeout_func
		self.UIconfig =      UIconfig
		# UI config: do you want a pmx button? do you want a vmd button? do you want both? do you want a txt button?
		
		###############################################
		# second, set up other non-ui class members
		# this variable is used in this new print function
		self.last_print_was_progress = False
		self.pmx_input = []
		self.vmd_input = []
		self.txt_input = []
		self.pmxpath = ""
		self.vmdpath = ""
		self.txtpath = ""
		
		###############################################
		# third, build the GUI buttons and etc
		
		if "pmx" in self.UIconfig:
			self.pmx_frame = tk.Frame(master, relief=tk.RAISED, borderwidth=1)
			self.pmx_frame.pack(side=tk.TOP, fill='x', padx=10, pady=10)
			
			# load PMX
			self.pmx_butt = tk.Button(self.pmx_frame, text="Load PMX", width=10, command=self.get_pmx_file)
			self.pmx_butt.pack(side=tk.LEFT, padx=10, pady=10)
			# load PMX label
			self.pmx_label = tk.Label(self.pmx_frame, text="PMX: ----")
			self.pmx_label.pack(side=tk.LEFT, fill='x')
			
		if "vmd" in self.UIconfig:
			self.vmd_frame = tk.Frame(master, relief=tk.RAISED, borderwidth=1)
			self.vmd_frame.pack(side=tk.TOP, padx=10, pady=10)
			
			# load vmd
			self.vmd_butt = tk.Button(self.vmd_frame, text="Load VMD", width=10, command=self.dummy)
			self.vmd_butt.pack(side=tk.LEFT, padx=10, pady=10)
			# load vmd label
			self.vmd_label = tk.Label(self.vmd_frame, text="VMD: ----")
			self.vmd_label.pack(side=tk.LEFT, fill='x')
		
		
		self.always_frame = tk.Frame(master, relief=tk.RAISED, borderwidth=1)
		self.always_frame.pack(side=tk.TOP, fill='x', padx=10, pady=10)
		
		# "run" button is disabled until a valid combination of inputs is loaded
		self.run_butt = tk.Button(self.always_frame, text="RUN", width=10, command=self.do_the_thing)
		self.run_butt.pack(side=tk.LEFT, padx=10, pady=10)
		self.run_butt.configure(state='disabled')
		
		# help
		self.help_butt = tk.Button(self.always_frame, text="Help", width=10, command=self.help_func)
		self.help_butt.pack(side=tk.LEFT, padx=10, pady=10)
		
		# debug checkbox
		self.debug_check_var = tk.IntVar()
		self.debug_check = tk.Checkbutton(self.always_frame, text="show extra info", variable=self.debug_check_var)
		self.debug_check.pack(side=tk.RIGHT, padx=10, pady=10)
		
		###############################################
		# fourth, build the "scrolledtext" object to serve as my output terminal
		self.edit_space = tkst.ScrolledText(
			master=master,
			wrap='word',  # wrap text at full words only
			width=100,  # characters
			height=25,  # text lines
			bg='beige'  # background color of edit area
		)
		self.edit_space.pack(fill='both', expand=True, padx=8, pady=8)
		self.edit_space.configure(state='disabled')
		
		# VERY IMPORTANT: overwrite the default print function with one that goes to the GUI
		core.MY_PRINT_FUNC = self.my_write
		
		core.MY_PRINT_FUNC("Nuthouse01 - 03/30/2020 - v3.51")
		core.MY_PRINT_FUNC("Begin by loading an input file, then click 'Run'")
		core.MY_PRINT_FUNC("Click 'Help' to print out details of what the script does")
		
		# done with init
		return
	
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
		# print visual separator
		core.MY_PRINT_FUNC("\n" + ("="*20))
		core.MY_PRINT_FUNC("...preparing...")
		# first, make a copy of the thing
		pmx = copy.deepcopy(self.pmx_input)
		try:
			result, is_changed = self.run_func(pmx, bool(self.debug_check_var.get()))
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("ERROR: failed to execute target script")
			return
		if is_changed:
			try:
				self.writeout_func(result, self.pmxpath)
			except Exception as e:
				core.MY_PRINT_FUNC(e.__class__.__name__, e)
				core.MY_PRINT_FUNC("ERROR: failed to write result of script")
				return
		return
		
		
	def dummy(self):
		return
	def get_pmx_file(self):
		# attached to "load PMX" button
		# get filename:	start in the last directory they opened from
		# if not "" then open with pmx reader
		# load a file & store it into the self.pmx object
		#
		
		# dont trust file dialog to remember last-opened path, do it manually
		recordpath = core.get_persistient_storage_path("last_opened_dir.txt")
		c = core.read_txt_to_rawlist(recordpath, quiet=True)
		if c and path.isdir(c[0][0]):
			start_here = c[0][0]
		else:
			start_here = "."
		
		newpath = fdg.askopenfilename(initialdir=start_here, title="Select input file", filetypes=(("PMX files", "*.pmx"),))
		
		# if user closed the prompt before giving a file path, quit here
		if newpath == "":
			return
		
		# print visual separator
		core.MY_PRINT_FUNC("\n" + ("="*20))
		
		# they got an existing file! update the last_opened_dir file
		core.write_rawlist_to_txt(recordpath, [[path.dirname(newpath)]], quiet=True)
		
		try:
			newpmx = pmxlib.read_pmx(newpath)
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("ERROR: failed to parse PMX file")
			return
			
		# if parsed without crashing, hooray!
		# save the name for displaying under the button
		self.pmxpath = newpath
		# write name into label widget
		self.pmx_label.config(text='PMX: "%s"' % path.basename(newpath))
		
		# save the PMX for giving to the actual processing later
		self.pmx_input = newpmx
		
		# unlock the "run" button once a valid PMX is loaded in
		self.run_butt.configure(state='normal')
		return

def launch_gui(title, help_func, run_func, writeout_func, UIconfig):
	root = tk.Tk()
	root.title(title)
	app = Application(root, help_func, run_func, writeout_func, UIconfig)
	app.mainloop()


if __name__ == '__main__':
	launch_gui("Do not execute this file directly, this is imported by other modules",
			   None,
			   None,
			   None,
			   tuple())

