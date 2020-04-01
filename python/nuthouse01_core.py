# Nuthouse01 - 03/30/2020 - v3.51
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# this contains a bunch of functions that are used throughout multiple different scripts
# it's better to keep them all in one place than copy them for each file

import csv
import math
import struct
from os import path, listdir, getenv, makedirs
from sys import platform, version_info, version



# first, version check: verify that this is using python3
# i don't know if it will actually work in 3.4 but i know it will fail in any python2 version
# actually written/tested with 3.6.6 so guaranteed to work on that or higher
# between 3.4 and 3.6, who knows
if version_info < (3, 4):
	print("Your version of Python is too old to run this script, please update!")
	print("Your current version = " + version)
	print("...press ENTER to exit...")
	input()
	exit()


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

bone_interpolation_default_linear = [20, 20, 20, 20, 20, 20, 20, 20, 107, 107, 107, 107, 107, 107, 107, 107]


########################################################################################################################
# misc functions and user-input functions
########################################################################################################################

def basic_print(*args, is_progress=False):
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

# global variable holding a function pointer that i can overwrite with a different function pointer
MY_PRINT_FUNC = basic_print

def pause_and_quit(message):
	# wait for user input before exiting because i want the window to stay open long enough for them to read output
	MY_PRINT_FUNC(message)
	MY_PRINT_FUNC("...press ENTER to exit...")
	input()
	exit()

def print_progress_oneline(curr, outof):
	# print progress updates on one line, continually overwriting itself
	# cursor gets left at the beginning of line, so the next print will overwrite this one
	p = "...working: {:06.2%}".format(curr / outof)
	MY_PRINT_FUNC(p, is_progress=True)


# useful as keys for sorting
def get1st(x):
	return x[0]
def get2nd(x):
	return x[1]

def my_sublist_find(searchme, sublist_idx, matchme):
	# in a list of lists, find the list with the specified item at the specified index
	for row in searchme:
		if row[sublist_idx] == matchme:
			return row
	return None

MAXDIFFERENCE = 0
# recursively check for equality, using a loose comparison for floatingpoints
# operating on test file, the greatest difference introduced by quaternion transform is 0.000257
# lets set sanity-check threshold at double that, 0.0005
# return the number of times a float difference exceeded the threshold
# if there is a non-float difference, return infinity
def recursively_compare(A,B):
	global MAXDIFFERENCE
	# return 1/true if it FAILS, return 0/false if it MATCHES
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

# recursively flatten a list of lists
# empty lists get turned into "none" instead of completely vanishing
def flatten(x):
	retme = []
	for thing in x:
		if isinstance(thing, list) or isinstance(thing, tuple):
			if len(thing) == 0:
				retme.append(None)
			else:
				retme += flatten(thing)
		else:
			retme.append(thing)
	return retme

def increment_occurance_dict(d: dict, k):
	# this does a pass-by-reference thing so i dont need to bother with returning, it just updates the value in-place
	try:
		d[k] += 1
	except KeyError:
		d[k] = 1
	return None

def prompt_user_choice(options):
	# assumes that options is a list of ints
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

def prompt_user_filename(extension: str) -> str:
	# loop until user enters the name of an existing file with the specified extension
	MY_PRINT_FUNC('(type/paste the path to the file, ".." means "go up a folder")')
	MY_PRINT_FUNC('(path can be absolute, like C:/username/Documents/miku.pmx)')
	MY_PRINT_FUNC('(or path can be relative to here, example: ../../mmd/models/miku.pmx)')
	while True:
		# continue prompting until the user gives valid input
		name = input(" Filename (ending with " + extension + ") = ")
		if len(name) <= 4:
			MY_PRINT_FUNC("Err: file name too short to be valid")
		elif name.lower()[-4:] != extension.lower():
			MY_PRINT_FUNC("Err: given file must have '"+extension+"' extension")
		elif not path.isfile(name):
			MY_PRINT_FUNC(path.abspath(name))
			MY_PRINT_FUNC("Err: given file does not exist, did you type it wrong?")
		else:
			break
	# windows is case insensitive, so this doesn't matter, but to make it match the same case as the existing file:
	# inputname > absolute path > dir name > list files in dir > compare-case-insensitive with inputname > get actual existing name
	manyfiles = listdir(path.dirname(path.abspath(name)))
	for casename in manyfiles:
		if casename.lower() == path.basename(name).lower():
			return path.join(path.dirname(name), casename)
	# just in case something goes sideways
	return name

def get_clean_basename(initial_name: str) -> str:
	return path.splitext(path.basename(initial_name))[0]

def get_unused_file_name(initial_name: str) -> str:
	# return a name that is unused, might be the same one passed in.
	# given an initial name, see if it is valid to use. if not, keep appending numbers until you find a name that is unused.
	sep = initial_name.rfind(".")
	basename = initial_name[:sep]
	extension = initial_name[sep:]
	test_name = basename + extension
	for append_num in range(2, 1000):
		if not path.isfile(test_name):
			return test_name
		else:
			test_name = basename + str(append_num) + extension
	# if it hits here, it tried 1,000 file names and none of them worked
	pause_and_quit("Err: unable to find unused variation of '" + initial_name + "' for file-write")
	return ""

def get_persistient_storage_path(filename="") -> str:
	# for writing to the "appdata" directory to preserve info between multiple runs of the script, from any location
	appname = "nuthouse01_mmd_tools"
	# build the appropriate path
	if platform == 'win32':
		appdata = path.join(getenv('APPDATA'), appname)
	else:
		appdata = path.expanduser(path.join("~", "." + appname))
	# if the folder(s) don't exist, then make them
	if not path.exists(appdata):
		makedirs(appdata)
	# if a filename was given, return it added onto the path
	if filename:
		retme = path.join(appdata, filename)
		# if it doesn't exist, create it empty
		if not path.exists(retme):
			write_rawlist_to_txt(retme, [], quiet=True)
		return retme
	return appdata


########################################################################################################################
# these functions do CSV read/write and binary-file read/write
########################################################################################################################

def write_rawlist_to_txt(name, content, use_jis_encoding=False, quiet=False):
	if not quiet:
		MY_PRINT_FUNC(path.abspath(name))
	# note: when PMXE writes a CSV, it backslash-escapes backslashes and dots and spaces, but it doesn't need these to be escaped when reading
	# opposite of read_txt_to_rawlist()
	
	# new: replaced csv.writer with my own convert-to-csv block to get the escaping behavior i needed
	# assuming input is either list of strings, or list of lists of things
	buildme = []
	for line in content:
		newline = []
		if isinstance(line, str):  # if it is already a string, don't do anything fancy, just use it
			newline_str = line
		else:  # if it is not a string, it should be a list or tuple, so iterate over it
			for item in line:
				# check if it needs special treatment, apply if needed
				if isinstance(item, str):
					# make a copy so I am not modifying the input list
					newstr = item
					# first, escape all doublequotes with more doublequotes
					newstr.replace('"', '""')
					# then check if the whole thing needs wrapped:
					# contains any doublequotes, contains any commas, or starts or ends with whitespace
					if ('"' in newstr) or (',' in newstr) or (len(newstr) > 0 and (newstr[0].isspace() or newstr[-1].isspace())):
						newstr = '"%s"' % newstr
					newline.append(newstr)
				else:
					# convert to string & append onto newline
					newline.append(str(item))
			# join the items on this line with commas & store elsewhere
			newline_str = ",".join(newline)
		buildme.append(newline_str)
	# add this so it has one empty line at the end just cuz
	buildme.append("")
	# join all the lines with newlines (duh)
	writeme = "\n".join(buildme)
	
	try:
		# finally, actually write the whole file all at once, using the proper encoding
		if use_jis_encoding:
			with open(name, "w", encoding="shift_jis") as my_file:
				my_file.write(writeme)
		else:
			with open(name, "w", encoding="utf-8") as my_file:
				my_file.write(writeme)
	except IOError as e:
		MY_PRINT_FUNC(e)
		pause_and_quit("Err: unable to write TXT file '" + name + "', maybe its a permissions issue?")


def read_txt_to_rawlist(input_filename, use_jis_encoding=False, quiet=False):
	if not quiet:
		MY_PRINT_FUNC(path.abspath(input_filename))
	# opposite of write_rawlist_to_txt()
	# take a file name as its argument
	# dump it from disk to a variable in memory, and also format it as a nice type-correct list
	try:
		if use_jis_encoding:
			with open(input_filename, "r", encoding="shift_jis") as my_file:
				rb_unicode = my_file.read()
		else:
			with open(input_filename, "r", encoding="utf-8") as my_file:
				rb_unicode = my_file.read()
	except IOError as e:
		MY_PRINT_FUNC(e)
		pause_and_quit("Err: error wile reading '" + input_filename + "', maybe you typed it wrong?")
	# break rb_unicode into a list object
	rb_list = rb_unicode.splitlines()
	# set up the csv reader object
	reader = csv.reader(rb_list, delimiter=',', quoting=csv.QUOTE_ALL)
	# actually iterate over and use the csv reader object, dump from file to list
	csv_content = []
	try:
		for row in reader:
			csv_content.append(row)
	except csv.Error as e:
		MY_PRINT_FUNC("file {}, line {}: {}".format(input_filename, reader.line_num, e))
		pause_and_quit("Err: malformed CSV format in the text file prevented parsing from text to list form, check your commas")
	# ideally the csv reader should detect what type each thing is but the encoding is making it all fucky
	# so, just read everything in as a string i guess, then build a new list 'data' where all the types are correct
	data = []
	for row in csv_content:
		newrow = []
		for item in row:
			# manual type conversion: everything in the document is either int,float,bool,string
			# is it an integer?
			try:
				newrow.append(int(item))
				continue
			except ValueError:
				pass
			# is it a float?
			try:
				newrow.append(float(item))
				continue
			except ValueError:
				pass
			# is it a bool?
			if item.lower() == "true":
				newrow.append(True)
				continue
			if item.lower() == "false":
				newrow.append(False)
				continue
			# is it a none?
			if item == "None":
				newrow.append(None)
				continue
			# i guess its just a string, then. keep it unchanged
			newrow.append(item)
		data.append(newrow)
	return data


def write_bytes_to_binfile(name, content, quiet=False):
	if not quiet:
		MY_PRINT_FUNC(path.abspath(name))
	# opposite of read_binfile_to_bytes()
	# write a binary file from a bytes object
	try:
		with open(name, "wb") as my_file:
			my_file.write(content)
	except IOError as e:
		MY_PRINT_FUNC(e)
		pause_and_quit("Err: unable to write binary file '" + name + "', maybe its a permissions issue?")


def read_binfile_to_bytes(input_filename, quiet=False):
	if not quiet:
		MY_PRINT_FUNC(path.abspath(input_filename))
	# opposite of write_bytes_to_binfile()
	# take a file name as its argument
	# return a "bytearray" object
	try:
		# r=read, b=binary
		with open(input_filename, mode='rb') as file:
			# dump from file into variable in memory
			raw = file.read()
	except IOError as e:
		MY_PRINT_FUNC(e)
		pause_and_quit("Err: error wile reading '" + input_filename + "', maybe you typed it wrong?")
	return bytearray(raw)


########################################################################################################################
# these functions are for various math operations
########################################################################################################################

def linear_map(x1, y1, x2, y2, x_in_val):
	m = (y2 - y1) / (x2 - x1)
	b = y2 - (m * x2)
	return x_in_val * m + b


BEZIER_RESOLUTION = 50

def my_bezier(t, point1, point2):
	# this function does bezier curve calculation as a function of "t"
	# ideally i want a function of X but this will have to be good enough
	# point0 is always (0,0), point3 is always (1,1)
	x0, y0 = 0, 0
	x1, y1 = point1
	x2, y2 = point2
	x3, y3 = 1, 1
	x = (1 - t) ** 3 * x0 + 3 * (1 - t) ** 2 * t * x1 + 3 * (1 - t) * t ** 2 * x2 + t ** 3 * x3
	y = (1 - t) ** 3 * y0 + 3 * (1 - t) ** 2 * t * y1 + 3 * (1 - t) * t ** 2 * y2 + t ** 3 * y3
	return x, y

def my_bezier_characterize(point1, point2):
	# return a list of points along the bezier curve, evenly spaced in "t"
	# this will be used for linear mapping approximations
	point1 = [p / 128 for p in point1]
	point2 = [p / 128 for p in point2]
	retlist = [(0, 0)]
	for i in range(1, BEZIER_RESOLUTION):
		retlist.append(my_bezier(i / BEZIER_RESOLUTION, point1, point2))
	retlist.append((1, 1))
	return retlist

def my_bezier_approximation(x, characterization):
	# use a previously-created bezier characterization with an input X value to create an output Y value
	for i in range(BEZIER_RESOLUTION):
		if characterization[i][0] <= x < characterization[i+1][0]:
			return linear_map(characterization[i][0],   characterization[i][1],
							  characterization[i+1][0], characterization[i+1][1],
							  x)
	MY_PRINT_FUNC("ERR: not supposed to hit here!")
	MY_PRINT_FUNC(x)
	MY_PRINT_FUNC(characterization)
	pause_and_quit("")

def my_dot(v0, v1):
	dot = 0.0
	for (a,b) in zip(v0, v1):
		dot += a*b
	return dot

def my_projection(x, y):
	# project x onto y:          y * (my_dot(x, y) / my_dot(y, y))
	scal = my_dot(x, y) / my_dot(y, y)
	out = [y_ * scal for y_ in y]
	return out

def my_quat_conjugate(q):
	return [q[0], -q[1], -q[2], -q[3]]


def my_slerp(v0, v1, t):
	"""
	Spherically Linear intERPolates between quat1 and quat2 by t.
	The parameter t should be clamped to the range [0, 1]
	"""
	# https://stackoverflow.com/questions/44706591/how-to-test-quaternion-slerp
	# fuck this guy his code is mostly wrong, except for the quaternion flipping bit thats clever
	# https://www.mathworks.com/help/fusion/ref/quaternion.slerp.html#mw_0419144b-0e16-4d56-b5d7-19783b790e4b
	# this algorithm works tho
	
	# calculate dot product manually
	# dot = np.dot(v0, v1)
	dot = my_dot(v0, v1)
	
	# If the dot product is negative, the quaternions
	# have opposite handed-ness and slerp won't take
	# the shorter path. Fix by reversing one quaternion.
	if dot < 0.0:
		for a in range(len(v1)):
			v1[a] = -v1[a]
		dot = -dot
	
	# clamp just to be safe
	if dot < -1.0:
		dot = -1.0
	elif dot > 1.0:
		dot = 1.0
	
	theta = math.acos(dot)
	if theta == 0:
		# if there is no angle between the two quaternions, then interpolation is pointless
		return v0
	
	# q1 * sin((1-t) * theta) / sin(theta) + q2 * sin(t * theta) / sin(theta)
	factor0 = math.sin((1 - t) * theta) / math.sin(theta)
	factor1 = math.sin(t * theta) / math.sin(theta)
	res = [(v0[i] * factor0) + (v1[i] * factor1) for i in range(4)]
	return res


def hamilton_product(quat1, quat2):
	# this product returns the equivalent of rotation quat2 followed by rotation quat1
	# thank you stackexchange and thank you wikipedia
	(a1, b1, c1, d1) = quat1
	(a2, b2, c2, d2) = quat2
	
	a3 = (a1 * a2) - (b1 * b2) - (c1 * c2) - (d1 * d2)
	b3 = (a1 * b2) + (b1 * a2) + (c1 * d2) - (d1 * c2)
	c3 = (a1 * c2) - (b1 * d2) + (c1 * a2) + (d1 * b2)
	d3 = (a1 * d2) + (b1 * c2) - (c1 * b2) + (d1 * a2)
	
	quat3 = [a3, b3, c3, d3]
	return quat3


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


def euler_to_quaternion(euler):
	# massive thanks and credit to "Isometric" for helping me discover the transformation method used in mmd!!!!
	# angles are in degrees, must convert to radians
	(roll, pitch, yaw) = euler
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
	
	return [w, x, y, z]


def quaternion_to_euler(quaternion):
	# massive thanks and credit to "Isometric" for helping me discover the transformation method used in mmd!!!!
	# angles are returned in degrees
	(w, x, y, z) = quaternion
	
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
	
	return [roll, pitch, yaw]


def rotate2d(origin, angle, point):
	"""
	Rotate a 2d point counterclockwise by a given angle around a given 2d origin.
	The angle should be given in radians.
	"""
	ox, oy = origin
	px, py = point
	# angle2 = math.radians(angle)
	angle2 = angle
	qx = ox + math.cos(angle2) * (px - ox) - math.sin(angle2) * (py - oy)
	qy = oy + math.sin(angle2) * (px - ox) + math.cos(angle2) * (py - oy)
	return qx, qy


########################################################################################################################
# these functions for binary file structure packing & unpacking
########################################################################################################################
# encoding notes:
# one known error case is that the "fullwidth tilde" = ～ = u"\uFF5E" cannot be represented in shift_jis
# 	this symbol can be in PMX files but will not be in VMD files
# 	MMD automatically replaces this with "wave dash" = 〜 = u"\u301c" when creating VMDs (which are saved in shift_jis)
# 	therefore I must do the same replacement in order to encode this as shift_jis
# also, shift_jis confuses the backslash \ and yen ¥
# 	in shift_jis, both get mapped to the same bytevalue and become indistinguishable
# 	in MMD, in the 4-group thing at the bottom with the dropdown lists, they both display as \
#	when I encode as shift_jis and write to file, they are printed as \
# 	in MMD, in the timeline on the left, they both display as ¥
#	(does it display in MMD as shift_jis_2004 or shift_jisx0208 but write to file as shift_jis? not really worth exploring)
# also, shift_jis confuses the overline ‾ and tilde ~ (the regular tilde, not the fullwidth tilde)
#	this is exactly the same as the backslash and yen, they are internally mapped to the same values so they are indistinguishable
#	when i encode as shift_jis and write to file, they are both printed as ~

# these functions add extra utility to the standard python packing/unpacking library
# they define a new atom "t" that represents an actual string type, if preceeded by numbers that indicates how many
#   bytes of space it uses, if NOT preceeded by numbers then it is represented in binary form as an int which indicates
#   how big the string is, followed by the actual string
# vmd format uses the "##t" syntax, pmx format uses the "t" syntax

# variable to keep track of where to start reading from next within the raw-file
UNPACKER_READFROM_BYTE = 0
# this should be hardcoded and never changed, something weird that nobody would ever use in a name
UNPACKER_ESCAPE_CHAR = "‡"
# encoding to use when packing/unpackign strings
UNPACKER_ENCODING = "utf8"
# dict to store all strings that failed to translate, plus counts
UNPACKER_FAILED_TRANSLATE_DICT = {}
# flag to indicate whether the last decoding needed escaping or not, cuz returning as a tuple is ugly
UNPACKER_FAILED_TRANSLATE_FLAG = False

# why do things with accessor functions? ¯\_(ツ)_/¯ cuz i want to
def reset_unpack():
	global UNPACKER_READFROM_BYTE
	global UNPACKER_FAILED_TRANSLATE_DICT
	UNPACKER_READFROM_BYTE = 0
	UNPACKER_FAILED_TRANSLATE_DICT = {}
def set_encoding(newencoding: str):
	global UNPACKER_ENCODING
	UNPACKER_ENCODING = newencoding
def get_readfrom_byte():
	return UNPACKER_READFROM_BYTE
def print_failed_decodes():
	if len(UNPACKER_FAILED_TRANSLATE_DICT) != 0:
		MY_PRINT_FUNC("List of all strings that failed to decode, plus their occurance rate")
		MY_PRINT_FUNC(UNPACKER_FAILED_TRANSLATE_DICT)
		
def decode_bytes_with_escape(r: bytearray) -> str:
	global UNPACKER_FAILED_TRANSLATE_FLAG
	# reverisible opposite of encode_string_with_escape()
	# now i have r, a bytearray which represents a string
	# want to convert it to actual string type (note decoding scheme varies depending on application)
	# if decoding from VMD, it's possible that it might be cut off mid multibyte char, and therefore undecodeable
	# undecodeable trailing bytes are escaped with a double-dagger and then represented with hex digits
	# all cases I tested require at most 1 escape char, but just to be safe recursively call until it succeeds
	try:
		s = r.decode(UNPACKER_ENCODING)				# try to decode the whole string
		return s
	except UnicodeDecodeError:
		UNPACKER_FAILED_TRANSLATE_FLAG = True
		s = decode_bytes_with_escape(r[:-1])		# if it cant, decode everything but the last char
		extra = r[-1]  								# this is the last byte that couldn't be decoded
		s = "%s%s%x" % (s, UNPACKER_ESCAPE_CHAR, extra)
		return s

def encode_string_with_escape(a: str) -> bytearray:
	# reverisible opposite of decode_bytes_with_escape()
	# now i have "a", a string to be converted to a bytearray, possibly containing escape char(s)
	# all cases I tested require at most 1 escape char, but just to be safe recursively call until it succeeds
	try:
		if len(a) > 3:									# is it long enough to maybe contain an escape char?
			if a[-3] == UNPACKER_ESCAPE_CHAR:			# check if 3rd from end is an escape char
				n = encode_string_with_escape(a[0:-3])	# convert str before escape from str to bytearray
				n += bytearray.fromhex(a[-2:])			# convert hex after escape char to single byte and append
				return n
		return bytearray(a, UNPACKER_ENCODING)			# no escape char: convert from str to bytearray the standard way
	except UnicodeEncodeError:
		# if the decode fails, I hope it is because the input string contains a fullwidth tilde, that's the only error i know how to handle
		# NOTE: there are probably other things that can fail that I just dont know about yet
		new_a = a.replace(u"\uFF5E", u"\u301c")			# replace "fullwidth tilde" with "wave dash", same as MMD does
		try:
			return bytearray(new_a, UNPACKER_ENCODING)	# no escape char: convert from str to bytearray the standard way
		except UnicodeEncodeError as e:
			MY_PRINT_FUNC(e)
			MY_PRINT_FUNC("warning: serious encoding problem")
			return bytearray()

def my_t_format_partitioning(fmt:str) -> (tuple, None):
	# return the indexes within fmt string that produce a slice containing exactly the "t" atom and any preceding numbers
	# if the "t" atom does not exist, return None
	t_pos_start = fmt.find("t")
	if t_pos_start == -1:
		# if no "t" atom is found, return None
		return None
	else:
		t_pos_end = t_pos_start + 1
		# find the t, then count left until i find non-numeric character or reach beginning of string
		while t_pos_start > 0:
			# if it becomes 0, then break
			if fmt[t_pos_start-1].isnumeric():
				# if the char before the current start is numeric, move the current start to include that number
				t_pos_start -= 1
			else:
				# if it is not numeric we don't want it
				break
		return t_pos_start, t_pos_end

def my_unpack(fmt:str, raw:bytearray, top=True):
	# recursively! handle the format string until it's all consumed
	# returns a list of values, or if there is only 1 value it automatically un-listifies it
	t_slice_idx = my_t_format_partitioning(fmt)
	if t_slice_idx is None:
		# if fmt string doesn't contain "t" atoms, no need to handle strings, give it to default unpacker
		retlist = unpack_other(fmt, raw)
	else:
		# if fmt string does contain "t" atoms, then need to handle those & return as strings, not byte arrays
		fmt_before = fmt[:t_slice_idx[0]]
		fmt_t = fmt[t_slice_idx[0]:t_slice_idx[1]]
		fmt_after = fmt[t_slice_idx[1]:]
		# before definitely does not contain t: parse as normal & return value
		if fmt_before == "" or fmt_before.isspace():
			before_ret = []		# if fmt is emtpy then don't attempt to unpack
		else:
			before_ret = unpack_other(fmt_before, raw)
		# the section with the text gets specially handled
		t_ret = unpack_text(fmt_t, raw)
		# after might still contain another t, needs further parsing
		if fmt_after == "" or fmt_after.isspace():
			after_ret = []		# if fmt is emtpy then don't attempt to unpack
		else:
			after_ret = my_unpack(fmt_after, raw, top=False)
			
		# concatenate the 3 returned lists (some might be empty, but they will all definitely be lists)
		retlist = before_ret + t_ret + after_ret
	# if it has length of 1, and about to return the final result, then de-listify it
	if top and len(retlist) == 1:
		return retlist[0]
	else:
		return retlist

def unpack_other(fmt:str, raw:bytearray) -> list:
	# takes format and sequence of bytes, format is guaranteed to not contain the atom "t"
	# returns a list of values, even if its just one value its still in a list
	global UNPACKER_READFROM_BYTE
	r = ()
	try:
		autofmt = "<" + fmt
		r = struct.unpack_from(autofmt, raw, UNPACKER_READFROM_BYTE)
		UNPACKER_READFROM_BYTE += struct.calcsize(autofmt)	# increment the global read-from tracker
	except struct.error as e:
		MY_PRINT_FUNC(e)
		pause_and_quit("Err: something went wrong while parsing, file is probably corrupt/malformed")
	# convert from tuple to list
	return list(r)

def unpack_text(fmt:str, raw:bytearray) -> list:
	global UNPACKER_READFROM_BYTE
	global UNPACKER_FAILED_TRANSLATE_DICT
	global UNPACKER_FAILED_TRANSLATE_FLAG
	r = ()
	# input fmt string is exactly either "t" or "#t" or "##t", etc
	try:
		if fmt == "t":		# this mode exclusively used for PMX parsing
			# auto-text: a text type is an int followed by that many bytes
			i = struct.unpack_from("<i", raw, UNPACKER_READFROM_BYTE)	# get how many bytes to read for str
			UNPACKER_READFROM_BYTE += 4							# increment the global read-from tracker
			autofmt = "<" + str(i[0]) + "s"						# build fmt string that includes # of bytes to read
		else:				# this mode exclusively used for VMD parsing
			# manual-text: if a number is provided with it in the format string, then just read that number of bytes
			autofmt = "<" + fmt[:-1] + "s"						# build fmt string that includes # of bytes to read
			
		v = struct.unpack_from(autofmt, raw, UNPACKER_READFROM_BYTE)	# unpack the actual string(bytearray)
		UNPACKER_READFROM_BYTE += struct.calcsize(autofmt)		# increment the global read-from tracker
		r = v[0]												# un-listify the result
		
		if fmt != "t":
			# manual-text strings are null-terminated: everything after a null byte is invalid garbage to be discarded
			i = r.find(b'\x00')									# look for a null terminator
			if i != -1:											# if null is found...
				r = r[0:i]										# ...return only bytes before it
	except struct.error as e:
		MY_PRINT_FUNC(e)
		pause_and_quit("Err: something went wrong while parsing, file is probably corrupt/malformed, bytepos = " + str(UNPACKER_READFROM_BYTE))
	# r is now a bytearray that should be mappable onto a string, unless it is cut off mid-multibyte-char
	s = decode_bytes_with_escape(r)
	# translated string is now in s (maybe with the escape char tacked on)
	# did it need escaping? add it to the dict for reporting later!
	if UNPACKER_FAILED_TRANSLATE_FLAG:
		UNPACKER_FAILED_TRANSLATE_FLAG = False
		increment_occurance_dict(UNPACKER_FAILED_TRANSLATE_DICT, s)
	# still need to return as a list for concatenation reasons
	return [s]

def my_pack(fmt: str, args_in) -> bytearray:
	# opposite of my_unpack()
	# takes format and list of args (if given a single non-list argument, automatically converts it to a list)
	# return a bytes object which should be appended onto a growing bytearray object
	
	if isinstance(args_in, list):
		args = args_in						# if given list, pass thru unchanged
	elif isinstance(args_in, tuple):
		args = list(args_in)
	else:
		args = [args_in]					# if given something other than a list, automatically convert it into a list
	
	# first search for "t"
	t_slice_idx = my_t_format_partitioning(fmt)
	if t_slice_idx is None:
		# if fmt string doesn't contain "t" atoms, no need to handle strings, give it to default packer
		return pack_other(fmt, args)
	else:
		# if fmt string does contain "t" atoms, then need to handle those specially
		fmt_before = fmt[:t_slice_idx[0]]
		fmt_t = fmt[t_slice_idx[0]:t_slice_idx[1]]
		fmt_after = fmt[t_slice_idx[1]:]
		# where is the string that corresponds to the "t" atom?
		i = 0
		for i in range(len(args)):
			if isinstance(args[i], str):
				break
		args_before = args[:i]
		args_t = args[i:i+1]
		args_after = args[i+1:]
		
		# before definitely does not contain t: parse as normal & return value
		if fmt_before == "" or fmt_before.isspace():
			ret_before = bytearray()	# if fmt is emtpy then don't attempt to pack
		else:
			ret_before = pack_other(fmt_before, args_before)
		# the section with the text gets specially handled
		ret_t = pack_text(fmt_t, args_t)
		# after might still contain another t, needs further parsing
		if fmt_after == "" or fmt_after.isspace():
			ret_after = bytearray()		# if fmt is emtpy then don't attempt to pack
		else:
			ret_after = my_pack(fmt_after, args_after)

		# concatenate the 3 returned bytearrays (some might be empty, but they will all definitely be bytearrays)
		retlist = ret_before + ret_t + ret_after
		return retlist

def pack_other(fmt: str, args: list) -> bytearray:
	try:
		b = struct.pack("<" + fmt, *args)	# now do the actual packing
		return bytearray(b)
	except struct.error as e:
		# repackage the error to add additional info and throw it again to be caught at a higher level
		newerrstr = "err=" + str(e) + "\nfmt=" + fmt + "\nargs=" + str(args)
		newerr = struct.error(newerrstr)
		raise newerr

def pack_text(fmt: str, args: list) -> bytearray:
	# input fmt string is exactly either "t" or "#t" or "##t", etc
	# input args list is list of exactly 1 string
	n = encode_string_with_escape(args[0])		# convert str to bytearray
	if fmt == "t":			# auto-text
		# "t" means "i ##s" where ##=i. convert to bytearray, measure len, replace t with "i ##s"
		autofmt = "<i" + str(len(n)) + "s"
		autoargs = [len(n), n]
	else:					# manual-text
		autofmt = fmt[:-1] + "s"				# simply replace trailing t with s
		autoargs = [n]
		
	try:
		b = struct.pack(autofmt, *autoargs)		# now do the actual packing
		return bytearray(b)
	except struct.error as e:
		# repackage the error to add additional info and throw it again to be caught at a higher level
		# these are the args before replacing t with s, and before converting strings to bytearrays
		newerrstr = "err=" + str(e) + "\nfmt=" + fmt + "\nargs=" + str(args)
		newerr = struct.error(newerrstr)
		raise newerr

if __name__ == '__main__':
	MY_PRINT_FUNC("Nuthouse01 - 03/30/2020 - v3.51")
	pause_and_quit("you are not supposed to directly run this file haha")
