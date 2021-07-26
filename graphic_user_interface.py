import importlib
import inspect
import sys
import threading
import tkinter as tk
import tkinter.filedialog as fdg
import tkinter.font as tkfont
import tkinter.scrolledtext as tkst
import traceback
from os import path, listdir
from typing import Sequence, Union

from mmd_scripting import __pkg_welcome__
from mmd_scripting.core import nuthouse01_core as core
from mmd_scripting.scripts_for_gui import bone_make_semistandard_auto_armtwist, bone_set_arm_localaxis, \
	bone_armik_addremove, bone_endpoint_addremove, bone_add_sdef_autotwist_handtwist_adapter, check_model_compatibility, \
	convert_vmd_to_txt, convert_vpd_to_vmd, file_sort_textures, file_translate_filenames, file_recompress_images, \
	make_ik_from_vmd, model_overall_cleanup, model_scale, model_shift, morph_scale, morph_hide, morph_invert, \
	translate_source_bone, vmd_armtwist_insert, vmd_rename_bones_morphs

SCRIPTS_WHEN_FROZEN = [
	bone_make_semistandard_auto_armtwist,
	bone_set_arm_localaxis,
	bone_armik_addremove,
	bone_endpoint_addremove,
	bone_add_sdef_autotwist_handtwist_adapter,
	check_model_compatibility,
	convert_vmd_to_txt,
	convert_vpd_to_vmd,
	file_sort_textures,
	file_translate_filenames,
	file_recompress_images,
	make_ik_from_vmd,
	model_overall_cleanup,
	model_scale,
	model_shift,
	morph_scale,
	morph_hide,
	morph_invert,
	translate_source_bone,
	vmd_armtwist_insert,
	vmd_rename_bones_morphs]

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.01 - 7/23/2021"
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


def module_to_dispname(mod) -> str:
	s = path.splitext(path.basename(mod.__file__))[0]
	return s

def get_scripts_from_folder(path_to_scripts: str, existing_scripts: list):
	"""
	Look thru all the scripts in a specified folder, import them, validate them, and append them onto the
	'existing_scripts' list.
	:param path_to_scripts: string path from 'graphic_user_interface.py' to the desired folder
	:param existing_scripts: list to be filled
	"""
	# to make this work even when "graphic_use_interface" is invoked from some other directory,
	# i'll get the absolute path of the GUI file & turn that into absolute path to the scripts!
	path_to_here = path.dirname(__file__)
	# build a list of all files in "scripts_for_gui"
	absdir = path.join(path_to_here, path_to_scripts)
	if not path.isdir(absdir):
		core.MY_PRINT_FUNC("ERROR: tried to import scripts from '%s' but it does not exist!" % path_to_scripts)
		return []
	filenames_in_scriptdir = listdir(absdir)
	# remove anything that starts with underscore
	filenames_in_scriptdir = [a for a in filenames_in_scriptdir if not a.startswith("_")]
	# remove anything that doesnt end with .py
	filenames_in_scriptdir = [a for a in filenames_in_scriptdir if a.endswith(".py")]
	
	# now i should have a list of all the scripts in the folder!
	# then, iterate over the list and import each file
	script_list = []
	for script_name in filenames_in_scriptdir:
		module_name = path.join(path_to_scripts, script_name)  # prepend the path to the scripts folder
		module_name = path.normpath(module_name)  # guarantee they use consistent path separator
		module_name = path.splitext(module_name)[0]  # strip the .py
		module_name = module_name.replace(path.sep, ".")  # replace the folderseparator slashes with dots
		try:
			module = importlib.import_module(module_name)  # actual dynamic import
			script_list.append(module)
		except Exception as e:
			# print an error and full traceback if this failed to parse!
			exc_type, exc_value, exc_traceback = sys.exc_info()
			printme_list = traceback.format_exception(e.__class__, e, exc_traceback)
			# now i have the complete traceback info as a list of strings, each ending with newline
			# but, I want to remove some of these layers to make things less confusing
			# lets remove the the invisible internal layers that the importlib is using
			printme_list = [p for p in printme_list if "_bootstrap" not in p]
			core.MY_PRINT_FUNC("")
			core.MY_PRINT_FUNC("".join(printme_list))
			core.MY_PRINT_FUNC("ERROR1: exception while importing script '%s' from folder '%s'\n" % (script_name, path_to_scripts))
			continue
	# now, iterate over all the laoded modules and validate that they define the things I need.
	successes = 0
	for module in script_list:
		# validate that it has helptext
		if not (hasattr(module, "helptext") and isinstance(module.helptext, str)):
			core.MY_PRINT_FUNC("ERROR2: '%s' is in the '%s' folder but is not a valid script!" % (module_to_dispname(module), path_to_scripts))
			core.MY_PRINT_FUNC("must contain string 'helptext'\n")
			continue
			
		# validate that "main" accepts exactly one boolean argument!
		if not (hasattr(module, "main") and callable(module.main) and len(inspect.signature(module.main).parameters) == 1):
			core.MY_PRINT_FUNC("ERROR3: '%s' is in the '%s' folder but is not a valid script!" % (module_to_dispname(module), path_to_scripts))
			core.MY_PRINT_FUNC("must contain function 'main(moreinfo=True)'\n")
			continue
		
		# validate that there is nothing with the same name already in the list
		if module_to_dispname(module) in [module_to_dispname(m) for m in existing_scripts]:
			core.MY_PRINT_FUNC("ERROR4: '%s' is in the '%s' folder but is not a valid script!" % (module_to_dispname(module), path_to_scripts))
			core.MY_PRINT_FUNC("somehow, some other script with the same name has already been imported! duplicate names are not allowd.\n")
			continue

		# if all validation passes, then store the module object
		existing_scripts.append(module)
		successes += 1
		
	core.MY_PRINT_FUNC("Loaded %d scripts from folder '%s'" % (successes, path_to_scripts))
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
	elif isinstance(ext_list, tuple):
		ext_list = list(ext_list)
	# replaces core func MY_FILEPROMPT_FUNC when running in GUI mode
	
	# ensure the extensions are sorted (for consistency in JSON keys)
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
		raise RuntimeError("file dialogue aborted")
	
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
		self.script_select_frame = tk.Frame(master)
		self.script_select_frame.pack(side=tk.TOP, padx=10, pady=5)
		lab = tk.Label(self.script_select_frame, text="Active script:")
		lab.pack(side=tk.LEFT)

		self.script_list_dispnames = []
		self.script_list_modules = []
		
		# underlying variable tied to the dropdown menu, needed to run self.change_mode when the selection changes
		self.script_select_optionvar = tk.StringVar(master)
		self.script_select_optionvar.trace("w", self.change_mode)
		# build the visible dropdown menu, containing only placeholder list
		self.script_select_optionmenu = tk.OptionMenu(self.script_select_frame, self.script_select_optionvar, "foobar")
		self.script_select_optionmenu.pack(side=tk.LEFT, padx=10)
		
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
		# read all modules from the "scripts_for_gui" folder & populate the optionmenu
		self.rebuild_script_list()
		
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
	
	def rebuild_script_list(self):
		# first, wipe away what I already have
		self.script_list_dispnames = []
		self.script_list_modules = []
		self.script_select_optionmenu.destroy()
		
		# then, re-read from the desired folder(s)
		if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
			self.script_list_modules = SCRIPTS_WHEN_FROZEN
		else:
			get_scripts_from_folder("mmd_scripting/scripts_for_gui/", self.script_list_modules)
			# get_scripts_from_folder("mmd_scripting/scripts_not_for_gui/", self.script_list_modules)
			# get_scripts_from_folder("mmd_scripting/wip/", self.script_list_modules)
		
		if len(self.script_list_modules) == 0:
			return
		
		# then, sort them! by name or by last used, idk, doesn't really matter
		self.script_list_modules.sort(key=module_to_dispname)
		# then rebuild displayed_names
		self.script_list_dispnames = [module_to_dispname(m) for m in self.script_list_modules]
		
		# set the default script, this should invoke "self.change_mode" at least once
		lastused = core.get_persistent_storage_json('last-script')
		if (lastused is not None) and (lastused in self.script_list_dispnames):
			# if the JSON contains a "lastused" value, and that value also matches one of the currently loaded scripts,
			self.script_select_optionvar.set(lastused)
		else:
			# otherwise, just use the top of the list
			self.script_select_optionvar.set(self.script_list_dispnames[0])
		# build the visible dropdown menu
		self.script_select_optionmenu = tk.OptionMenu(self.script_select_frame, self.script_select_optionvar,
													  *self.script_list_dispnames)
		self.script_select_optionmenu.pack(side=tk.LEFT, padx=10)
		return
	
	def run_the_script_as_thread(self):
		"""
		Attached to the big-ass "RUN" button. Invokes the "run_the_script" function in a new thread.
		If not launched in a new thread, the UI is entirely locked up while the script is running, can't even resize
		the window. Honestly not sure why the print function even works when it's being called from a separate thread
		but don't question it.
		"""
		# new thread is set as a "daemon" which means "if the parent dies, the child dies too" i think
		thread = threading.Thread(name="do-the-thing", target=self.run_the_script, daemon=True)
		# start the thread
		thread.start()
	
	def run_the_script(self):
		"""
		Disable all GUI elements, then invoke the script, then re-enable all GUI elements.
		"""
		script_name = str(self.script_select_optionvar.get())
		core.MY_PRINT_FUNC("="*50)
		core.MY_PRINT_FUNC(script_name)
		
		# disable all gui elements for the duration of this function
		# run_butt, spinbox, clear, help, debug
		self.run_butt.configure(state='disabled')
		self.script_select_optionmenu.configure(state='disabled')
		self.clear_butt.configure(state='disabled')
		self.help_butt.configure(state='disabled')
		self.debug_check.configure(state='disabled')
		
		try:
			moreinfo = bool(self.debug_check_var.get())
			self.loaded_script.main(moreinfo)
		except Exception as e:
			# if this exception SPECIFICALLY CAME FROM FILEDIALOGUE ABORT,
			if isinstance(e, RuntimeError) and len(e.args) == 1 and e.args[0] == "file dialogue aborted":
				# just print this polite little message
				core.MY_PRINT_FUNC("ERROR: this script requires an input file to run.")
			# if it is an exception from any other source,
			else:
				# print the full traceback
				exc_type, exc_value, exc_traceback = sys.exc_info()
				printme_list = traceback.format_exception(e.__class__, e, exc_traceback)
				# now i have the complete traceback info as a list of strings, each ending with newline
				core.MY_PRINT_FUNC("")
				core.MY_PRINT_FUNC("".join(printme_list))
				core.MY_PRINT_FUNC("ERROR: the script did not complete succesfully.")
		
		# re-enable GUI elements when finished running
		self.run_butt.configure(state='normal')
		self.script_select_optionmenu.configure(state='normal')
		self.clear_butt.configure(state='normal')
		self.help_butt.configure(state='normal')
		self.debug_check.configure(state='normal')
		return
	
	def change_mode(self, *_):
		# get the the currently displayed item in the dropdown menu
		newstr = self.script_select_optionvar.get()
		# find which index within SCRIPT_LIST it corresponds to (guaranteed to succeed)
		idx = self.script_list_dispnames.index(newstr)
		# set helptext and execute func
		self.loaded_script = self.script_list_modules[idx]
		# set the 'last used script' item in the json
		core.write_persistent_storage_json('last-script', newstr)

		core.MY_PRINT_FUNC(">>>>>>>>>>\nLoad new script '%s'\n" % newstr)
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
	# path_to_scripts = "mmd_scripting/scripts_for_gui/"
	launch_gui("Nuthouse01 MMD PMX VMD tools")

