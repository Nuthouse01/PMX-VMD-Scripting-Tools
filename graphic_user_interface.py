_SCRIPT_VERSION = "Nuthouse01 - 1/24/2021 - v5.06"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# pyinstaller --onefile --noconsole graphic_user_interface.py


# to get better GUI responsiveness, I need to launch the parser and processing functions in separate threads.
# this causes the GUI progress updates to look all flickery and unpleasant... but its worth it.
import threading
import tkinter as tk
import tkinter.filedialog as fdg
import tkinter.font as tkfont
import tkinter.scrolledtext as tkst
from os import path

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from python import nuthouse01_core as core
	from python import bone_armik_addremove
	from python import bone_auto_armtwist
	from python import bone_endpoint_addremove
	from python import check_model_compatibility
	from python import convert_vmd_to_txt
	from python import convert_vpd_to_vmd
	from python import file_recompress_images
	from python import file_sort_textures
	from python import file_translate_names
	from python import model_overall_cleanup
	from python import model_scale
	from python import model_shift
	from python import morph_hide
	from python import morph_invert
	from python import morph_scale
	from python import make_ik_from_vmd
	from python import pmx_list_bone_morph_names
	from python import translate_source_bone
	from python import vmd_armtwist_insert
except ImportError as eee:
	print(eee.__class__.__name__, eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	convert_vmd_to_txt = model_overall_cleanup = file_sort_textures = check_model_compatibility = None
	make_ik_from_vmd = pmx_list_bone_morph_names = vmd_armtwist_insert = bone_armik_addremove = None
	core = morph_invert = morph_hide = morph_scale = file_translate_names = convert_vpd_to_vmd = None
	model_shift = model_scale = bone_endpoint_addremove = translate_source_bone = bone_auto_armtwist = None
	file_recompress_images = None

########################################################################################################################
# constants & options
########################################################################################################################

# if true, calls stock "print" function whenever it prints to the GUI print-space.
# when running from EXE, in noconsole mode, this does nothing at all.
ALSO_PRINT_TO_CONSOLE = False

# list of all possible displayed names in the dropdown list, with associated helptext and mainfunc
# do I want to sort by usefulness? or do I want to group by categories? or maybe just alphabetical? idk
all_script_list = [
	("model_overall_cleanup.py",         model_overall_cleanup.helptext,         model_overall_cleanup.main),
	("file_sort_textures.py",            file_sort_textures.helptext,            file_sort_textures.main),
	("file_translate_names.py",          file_translate_names.helptext,          file_translate_names.main),
	("file_recompress_images.py",        file_recompress_images.helptext,        file_recompress_images.main),
	("bone_auto_armtwist.py",            bone_auto_armtwist.helptext,            bone_auto_armtwist.main),
	("morph_invert.py",                  morph_invert.helptext,                  morph_invert.main),
	("morph_hide.py",                    morph_hide.helptext,                    morph_hide.main),
	("morph_scale.py",                   morph_scale.helptext,                   morph_scale.main),
	("check_model_compatibility.py",     check_model_compatibility.helptext,     check_model_compatibility.main),
	("model_shift.py",                   model_shift.helptext,                   model_shift.main),
	("model_scale.py",                   model_scale.helptext,                   model_scale.main),
	("convert_vmd_to_txt.py",            convert_vmd_to_txt.helptext,            convert_vmd_to_txt.main),
	("convert_vpd_to_vmd.py",            convert_vpd_to_vmd.helptext,            convert_vpd_to_vmd.main),
	("translate_source_bone.py",         translate_source_bone.helptext,         translate_source_bone.main),
	("bone_armik_addremove.py",          bone_armik_addremove.helptext,          bone_armik_addremove.main),
	("bone_endpoint_addremove.py",       bone_endpoint_addremove.helptext,       bone_endpoint_addremove.main),
	("vmd_armtwist_insert.py",           vmd_armtwist_insert.helptext,           vmd_armtwist_insert.main),
	("make_ik_from_vmd.py",              make_ik_from_vmd.helptext,              make_ik_from_vmd.main),
	("pmx_list_bone_morph_names.py",     pmx_list_bone_morph_names.helptext,     pmx_list_bone_morph_names.main),
]


# DO NOT TOUCH: mapping from MY_FILEPROMPT_FUNC filetype input to the info the gui filedialog needs
FILE_EXTENSION_MAP = {
	".vpd .vmd": ("VPD/VMD file", "*.vpd *.vmd *.vmd.bak"),
	".vmd .vpd": ("VPD/VMD file", "*.vpd *.vmd *.vmd.bak"),
	".vmd .txt": ("VMD/TXT file", "*.txt *.vmd *.vmd.bak"),
	".txt .vmd": ("VMD/TXT file", "*.txt *.vmd *.vmd.bak"),
	".vpd": ("VPD file", "*.vpd"),
	".csv": ("CSV file", "*.csv"),
	".txt": ("Text file", "*.txt"),
	".pmx": ("PMX model", "*.pmx"),
	".vmd": ("VMD file", "*.vmd *.vmd.bak"),
	"*": tuple()
}

# DO NOT TOUCH: global vars for passing info between GUI input popup and the thread the script lives in
inputpopup_args = None
inputpopup_done = threading.Event()
inputpopup_done.clear()
inputpopup_result = None


########################################################################################################################
# MAIN & functions
########################################################################################################################




def gui_fileprompt(extensions: str) -> str:
	"""
	Use a Tkinter File Dialogue popup to prompt for a file. Same signature as core.prompt_user_filename().
	
	:param extensions: string of valid extensions, separated by spaces
	:return: case-correct absolute file path
	"""
	# replaces core func MY_FILEPROMPT_FUNC when running in GUI mode
	
	# make this list into a new, separate thing: list of identifiers + globs
	if extensions in FILE_EXTENSION_MAP:
		extensions_labels = FILE_EXTENSION_MAP[extensions]
	else:
		extensions_labels = ("Unknown type", extensions)
	extensions_labels = (extensions_labels,)
	
	# dont trust file dialog to remember last-opened path, manually save/read it
	recordpath = core.get_persistient_storage_path("last_opened_dir.txt")
	c = core.read_txtfile_to_list(recordpath, quiet=True)
	if c:
		# if it has been used before, use the path from last time.
		c = c[0]
		# if the path from last time does not exist, walk up the path till I find a level that does still exist.
		while c and not path.isdir(c):
			c = path.dirname(c)
		start_here = c
	else:
		# if never used before, start in the executable directory
		start_here = "."
	
	newpath = fdg.askopenfilename(initialdir=start_here,
								  title="Select input file: {%s}" % extensions,
								  filetypes=extensions_labels)
	
	# if user closed the prompt before giving a file path, quit here
	if newpath == "":
		core.MY_PRINT_FUNC("ERROR: this script requires an input file to run")
		raise RuntimeError()
	
	# they got an existing file! update the last_opened_dir file
	core.write_list_to_txtfile(recordpath, [path.dirname(newpath)], quiet=True)
	
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


# this lets the window be moved or resized as the target function is executing
def run_as_thread(func):
	thread = threading.Thread(name="do-the-thing", target=func, daemon=True)
	# start the thread
	thread.start()




class Application(tk.Frame):
	def __init__(self, master):
		tk.Frame.__init__(self, master)
		
		###############################################
		# first, set up non-ui class members
		# this variable is used in this new print function, very important
		self.last_print_was_progress = False
		# payload is pointer to currently selected main() func, helptext is the currently selected help string
		self.payload = None
		self.helptext = ""
		# list of all possible displayed names in the OptionMenu, with assoc helptext and mainfunc
		self.all_script_list = all_script_list
		
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
		self.optionvar.set(self.all_script_list[0][0])
		# build the acutal dropdown menu
		self.which_script = tk.OptionMenu(self.which_script_frame, self.optionvar, *[x[0] for x in self.all_script_list])
		self.which_script.pack(side=tk.LEFT, padx=10)
		
		###############################################
		# third, build the GUI control buttons
		self.control_frame = tk.Frame(master, relief=tk.RAISED, borderwidth=1)
		self.control_frame.pack(side=tk.TOP, fill='x', padx=10, pady=5)
		
		self.run_butt = tk.Button(self.control_frame, text="RUN", width=7, command=lambda: run_as_thread(self.do_the_thing))
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
		self.print_header()
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
		core.MY_PRINT_FUNC(self.helptext)
	
	def do_the_thing(self):
		core.MY_PRINT_FUNC("="*50)
		core.MY_PRINT_FUNC(str(self.optionvar.get()))
		# disable all gui elements for the duration of this function
		# run_butt, spinbox, clear, help, debug
		self.run_butt.configure(state='disabled')
		self.which_script.configure(state='disabled')
		self.clear_butt.configure(state='disabled')
		self.help_butt.configure(state='disabled')
		self.debug_check.configure(state='disabled')
		
		try:
			self.payload(bool(self.debug_check_var.get()))
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("ERROR: failed to complete target script")
		
		# re-enable GUI elements when finished running
		self.run_butt.configure(state='normal')
		self.which_script.configure(state='normal')
		self.clear_butt.configure(state='normal')
		self.help_butt.configure(state='normal')
		self.debug_check.configure(state='normal')
		return
	
	def print_header(self):
		core.MY_PRINT_FUNC(core.PACKAGE_VERSION)
		core.MY_PRINT_FUNC("Begin by selecting a script above, then click 'Run'")
		core.MY_PRINT_FUNC("Click 'Help' to print out details of what the selected script does")
		return
		
	def change_mode(self, *_):
		# need to have *args here even if i dont use them
		# the the currently displayed item in the dropdown menu
		newstr = self.optionvar.get()
		# find which index within all_script_list it corresponds to
		idx = [x[0] for x in self.all_script_list].index(newstr)
		# set helptext and execute func
		self.helptext = self.all_script_list[idx][1]
		self.payload = self.all_script_list[idx][2]
		core.MY_PRINT_FUNC(">>>>>>>>>>")
		core.MY_PRINT_FUNC("Load new script '%s'" % newstr)
		core.MY_PRINT_FUNC("")
		return
		
	def clear_func(self):
		# need to "enable" the box to delete its contents
		self.edit_space.configure(state='normal')
		self.edit_space.delete("1.0", tk.END)
		# these print functions will immediately set it back to the 'disabled' state
		self.print_header()
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
	launch_gui("Nuthouse01 MMD PMX VMD tools")

