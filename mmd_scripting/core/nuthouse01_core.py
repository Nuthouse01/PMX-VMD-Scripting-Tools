import math
import sys
import traceback
from os import path, listdir
from typing import Any, Tuple, List, Sequence, Callable, Iterable, TypeVar, Union

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.03 - 8/9/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# this contains a bunch of functions that are used throughout multiple different scripts
# it's better to keep them all in one place than copy them for each file


########################################################################################################################
# constants used in many files that I don't wanna keep copying over and over
########################################################################################################################

pmxe_material_csv_header = [";Material", "材質名", "材質名(英)", "拡散色_R", "拡散色_G", "拡散色_B", "拡散色_A(非透過度)",
							"反射色_R", "反射色_G", "反射色_B", "反射強度", "環境色_R", "環境色_G", "環境色_B", "両面描画(0/1)",
							"地面影(0/1)", "セルフ影マップ(0/1)", "セルフ影(0/1)", "頂点色(0/1)", "描画(0:Tri/1:Point/2:Line)",
							"エッジ(0/1)", "エッジサイズ", "エッジ色_R", "エッジ色_G", "エッジ色_B", "エッジ色_A",
							"テクスチャパス", "スフィアテクスチャパス", "スフィアモード(0:無効/1:乗算/2:加算/3:サブテクスチャ)",
							"Toonテクスチャパス", "メモ"]
pmxe_material_csv_tag = "Material"
pmxe_vertex_csv_header = [";Vertex", "頂点Index", "位置_x", "位置_y", "位置_z", "法線_x", "法線_y", "法線_z", "エッジ倍率",
						  "UV_u", "UV_v", "追加UV1_x", "追加UV1_y", "追加UV1_z", "追加UV1_w", "追加UV2_x", "追加UV2_y",
						  "追加UV2_z", "追加UV2_w", "追加UV3_x", "追加UV3_y", "追加UV3_z", "追加UV3_w", "追加UV4_x",
						  "追加UV4_y", "追加UV4_z", "追加UV4_w", "ウェイト変形タイプ(0:BDEF1/1:BDEF2/2:BDEF4/3:SDEF/4:QDEF)",
						  "ウェイト1_ボーン名", "ウェイト1_ウェイト値", "ウェイト2_ボーン名", "ウェイト2_ウェイト値",
						  "ウェイト3_ボーン名", "ウェイト3_ウェイト値", "ウェイト4_ボーン名", "ウェイト4_ウェイト値", "C_x",
						  "C_y", "C_z", "R0_x", "R0_y", "R0_z", "R1_x", "R1_y", "R1_z"]
pmxe_vertex_csv_tag = "Vertex"
pmxe_bone_csv_header = [";Bone", "ボーン名", "ボーン名(英)", "変形階層", "物理後(0/1)", "位置_x", "位置_y", "位置_z",
						"回転(0/1)", "移動(0/1)", "IK(0/1)", "表示(0/1)", "操作(0/1)", "親ボーン名", "表示先(0:オフセット/1:ボーン)",
						"表示先ボーン名", "オフセット_x", "オフセット_y", "オフセット_z", "ローカル付与(0/1)", "回転付与(0/1)",
						"移動付与(0/1)", "付与率", "付与親名", "軸制限(0/1)", "制限軸_x", "制限軸_y", "制限軸_z", "ローカル軸(0/1)",
						"ローカルX軸_x", "ローカルX軸_y", "ローカルX軸_z", "ローカルZ軸_x", "ローカルZ軸_y", "ローカルZ軸_z",
						"外部親(0/1)", "外部親Key", "IKTarget名", "IKLoop", "IK単位角[deg]"]
pmxe_bone_csv_tag = "Bone"
pmxe_morph_csv_header = [";Morph", "モーフ名", "モーフ名(英)", "パネル(0:無効/1:眉(左下)/2:目(左上)/3:口(右上)/4:その他(右下))",
						 "モーフ種類(0:グループモーフ/1:頂点モーフ/2:ボーンモーフ/3:UV(Tex)モーフ/4:追加UV1モーフ/5:追加UV2モーフ/6:追加UV3モーフ/7:追加UV4モーフ/8:材質モーフ/9:フリップモーフ/10:インパルスモーフ)"]
pmxe_morph_csv_tag = "Morph"
pmxe_morphvertex_csv_tag = "VertexMorph"
pmxe_morphmaterial_csv_tag = "MaterialMorph"
pmxe_morphuv_csv_tag = "UVMorph"
pmxe_rigidbody_csv_header = [";Body", "剛体名", "剛体名(英)", "関連ボーン名", "剛体タイプ(0:Bone/1:物理演算/2:物理演算+ボーン追従)",
							 "グループ(0~15)", "非衝突グループ文字列(ex:1 2 3 4)", "形状(0:球/1:箱/2:カプセル)", "サイズ_x",
							 "サイズ_y", "サイズ_z", "位置_x", "位置_y", "位置_z", "回転_x[deg]", "回転_y[deg]", "回転_z[deg]",
							 "質量", "移動減衰", "回転減衰", "反発力", "摩擦力"]
pmxe_rigidbody_csv_tag = "Body"
pmxe_face_csv_header = [";Face", "親材質名", "面Index", "頂点Index1", "頂点Index2", "頂点Index3"]
pmxe_face_csv_tag = "Face"

interpolation_default_linear = [20, 20, 107, 107]

########################################################################################################################
# misc functions and user-input functions
########################################################################################################################

def basic_print(*args, is_progress=False) -> None:
	"""
	CONSOLE FUNCTION: emulate builtin print() function and display text in console.
	
	:param args: any number of string-able objects, will be joined with spaces.
	:param is_progress: default false. if true, move the cursor to the beginning of THIS line after printing, so NEXT
	print contents will overwrite this one.
	"""
	the_string = ' '.join([str(x) for x in args])
	# replace the print() function with this so i can replace this with the text redirector
	if is_progress:
		# leave the cursor at the beginning of the line so the next print statement overwrites this
		print(the_string, end='\r', flush=True)
		# print('\r' + p, end='', flush=True)  # leave cursor at the end of the line
		# print('\r', end='', flush=False)  # force NEXT print statement to begin by resetting to the start of the line
	else:
		# otherwise use the normal print
		print(the_string)

# global variable holding a function pointer that i can overwrite with a different function pointer when in GUI mode
MY_PRINT_FUNC = basic_print

def pause_and_quit(message=None) -> None:
	"""
	CONSOLE FUNCTION: use input() to suspend until user presses ENTER, then die.
	DO NOT USE THIS FUNCTION IN ANY SCRIPTS THAT WILL BE EXECUTED BY THE GUI.
	
	:param message: optional string to print before dying
	"""
	# wait for user input before exiting because i want the window to stay open long enough for them to read output
	MY_PRINT_FUNC(message)
	MY_PRINT_FUNC("...press ENTER to exit...")
	input()
	exit()


PROGRESS_REFRESH_RATE = 0.03  # threshold for actually printing
PROGRESS_LAST_VALUE = 0.0  # last%
def print_progress_oneline(newpercent:float) -> None:
	"""
	Prints progress percentage on one continually-overwriting line. To minimize actual print-to-screen events, only
	print in increments of PROGRESS_REFRESH_RATE (currently 3%) regardless of how often this function is called.
	This uses the MY_PRINT_FUNC approach so this function works in both GUI and CONSOLE modes.
	
	:param newpercent: float [0-1], current progress %
	"""
	global PROGRESS_LAST_VALUE
	# if 'curr' is lower than it was last printed (meaning reset), or it's been a while since i last printed a %, then print
	if (newpercent < PROGRESS_LAST_VALUE) or (newpercent >= PROGRESS_LAST_VALUE + PROGRESS_REFRESH_RATE):
		# cursor gets left at the beginning of line, so the next print will overwrite this one
		p = "...working: {:05.1%}".format(newpercent)
		MY_PRINT_FUNC(p, is_progress=True)
		PROGRESS_LAST_VALUE = newpercent

# useful as keys for sorting
def get1st(x):
	return x[0]
def get2nd(x):
	return x[1]

THING = TypeVar('THING')      # Declare type variable so I can say "whatever input type is, it matches the output type"
def my_list_search(searchme: Iterable[THING], condition: Callable[[THING], bool], getitem=False):
	# in a list of things, find the first thing where the condition is true
	for d,row in enumerate(searchme):
		if condition(row):
			return row if getitem else d
	return None

def my_list_partition(l: Iterable[THING], condition: Callable[[THING], bool]) -> Tuple[List[THING], List[THING]]:
	"""
	Split one list into two NEW lists based on a condition. Kinda like a list comprehension but it produces 2 results.
	
	:param l: the list to be split in two
	:param condition: lambda function that returns true or false
	:return: tuple of lists, (list_lambda_true, list_lambda_false)
	"""
	list_where_true = []
	list_where_false = []
	for iiiii in l:
		if condition(iiiii):
			list_where_true.append(iiiii)
		else:
			list_where_false.append(iiiii)
	return list_where_true, list_where_false

def prettyprint_file_size(size_b: int) -> str:
	"""
	Format a filesize in terms of bytes, KB, MB, GB, whatever is most appropriate.
	:param size_b: int size in bytes
	:return: string
	"""
	if abs(size_b) < 1024:
		# bytes
		ret = "%d B" % size_b
	elif abs(size_b) < 1024*1024:
		# kilobytes
		s = size_b / 1024
		ret = "{:.2f} KB".format(s)
	elif abs(size_b) < 1024*1024*1024:
		# megabytes
		s = size_b / (1024*1024)
		ret = "{:.2f} MB".format(s)
	else:
		# gigabytes
		s = size_b / (1024*1024*1024)
		ret = "{:.2f} GB".format(s)
	return ret
	

MAXDIFFERENCE = 0
# recursively check for equality, using a loose comparison for floatingpoints
# operating on test file, the greatest difference introduced by quaternion transform is 0.000257
# lets set sanity-check threshold at double that, 0.0005
# return the number of times a float difference exceeded the threshold
# if there is a non-float difference, return infinity
def recursively_compare(A,B):
	global MAXDIFFERENCE
	# return 1/true if it FAILS, return 0/false if it MATCHES
	if hasattr(A, "list"): A = A.list()
	if hasattr(B, "list"): B = B.list()
	if isinstance(A, float) and isinstance(B, float):
		# for floats specifically, replace exact compare with approximate compare
		diff = abs(A-B)
		MAXDIFFERENCE = max(diff, MAXDIFFERENCE)
		return diff >= 0.0005
	if isinstance(A, list) and isinstance(B, list):
		if len(A) != len(B):
			return float("inf")
		collect = 0
		for A_, B_ in zip(A, B):
			collect += recursively_compare(A_, B_)
		return collect
	# if not float and not list, then use standard compare
	if A != B:
		return float("inf")
	return 0

def new_recursive_compare(L, R):
	diffcount = 0
	maxdiff = 0
	if isinstance(L, (list,tuple)) and isinstance(R, (list,tuple)):
		# if both are listlike, recurse on each element of 'em
		if len(L) != len(R):
			diffcount += 1
		# walk down both for as long as it will go, i guess?
		for d,(LL, RR) in enumerate(zip(L, R)):
			thisdiff, thismax = new_recursive_compare(LL, RR)
			diffcount += thisdiff
			maxdiff = max(maxdiff, thismax)
	elif hasattr(L,"validate") and hasattr(R,"validate"):
		# for my custom classes, look over the members with "vars" because its fancy
		Lvars = sorted(list(vars(L).items()))
		Rvars = sorted(list(vars(R).items()))
		for (nameL, LL), (nameR, RR) in zip(Lvars, Rvars):
			thisdiff, thismax = new_recursive_compare(LL, RR)
			diffcount += thisdiff
			maxdiff = max(maxdiff, thismax)
	elif isinstance(L, float) and isinstance(R, float):
		# for floats specifically, replace exact compare with approximate compare
		diff = abs(L - R)
		maxdiff = diff
		if L != R:
			diffcount += 1
	else:
		# if not float and not list, then use standard compare
		if L != R:
			diffcount += 1
	return diffcount, maxdiff

def flatten(x: Sequence) -> list:
	"""
	Recursively flatten a list of lists (or tuples). Empty lists get replaced with "None" instead of completely vanishing.
	"""
	retme = []
	for thing in x:
		if isinstance(thing, (list, tuple)):
			if len(thing) == 0:
				retme.append(None)
			else:
				retme += flatten(thing)
		else:
			retme.append(thing)
	return retme

def justify_stringlist(j: List[str], right=False) -> List[str]:
	"""
	CONSOLE FUNCTION: justify all str in a list to match the length of the longest str in that list. Determined by
	len() function, i.e. number of chars, not by true width when printed, so it doesn't work well with JP/CN chars.
	
	:param j: list[str] to be justified
	:param right: by default, left-justify (right-pad). if this is true, right-justify (left-pad) instead.
	:return: list[str] after padding/justifying
	"""
	# first, look for an excuse to give up early
	if len(j) == 0 or len(j) == 1: return j
	# second, find the length of the longest string in the list
	longest_name_len = max([len(p) for p in j])
	# third, make a new list of strings that have been padded to be that length
	if right:
		# right-justify, force strings to right by padding on left
		retlist = [(" " * (longest_name_len - len(p))) + p for p in j]
	else:
		# left-justify, force strings to left by padding on right
		retlist = [p + (" " * (longest_name_len - len(p))) for p in j]
	return retlist
# global variable holding a function pointer that i can overwrite with a different function pointer when in GUI mode
MY_JUSTIFY_STRINGLIST = justify_stringlist

def prompt_user_choice(options: Sequence[int], explain_info=None) -> int:
	"""
	CONSOLE FUNCTION: prompt for multiple-choice question & continue prompting until one of those options is chosen.
	
	:param options: list/tuple of ints
	:param explain_info: None or str or list[str], help text that will be printed when func is called
	:return: int that the user chose
	"""
	if isinstance(explain_info, (list, tuple)):
		for p in explain_info:
			MY_PRINT_FUNC(p)
	elif isinstance(explain_info, str):
		MY_PRINT_FUNC(explain_info)
	# create set for matching against
	choicelist = [str(i) for i in options]
	# create printable string which is all options separated by slashes
	promptstr = "/".join(choicelist)
	
	while True:
		# continue prompting until the user gives valid input
		choice = input(" Choose [" + promptstr + "]: ")
		if choice in choicelist:
			# if given valid input, break
			break
		# if given invalid input, prompt and loop again
		MY_PRINT_FUNC("invalid choice")
	return int(choice)

# global variable holding a function pointer that i can overwrite with a different function pointer when in GUI mode
MY_SIMPLECHOICE_FUNC = prompt_user_choice

def general_input(valid_check: Callable[[str], bool], explain_info=None) -> str:
	"""
	CONSOLE FUNCTION: Prompt for string input & continue prompting until given function 'valid_check' returns True.
	'valid_check' should probably print some kind of error whenever it returns False, explaining why input isn't valid.
	Trailing whitespace is removed before calling 'valid_check' and before returning result.
	
	:param valid_check: function or lambda that takes str as in put and returns bool
	:param explain_info: None or str or list[str], help text that will be printed when func is called
	:return: input string (trailing whitespace removed)
	"""
	if explain_info is None:
		pass
	elif isinstance(explain_info, str):
		MY_PRINT_FUNC(explain_info)
	elif isinstance(explain_info, (list, tuple)):
		for p in explain_info:
			MY_PRINT_FUNC(p)
	
	while True:
		s = input("> ")
		s = s.rstrip()  # no use for trailing whitespace, sometimes have use for leading whitespace
		# perform valid-check
		if valid_check(s):
			break
		else:
			# if given invalid input, prompt and loop again
			MY_PRINT_FUNC("invalid input")
	return s

# global variable holding a function pointer that i can overwrite with a different function pointer when in GUI mode
MY_GENERAL_INPUT_FUNC = general_input


def prompt_user_filename(label: str, ext_list: Union[str,Sequence[str]]) -> str:
	"""
	CONSOLE FUNCTION: prompt for file & continue prompting until user enters the name of an existing file with the
	specified file extension. Returns case-correct absolute file path to the specified file.
	
	:param label: {{short}} string label that identifies this kind of input, like "Text file" or "VMD file"
	:param ext_list: list of acceptable extensions, or just one string
	:return: case-correct absolute file path
	"""
	if isinstance(ext_list, str):
		# if it comes in as a string, wrap it in a list
		ext_list = [ext_list]
	MY_PRINT_FUNC('(type/paste the path to the file, ".." means "go up a folder")')
	MY_PRINT_FUNC('(path can be absolute, like C:/username/Documents/miku.pmx)')
	MY_PRINT_FUNC('(or path can be relative to here, example: ../../mmd/models/miku.pmx)')
	while True:
		# continue prompting until the user gives valid input
		if ext_list:
			name = input(" {:s} path ending with [{:s}] = ".format(label, ", ".join(ext_list)))
			valid_ext = any(name.lower().endswith(a.lower()) for a in ext_list)
			if not valid_ext:
				MY_PRINT_FUNC("Err: given file does not have acceptable extension")
				continue
		else:
			# if given an empty sequence, then do not check for valid extension. accept anything.
			name = input(" {:s} path = ".format(label))
		if not path.isfile(name):
			MY_PRINT_FUNC("Err: given name is not a file, did you type it wrong?")
			abspath = path.abspath(name)
			# find the point where the filepath breaks! walk up folders 1 by 1 until i find the last place where the path was valid
			c = abspath
			while c and not path.exists(c):
				c = path.dirname(c)
			whereitbreaks = (" " * len(c)) + " ^^^^"
			MY_PRINT_FUNC(abspath)
			MY_PRINT_FUNC(whereitbreaks)
			continue
		break
	# it exists, so make it absolute
	name = path.abspath(path.normpath(name))
	# windows is case insensitive, so this doesn't matter, but to make it match the same case as the existing file:
	return filepath_make_casecorrect(name)

# global variable holding a function pointer that i can overwrite with a different function pointer when in GUI mode
MY_FILEPROMPT_FUNC = prompt_user_filename

def filepath_splitdir(initial_name: str) -> Tuple[str,str]:
	"""
	Alias for path.split()
	:param initial_name: string filepath
	:return: (directories, filename)
	"""
	return path.split(initial_name)

def filepath_splitext(initial_name: str) -> Tuple[str,str]:
	"""
	Alias for path.splitext()
	:param initial_name: string filepath
	:return: (directories+filename, extension)
	"""
	return path.splitext(initial_name)

def filepath_insert_suffix(initial_name: str, suffix:str) -> str:
	"""
	Simple function, insert the suffix between the Basename and Extension.
	:param initial_name: string filepath
	:param suffix: string to append to filepath
	:return: string filepath
	"""
	N,E = filepath_splitext(initial_name)
	ret = N + suffix + E
	return ret

def filepath_make_casecorrect(initial_name: str) -> str:
	"""
	Make the given path match the case of the file/folders on the disk.
	If the path does not exist, then make it casecorrect up to the point where it no longer exists.
	:param initial_name: string filepath
	:return: string filepath, exactly the same as input except for letter case
	"""
	initial_name = path.normpath(initial_name)
	# all "." are removed, all ".." are removed except for leading...
	# first, break the given path into all of its segments
	seglist = initial_name.split(path.sep)
	if len(seglist) == 0:
		raise ValueError("ERROR: input path '%s' is too short" % initial_name)

	if path.isabs(initial_name):
		first = seglist.pop(0) + path.sep
		if path.ismount(first):
			# windows absolute path! begins with a drive letter
			reassemble_name = first.upper()
		elif first == "":
			# ???? linux ????
			reassemble_name = path.sep
		else:
			MY_PRINT_FUNC("path is abs, but doesn't start with drive or filesep? what? '%s'" % initial_name)
			reassemble_name = first
	else:
		# if not an absolute path, it needs to start as "." so that listdir works right (need to remove this when done tho)
		reassemble_name = "."
	
	while seglist:
		nextseg = seglist.pop(0)
		if nextseg == "..":
			reassemble_name = path.join(reassemble_name, nextseg)
		else:
			try:
				whats_here = listdir(reassemble_name)
			except FileNotFoundError:
				# fallback just in case I forgot about something
				return initial_name
			whats_here = [str(w) for w in whats_here]
			whats_here_lower = [w.lower() for w in whats_here]
			try:
				# find which entry in listdir corresponds to nextseg, when both sides are lowered
				idx = whats_here_lower.index(nextseg.lower())
			except ValueError:
				# the next segment isnt available in the listdir! the path is invalid from here on out!
				# so, just join everything remaining & break out of the loop.
				reassemble_name = path.join(reassemble_name, nextseg, *seglist)
				break
			# the next segment IS available in the listdir, so use the case-correct version of it
			reassemble_name = path.join(reassemble_name, whats_here[idx])
			# then, loop!
	# call normpath one more time to get rid of leading ".\\" when path is relative!
	reassemble_name = path.normpath(reassemble_name)
	return reassemble_name
	
def filepath_get_unused_name(initial_name: str, checkdisk=True, namelist=None) -> str:
	"""
	Given a desired filepath, generate a path that is guaranteed to be unused & safe to write to.
	Append integers to the end of the basename until it passes.
	Often it doesn't need to append anything and returns initial_name unmodified.
	
	:param initial_name: desired file path, absolute or relative.
	:param checkdisk: default True. if true, then check uniqueness against names on disk.
	:param namelist: default empty. if given, then check uniqueness against these names. list or set.
	:return: same file path as initial_name, but with integers inserted until it becomes unique (if needed)
	"""
	# if namelist is given, check against namelist as well as what's on the disk...
	# make an all-lower version of namelist
	if namelist is None: namelist_lower = []
	else:                namelist_lower = [n.lower() for n in namelist]
	basename, extension = path.splitext(initial_name)
	test_name = basename + extension  # first, try it without adding any numbers
	for append_num in range(1, 1000):
		diskpass = not (checkdisk and path.exists(test_name))
		listpass = (test_name.lower() not in namelist_lower)
		if diskpass and listpass:
			# if this name passes the disk check (or disk check is skipped), AND it passes the list check (or list is empty),
			# then this name will be kept.
			return test_name
		else:
			# if test_name is already used, then assemle a new name that includes a number
			test_name = "%s (%d)%s" % (basename, append_num, extension)
	# if it hits here, it tried 999 file names and none of them worked
	raise RuntimeError("ERROR: unable to find unused variation of '%s' for file-write" % initial_name)


def RUN_WITH_TRACEBACK(func: Callable, *args) -> None:
	"""
	Used to execute the "main" function of a script in direct-run mode.
	If it runs succesfully, do a pause-and-quit afterward.
	If an exception occurs, print the traceback info and do a pause-and-quit.
	If it was CTRL+C aborted, do not pause-and-quit.
	:param func: main-function
	:param args: optional args to pass to main-function
	"""
	try:
		MY_PRINT_FUNC("")
		func(*args)
		pause_and_quit("Done with everything! Goodbye!")
	except (KeyboardInterrupt, SystemExit):
		# this is normal and expected, do nothing and die
		pass
	except Exception as e:
		# print an error and full traceback if an exception was received!
		exc_type, exc_value, exc_traceback = sys.exc_info()
		printme_list = traceback.format_exception(e.__class__, e, exc_traceback)
		# now i have the complete traceback info as a list of strings, each ending with newline
		MY_PRINT_FUNC("")
		MY_PRINT_FUNC("".join(printme_list))
		pause_and_quit("ERROR: the script did not complete succesfully.")
		


########################################################################################################################
# searching thru sorted lists for MASSIVE speedup
########################################################################################################################

# bisect_left and bisect_right literally just copied from the "bisect" library so I don't need to import that file
def bisect_left(a: Sequence[Any], x: Any) -> int:
	"""
	Return the index where to insert item x in list a, assuming a is sorted.
	The return value i is such that all e in a[:i] have e < x, and all e in
	a[i:] have e >= x.  So if x already appears in the list, then i = the index
	where the leftmost x can be found.
	"""
	lo = 0
	hi = len(a)
	while lo < hi:
		mid = (lo+hi)//2
		if a[mid] < x: lo = mid+1
		else: hi = mid
	return lo
def bisect_right(a: Sequence[Any], x: Any) -> int:
	"""
	Return the index where to insert item x in list a, assuming a is sorted.
	The return value i is such that all e in a[:i] have e <= x, and all e in
	a[i:] have e > x.  So if x already appears in the list, then i = index + 1
	of the rightmost x already there.
	"""
	lo = 0
	hi = len(a)
	while lo < hi:
		mid = (lo+hi)//2
		if x < a[mid]: hi = mid
		else: lo = mid+1
	return lo
def binary_search_isin(x: Any, a: Sequence[Any]) -> bool:
	"""
	If x is in a, return True. Otherwise return False. a must be in ascending sorted order.
	"""
	pos = bisect_left(a, x)  # find insertion position
	return True if pos != len(a) and a[pos] == x else False  # don't walk off the end
def binary_search_wherein(x: Any, a: Sequence[Any]) -> int:
	"""
	If x is in a, return its index. Otherwise return -1. a must be in ascending sorted order.
	"""
	pos = bisect_left(a, x)  # find insertion position
	return pos if pos != len(a) and a[pos] == x else -1  # don't walk off the end


########################################################################################################################
# simple, fundamental math operations
########################################################################################################################

def linear_map(x1: float, y1: float, x2: float, y2: float, x_in_val: float) -> float:
	"""
	Define a Y=MX+B slope via coords x1,y1 and x2,y2. Then given an X value, calculate the resulting Y.
	
	:param x1: x1
	:param y1: y1
	:param x2: x2
	:param y2: y2
	:param x_in_val: any float, does not need to be constrained by x1/x2
	:return: resulting Y
	"""
	m = (y2 - y1) / (x2 - x1)
	b = y2 - (m * x2)
	return x_in_val * m + b

def clamp(value: float, lower: float, upper: float) -> float:
	"""
	Basic clamp function: if below the floor, return floor; if above the ceiling, return ceiling; else return unchanged.
	
	:param value: float input
	:param lower: float floor
	:param upper: float ceiling
	:return: float within range [lower-upper]
	"""
	return lower if value < lower else upper if value > upper else value

def bidirectional_clamp(val: float, a: float, b: float) -> float:
	"""
	Clamp when you don't know the relative order of a and b.
	
	:param val: float input
	:param a: ceiling or floor
	:param b: ceiling or floor
	:return: float within range [lower-upper]
	"""
	return clamp(val, a, b) if a < b else clamp(val, b, a)

def my_dot(v0: Sequence[float], v1: Sequence[float]) -> float:
	"""
	Perform mathematical dot product between two same-length vectors. IE component-wise multiply, then sum.

	:param v0: any number of floats
	:param v1: same number of floats
	:return: single float
	"""
	dot = 0.0
	for (a, b) in zip(v0, v1):
		dot += a * b
	return dot

def my_euclidian_distance(x: Sequence[float]) -> float:
	"""
	Calculate Euclidian distance (square each component, sum, and square root).

	:param x: list/tuple, any number of floats
	:return: single float
	"""
	return math.sqrt(my_dot(x, x))

def normalize_distance(foo: Sequence[float]) -> List[float]:
	"""
	Normalize by Euclidian distance. Supports any number of dimensions.
	
	:param foo: list/tuple, any number of floats
	:return: list of floats
	"""
	LLL = my_euclidian_distance(foo)
	return [t / LLL for t in foo]

def normalize_sum(foo: Sequence[float]) -> List[float]:
	"""
	Normalize by sum. Supports any number of dimensions.
	
	:param foo: list/tuple, any number of floats
	:return: list of floats
	"""
	LLL = sum(foo)
	return [t / LLL for t in foo]


########################################################################################################################
# MyBezier object for bezier curve interpolation
########################################################################################################################

def _bezier_math(t: float, p1: Tuple[float, float], p2: Tuple[float, float]) -> Tuple[float, float]:
	"""
	Internal use only.
	Use standard bezier equations, assuming p0=(0,0) and p3=(1,1) and p1/p2 are args, with a time value t, to calculate
	the resulting X and Y. If X/Y of p1/p2 are within range [0-1] then output X/Y are guaranteed to also be within
	[0-1].
	
	:param t: float time value
	:param p1: 2x float, coord of p1
	:param p2: 2x float, coord of p2
	:return: 2x float, resulting X Y coords
	"""
	x0, y0 = 0, 0
	x1, y1 = p1
	x2, y2 = p2
	x3, y3 = 1, 1
	x = (1 - t) ** 3 * x0 + 3 * (1 - t) ** 2 * t * x1 + 3 * (1 - t) * t ** 2 * x2 + t ** 3 * x3
	y = (1 - t) ** 3 * y0 + 3 * (1 - t) ** 2 * t * y1 + 3 * (1 - t) * t ** 2 * y2 + t ** 3 * y3
	return x, y

class MyBezier(object):
	def __init__(self, p1: Tuple[int,int], p2: Tuple[int,int], resolution=50) -> None:
		"""
		This implements a linear approximation of a constrained Bezier curve for motion interpolation. After defining
		the control points, Y values can be easily generated from X values using self.approximate(x).
		
		:param p1: 2x int range [0-128], XY coordinates of control point
		:param p2: 2x int range [0-128], XY coordinates of control point
		:param resolution: int, number of points in the linear approximation of the bezier curve
		"""
		# first convert tuple(int [0-128]) to tuple(float [0.0-1.0])
		point1 = (clamp(p1[0] / 128, 0.0, 1.0), clamp(p1[1] / 128, 0.0, 1.0))
		point2 = (clamp(p2[0] / 128, 0.0, 1.0), clamp(p2[1] / 128, 0.0, 1.0))
		retlist = [(0.0, 0.0)]  # curve always starts at 0,0
		# use bezier math to create a list of XY points along the actual bezier curve, evenly spaced in t=time
		# both x-coords and y-coords are strictly increasing, but not evenly spaced
		for i in range(1, resolution):
			retlist.append(_bezier_math(i / resolution, point1, point2))
		retlist.append((1.0, 1.0))  # curve always ends at 1,1
		self.resolution = resolution  # store resolution param
		xx, yy = zip(*retlist)  # unzip
		self.xx = list(xx)
		self.yy = list(yy)

	def approximate(self, x: float) -> float:
		"""
		In a constrained bezier curve, X and Y have a perfect one-to-one correspondance, but the math makes it
		incredibly difficult to exactly calculate a Y given an X. So, approximate it via a series of precalculated line
		segments.

		:param x: float input x [0.0-1.0]
		:return: float output y [0.0-1.0]
		"""
		x = clamp(x, 0.0, 1.0)
		# first take care of the corner cases, i.e. the cases I already know the answers to:
		if x == 1.0:	return 1.0
		elif x == 0.0:	return 0.0
		else:
			# use binary search to find pos, the idx of the entry in self.xx which is <= x
			# if xx[3] < x < xx[4], then pos=4. so the segment starts at pos-1 and ends at pos.
			pos = bisect_left(self.xx, x)
		# use pos-1 and pos to get two xy points, to build a line segment, to perform linear approximation
		return linear_map(self.xx[pos-1], self.yy[pos-1],
						  self.xx[pos],   self.yy[pos],
						  x)

########################################################################################################################
# advanced geometric math functions
########################################################################################################################

def my_projection(x: Sequence[float], y: Sequence[float]) -> Tuple[float,float,float]:
	"""
	Project 3D vector X onto vector Y, i.e. the component of X that is parallel with Y.
	
	:param x: 3x float X Y Z
	:param y: 3x float X Y Z
	:return: 3x float X Y Z
	"""
	# project x onto y:          y * (my_dot(x, y) / my_dot(y, y))
	scal = my_dot(x, y) / my_dot(y, y)
	# out = tuple(y_ * scal for y_ in y)
	return y[0]*scal, y[1]*scal, y[2]*scal

def my_cross_product(a: Sequence[float], b: Sequence[float]) -> Tuple[float,float,float]:
	"""
	Perform mathematical cross product between two 3D vectors.
	
	:param a: 3x float
	:param b: 3x float
	:return: 3x float
	"""
	return a[1]*b[2] - a[2]*b[1],\
		   a[2]*b[0] - a[0]*b[2],\
		   a[0]*b[1] - a[1]*b[0]

def my_quat_conjugate(q: Sequence[float]) -> Tuple[float,float,float,float]:
	"""
	"invert" or "reverse" or "conjugate" a quaternion by negating the x/y/z components.
	
	:param q: 4x float, W X Y Z quaternion
	:return: 4x float, W X Y Z quaternion
	"""
	return q[0], -q[1], -q[2], -q[3]

def my_slerp(v0: Sequence[float], v1: Sequence[float], t: float) -> Tuple[float,float,float,float]:
	"""
	Spherically Linear intERPolates between quat1 and quat2 by t.
	The param t will normally be clamped to the range [0, 1]. However, negative values or greater than 1 will still
	work.
	If t==0, return v0. If t==1, return v1.

	:param v0: 4x float, W X Y Z quaternion
	:param v1: 4x float, W X Y Z quaternion
	:param t: float [0,1] how far to interpolate
	:return: 4x float, W X Y Z quaternion
	"""
	# https://stackoverflow.com/questions/44706591/how-to-test-quaternion-slerp
	# fuck this guy his code is mostly wrong, except for the quaternion flipping bit thats clever
	# https://www.mathworks.com/help/fusion/ref/quaternion.slerp.html#mw_0419144b-0e16-4d56-b5d7-19783b790e4b
	# this algorithm works tho
	
	if math.isclose(t, 0.0, abs_tol=1e-6):
		return v0
	if math.isclose(t, 1.0, abs_tol=1e-6):
		return v1
	
	# If the dot product is negative, the quaternions
	# have opposite handed-ness and slerp won't take
	# the shorter path. Fix by reversing one quaternion.
	dot = my_dot(v0, v1)
	if dot < 0.0:
		v1 = [-v for v in v1]
		dot = -dot
	
	# q0not = my_quat_conjugate(q0)
	# a = hamilton_product(q1, q0not)
	# a = normalize_distance(a)
	# b = quat_pow(a, t)
	# c = hamilton_product(b, q0)
	# return c
	
	# clamp just to be safe
	dot = clamp(dot, -1.0, 1.0)
	
	theta = math.acos(dot)
	if theta == 0:
		# if there is no angle between the two quaternions, then interpolation is pointless
		return v0[0], v0[1], v0[2], v0[3]
	
	# q1 * sin((1-t) * theta) / sin(theta) + q2 * sin(t * theta) / sin(theta)
	factor0 = math.sin((1 - t) * theta) / math.sin(theta)
	factor1 = math.sin(t * theta) / math.sin(theta)
	res = tuple((v0[i] * factor0) + (v1[i] * factor1) for i in range(4))
	return res[0], res[1], res[2], res[3]
	
# https://en.wikipedia.org/wiki/Quaternion#Exponential,_logarithm,_and_power_functions
# https://math.stackexchange.com/questions/939229/unit-quaternion-to-a-scalar-power
# wikipedia is always good, this stackexchange thing is a bit hard to parse

def quat_ln(_q: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
	vm = my_euclidian_distance(_q[1:4])
	qm = my_euclidian_distance(_q)
	tt = (math.acos(_q[0] / qm) / vm) if (vm > 1e-9) else 0.0
	w = math.log(qm)
	return w, _q[1] * tt, _q[2] * tt, _q[3] * tt

def quat_exp(_q: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
	r = my_euclidian_distance(_q[1:4])
	et = math.exp(_q[0])
	s = (et * math.sin(r) / r) if (r > 1e-9) else 0.0
	w = et * math.cos(r)
	return w, _q[1] * s, _q[2] * s, _q[3] * s

def quat_pow(_q: Tuple[float, float, float, float], _n: float) -> Tuple[float, float, float, float]:
	aa = quat_ln(_q)  # pycharm type checker can go to hell
	bb = tuple(_n * i for i in aa)
	cc = quat_exp(bb)  # pycharm type checker can go to hell
	return cc


'''
# code block to validate the SLERP code via 3d plotting
	original_point = [1, 0, 0]
	t_list = [i/20 for i in range(20)]
	while True:
		R = [random.randint(-170, 170) for _ in range(6)]
		euler1 = R[0:3]
		euler2 = R[3:6]
		print(euler1, euler2)
		quat1 = core.euler_to_quaternion(euler1)
		quat2 = core.euler_to_quaternion(euler2)
		point_list = []
		point_list_new = []
		for t in t_list:
			rot = core.my_slerp(quat1, quat2, t) # old slerp
			newpoint = core.rotate3d((0,0,0), rot, original_point)
			point_list.append(newpoint)
			rot = core.new_slerp(quat1, quat2, t) # new slerp
			newpoint = core.rotate3d((0, 0, 0), rot, original_point)
			point_list_new.append(newpoint)
		# now graph them
		fig = plt.figure()
		ax = fig.add_subplot(111, projection='3d')
		x,y,z = zip(*point_list)
		ax.scatter(x,y,z, label="old")
		x,y,z = zip(*point_list_new)
		ax.scatter(x,y,z, label="new")
		ax.scatter(0,0,0, label="origin")  # plot the origin too
		ax.set_xlim(-1, 1)
		ax.set_ylim(-1, 1)
		ax.set_zlim(-1, 1)
		STARTPOINT = core.rotate3d((0,0,0), quat1, original_point)
		ENDPOINT = core.rotate3d((0,0,0), quat2, original_point)
		ax.scatter(*STARTPOINT, marker='x', label='START')
		ax.scatter(*ENDPOINT, marker='x', label='END')
		ax.legend()
		plt.show(block=True)
'''

def hamilton_product(quat1: Sequence[float], quat2: Sequence[float]) -> Tuple[float,float,float,float]:
	"""
	Perform the mathematical "hamilton product", effectively adds two quaternions. However the order of the inputs does matter.
	Returns the equivalent of rotation quat2 followed by rotation quat1.
	Result is another quaternion.
	
	:param quat1: 4x float, W X Y Z quaternion
	:param quat2: 4x float, W X Y Z quaternion
	:return: 4x float, W X Y Z quaternion
	"""
	# thank you stackexchange and thank you wikipedia
	(a1, b1, c1, d1) = quat1
	(a2, b2, c2, d2) = quat2
	
	a3 = (a1 * a2) - (b1 * b2) - (c1 * c2) - (d1 * d2)
	b3 = (a1 * b2) + (b1 * a2) + (c1 * d2) - (d1 * c2)
	c3 = (a1 * c2) - (b1 * d2) + (c1 * a2) + (d1 * b2)
	d3 = (a1 * d2) + (b1 * c2) - (c1 * b2) + (d1 * a2)
	
	return a3, b3, c3, d3

# def pure_euler_to_quaternion(euler):
# 	# THIS IS THE PURE MATH-ONLY TRANSFORM WITHOUT ANY OF THE MMD SPECIAL CASE COMPENSATION
# 	# angles are in radians
# 	# this logic copied from wikipedia: https://en.wikipedia.org/wiki/Conversion_between_quaternions_and_Euler_angles
# 	(roll, pitch, yaw) = euler
#
# 	# r=x, p=y, y=z
#
# 	# roll (X), pitch (Y), yaw (Z)
# 	sr = math.sin(roll * 0.5)
# 	sp = math.sin(pitch * 0.5)
# 	sy = math.sin(yaw * 0.5)
# 	cr = math.cos(roll * 0.5)
# 	cp = math.cos(pitch * 0.5)
# 	cy = math.cos(yaw * 0.5)
#
# 	w = (cy * cp * cr) + (sy * sp * sr)
# 	x = (cy * cp * sr) - (sy * sp * cr)
# 	y = (sy * cp * sr) + (cy * sp * cr)
# 	z = (sy * cp * cr) - (cy * sp * sr)
#
# 	return [w, x, y, z]
#
# def pure_quaternion_to_euler(quaternion):
# 	# THIS IS THE PURE MATH-ONLY TRANSFORM WITHOUT ANY OF THE MMD SPECIAL CASE COMPENSATION
# 	# angles are in radians
# 	# this logic copied from wikipedia: https://en.wikipedia.org/wiki/Conversion_between_quaternions_and_Euler_angles
# 	(w, x, y, z) = quaternion
#
# 	# roll (x-axis2 rotation)
# 	sinr_cosp = 2 * ((w * x) + (y * z))
# 	cosr_cosp = 1 - (2 * ((x ** 2) + (y ** 2)))
# 	roll = math.atan2(sinr_cosp, cosr_cosp)
#
# 	# pitch (y-axis2 rotation)
# 	sinp = 2 * ((w * y) - (z * x))
# 	if sinp >= 1.0:
# 		pitch = math.pi / 2  # use 90 degrees if out of range
# 	elif sinp <= -1.0:
# 		pitch = -math.pi / 2
# 	else:
# 		pitch = math.asin(sinp)
#
# 	# yaw (z-axis2 rotation)
# 	siny_cosp = 2 * ((w * z) + (x * y))
# 	cosy_cosp = 1 - (2 * ((y ** 2) + (z ** 2)))
# 	yaw = math.atan2(siny_cosp, cosy_cosp)
#
# 	return [roll, pitch, yaw]

def euler_to_quaternion(euler: Sequence[float]) -> Tuple[float,float,float,float]:
	"""
	Convert XYZ euler angles to WXYZ quaternion, using the same method as MikuMikuDance.
	Massive thanks and credit to "Isometric" for helping me discover the transformation method used in mmd!!!!

	:param euler: 3x float, X Y Z angle in degrees
	:return: 4x float, W X Y Z quaternion
	"""
	# massive thanks and credit to "Isometric" for helping me discover the transformation method used in mmd!!!!
	# angles are in degrees, must convert to radians
	roll, pitch, yaw = euler
	roll = math.radians(roll)
	pitch = math.radians(pitch)
	yaw = math.radians(yaw)
	
	# roll (X), pitch (Y), yaw (Z)
	sx = math.sin(roll * 0.5)
	sy = math.sin(pitch * 0.5)
	sz = math.sin(yaw * 0.5)
	cx = math.cos(roll * 0.5)
	cy = math.cos(pitch * 0.5)
	cz = math.cos(yaw * 0.5)
	
	w = (cz * cy * cx) + (sz * sy * sx)
	x = (cz * cy * sx) + (sz * sy * cx)
	y = (sz * cy * sx) - (cz * sy * cx)
	z = (cz * sy * sx) - (sz * cy * cx)
	
	return w, x, y, z

def quaternion_to_euler(quat: Sequence[float]) -> Tuple[float,float,float]:
	"""
	Convert WXYZ quaternion to XYZ euler angles, using the same method as MikuMikuDance.
	Massive thanks and credit to "Isometric" for helping me discover the transformation method used in mmd!!!!
	
	:param quat: 4x float, W X Y Z quaternion
	:return: 3x float, X Y Z angle in degrees
	"""
	w, x, y, z = quat
	
	# pitch (y-axis rotation)
	sinr_cosp = 2 * ((w * y) + (x * z))
	cosr_cosp = 1 - (2 * ((x ** 2) + (y ** 2)))
	pitch = -math.atan2(sinr_cosp, cosr_cosp)
	
	# yaw (z-axis rotation)
	siny_cosp = 2 * ((-w * z) - (x * y))
	cosy_cosp = 1 - (2 * ((x ** 2) + (z ** 2)))
	yaw = math.atan2(siny_cosp, cosy_cosp)
	
	# roll (x-axis rotation)
	sinp = 2 * ((z * y) - (w * x))
	if sinp >= 1.0:
		roll = -math.pi / 2  # use 90 degrees if out of range
	elif sinp <= -1.0:
		roll = math.pi / 2
	else:
		roll = -math.asin(sinp)
	
	# fixing the x rotation, part 1
	if x ** 2 > 0.5 or w < 0:
		if x < 0:
			roll = -math.pi - roll
		else:
			roll = math.pi * math.copysign(1, w) - roll
	
	# fixing the x rotation, part 2
	if roll > (math.pi / 2):
		roll = math.pi - roll
	elif roll < -(math.pi / 2):
		roll = -math.pi - roll
	
	roll = math.degrees(roll)
	pitch = math.degrees(pitch)
	yaw = math.degrees(yaw)
	
	return roll, pitch, yaw


def rotate3d(rotate_around: Sequence[float],
			 angle_quat: Sequence[float],
			 initial_position: Sequence[float]) -> List[float]:
	"""
	Rotate a point within 3d space around another specified point by a specific quaternion angle.
	:param rotate_around: X Y Z usually a bone location
	:param angle_quat: W X Y Z quaternion rotation to apply
	:param initial_position: X Y Z starting location of the point to be rotated
	:return: X Y Z position after rotating
	"""
	# "rotate around a point in 3d space"
	
	# subtract "origin" to move the whole system to rotating around 0,0,0
	point = [p - o for p, o in zip(initial_position, rotate_around)]
	
	# might need to scale the point down to unit-length???
	# i'll do it just to be safe, it couldn't hurt
	length = my_euclidian_distance(point)
	if length != 0:
		point = [p / length for p in point]
		
		# set up the math as instructed by math.stackexchange
		p_vect = [0.0] + point
		r_prime_vect = my_quat_conjugate(angle_quat)
		# r_prime_vect = [angle_quat[0], -angle_quat[1], -angle_quat[2], -angle_quat[3]]
		
		# P' = R * P * R'
		# P' = H( H(R,P), R')
		temp = hamilton_product(angle_quat, p_vect)
		p_prime_vect = hamilton_product(temp, r_prime_vect)
		# note that the first element of P' will always be 0
		point = p_prime_vect[1:4]
		
		# might need to undo scaling the point down to unit-length???
		point = [p * length for p in point]
	
	# re-add "origin" to move the system to where it should have been
	point = [p + o for p, o in zip(point, rotate_around)]
	
	return point


def rotate2d(origin: Sequence[float], angle: float, point: Sequence[float]) -> Tuple[float,float]:
	"""
	Rotate a 2d point counterclockwise by a given angle around a given 2d origin.
	The angle should be given in radians.
	
	:param origin: 2x float X Y, rotate-around point
	:param angle: float, radians to rotate
	:param point: 2x float X Y, point-that-will-be-rotated
	:return: 2x float X Y, point after rotation
	"""
	ox, oy = origin
	px, py = point
	qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
	qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)
	return qx, qy





if __name__ == '__main__':
	print(_SCRIPT_VERSION)
	pause_and_quit("you are not supposed to directly run this file haha")


