from typing import List

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_io as io
import mmd_scripting.core.nuthouse01_vmd_parser as vmdlib
import mmd_scripting.core.nuthouse01_vmd_struct as vmdstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.04 - 8/19/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################
# massive thanks and credit to "Isometric" for helping me discover the quaternion transformation method used in mmd!!!!
# the script wouldn't be completable without him :)
#####################
# VMD format partially described here: https://mikumikudance.fandom.com/wiki/VMD_file_format
# i have actually gone above & beyond what is described on this wiki and discovered the secrets of the remaining parts of the format!
# the complete format is described in the attached README file
#####################


# this script can perfectly* and reversibly convert VMD->text and text->VMD! the rotations values drift very slightly
# during conversion because of the needed math operations, so it is not exactly identical, but it is below the
# threshold of what is noticable.


# note: VPD files are plain-text, not binary files, you can literally open them with Notepad++ and see the contents

# VMD files do not contain outside parent data, gravity data, or accessory data, but everything else that can be 
# keyframed with in the MMD timeline can be saved/restored.

# VMD FORMAT: described in the attached README file

# I'm not going to bother describing the "nicelist" format too much because if you're good enough that you want to
# use my functions to accomplish something new, you're good enough to read the functions and see how the format
# is assembled at the end of each sub-function. All the data fields and functions have pretty reasonable names.
# All angles are internally represented as degrees (and printed to text in degrees), and they should match the angle
# values that MMD displays as well.


# FUNCTIONS & STRUCTURE:
#
# VMD -> TEXT:
# convert_vmd_to_txt()
# 	vmdlib.read_vmd()
# 		core.read_binfile_to_bytes()
# 		vmdlib.parse_vmd_header()
# 		vmdlib.parse_vmd_boneframe()
# 		vmdlib.parse_vmd_morphframe()
# 		vmdlib.parse_vmd_camframe()
# 		vmdlib.parse_vmd_lightframe()
# 		vmdlib.parse_vmd_shadowframe()
# 		vmdlib.parse_vmd_ikdispframe()
# 	write_vmdtext()
# 		format_nicelist_as_rawlist()
# 		core.write_rawlist_to_txt()
#
# TEXT -> VMD:
# convert_txt_to_vmd()
# 	read_vmdtext()
# 		core.read_txt_to_rawlist()
# 		read_vmdtext_header()
# 		read_vmdtext_boneframe()
# 		read_vmdtext_morphframe()
# 		read_vmdtext_camframe()
# 		read_vmdtext_lightframe()
# 		read_vmdtext_shadowframe()
# 		read_vmdtext_ikdispframe()
# 	vmdlib.write_vmd()
# 		vmdlib.encode_vmd_header()
# 		vmdlib.encode_vmd_boneframe()
# 		vmdlib.encode_vmd_morphframe()
# 		vmdlib.encode_vmd_camframe()
# 		vmdlib.encode_vmd_lightframe()
# 		vmdlib.encode_vmd_shadowframe()
# 		vmdlib.encode_vmd_ikdispframe()
# 		core.write_bytes_to_binfile()


########################################################################################################################
# constants & options
########################################################################################################################


# do you want to print a summary of bones & morphs in the VMD file?
# now that "model_compatability_check.py" exists, this feature is turned off by default
PRINT_BONE_MORPH_SUMMARY_FILE = False

filestr_txt = ".txt"
# filestr_txt = ".csv"


# set up the text-file labels to use for writing and comparing against when reading
# probably don't want to change these
keystr_version = "version:"
keystr_modelname = "modelname:"
keystr_boneframect = "boneframe_ct:"
keystr_boneframekey = ["bone_name", "frame_num", "Xpos", "Ypos", "Zpos", "Xrot", "Yrot", "Zrot", "phys_disable",
					   "interp_x_ax", "interp_x_ay", "interp_x_bx", "interp_x_by", 
					   "interp_y_ax", "interp_y_ay", "interp_y_bx", "interp_y_by", 
					   "interp_z_ax", "interp_z_ay", "interp_z_bx", "interp_z_by", 
					   "interp_r_ax", "interp_r_ay", "interp_r_bx", "interp_r_by"]
keystr_morphframect = "morphframe_ct:"
keystr_morphframekey = ["morph_name", "frame_num", "value"]
keystr_camframect = "camframe_ct:"
keystr_camframekey = ["frame_num", "target_dist", "Xpos", "Ypos", "Zpos", "Xrot", "Yrot", "Zrot", "FOV", "perspective",
					  "interp_x_ax", "interp_x_ay", "interp_x_bx", "interp_x_by",
					  "interp_y_ax", "interp_y_ay", "interp_y_bx", "interp_y_by",
					  "interp_z_ax", "interp_z_ay", "interp_z_bx", "interp_z_by",
					  "interp_r_ax", "interp_r_ay", "interp_r_bx", "interp_r_by",
					  "interp_dist_ax", "interp_dist_ay", "interp_dist_bx", "interp_dist_by",
					  "interp_fov_ax", "interp_fov_ay", "interp_fov_bx", "interp_fov_by"]
keystr_lightframect = "lightframe_ct:"
keystr_lightframekey = ["frame_num", "red", "green", "blue", "x_dir", "y_dir", "z_dir"]
keystr_shadowframect = "shadowframe_ct:"
keystr_shadowframekey = ["frame_num", "mode", "shadowrange"]
keystr_ikdispframect = "ik/dispframe_ct:"
keystr_ikdispframekey = ["frame_num", "display_model", "{ik_name", "ik_enable}"]

keystr_morphsummct = "num_morphs:"
keystr_morphsummmultict = "num_morphs_multi_use:"
keystr_morphsummkey = ["morph_name", "num_times_used"]
keystr_bonesummct = "num_bones:"
keystr_bonesummmultict = "num_bones_multi_use:"
keystr_bonesummkey = ["bone_name", "num_times_used"]

# variable to keep track of where to start reading from next within the raw-file
readfrom_line = 0


########################################################################################################################
# error-checking functions while reading vmd-as-text
########################################################################################################################

def check1_match_len(rawlist_text: list, target_len: int):
	if len(rawlist_text[readfrom_line]) != target_len:
		core.MY_PRINT_FUNC("Err1: on line %d, incomplete or malformed .txt file: expected %d items but found %d" %
							(readfrom_line+1, target_len, len(rawlist_text[readfrom_line])))
		raise RuntimeError()
def check2_match_first_item(rawlist_text: list, label: str):
	check1_match_len(rawlist_text, 2)
	if rawlist_text[readfrom_line][0] != label:
		core.MY_PRINT_FUNC("Err2: on line %d, incomplete or malformed .txt file: expected '%s' in pos0" %
							(readfrom_line + 1, label))
		raise RuntimeError()
def check3_match_keystr(rawlist_text: list, keystr: list):
	if rawlist_text[readfrom_line] != keystr:
		core.MY_PRINT_FUNC("Err3: on line %d, incomplete or malformed .txt file: expected keyline '%s'" %
							(readfrom_line + 1, keystr))
		raise RuntimeError()

########################################################################################################################
# functions to allow reading vmd-as-txt
########################################################################################################################

def read_vmdtext_header(rawlist_text: List[list]) -> vmdstruct.VmdHeader:
	##################################
	# header data
	global readfrom_line
	
	# first check for bad format
	check2_match_first_item(rawlist_text, keystr_version)

	# read version
	version = rawlist_text[readfrom_line][1]
	readfrom_line += 1

	# check for bad format again
	check2_match_first_item(rawlist_text, keystr_modelname)

	# read model name
	modelname = rawlist_text[readfrom_line][1]
	readfrom_line += 1
	core.MY_PRINT_FUNC("...model name   = JP:'%s'" % modelname)
	# assemble and return
	return vmdstruct.VmdHeader(version, modelname)

def read_vmdtext_boneframe(rawlist_text: List[list]) -> List[vmdstruct.VmdBoneFrame]:
	#############################
	# bone frames
	global readfrom_line
	bone_list = []
	
	# first, check for bad format
	check2_match_first_item(rawlist_text, keystr_boneframect)

	boneframe_ct = rawlist_text[readfrom_line][1]
	readfrom_line += 1
	core.MY_PRINT_FUNC("...# of boneframes          = %d" % boneframe_ct)
	
	if boneframe_ct > 0:
		# ensure the key-line is where i think it is
		check3_match_keystr(rawlist_text, keystr_boneframekey)
		# if it is indeed here, then inc the readpointer
		readfrom_line += 1
		
		for i in range(boneframe_ct):
			# ensure it has the right # of items on the line
			check1_match_len(rawlist_text, len(keystr_boneframekey))
			# the nicelist has angles in euler format, no conversion is needed
			r = rawlist_text[readfrom_line]
			# create the boneframe object, distribute the listified data to the proper named members
			newframe = vmdstruct.VmdBoneFrame(name=r[0],
											  f=r[1],
											  pos=r[2:5],
											  rot=r[5:8],
											  phys_off=r[8],
											  interp_x=r[9:13],
											  interp_y=r[13:17],
											  interp_z=r[17:21],
											  interp_r=r[21:25],)
			bone_list.append(newframe)
			# increment the readfrom_line pointer
			readfrom_line += 1
			# progress tracker just because
			core.print_progress_oneline(i / boneframe_ct)
	return bone_list

def read_vmdtext_morphframe(rawlist_text: List[list]) -> List[vmdstruct.VmdMorphFrame]:
	###########################################
	# morph frames
	global readfrom_line
	morph_list = []
	# first check for bad format
	check2_match_first_item(rawlist_text, keystr_morphframect)

	morphframe_ct = rawlist_text[readfrom_line][1]
	core.MY_PRINT_FUNC("...# of morphframes         = %d" % morphframe_ct)
	readfrom_line += 1
	
	if morphframe_ct > 0:
		# ensure the key-line is where i think it is
		check3_match_keystr(rawlist_text, keystr_morphframekey)
		# if it is indeed here, then inc the readpointer
		readfrom_line += 1
		
		for i in range(morphframe_ct):
			# ensure it has the right # of items on the line
			check1_match_len(rawlist_text, len(keystr_morphframekey))
			r = rawlist_text[readfrom_line]
			newframe = vmdstruct.VmdMorphFrame(name=r[0], f=r[1], val=r[2])
			morph_list.append(newframe)
			# increment the readfrom_line pointer
			readfrom_line += 1
			# progress tracker just because
			core.print_progress_oneline(i / morphframe_ct)
	return morph_list

def read_vmdtext_camframe(rawlist_text: List[list]) -> List[vmdstruct.VmdCamFrame]:
	###########################################
	# cam frames
	global readfrom_line
	cam_list = []
	check2_match_first_item(rawlist_text, keystr_camframect)

	camframe_ct = rawlist_text[readfrom_line][1]
	core.MY_PRINT_FUNC("...# of camframes           = %d" % camframe_ct)
	readfrom_line += 1
	
	if camframe_ct > 0:
		# ensure the key-line is where i think it is
		check3_match_keystr(rawlist_text, keystr_camframekey)
		# if it is indeed here, then inc the readpointer
		readfrom_line += 1
		
		for i in range(camframe_ct):
			# ensure it has the right # of items on the line
			check1_match_len(rawlist_text, len(keystr_camframekey))
			r = rawlist_text[readfrom_line]
			# create the camframe object, distribute the listified data to the proper named members
			newframe = vmdstruct.VmdCamFrame(f=r[0],
											 dist=r[1],
											 pos=r[2:5],
											 rot=r[5:8],
											 fov=r[8],
											 perspective=r[9],
											 interp_x=r[10:14],
											 interp_y=r[14:18],
											 interp_z=r[18:22],
											 interp_r=r[22:26],
											 interp_dist=r[26:30],
											 interp_fov=r[30:34],
											 )
			cam_list.append(newframe)
			# increment the readfrom_line pointer
			readfrom_line += 1
			# progress tracker just because
			core.print_progress_oneline(i / camframe_ct)
	return cam_list

def read_vmdtext_lightframe(rawlist_text: List[list]) -> List[vmdstruct.VmdLightFrame]:
	###########################################
	# light frames
	global readfrom_line
	light_list = []
	check2_match_first_item(rawlist_text, keystr_lightframect)

	lightframe_ct = rawlist_text[readfrom_line][1]
	core.MY_PRINT_FUNC("...# of lightframes         = %d" % lightframe_ct)
	readfrom_line += 1
	
	if lightframe_ct > 0:
		# ensure the key-line is where i think it is
		check3_match_keystr(rawlist_text, keystr_lightframekey)
		# if it is indeed here, then inc the readpointer
		readfrom_line += 1
		
		for i in range(lightframe_ct):
			# ensure it has the right # of items on the line
			check1_match_len(rawlist_text, len(keystr_lightframekey))
			r = rawlist_text[readfrom_line]
			newframe = vmdstruct.VmdLightFrame(f=r[0], color=r[1:4], pos=r[4:7])
			light_list.append(newframe)
			# increment the readfrom_line pointer
			readfrom_line += 1
	return light_list

def read_vmdtext_shadowframe(rawlist_text: List[list]) -> List[vmdstruct.VmdShadowFrame]:
	###########################################
	# shadow frames
	global readfrom_line
	shadow_list = []
	check2_match_first_item(rawlist_text, keystr_shadowframect)

	shadowframe_ct = rawlist_text[readfrom_line][1]
	core.MY_PRINT_FUNC("...# of shadowframes        = %d" % shadowframe_ct)
	readfrom_line += 1
	
	if shadowframe_ct > 0:
		# ensure the key-line is where i think it is
		check3_match_keystr(rawlist_text, keystr_shadowframekey)
		# if it is indeed here, then inc the readpointer
		readfrom_line += 1
		
		for i in range(shadowframe_ct):
			# ensure it has the right # of items on the line
			check1_match_len(rawlist_text, len(keystr_shadowframekey))
			# the nicelist has angles in euler format, don't convert the values here
			r = rawlist_text[readfrom_line]
			newframe = vmdstruct.VmdShadowFrame(f=r[0], mode=r[1], val=r[2])
			shadow_list.append(newframe)
			# increment the readfrom_line pointer
			readfrom_line += 1
	return shadow_list

def read_vmdtext_ikdispframe(rawlist_text: List[list]) -> List[vmdstruct.VmdIkdispFrame]:
	###########################################
	# disp/ik frames
	global readfrom_line
	ikdisp_list = []
	check2_match_first_item(rawlist_text, keystr_ikdispframect)

	ikdispframe_ct = rawlist_text[readfrom_line][1]
	core.MY_PRINT_FUNC("...# of ik/disp frames      = %d" % ikdispframe_ct)
	readfrom_line += 1
	
	if ikdispframe_ct > 0:
		# ensure the key-line is where i think it is
		check3_match_keystr(rawlist_text, keystr_ikdispframekey)
		# if it is indeed here, then inc the readpointer
		readfrom_line += 1
		
		for i in range(ikdispframe_ct):
			# ensure it has the right # of items on the line
			# this line is variable size, no simple way to check without trying to read it
			# valid sizes are 2/4/6/8etc, so fail if it is even or if it is less than 2 items
			if len(rawlist_text[readfrom_line]) < 2 or len(rawlist_text[readfrom_line]) % 2 == 1:
				core.MY_PRINT_FUNC(
					"Err1: on line %d, incomplete or malformed .txt file: expected even# of items >= 2 but found %d" %
					(readfrom_line + 1, len(rawlist_text[readfrom_line])))
				raise RuntimeError()
			l = rawlist_text[readfrom_line]
			# need to restructure the frame before it becomes the correct nicelist format
			ik_pairs = []
			for pos in range(2, len(l), 2):
				ik_pairs.append(vmdstruct.VmdIkbone(name=l[pos], enable=l[pos + 1]))
			newframe = vmdstruct.VmdIkdispFrame(f=l[0], disp=l[1], ikbones=ik_pairs)
			ikdisp_list.append(newframe)
			# increment the readfrom_line pointer
			readfrom_line += 1
	return ikdisp_list

########################################################################################################################
# functions to allow writing vmd-as-txt
########################################################################################################################

# TODO LOW: redo vmd-as-text structure to remove "how many of each frame type" specifiers

def format_nicelist_as_rawlist(vmd: vmdstruct.Vmd) -> List[list]:
	# unpack the fields of the nicelist format into named lists
	# (header, boneframe_list, morphframe_list, camframe_list, lightframe_list, shadowframe_list,
	#  ikdispframe_list) = nicelist
	
	# format the nicelist with the CSV format I decided to use, return a list of lines for file-write
	# header
	rawlist = [[keystr_version, vmd.header.version], [keystr_modelname, vmd.header.modelname]]
	
	# bones
	boneframe_ct = len(vmd.boneframes)
	rawlist.append([keystr_boneframect, boneframe_ct])
	if boneframe_ct != 0:
		rawlist.append(keystr_boneframekey)  # key
		rawlist += [b.list() for b in vmd.boneframes]
	
	# morphs
	morphframe_ct = len(vmd.morphframes)
	rawlist.append([keystr_morphframect, morphframe_ct])
	if morphframe_ct != 0:
		rawlist.append(keystr_morphframekey)  # key
		rawlist += [b.list() for b in vmd.morphframes]
	
	# cams
	camframe_ct = len(vmd.camframes)
	rawlist.append([keystr_camframect, camframe_ct])
	if camframe_ct != 0:
		rawlist.append(keystr_camframekey)  # key
		rawlist += [b.list() for b in vmd.camframes]
	
	# light
	lightframe_ct = len(vmd.lightframes)
	rawlist.append([keystr_lightframect, lightframe_ct])
	if lightframe_ct != 0:
		rawlist.append(keystr_lightframekey)  # key
		rawlist += [b.list() for b in vmd.lightframes]
	
	# shadows
	shadowframe_ct = len(vmd.shadowframes)
	rawlist.append([keystr_shadowframect, shadowframe_ct])
	if shadowframe_ct != 0:
		rawlist.append(keystr_shadowframekey)  # key
		rawlist += [b.list() for b in vmd.shadowframes]
	
	# ikdisp
	ikdispframe_ct = len(vmd.ikdispframes)
	rawlist.append([keystr_ikdispframect, ikdispframe_ct])
	if ikdispframe_ct != 0:
		rawlist.append(keystr_ikdispframekey)  # key
		rawlist += [b.list() for b in vmd.ikdispframes]
	
	return rawlist

# def format_dicts_as_rawlist(bonedict: dict, morphdict: dict) -> list:
# 	# add headers and stuff to arrange the dictionaries into CSV format to prep for printing
# 	rawlist = []
#
# 	# morphdict totals
# 	num_morphs_multi_use = 0
# 	for b, c in morphdict.items():
# 		if c > 1:
# 			num_morphs_multi_use += 1
# 	rawlist.append([keystr_morphsummct, len(morphdict)])
# 	if len(morphdict) > 0:
# 		rawlist.append([keystr_morphsummmultict, num_morphs_multi_use])
# 		# morphdict actual
# 		morphdict_sorted = list(morphdict.items())  # dict -> list
# 		morphdict_sorted.sort(key=core.get1st)  # sort by name as tiebreaker
# 		morphdict_sorted.sort(key=core.get2nd, reverse=True)  # sort in-place descending by 2nd element as primary
# 		rawlist.append(keystr_morphsummkey)  # key
# 		rawlist += morphdict_sorted  # append
#
# 	# bonedict totals
# 	num_bones_multi_use = 0
# 	for b, c in bonedict.items():
# 		if c > 1:
# 			num_bones_multi_use += 1
# 	rawlist.append([keystr_bonesummct, len(bonedict)])
# 	if len(bonedict) > 0:
# 		rawlist.append([keystr_bonesummmultict, num_bones_multi_use])
# 		# bonedict actual
# 		bonedict_sorted = list(bonedict.items())  # dict -> list
# 		bonedict_sorted.sort(key=core.get1st)  # sort by name as tiebreaker
# 		bonedict_sorted.sort(key=core.get2nd, reverse=True)  # sort in-place descending by 2nd element as primary
# 		rawlist.append(keystr_bonesummkey)  # key
# 		rawlist += bonedict_sorted  # append
# 	return rawlist

########################################################################################################################
# read_vmdtext() and write_vmdtext()
########################################################################################################################

def read_vmdtext(vmdtext_filename: str) -> vmdstruct.Vmd:
	# break apart the CSV text-file format, arrange the data into a easier-to-manipulate list of lists
	# also check that headers are where they should be and each line has the proper number of items on it
	# return nicelist = [header, modelname, bone_list, morph_list, cam_list, light_list, shadow_list, ikdisp_list]
	
	cleanname = core.filepath_splitdir(vmdtext_filename)[1]
	core.MY_PRINT_FUNC("Begin reading VMD-as-text file '%s'" % cleanname)
	vmdtext_rawlist = io.read_file_to_csvlist(vmdtext_filename)
	core.MY_PRINT_FUNC("...total size   = %s lines" % len(vmdtext_rawlist))
	core.MY_PRINT_FUNC("Begin parsing VMD-as-text file '%s'" % cleanname)
	
	global readfrom_line
	# set this to zero just in case
	readfrom_line = 0
	
	# wrap the entire parsing section in a try-except block looking for index errors
	try:
		A = read_vmdtext_header(vmdtext_rawlist)
		B = read_vmdtext_boneframe(vmdtext_rawlist)
		C = read_vmdtext_morphframe(vmdtext_rawlist)
		D = read_vmdtext_camframe(vmdtext_rawlist)
		E = read_vmdtext_lightframe(vmdtext_rawlist)
		F = read_vmdtext_shadowframe(vmdtext_rawlist)
		G = read_vmdtext_ikdispframe(vmdtext_rawlist)
	except IndexError as e:
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		core.MY_PRINT_FUNC("ERROR: unexpected end-of-file or end-of-line, was reading from line " + str(readfrom_line + 1))
		raise RuntimeError()
	
	if readfrom_line != len(vmdtext_rawlist):
		core.MY_PRINT_FUNC("Warning: there are unsupported trailing lines on the end of the file", readfrom_line,
			  len(vmdtext_rawlist))
	
	core.MY_PRINT_FUNC("Done parsing VMD-as-text file '%s'" % cleanname)
	# stuff to return:
	# version+modelname, bonelist, morphlist, camlist, lightlist, shadowlist, ikdisplist
	return vmdstruct.Vmd(A, B, C, D, E, F, G)

def write_vmdtext(vmdtext_filename: str, nicelist: vmdstruct.Vmd):
	# assume the output filename has already been validated as unused, etc
	cleanname = core.filepath_splitdir(vmdtext_filename)[1]
	core.MY_PRINT_FUNC("Begin formatting VMD-as-text file '%s'" % cleanname)
	
	rawlist = format_nicelist_as_rawlist(nicelist)
	
	# done formatting!
	core.MY_PRINT_FUNC("Begin writing VMD-as-text file '%s'" % cleanname)
	core.MY_PRINT_FUNC("...total size   = %s lines" % len(rawlist))
	io.write_csvlist_to_file(vmdtext_filename, rawlist)
	core.MY_PRINT_FUNC("Done writing VMD-as-text file '%s'" % cleanname)
	return

# def write_summary_dicts(bonedict: dict, morphdict: dict, summary_filename: str) -> None:
# 	# assume the output filename has already been validated as unused, etc
# 	core.MY_PRINT_FUNC("Begin formatting bone & morph summary file '%s'" % summary_filename)
#
# 	rawlist = format_dicts_as_rawlist(bonedict, morphdict)
#
# 	# done formatting!
# 	core.MY_PRINT_FUNC("Begin writing bone & morph summary file '%s'" % summary_filename)
# 	core.MY_PRINT_FUNC("...total size   = %s lines" % len(rawlist))
# 	core.write_csvlist_to_file(summary_filename, rawlist)
# 	core.MY_PRINT_FUNC("Done writing bone & morph summary file '%s'" % summary_filename)
# 	return None

########################################################################################################################
# MAIN & menu, also convert_txt_to_vmd() and convert_vmd_to_txt()
########################################################################################################################

def convert_txt_to_vmd(input_filename, moreinfo=True):
	"""
	Read a VMD-as-text file from disk, convert it, and write to disk as a VMD motion file.
	The output will have the same path and basename, but the opposite file extension.
	
	:param input_filename: filepath to input txt, absolute or relative to CWD
	:param moreinfo: default false. if true, get extra printouts with more info about stuff.
	"""
	# read the VMD-as-text into the nicelist format, all in one function
	vmd_nicelist = read_vmdtext(input_filename)
	core.MY_PRINT_FUNC("")
	# identify an unused filename for writing the output
	base = core.filepath_splitext(input_filename)[0]
	base += ".vmd"
	dumpname = core.filepath_get_unused_name(base)
	# write the output VMD file
	vmdlib.write_vmd(dumpname, vmd_nicelist, moreinfo=moreinfo)
	
	# done!
	return


def convert_vmd_to_txt(input_filename: str, moreinfo=True):
	"""
	Read a VMD motion file from disk, convert it, and write to disk as a text file.
	The output will have the same path and basename, but the opposite file extension.
	See 'README.txt' for more details about VMD-as-text output format.
	
	:param input_filename: filepath to input vmd, absolute or relative to CWD
	:param moreinfo: default false. if true, get extra printouts with more info about stuff.
	"""
	# read the entire VMD, all in this one function
	# also create the bonedict & morphdict
	vmd_nicelist = vmdlib.read_vmd(input_filename, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("")
	# identify an unused filename for writing the output
	base = core.filepath_splitext(input_filename)[0]
	base += filestr_txt
	dumpname = core.filepath_get_unused_name(base)
	# write the output VMD-as-text file
	write_vmdtext(dumpname, vmd_nicelist)
	
	# #####################################
	# # summary file:
	#
	# # if there are no bones and no morphs, there is no need for a summary file... just return early
	# if len(bonedict) == 0 and len(morphdict) == 0:
	# 	return None
	# # if the user doesn't want a summary, dont bother
	# elif not PRINT_BONE_MORPH_SUMMARY_FILE:
	# 	return None
	# else:
	# 	# identify an unused filename for writing the output
	# 	summname = core.filepath_get_unused_name(core.get_clean_basename(dumpname) + "_summary" + filestr_txt)
	# 	write_summary_dicts(bonedict, morphdict, summname)
	
	# done!
	return

helptext = '''=================================================
convert_vmd_to_txt:
This tool is for converting VMD files to and from human-readable text form.
VMD -> TXT and TXT -> VMD are both supported.
This supports all types of VMD frame data: bones, morphs, camera, lighting, shadow, IK/disp.
That means this tool supports literally ALL types of VMD files: dance, cam, or facials.
The text output file is arranged as valid CSV (comma-separated value) format, so you can technically change the file extension and load it into Microsoft Excel or whatever. But Excel doesn't properly display the Japanese characters so this is not recommended.
See 'README.txt' for more details about output format.

This takes as input either a VMD file or a TXT file produced by this tool.
The output will have the same path and basename, but the opposite file extension.
'''

def main(moreinfo=False):
	# prompt for "convert text -> VMD" or "VMD -> text"
	core.MY_PRINT_FUNC("For VMD->TXT, please enter the name of a .vmd file.\nOr for TXT->VMD, please enter the name of a .txt file.")
	core.MY_PRINT_FUNC("")
	input_filename = core.MY_FILEPROMPT_FUNC("VMD or TXT file", (".vmd",".txt"))
	
	if input_filename.lower().endswith(".vmd"):
		# activate correct function
		convert_vmd_to_txt(input_filename, moreinfo=moreinfo)
	else:
		# activate correct function
		convert_txt_to_vmd(input_filename, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return
	
########################################################################################################################
# after all the funtions are defined, actually execute main()
########################################################################################################################

if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
