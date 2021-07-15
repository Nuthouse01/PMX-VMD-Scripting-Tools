import importlib
import threading
import tkinter as tk
import tkinter.filedialog as fdg
import tkinter.font as tkfont
import tkinter.scrolledtext as tkst
from os import path, listdir
from typing import Sequence, Union

from mmd_scripting import __pkg_welcome__
from mmd_scripting.core import nuthouse01_core as core

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.01 - 7/12/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# pyinstaller --onefile --noconsole graphic_user_interface.py


# to get better GUI responsiveness, I need to launch the parser and processing functions in separate threads.
# this causes the GUI progress updates to look all flickery and unpleasant... but its worth it.

########################################################################################################################
# constants & options
########################################################################################################################

# if true, calls stock "print" function whenever it prints to the GUI print-space.
# when running from EXE, in noconsole mode, this does nothing at all.
ALSO_PRINT_TO_CONSOLE = False


# SCRIPT_LIST is the list of all things I found to fill the GUI with
# do I want to sort by usefulness? or do I want to group by categories? or maybe just alphabetical? idk
SCRIPT_LIST = []

def populate_script_list():
	# first, assert that the current directory is where i think it is
	thisscriptname = path.split(__file__)[1]
	assert thisscriptname in listdir(".")
	# second, build a list of all files in "scripts_for_gui"
	path_to_scripts = "mmd_scripting/scripts_for_gui/"
	filenames = listdir(path_to_scripts)
	# remove anything that starts with underscore
	filenames = [a for a in filenames if not a.startswith("_")]
	# now i should have a list of all the scripts in the folder!
	# then, iterate over the list and import each file
	script_list = []
	for filename in filenames:
		mname = path_to_scripts + filename  # prepend the path to the scripts folder
		mname = path.splitext(mname)[0]  # strip the .py
		mname = mname.replace("/", ".")  # replace the folderseparator slashes with dots
		try:
			module = importlib.import_module(mname)  # actual magical import
		except Exception as e:
			core.MY_PRINT_FUNC("ERROR: exception while importing script '%s'" % filename)
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			# todo possibly print full traceback?
			continue
		# a valid script only needs main() and helptext
		# todo: validate that "main" accepts exactly one boolean argument!
		if hasattr(module, "main") and callable(module.main) and \
				hasattr(module, "helptext") and isinstance(module.helptext, str):
			# store the displayname with the module object
			# do i want the module to have .py or not? hm....
			# if i don't want it, then strip .py outside the loop
			script_list.append((filename, module))
		else:
			core.MY_PRINT_FUNC("WARNING: '%s' is in the '%s' folder but is not a valid script" % (filename, path_to_scripts))
	
	# store this list into the global
	global SCRIPT_LIST
	SCRIPT_LIST = script_list
	return None
	

# DO NOT TOUCH: global vars for passing info between GUI input popup and the thread the script lives in
inputpopup_args = None
inputpopup_done = threading.Event()
inputpopup_done.clear()
inputpopup_result = None


########################################################################################################################
# MAIN & functions
########################################################################################################################




def gui_fileprompt(label: str, ext_list: Union[str,Sequence[str]]) -> str:
	"""
	Use a Tkinter File Dialogue popup to prompt for a file. Same signature as core.prompt_user_filename().
	
	:param label: {{short}} string label that identifies this kind of input, like "Text file" or "VMD file"
	:param ext_list: list of acceptable extensions, or just one string
	:return: case-correct absolute file path
	"""
	if isinstance(ext_list, str):
		# if it comes in as a string, wrap it in a list
		ext_list = [ext_list]
	# replaces core func MY_FILEPROMPT_FUNC when running in GUI mode
	
	# ensure the extensions are sorted (for consistency)
	ext_list.sort()
	
	# labelled extensions: tuple of string label plus string of acceptable extensions, space-separated, with * prepended
	if ext_list:
		ext_list_flattened = " ".join(["*"+a for a in ext_list])
	else:
		# if given an empty list, then accept any extension! pretty sure this is the right syntax for that?
		ext_list_flattened = "*"
	labelled_extensions = (label, ext_list_flattened)
	labelled_extensions = (labelled_extensions,)  # it just needs this, dont ask why
	
	# dont trust file dialog to remember last-opened path, manually save/read it
	# NEW: file dialog start path is stored independently for each file type!!
	json_key = "last-input-path-" + ",".join(ext_list)
	json_data = core.get_persistent_storage_json(json_key)
	if json_data is None:
		# if never used before, start wherever i am right now i guess
		start_here = path.abspath(".")
	else:
		# if it has been used before, use the path from last time.
		c = json_data
		# if the path from last time does not exist, walk up the path till I find a level that does still exist.
		while c and not path.isdir(c):
			c = path.dirname(c)
		start_here = c
	
	newpath = fdg.askopenfilename(initialdir=start_here,
								  title="Select input file: [%s]" % ", ".join(ext_list),
								  filetypes=labelled_extensions)
	
	# if user closed the prompt before giving a file path, quit here
	if newpath == "":
		core.MY_PRINT_FUNC("ERROR: this script requires an input file to run")
		raise RuntimeError()
	
	# they got an existing file! update the last_opened_dir file
	core.write_persistent_storage_json(json_key, path.dirname(newpath))
	
	return newpath



# this is the function called by the script-thread to invoke a popup
# waits for the popup to be dismissed before getting the result & resuming the thread
def gui_inputpopup_trigger(args, explain_info=None):
	# print("trig")
	global inputpopup_args
	# write into simplechoice_args to signify that I want a popup
	inputpopup_args = [args, explain_info]
	# wait for a choice to be made from within the popup
	inputpopup_done.wait()
	inputpopup_done.clear()
	# if they clicked x ...
	if inputpopup_result is None:
		if callable(args):
			# this is general-input mode
			# return empty string (usually aborts the script)
			return ""
		else:
			# this is simplechoice (multichoice) mode
			# return the first option
			return args[0]
	else:
		core.MY_PRINT_FUNC(str(inputpopup_result))
		return inputpopup_result

# a popupwindow controlled by the GUI thread
# contains buttons
def gui_inputpopup(args, explain_info=None):
	# print("pop")
	# create popup
	win = tk.Toplevel()
	win.title("User input needed")
	# normally when X button is pressed, it calls "destroy". that would leave the script-thread indefinitely waiting on the flag!
	# this redefine will set the flag so the script resumes when X is clicked
	def on_x():
		global inputpopup_result
		inputpopup_result = None
		inputpopup_done.set()
		win.destroy()
	win.protocol("WM_DELETE_WINDOW", on_x)
	
	# init the result to None, just because
	global inputpopup_result
	inputpopup_result = None
	
	# if explain_info is given, create labels that display those strings
	if isinstance(explain_info, str):
		explain_info = [explain_info]
	if explain_info is not None:
		labelframe = tk.Frame(win)
		labelframe.pack(side=tk.TOP, fill='x')
		for f in explain_info:
			# create labels for each line
			label = tk.Label(labelframe, text=f)
			label.pack(side=tk.TOP, fill='x', padx=10, pady=10)
			core.MY_PRINT_FUNC(f)
	
	# this function commits the result & closes the popup
	def setresult(r):
		global inputpopup_result
		inputpopup_result = r
		# pressing the button should stop the mainloop
		inputpopup_done.set()
		win.destroy()
		
	# build a frame for the interactables to live in
	buttonframe = tk.Frame(win)
	buttonframe.pack(side=tk.TOP)
	
	# guarantee the popup is in front of the main window
	win.lift()
	# guarantee the popup has focus
	win.focus_set()
	
	# decide what the mode is & how to fill the popup
	if callable(args):
		# this is general-input mode, create text-entry box and submit button
		# for some reason the snow/white color still looks beige? :( oh well i tried
		textbox = tk.Entry(buttonframe, width=50, bg='snow')
		textbox.pack(side=tk.TOP, padx=10, pady=10)
		def submit_callback(_=None):
			# validate the text input using the validity check function "args"
			# if its good then invoke "setresult", if its bad then clear the text box
			# the func should be defined to print something explaining why it failed whenever it fails
			t = textbox.get().rstrip()
			if args(t): setresult(t)
			else: textbox.delete(0, tk.END)
		submit = tk.Button(buttonframe, text="Submit", command=submit_callback)
		submit.pack(side=tk.TOP, padx=10, pady=10)
		# "enter" key will be equivalent to clicking the submit button...
		# (technically this will happen whenever focus is inside the popup window, not just when focus is in the text entry box, but oh well)
		win.bind('<Return>', submit_callback)
		# guarantee the textbox within the popup has focus so user can start typing immediately (requires overall popup to already have focus)
		textbox.focus_set()
	else:
		# this is simplechoice (multichoice) mode, "args" is a list... create buttons for each option
		# create buttons for each numbered option
		for i in args:
			# each button will call "setresult" with its corresponding number, lambda needs to be written EXACTLY like this, i forget why it works
			c = lambda v=i: setresult(v)
			button = tk.Button(buttonframe, text=str(i), command=c)
			button.pack(side=tk.LEFT, padx=10, pady=10)
	
	return None
	
def print_header():
	core.MY_PRINT_FUNC(__pkg_welcome__)
	core.MY_PRINT_FUNC("Begin by selecting a script above, then click 'Run'")
	core.MY_PRINT_FUNC("Click 'Help' to print out details of what the selected script does")
	return


class Application(tk.Frame):
	def __init__(self, master):
		tk.Frame.__init__(self, master)
		
		###############################################
		# first, set up non-ui class members
		# this variable is used in this new print function, very important
		self.last_print_was_progress = False
		# loaded_script is the module object that matches the selected name
		self.loaded_script = None
		
		###############################################
		# second, build the dropdown menu
		# frame that holds the dropdown + the label
		self.which_script_frame = tk.Frame(master)
		self.which_script_frame.pack(side=tk.TOP, padx=10, pady=5)
		lab = tk.Label(self.which_script_frame, text="Active script:")
		lab.pack(side=tk.LEFT)

		# underlying variable tied to the dropdown menu, needed to run self.change_mode when the selection changes
		self.optionvar = tk.StringVar(master)
		self.optionvar.trace("w", self.change_mode)
		# set the default script, this should invoke "self.change_mode" at least once
		lastused = core.get_persistent_storage_json('last-script')
		if lastused is None:
			# if entry doesn't exist, choose the top of the list
			self.optionvar.set(SCRIPT_LIST[0][0])
		else:
			# if entry does exist, look for it
			idx = core.my_list_search(SCRIPT_LIST, lambda x: x[0] == lastused)
			if idx is None:
				# if not in the current list of scripts, choose the top of the list
				self.optionvar.set(SCRIPT_LIST[0][0])
			else:
				self.optionvar.set(SCRIPT_LIST[idx][0])
		# build the visible dropdown menu
		self.which_script = tk.OptionMenu(self.which_script_frame, self.optionvar, *[x[0] for x in SCRIPT_LIST])
		self.which_script.pack(side=tk.LEFT, padx=10)
		
		###############################################
		# third, build the GUI control buttons
		self.control_frame = tk.Frame(master, relief=tk.RAISED, borderwidth=1)
		self.control_frame.pack(side=tk.TOP, fill='x', padx=10, pady=5)
		
		self.run_butt = tk.Button(self.control_frame, text="RUN", width=7, command=self.run_the_script_as_thread)
		button_default_font = self.run_butt.cget("font")
		# print(button_default_font)
		# RUN button has bigger font than the other buttons
		self.run_butt.configure(font=(button_default_font, 18))
		self.run_butt.pack(side=tk.LEFT, padx=10, pady=10)
		
		# help
		self.help_butt = tk.Button(self.control_frame, text="Help", width=10, command=self.help_func)
		self.help_butt.pack(side=tk.LEFT, padx=10, pady=10)
		
		# clear
		self.clear_butt = tk.Button(self.control_frame, text="Clear", width=10, command=self.clear_func)
		self.clear_butt.pack(side=tk.LEFT, padx=10, pady=10)
		
		# debug checkbox
		self.debug_check_var = tk.IntVar()
		self.debug_check = tk.Checkbutton(self.control_frame, text="show extra info", variable=self.debug_check_var)
		self.debug_check.pack(side=tk.RIGHT, padx=10, pady=10)
		
		###############################################
		# fourth, build the "scrolledtext" object to serve as my output terminal
		# doesn't need a frame, already has a frame built into it kinda
		self.edit_space = tkst.ScrolledText(
			master=master,
			wrap='word',  # wrap text at full words only
			width=100,  # characters
			height=25,  # text lines
			bg='beige'  # background color of edit area
		)
		self.edit_space.pack(fill='both', expand=True, padx=8, pady=8)
		self.edit_space.configure(state='disabled')
		# get the default font & measure size of a space char in this font
		self.edit_space_font = tkfont.nametofont(self.edit_space.cget("font"))
		self.edit_space_unit = self.edit_space_font.measure(" ")

		###############################################
		# fifth, overwrite the core function pointers to use new GUI methods
		
		# VERY IMPORTANT: overwrite the default print function with one that goes to the GUI
		core.MY_PRINT_FUNC = self.my_write
		# VERY IMPORTANT: overwrite the default simple-choice function with one that makes a popup
		core.MY_SIMPLECHOICE_FUNC = gui_inputpopup_trigger
		# VERY IMPORTANT: overwrite the default general input function with one that makes a popup
		core.MY_GENERAL_INPUT_FUNC = gui_inputpopup_trigger
		# VERY IMPORTANT: overwrite the default fileprompt function with one that uses a popup filedialogue
		core.MY_FILEPROMPT_FUNC = gui_fileprompt
		# also this
		core.MY_JUSTIFY_STRINGLIST = self.gui_justify_stringlist
		
		# print version & instructions
		print_header()
		# start the popup loop
		self.spin_to_handle_inputs()
		# load the initial script to populate payload & helptext
		self.change_mode()
		
		# done with init
		return
	
	# replacement for core.basic_print function, print to text thingy instead of to console
	def my_write(self, *args, is_progress=False):
		the_string = ' '.join([str(x) for x in args])
		if ALSO_PRINT_TO_CONSOLE: core.basic_print(the_string, is_progress=is_progress)
		# if last print was a progress update, then overwrite it with next print
		if self.last_print_was_progress:	self._overwrite(the_string)
		# if last print was a normal print, then print normally
		else: 								self._write(the_string)
		# DO force scrolling down for non-progress printouts
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
	
	def spin_to_handle_inputs(self):
		# check if an input is requested
		global inputpopup_args
		if inputpopup_args is not None:
			# print("do")
			# if it is requested, create the popup
			gui_inputpopup(inputpopup_args[0], inputpopup_args[1])
			# print("return")
			# clear the request for the popup
			inputpopup_args = None
		# re-call self every 200ms to check if threads have requested a popup
		self.after(200, self.spin_to_handle_inputs)
		
	def help_func(self):
		core.MY_PRINT_FUNC(self.loaded_script.helptext)
	
	# this lets the window be moved or resized as the target function is executing
	def run_the_script_as_thread(self):
		thread = threading.Thread(name="do-the-thing", target=self.run_the_script, daemon=True)
		# start the thread
		thread.start()
	
	def run_the_script(self):
		script_name = str(self.optionvar.get())
		core.MY_PRINT_FUNC("="*50)
		core.MY_PRINT_FUNC(script_name)
		# set the 'last used script' item in the json
		core.write_persistent_storage_json('last-script', script_name)
		
		# disable all gui elements for the duration of this function
		# run_butt, spinbox, clear, help, debug
		self.run_butt.configure(state='disabled')
		self.which_script.configure(state='disabled')
		self.clear_butt.configure(state='disabled')
		self.help_butt.configure(state='disabled')
		self.debug_check.configure(state='disabled')
		
		try:
			moreinfo = bool(self.debug_check_var.get())
			self.loaded_script.main(moreinfo)
		except Exception as e:
			# todo: print full traceback for any exception EXCEPT make a special condition for "cancelled file dialogue"
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("ERROR: failed to complete target script")
		
		# re-enable GUI elements when finished running
		self.run_butt.configure(state='normal')
		self.which_script.configure(state='normal')
		self.clear_butt.configure(state='normal')
		self.help_butt.configure(state='normal')
		self.debug_check.configure(state='normal')
		return
	
	def change_mode(self, *_):
		# get the the currently displayed item in the dropdown menu
		newstr = self.optionvar.get()
		# find which index within SCRIPT_LIST it corresponds to
		idx = core.my_list_search(SCRIPT_LIST, lambda x: x[0] == newstr)
		# set helptext and execute func
		dispname, module = SCRIPT_LIST[idx]
		self.loaded_script = module
		
		core.MY_PRINT_FUNC(">>>>>>>>>>")
		core.MY_PRINT_FUNC("Load new script '%s'" % newstr)
		core.MY_PRINT_FUNC("")
		return
		
	def clear_func(self):
		# need to "enable" the box to delete its contents
		self.edit_space.configure(state='normal')
		self.edit_space.delete("1.0", tk.END)
		# these print functions will immediately set it back to the 'disabled' state
		print_header()
		return
	
	def gui_justify_stringlist(self, j: list, right=False) -> list:
		# receive a list of strings and add padding such that they are all the same length
		# first, look for an excuse to give up early
		# if list is empty, nothing to do. if list has only 1 item, also nothing to do.
		if len(j) == 0 or len(j) == 1: return j
		# second, find the length of the longest string in the list (using literal size if printed on screen)
		lengths = [self.edit_space_font.measure(p) for p in j]
		longest_name_len = max(lengths)
		# third, make a new list of strings that have been padded to be that length
		if right:
			# right-justify, force strings to right by padding on left
			retlist = [(" " * (int((longest_name_len - l) / self.edit_space_unit))) + p for p,l in zip(j,lengths)]
		else:
			# left-justify, force strings to left by padding on right
			retlist = [p + (" " * (int((longest_name_len - l) / self.edit_space_unit))) for p,l in zip(j,lengths)]
		return retlist


def launch_gui(title):
	root = tk.Tk()
	root.title(title)
	app = Application(root)
	app.mainloop()


if __name__ == '__main__':
	print(_SCRIPT_VERSION)
	populate_script_list()
	launch_gui("Nuthouse01 MMD PMX VMD tools")

