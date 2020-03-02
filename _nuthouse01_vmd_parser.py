# Nuthouse01 - 02/29/2020 - v3.00
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
# read_vmd()
# 	core.read_binfile_to_bytes()
# 	parse_vmd_header()
# 	parse_vmd_boneframe()
# 	parse_vmd_morphframe()
# 	parse_vmd_camframe()
# 	parse_vmd_lightframe()
# 	parse_vmd_shadowframe()
# 	parse_vmd_ikdispframe()
#
# write_vmd()
# 	encode_vmd_header()
# 	encode_vmd_boneframe()
# 	encode_vmd_morphframe()
# 	encode_vmd_camframe()
# 	encode_vmd_lightframe()
# 	encode_vmd_shadowframe()
# 	encode_vmd_ikdispframe()
# 	core.write_bytes_to_binfile()



import sys
# first, version check: verify that this is using python3
# i don't know if it will actually work in 3.4 but i know it will fail in any python2 version
# actually written/tested with 3.6.6 so guaranteed to work on that or higher
# between 3.4 and 3.6, who knows
if sys.version_info < (3, 4):
	print("Your version of Python is too old to run this script, please update!")
	print("Your current version = " + sys.version)
	print("...press ENTER to exit...")
	input()
	exit()

import math
import struct

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	import _nuthouse01_core as core
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	core = None

########################################################################################################################
# constants & options
########################################################################################################################

# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


# VMD format doesn't need to sort by frame number, but i can do it
# this is applied when reading or when writing a VMD
GUARANTEE_FRAMES_SORTED = True

# this is added to the end of any VMDs created, to prove that they were modified with this tool
# doesn't affect the ability of MikuMikuDance, MikuMikuMoving, or MMDTools to read the file
APPEND_SIGNATURE = True
SIGNATURE = "Nuthouse01"



# set up the format specifier strings for packing/unpacking the binary data
# DO NOT CHANGE THESE, NO MATTER WHAT
fmt_header = "30t"
fmt_modelname_new = "20t"
fmt_modelname_old = "10t"
fmt_number = "I"
fmt_boneframe_no_interpcurve = "15t I 7f"
fmt_boneframe_interpcurve = "bb bb 12b xbb 45x"
fmt_boneframe_interpcurve_oneline = "16b"
fmt_morphframe = "15t I f"
fmt_camframe = "I 7f 24b I ?"
fmt_lightframe = "I 3f 3f"
fmt_shadowframe = "I b f"
fmt_ikdispframe = "I ? I"
fmt_ikframe = "20t ?"



########################################################################################################################
# pipeline functions for READING
########################################################################################################################

def parse_vmd_header(raw) -> list:
	############################
	# unpack the header, get file version and model name
	# version only affects the length of the model name text field, but i'll return it anyway
	header = core.my_unpack(fmt_header, raw)
	if header == "Vocaloid Motion Data 0002":
		# if this matches, this is version >= 1.30
		# but i will just return "2"
		version = 2
		# model name string is 20-chars long
		modelname = core.my_unpack(fmt_modelname_new, raw)
	elif header == "Vocaloid Motion Data file":
		# this is actually untested & unverified, but according to the docs this is how it's labelled
		# if this matches, this is version < 1.30
		# but i will just return "1"
		version = 1
		# model name string is 10-chars long
		modelname = core.my_unpack(fmt_modelname_old, raw)
	else:
		print("ERR: found unsupported file version identifier string, '%s'" % header)
		raise ValueError()
	print("...model name   = JP:'%s'" % modelname)
	
	return [version, modelname]

def parse_vmd_boneframe(raw) -> (list, dict):
	# get all the bone-frames, store in a list of lists
	boneframe_list = []
	# all bones usages will be counted in this dictionary
	bonedict = {}
	# verify that there is enough file left to read a single number
	if (len(raw) - core.get_readfrom_byte()) < struct.calcsize(fmt_number):
		print("Warning: expected boneframe_ct field but file ended unexpectedly! Assuming 0 boneframes and continuing...")
		return boneframe_list, bonedict

	############################
	# get the number of bone-frames
	boneframe_ct = core.my_unpack(fmt_number, raw)
	print("...# of boneframes          = %d" % boneframe_ct)
	last_progress = -1
	for z in range(boneframe_ct):
		# unpack the bone-frame into variables
		(bname_str, f, xp, yp, zp, xrot_q, yrot_q, zrot_q, wrot_q) = core.my_unpack(fmt_boneframe_no_interpcurve, raw)
		# break inter_curve into its individual pieces, knowing that the 3rd and 4th bytes in line1 are overwritten with phys
		# therefore we need to get their data from line2 which is left-shifted by 1 byte, but otherwise a copy
		(x_ax, y_ax, phys1, phys2, x_ay, y_ay, z_ay, r_ay, x_bx, y_bx, z_bx, r_bx, x_by, y_by, z_by, r_by,
		 z_ax, r_ax) = core.my_unpack(fmt_boneframe_interpcurve, raw)
		# convert the quaternion angles to euler angles
		(xrot, yrot, zrot) = core.quaternion_to_euler([wrot_q, xrot_q, yrot_q, zrot_q])
		# interpret the physics enable/disable bytes
		if (phys1, phys2) == (z_ax, r_ax):
			# if they match the values they should be, they were never overwritten in the first place???
			phys_off = False
		elif (phys1, phys2) == (0, 0):
			# phys stays on
			phys_off = False
		elif (phys1, phys2) == (99, 15):
			# phys turns off
			phys_off = True
		else:
			print("Warning: found unusual values where I expected to find physics enable/disable! Assuming this means physics off")
			print(bname_str, "f=", str(f), "(phys1,phys2)=", str((phys1, phys2)))
			phys_off = True
		# store them all on the list
		# create a list to hold all the boneframe data, then append it onto the return-list
		this_boneframe = [bname_str, f, xp, yp, zp, xrot, yrot, zrot, phys_off, x_ax, y_ax, z_ax, r_ax, x_ay, y_ay,
						  z_ay, r_ay, x_bx, y_bx, z_bx, r_bx, x_by, y_by, z_by, r_by]
		boneframe_list.append(this_boneframe)
		# update the bonedict
		# new idea: mask out the boilerplate unused frames! if time=0 and value=0, then its not "used" so dont count it
		if f != 0 or [xp, yp, zp] != [0, 0, 0] or [xrot_q, yrot_q, zrot_q, wrot_q] != [0, 0, 0, 1]:
			core.increment_occurance_dict(bonedict, bname_str)
		# display progress printouts
		if z > last_progress:
			last_progress += 1000
			core.print_progress_oneline(z, boneframe_ct)
	
	if len(bonedict) > 0:
		print("...# of unique bones        = %d" % len(bonedict))
	
	return boneframe_list, bonedict

def parse_vmd_morphframe(raw) -> (list, dict):
	# get all the morph-frames, store in a list of lists
	morphframe_list = []
	# all morphs will be stored in this set (prevents duplicates)
	morphdict = {}
	# is there enough file left to read a single number?
	if (len(raw) - core.get_readfrom_byte()) < struct.calcsize(fmt_number):
		print("Warning: expected morphframe_ct field but file ended unexpectedly! Assuming 0 morphframes and continuing...")
		return morphframe_list, morphdict
	
	############################
	# get the number of morph frames
	morphframe_ct = core.my_unpack(fmt_number, raw)
	print("...# of morphframes         = %d" % morphframe_ct)
	last_progress = -1
	for z in range(morphframe_ct):
		# unpack the morphframe
		(mname_str, f, v) = core.my_unpack(fmt_morphframe, raw)
		morphframe_list.append([mname_str, f, v])
		
		# update the morphdict
		# new idea: mask out the boilerplate unused frames! if time=0 and value=0, then its not "used" so dont count it
		if f != 0 or v != 0:
			core.increment_occurance_dict(morphdict, mname_str)
		# display progress printouts
		if z > last_progress:
			last_progress += 1000
			core.print_progress_oneline(z, morphframe_ct)
	
	if len(morphdict) > 0:
		print("...# of unique morphs       = %d" % len(morphdict))
	
	return morphframe_list, morphdict

def parse_vmd_camframe(raw) -> list:
	camframe_list = []
	# is there enough file left to read a single number?
	if (len(raw) - core.get_readfrom_byte()) < struct.calcsize(fmt_number):
		print("Warning: expected camframe_ct field but file ended unexpectedly! Assuming 0 camframes and continuing...")
		return camframe_list
	############################
	# get the number of cam frames
	camframe_ct = core.my_unpack(fmt_number, raw)
	print("...# of camframes           = %d" % camframe_ct)
	last_progress = -1
	for z in range(camframe_ct):
		# unpack into variables
		(f, d, xp, yp, zp, xr, yr, zr,
		 x_ax, x_bx, x_ay, x_by, y_ax, y_bx, y_ay, y_by, z_ax, z_bx, z_ay, z_by, r_ax, r_bx, r_ay, r_by,
		 dist_ax, dist_bx, dist_ay, dist_by, ang_ax, ang_bx, ang_ay, ang_by,
		 fov, per) = core.my_unpack(fmt_camframe, raw)
		# print(x_ax, x_ay, x_bx, x_by)
		# dont forget radians to degrees
		this_camframe = [f, d, xp, yp, zp, math.degrees(xr), math.degrees(yr), math.degrees(zr), x_ax, x_bx, x_ay,
						 x_by, y_ax, y_bx, y_ay, y_by, z_ax, z_bx, z_ay, z_by, r_ax, r_bx, r_ay, r_by, dist_ax,
						 dist_bx, dist_ay, dist_by, ang_ax, ang_bx, ang_ay, ang_by, fov, per]
		camframe_list.append(this_camframe)
		# display progress printouts
		if z > last_progress:
			last_progress += 1000
			core.print_progress_oneline(z, camframe_ct)
	
	return camframe_list

def parse_vmd_lightframe(raw) -> list:
	lightframe_list = []
	# is there enough file left to read a single number?
	if (len(raw) - core.get_readfrom_byte()) < struct.calcsize(fmt_number):
		print("Warning: expected lightframe_ct field but file ended unexpectedly! Assuming 0 lightframes and continuing...")
		return lightframe_list
	############################
	# if it exists, get the number of lightframes
	lightframe_ct = core.my_unpack(fmt_number, raw)
	print("...# of lightframes         = %d" % lightframe_ct)
	for i in range(lightframe_ct):
		(f, r, g, b, x, y, z) = core.my_unpack(fmt_lightframe, raw)
		# the r g b actually come back as floats, representing (int)/256
		# i wanna put them in the textformat as ints tho
		this_lightframe = [f, round(r * 256), round(g * 256), round(b * 256), x, y, z]
		lightframe_list.append(this_lightframe)
	
	return lightframe_list

def parse_vmd_shadowframe(raw) -> list:
	shadowframe_list = []
	# is there enough file left to read a single number?
	if (len(raw) - core.get_readfrom_byte()) < struct.calcsize(fmt_number):
		print("Warning: expected shadowframe_ct field but file ended unexpectedly! Assuming 0 shadowframes and continuing...")
		return shadowframe_list

	############################
	# if it exists, get the number of shadowframes
	shadowframe_ct = core.my_unpack(fmt_number, raw)
	print("...# of shadowframes        = %d" % shadowframe_ct)
	for i in range(shadowframe_ct):
		(f, m, v) = core.my_unpack(fmt_shadowframe, raw)
		v = round(10000 - (v * 100000))
		# stored as 0.0 to 0.1 ??? why would it use this range!? also its range-inverted
		# [0,9999] -> [0.1, 0.0]
		shadowframe_list.append([f, m, v])
	return shadowframe_list

def parse_vmd_ikdispframe(raw) -> list:
	ikdispframe_list = []
	# is there enough file left to read a single number?
	if (len(raw) - core.get_readfrom_byte()) < struct.calcsize(fmt_number):
		print("Warning: expected ikdispframe_ct field but file ended unexpectedly! Assuming 0 ikdispframes and continuing...")
		return ikdispframe_list

	############################
	# if it exists, get the number of ikdisp frames
	ikdispframe_ct = core.my_unpack(fmt_number, raw)
	print("...# of ik/disp frames      = %d" % ikdispframe_ct)
	for i in range(ikdispframe_ct):
		(f, disp, numbones) = core.my_unpack(fmt_ikdispframe, raw)
		# want to print it to file in the old way tho
		maybe_ik_bones = []
		for j in range(numbones):
			#(ikname, enable)
			templist = core.my_unpack(fmt_ikframe, raw)
			maybe_ik_bones.append(templist)
		this_ikdisp = [f, disp, maybe_ik_bones]
		ikdispframe_list.append(this_ikdisp)
	return ikdispframe_list

########################################################################################################################
# pipeline functions for WRITING
########################################################################################################################

def encode_vmd_header(nice) -> bytearray:
	output = bytearray()
	print("...model name   = JP:'%s'" % nice[1])
	##################################
	# header data
	# first, version: if ver==1, then use "Vocaloid Motion Data file", if ver==2, then use "Vocaloid Motion Data 0002"
	if nice[0] == 2:
		writeme = ["Vocaloid Motion Data 0002", nice[1]]
		output += core.my_pack(fmt_header + fmt_modelname_new, writeme)
	elif nice[0] == 1:
		writeme = ["Vocaloid Motion Data file", nice[1]]
		output += core.my_pack(fmt_header + fmt_modelname_old, writeme)
	else:
		print("ERR: unsupported VMD version value", nice[0])
		raise ValueError
	
	return output

def encode_vmd_boneframe(nice) -> bytearray:
	output = bytearray()
	#############################
	# bone frames
	# first, the number of frames
	print("...# of boneframes          = %d" % len(nice))
	output += core.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	last_progress = -1
	for i, frame in enumerate(nice):
		# assemble the boneframe
		# first, gotta convert from euler to quaternion!
		euler = frame[5:8]  # x y z
		(w, x, y, z) = core.euler_to_quaternion(euler)  # w x y z
		quat = [x, y, z, w]  # x y z w
		# then, do the part that isn't the interpolation curve (first 9 values in binary, 8 things in frame), save as frame
		try:
			# now encode/pack/append the non-interp, non-phys portion
			output += core.my_pack(fmt_boneframe_no_interpcurve, frame[0:5] + quat)
			# then, create one line of the interpolation curve (last 16 values of frame obj)
			interp = core.my_pack(fmt_boneframe_interpcurve_oneline, frame[-16:])
		except struct.error as e:
			print(e)
			print("line=", i)
			print("section=boneframe")
			core.pause_and_quit("Err: something went wrong while synthesizing binary output, probably the wrong type/order of values on a line")
			return bytearray()
		# returns bytes, convert to bytearray for easier appending into this
		interp = bytearray(interp)
		# do the dumb copy-and-shift thing to rebuild the original 4-line structure of redundant bytes
		interp += interp[1:] + bytes(1) + interp[2:] + bytes(2) + interp[3:] + bytes(3)
		# now overwrite the odd missing bytes with physics enable/disable data
		if frame[8] is True:
			interp[2] = 99
			interp[3] = 15
		else:
			interp[2] = 0
			interp[3] = 0
		# append the interpolation data onto the real output
		output += interp
		# progress thing just because
		if i > last_progress:
			last_progress += 1000
			core.print_progress_oneline(i, len(nice))

	return output

def encode_vmd_morphframe(nice) -> bytearray:
	output = bytearray()
	###########################################
	# morph frames
	# first, the number of frames
	print("...# of morphframes         = %d" % len(nice))
	output += core.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	last_progress = -1
	for i, frame in enumerate(nice):
		try:
			output += core.my_pack(fmt_morphframe, frame)
		except struct.error as e:
			print(e)
			print("line=", i)
			print("section=morphframe")
			core.pause_and_quit("Err: something went wrong while synthesizing binary output, probably the wrong type/order of values on a line")

		# print a progress update every so often just because
		if i > last_progress:
			last_progress += 1000
			core.print_progress_oneline(i, len(nice))
	return output

def encode_vmd_camframe(nice) -> bytearray:
	output = bytearray()
	###########################################
	# cam frames
	# first, the number of frames
	print("...# of camframes           = %d" % len(nice))
	output += core.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	last_progress = -1
	for i, frame in enumerate(nice):
		# degrees to radians
		xyz_rads = [math.radians(frame[5]), math.radians(frame[6]), math.radians(frame[7])]
		try:
			output += core.my_pack(fmt_camframe, frame[:5] + xyz_rads + frame[8:])
		except struct.error as e:
			print(e)
			print("line=", i)
			print("section=camframe")
			core.pause_and_quit("Err: something went wrong while synthesizing binary output, probably the wrong type/order of values on a line")
		
		# progress thing just because
		if i > last_progress:
			last_progress += 1000
			core.print_progress_oneline(i, len(nice))
	return output

def encode_vmd_lightframe(nice) -> bytearray:
	output = bytearray()
	###########################################
	# light frames
	# first, the number of frames
	print("...# of lightframes         = %d" % len(nice))
	output += core.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	for i,frame in enumerate(nice):
		# the RGB come in as ints, but are actually stored as floats
		# convert them back to floats for packing
		frame[1] = frame[1] / 256
		frame[2] = frame[2] / 256
		frame[3] = frame[3] / 256
		try:
			output += core.my_pack(fmt_lightframe, frame)
		except struct.error as e:
			print(e)
			print("line=", i)
			print("section=lightframe")
			core.pause_and_quit("Err: something went wrong while synthesizing binary output, probably the wrong type/order of values on a line")
	return output

def encode_vmd_shadowframe(nice) -> bytearray:
	output = bytearray()
	###########################################
	# shadow frames
	# first, the number of frames
	print("...# of shadowframes        = %d" % len(nice))
	output += core.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	for i,frame in enumerate(nice):
		# the shadow value comes in as an int, but it actually stored as a float
		# convert it back to its natural form for packing
		frame[2] = (10000 - frame[2]) / 100000
		try:
			output += core.my_pack(fmt_shadowframe, frame)
		except struct.error as e:
			print(e)
			print("line=", i)
			print("section=shadowframe")
			core.pause_and_quit("Err: something went wrong while synthesizing binary output, probably the wrong type/order of values on a line")

	return output

def encode_vmd_ikdispframe(nice) -> bytearray:
	output = bytearray()
	###########################################
	# disp/ik frames
	# first, the number of frames
	print("...# of ik/disp frames      = %d" % len(nice))
	output += core.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	for i, frame in enumerate(nice):
		try:
			# pack the first 3 args with the "ikdispframe" template
			output += core.my_pack(fmt_ikdispframe, frame[0:2] + [len(frame[2])])
			# for each ikbone listed in the template:
			for z in frame[2]:
				output += core.my_pack(fmt_ikframe, z)
		except struct.error as e:
			print(e)
			print("line=", i)
			print("section=ikdispframe")
			core.pause_and_quit("Err: something went wrong while synthesizing binary output, probably the wrong type/order of values on a line")

	return output

########################################################################################################################
# primary functions: read_vmd() and write_vmd()
########################################################################################################################

def read_vmd(vmd_filename: str, getdict=False):
	# creates object 	(header, boneframe_list, morphframe_list, camframe_list, lightframe_list, shadowframe_list, ikdispframe_list)
	# assumes the calling function already verified correct file extension
	print("Begin reading VMD file '%s'" % vmd_filename)
	vmd_bytes = core.read_binfile_to_bytes(vmd_filename)
	print("...total size   = %sKB" % round(len(vmd_bytes) / 1024))
	print("Begin parsing VMD file '%s'" % vmd_filename)
	core.reset_unpack()
	core.set_encoding("shift_jis")
	
	# !!!! this does eliminate all the garbage data MMD used to pack strings so this isnt 100% reversable !!!
	# read the bytes object and return all the data from teh VMD broken up into a list of lists
	# also convert things from packed formats to human-readable scales
	# (quaternion to euler, radians to degrees, floats to ints, etc)
	# also generate the bonedict and morphdict
	
	A = parse_vmd_header(vmd_bytes)
	B, bonedict = parse_vmd_boneframe(vmd_bytes)
	C, morphdict = parse_vmd_morphframe(vmd_bytes)
	D = parse_vmd_camframe(vmd_bytes)
	E = parse_vmd_lightframe(vmd_bytes)
	F = parse_vmd_shadowframe(vmd_bytes)
	G = parse_vmd_ikdispframe(vmd_bytes)
	core.print_failed_decodes()
	
	bytes_remain = len(vmd_bytes) - core.get_readfrom_byte()
	if bytes_remain != 0:
		# padding with my SIGNATURE is acceptable, anything else is strange
		leftover = vmd_bytes[core.get_readfrom_byte():]
		if leftover == bytes(SIGNATURE, encoding="shift_jis"):
			print("...note: this VMD file was previously modified with this tool!")
		else:
			print("Warning: finished parsing but %d bytes are left over at the tail!" % bytes_remain)
			print("The file may be corrupt or maybe it contains unknown/unsupported data formats")
			print(leftover)
	
	# this is where sorting happens, if it happens
	if GUARANTEE_FRAMES_SORTED:
		# bones & morphs: primarily sorted by frame number, with bone name as tiebreaker. the second sort is the primary one.
		B.sort(key=core.get1st)
		B.sort(key=core.get2nd)
		C.sort(key=core.get1st)
		C.sort(key=core.get2nd)
		# all of these only sort by frame number.
		D.sort(key=core.get1st)
		E.sort(key=core.get1st)
		F.sort(key=core.get1st)
		G.sort(key=core.get1st)
	
	print("Done parsing VMD file '%s'" % vmd_filename)
	if getdict:
		return [A, B, C, D, E, F, G], bonedict, morphdict
	else:
		return [A, B, C, D, E, F, G]

def write_vmd(vmd: list, vmd_filename: str) -> None:
	# recives object 	(header, boneframe_list, morphframe_list, camframe_list, lightframe_list, shadowframe_list, ikdispframe_list)
	# assumes the calling function already verified correct file extension
	print("Begin encoding VMD file '%s'" % vmd_filename)
	core.set_encoding("shift_jis")
	
	# this is where sorting happens, if it happens
	if GUARANTEE_FRAMES_SORTED:
		# bones & morphs: primarily sorted by frame number, with bone name as tiebreaker. the second sort is the primary one.
		vmd[1].sort(key=core.get1st)
		vmd[1].sort(key=core.get2nd)
		vmd[2].sort(key=core.get1st)
		vmd[2].sort(key=core.get2nd)
		# all of these only sort by frame number.
		vmd[3].sort(key=core.get1st)
		vmd[4].sort(key=core.get1st)
		vmd[5].sort(key=core.get1st)
		vmd[6].sort(key=core.get1st)
	
	# arg "vmd" is the same structure created by "parse_vmd()"
	# assume the object is perfect, no sanity-checking needed, it will all be done when parsing the text input
	output_bytes = bytearray()
	
	output_bytes += encode_vmd_header(vmd[0])
	output_bytes += encode_vmd_boneframe(vmd[1])
	output_bytes += encode_vmd_morphframe(vmd[2])
	output_bytes += encode_vmd_camframe(vmd[3])
	output_bytes += encode_vmd_lightframe(vmd[4])
	output_bytes += encode_vmd_shadowframe(vmd[5])
	output_bytes += encode_vmd_ikdispframe(vmd[6])
	
	# done encoding!!
	
	# add a cheeky little binary stamp just to prove that people actually used my tool :)
	if APPEND_SIGNATURE:
		# signature to prove that this file was created with this tool
		output_bytes += bytes(SIGNATURE, encoding="shift_jis")
	
	print("Begin writing VMD file '%s'" % vmd_filename)
	print("...total size   = %sKB" % round(len(output_bytes) / 1024))
	core.write_bytes_to_binfile(output_bytes, vmd_filename)
	print("Done writing VMD file '%s'" % vmd_filename)
	# done with everything!
	return None

########################################################################################################################
# self-test section when this file is executed
########################################################################################################################

def main():
	print("Specify a VMD file to attempt parsing")
	print("Because MikuMikuDance pads with garbage, but I pad with zeros, the binary file I write back will not be exactly bitwise identical")
	print("But I can read the version I wrote and verify that the internal representation matches")
	input_filename = core.prompt_user_filename(".vmd")
	# input_filename = "vmdtest.vmd"
	Z= read_vmd(input_filename)
	write_vmd(Z, "____vmdparser_selftest_DELETEME.vmd")
	ZZ = read_vmd("____vmdparser_selftest_DELETEME.vmd")
	print("")
	print("Is the readback EXACTLY identical to original?", Z == ZZ)
	# boneframelist is different!!! but its just floating-point wibblyness caused by the quaternion transform math
	result = core.recursively_compare(Z, ZZ)
	print("Max difference between two floats:", core.MAXDIFFERENCE)
	print("Number of floats that exceed reasonable threshold 0.0005:", result)
	core.pause_and_quit("Parsed without error")

########################################################################################################################
# after all the funtions are defined, actually execute main()
########################################################################################################################

if __name__ == '__main__':
	print("Nuthouse01 - 02/29/2020 - v3.00")
	if DEBUG:
		main()
	else:
		try:
			main()
		except (KeyboardInterrupt, SystemExit):
			# this is normal and expected, do nothing and die normally
			pass
		except Exception as ee:
			# if an unexpected error occurs, catch it and print it and call core.pause_and_quit so the window stays open for a bit
			print(ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
