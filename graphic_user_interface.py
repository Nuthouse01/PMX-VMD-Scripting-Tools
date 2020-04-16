# Nuthouse01 - 04/15/2020 - v4.02
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# pyinstaller --onefile --noconsole graphic_user_interface.py


# TODO: error wrappers in PMX parser? ugh

# to get better GUI responsiveness, I need to launch the parser and processing functions in separate threads.
# this causes the GUI progress updates to look all flickery and unpleasant... but its worth it.
import threading
import tkinter as tk
import tkinter.filedialog as fdg
import tkinter.scrolledtext as tkst
from os import path

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from python import nuthouse01_core as core
	from python import make_ik_from_vmd
	from python import pmx_arm_ik_addremove
	from python import pmx_list_bone_morph_names
	from python import pmx_overall_cleanup
	from python import texture_file_sort
	from python import vmd_armtwist_insert
	from python import vmd_convert_tool
	from python import vmd_model_compatability_check
except ImportError as eee:
	print(eee.__class__.__name__, eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	vmd_convert_tool = pmx_overall_cleanup = texture_file_sort = vmd_model_compatability_check = None
	make_ik_from_vmd = pmx_list_bone_morph_names = vmd_armtwist_insert = None
	core = None


FILE_EXTENSION_MAP = {
	".vmd .txt": ("VMD/TXT file", "*.txt *.vmd *.vmd.bak"),
	".txt .vmd": ("VMD/TXT file", "*.txt *.vmd *.vmd.bak"),
	".csv": ("CSV file", "*.csv"),
	".txt": ("Text file", "*.txt"),
	".pmx": ("PMX model", "*.pmx"),
	".vmd": ("VMD file", "*.vmd *.vmd.bak"),
	"*": tuple()
}

def gui_fileprompt(extensions: str) -> str:
	# replaces core func MY_FILEPROMPT_FUNC when running in GUI mode
	
	# make this list into a new, separate thing: list of identifiers + globs
	if extensions in FILE_EXTENSION_MAP:
		extensions_labels = FILE_EXTENSION_MAP[extensions]
	else:
		extensions_labels = ("Unknown type", extensions)
	extensions_labels = (extensions_labels,)
	
	# dont trust file dialog to remember last-opened path, manually save/read it
	recordpath = core.get_persistient_storage_path("last_opened_dir.txt")
	c = core.read_txt_to_rawlist(recordpath, quiet=True)
	if c and path.isdir(c[0][0]):
		start_here = c[0][0]
	else:
		start_here = "."
	
	newpath = fdg.askopenfilename(initialdir=start_here,
								  title="Select input file: {%s}" % extensions,
								  filetypes=extensions_labels)
	
	# if user closed the prompt before giving a file path, quit here
	if newpath == "":
		core.MY_PRINT_FUNC("ERROR: this script requires an input file to run")
		raise RuntimeError()
	
	# they got an existing file! update the last_opened_dir file
	core.write_rawlist_to_txt(recordpath, [[path.dirname(newpath)]], quiet=True)
	
	return newpath



simplechoice_args = None
simplechoice_done = threading.Event()
simplechoice_done.clear()
simplechoice_result = -1

def gui_simplechoice_trigger(options, explain_info=None):
	# print("trig")
	global simplechoice_args
	# write into simplechoice_args to signify that I want a popup
	simplechoice_args = [options, explain_info]
	# wait for a choice to be made from within the popup
	simplechoice_done.wait()
	simplechoice_done.clear()
	if simplechoice_result == -1:
		# if they clicked x without choosing a result, return the first option
		return options[0]
	else:
		return simplechoice_result


def gui_simplechoice(options, explain_info=None):
	# a popupwindow to replace the stock "input()" function when running in GUI mode
	# print("pop")
	# create popup
	win = tk.Toplevel()
	win.title("Make a selection")
	# normally when x button is pressed, it calls "destroy". this replaces that with "quit", so i return from mainloop
	# that way the x button resumes executing below win.mainloop and the script continues
	def on_x():
		simplechoice_done.set()
		win.destroy()
	win.protocol("WM_DELETE_WINDOW", on_x)
	
	global simplechoice_result
	simplechoice_result = -1
	
	# if explain_info is given, create labels that display those strings
	if isinstance(explain_info, str):
		explain_info = [explain_info]
	if explain_info is not None:
		labelframe = tk.Frame(win)
		labelframe.pack(side=tk.TOP, fill='x')
		for f in explain_info:
			# create labels for each line
			# todo: make them centered & wrap nicely
			label = tk.Label(labelframe, text=f)
			label.pack(side=tk.TOP, fill='x', padx=10, pady=10)
			core.MY_PRINT_FUNC(f)
		
	buttonframe = tk.Frame(win)
	buttonframe.pack(side=tk.TOP)
	
	def setresult(r):
		global simplechoice_result
		simplechoice_result = r
		# pressing the button should stop the mainloop
		simplechoice_done.set()
		win.destroy()
	
	# create buttons for each numbered option
	for i in options:
		c = lambda v=i: setresult(v)
		button = tk.Button(buttonframe, text=str(i), command=c)
		button.pack(side=tk.LEFT, padx=10, pady=10)
	
	return None


# this lets the window be moved or resized as the target function is executing
# however, this makes the text kinda flickery, oh well
def run_as_thread(func):
	thread = threading.Thread(name="do-the-thing", target=func, daemon=True)
	# start the thread
	thread.start()




class Application(tk.Frame):
	def __init__(self, master):
		tk.Frame.__init__(self, master)
		
		# from each script, get main() and helptext
		self.payload = None
		self.helptext = ""
		
		# list of all possible displayed names in the OptionMenu, with assoc helptext and mainfunc
		self.all_script_list = [
			("pmx_overall_cleanup.py",           pmx_overall_cleanup.helptext,           pmx_overall_cleanup.main),
			("texture_file_sort.py",             texture_file_sort.helptext,             texture_file_sort.main),
			("vmd_model_compatability_check.py", vmd_model_compatability_check.helptext, vmd_model_compatability_check.main),
			("vmd_armtwist_insert.py",           vmd_armtwist_insert.helptext,           vmd_armtwist_insert.main),
			("vmd_convert_tool.py",              vmd_convert_tool.helptext,              vmd_convert_tool.main),
			("make_ik_from_vmd.py",              make_ik_from_vmd.helptext,              make_ik_from_vmd.main),
			("pmx_arm_ik_addremove.py",          pmx_arm_ik_addremove.helptext,          pmx_arm_ik_addremove.main),
			("pmx_list_bone_morph_names.py",     pmx_list_bone_morph_names.helptext,     pmx_list_bone_morph_names.main),
		]
		
		self.optionvar = tk.StringVar(master)
		self.optionvar.trace("w", self.change_mode)
		self.optionvar.set(self.all_script_list[0][0])
		
		self.which_script_frame = tk.Frame(master)
		self.which_script_frame.pack(side=tk.TOP, padx=10, pady=5)
		
		lab = tk.Label(self.which_script_frame, text="Active script:")
		lab.pack(side=tk.LEFT)
		
		self.which_script = tk.OptionMenu(self.which_script_frame, self.optionvar, *[x[0] for x in self.all_script_list])
		self.which_script.pack(side=tk.LEFT, padx=10)
		
		
		
		###############################################
		# second, set up other non-ui class members
		# this variable is used in this new print function, very important
		self.last_print_was_progress = False
		
		###############################################
		# third, build the GUI buttons and etc
		
		self.control_frame = tk.Frame(master, relief=tk.RAISED, borderwidth=1)
		self.control_frame.pack(side=tk.TOP, fill='x', padx=10, pady=5)
		
		self.run_butt = tk.Button(self.control_frame, text="RUN", width=7, command=lambda: run_as_thread(self.do_the_thing))
		self.defaultfont = self.run_butt.cget("font")
		# print(self.defaultfont)
		self.run_butt.configure(font=(self.defaultfont, 18))
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
		# VERY IMPORTANT: overwrite the default simple-choice function with one that makes a popup
		core.MY_SIMPLECHOICE_FUNC = gui_simplechoice_trigger
		# VERY IMPORTANT: overwrite the default fileprompt function with one that uses a popup filedialogue
		core.MY_FILEPROMPT_FUNC = gui_fileprompt
		
		self.print_header()
		
		self.spin_to_handle_inputs()
		
		self.change_mode()
		
		# done with init
		return
	
	# replacement for core.basic_print function, print to text thingy instead of to console
	def my_write(self, *args, is_progress=False):
		the_string = ' '.join([str(x) for x in args])
		core.basic_print(the_string, is_progress=is_progress)  # todo remove this probably?
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
		# print("spin")
		global simplechoice_args
		if simplechoice_args is not None:
			# print("do")
			# if it is requested, create the popup
			gui_simplechoice(simplechoice_args[0], simplechoice_args[1])
			# print("return")
			# dismiss the request for the popup
			simplechoice_args = None
		
		self.after(200, self.spin_to_handle_inputs)
		
	def help_func(self):
		core.MY_PRINT_FUNC(self.helptext)
	
	def do_the_thing(self):
		core.MY_PRINT_FUNC("="*50)
		# disable run_butt for the duration of this function
		self.run_butt.configure(state='disabled')
		# disable spinbox
		self.which_script.configure(state='disabled')
		# disable clear button, help button
		self.clear_butt.configure(state='disabled')
		self.help_butt.configure(state='disabled')
		
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
		return
	
	def print_header(self):
		core.MY_PRINT_FUNC("Nuthouse01 - 04/15/2020 - v4.02")
		core.MY_PRINT_FUNC("Begin by selecting a script above, then click 'Run'")
		core.MY_PRINT_FUNC("Click 'Help' to print out details of what the selected script does")
		return
		
	def change_mode(self, *args):
		# need to have *args here even if i dont use them
		newstr = self.optionvar.get()
		idx = [x[0] for x in self.all_script_list].index(newstr)
		self.helptext = self.all_script_list[idx][1]
		self.payload = self.all_script_list[idx][2]
		core.MY_PRINT_FUNC(">>>>>>>>>>")
		core.MY_PRINT_FUNC("Load new script '%s'" % newstr)
		core.MY_PRINT_FUNC("")
		return
		
	def clear_func(self):
		self.edit_space.configure(state='normal')
		self.edit_space.delete("1.0", tk.END)
		self.print_header()
		# these print functions will immediately set it back to the 'disabled' state
		return
	
	
def launch_gui(title):
	root = tk.Tk()
	root.title(title)
	app = Application(root)
	app.mainloop()


if __name__ == '__main__':
	launch_gui("Nuthouse01 MMD PMX VMD tools")

