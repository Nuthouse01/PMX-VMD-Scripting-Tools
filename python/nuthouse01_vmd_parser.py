# Nuthouse01 - 07/24/2020 - v4.63
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


# first, system imports
import math
import struct
from typing import List, Union

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from . import nuthouse01_core as core
	from . import nuthouse01_vmd_struct as vmdstruct
except ImportError as eee:
	try:
		import nuthouse01_core as core
		import nuthouse01_vmd_struct as vmdstruct
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = vmdstruct = None

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

# parsing progress printouts: depend on the actual number of bytes processed, very accurate & linear
# encoding progress printouts: these vars estimate how long one item of each type will take to complete (relatively)
ENCODE_FACTOR_BONE = 1
ENCODE_FACTOR_MORPH = 0.25
# dont touch these
ENCODE_PERCENT_BONE = 0
ENCODE_PERCENT_MORPH = 0



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

def parse_vmd_header(raw:bytearray, moreinfo:bool) -> vmdstruct.VmdHeader:
	############################
	# unpack the header, get file version and model name
	# version only affects the length of the model name text field, but i'll return it anyway
	try:
		header = core.my_unpack(fmt_header, raw)
	except Exception as e:
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		core.MY_PRINT_FUNC("section=header")
		core.MY_PRINT_FUNC("Err: something went wrong while parsing, file is probably corrupt/malformed")
		raise RuntimeError()
	
	if header == "Vocaloid Motion Data 0002":
		# if this matches, this is version >= 1.30
		# but i will just return "2"
		version = 2
		# model name string is 20-chars long
		useme = fmt_modelname_new
	elif header == "Vocaloid Motion Data file":
		# this is actually untested & unverified, but according to the docs this is how it's labelled
		# if this matches, this is version < 1.30
		# but i will just return "1"
		version = 1
		# model name string is 10-chars long
		useme = fmt_modelname_old
	else:
		core.MY_PRINT_FUNC("ERR: found unsupported file version identifier string, '%s'" % header)
		raise RuntimeError()
	
	try:
		modelname = core.my_unpack(useme, raw)
	except Exception as e:
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		core.MY_PRINT_FUNC("section=modelname")
		core.MY_PRINT_FUNC("Err: something went wrong while parsing, file is probably corrupt/malformed")
		raise RuntimeError()
	
	if moreinfo: core.MY_PRINT_FUNC("...model name   = JP:'%s'" % modelname)
	
	return vmdstruct.VmdHeader(version=version, modelname=modelname)

def parse_vmd_boneframe(raw:bytearray, moreinfo:bool) -> List[vmdstruct.VmdBoneFrame]:
	# get all the bone-frames, store in a list of lists
	boneframe_list = []
	# verify that there is enough file left to read a single number
	if (len(raw) - core.get_readfrom_byte()) < struct.calcsize(fmt_number):
		core.MY_PRINT_FUNC("Warning: expected boneframe_ct field but file ended unexpectedly! Assuming 0 boneframes and continuing...")
		return boneframe_list

	############################
	# get the number of bone-frames
	boneframe_ct = core.my_unpack(fmt_number, raw)
	if moreinfo: core.MY_PRINT_FUNC("...# of boneframes          = %d" % boneframe_ct)
	for z in range(boneframe_ct):
		try:
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
				core.MY_PRINT_FUNC("Warning: found unusual values where I expected to find physics enable/disable! Assuming this means physics off")
				core.MY_PRINT_FUNC(bname_str, "f=", str(f), "(phys1,phys2)=", str((phys1, phys2)))
				phys_off = True
			# store them all on the list
			# create a list to hold all the boneframe data, then append it onto the return-list
			interp_list = [x_ax, y_ax, z_ax, r_ax, x_ay, y_ay, z_ay, r_ay, x_bx, y_bx, z_bx, r_bx, x_by, y_by, z_by, r_by]
			this_boneframe = vmdstruct.VmdBoneFrame(name=bname_str,
										  f=f,
										  pos=[xp,yp,zp],
										  rot=[xrot,yrot,zrot],
										  phys_off=phys_off,
										  interp=interp_list)
			boneframe_list.append(this_boneframe)
			# display progress printouts
			core.print_progress_oneline(core.get_readfrom_byte() / len(raw))
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("frame=", z)
			core.MY_PRINT_FUNC("totalframes=", boneframe_ct)
			core.MY_PRINT_FUNC("section=boneframe")
			core.MY_PRINT_FUNC("Err: something went wrong while parsing, file is probably corrupt/malformed")
			raise RuntimeError()
	
	return boneframe_list

def parse_vmd_morphframe(raw:bytearray, moreinfo:bool) -> List[vmdstruct.VmdMorphFrame]:
	# get all the morph-frames, store in a list of lists
	morphframe_list = []
	# is there enough file left to read a single number?
	if (len(raw) - core.get_readfrom_byte()) < struct.calcsize(fmt_number):
		core.MY_PRINT_FUNC("Warning: expected morphframe_ct field but file ended unexpectedly! Assuming 0 morphframes and continuing...")
		return morphframe_list
	
	############################
	# get the number of morph frames
	morphframe_ct = core.my_unpack(fmt_number, raw)
	if moreinfo: core.MY_PRINT_FUNC("...# of morphframes         = %d" % morphframe_ct)
	for z in range(morphframe_ct):
		try:
			# unpack the morphframe
			(mname_str, f, v) = core.my_unpack(fmt_morphframe, raw)
			morphframe_list.append(vmdstruct.VmdMorphFrame(name=mname_str, f=f, val=v))
			
			# display progress printouts
			core.print_progress_oneline(core.get_readfrom_byte() / len(raw))
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("frame=", z)
			core.MY_PRINT_FUNC("totalframes=", morphframe_ct)
			core.MY_PRINT_FUNC("section=morphframe")
			core.MY_PRINT_FUNC("Err: something went wrong while parsing, file is probably corrupt/malformed")
			raise RuntimeError()
	
	return morphframe_list

def parse_vmd_camframe(raw:bytearray, moreinfo:bool) -> List[vmdstruct.VmdCamFrame]:
	camframe_list = []
	# is there enough file left to read a single number?
	if (len(raw) - core.get_readfrom_byte()) < struct.calcsize(fmt_number):
		core.MY_PRINT_FUNC("Warning: expected camframe_ct field but file ended unexpectedly! Assuming 0 camframes and continuing...")
		return camframe_list
	############################
	# get the number of cam frames
	camframe_ct = core.my_unpack(fmt_number, raw)
	if moreinfo: core.MY_PRINT_FUNC("...# of camframes           = %d" % camframe_ct)
	for z in range(camframe_ct):
		try:
			# unpack into variables
			(f, d, xp, yp, zp, xr, yr, zr,
			 x_ax, x_bx, x_ay, x_by, y_ax, y_bx, y_ay, y_by, z_ax, z_bx, z_ay, z_by, r_ax, r_bx, r_ay, r_by,
			 dist_ax, dist_bx, dist_ay, dist_by, ang_ax, ang_bx, ang_ay, ang_by,
			 fov, per) = core.my_unpack(fmt_camframe, raw)
			
			interp_list = [x_ax, x_bx, x_ay, x_by, y_ax, y_bx, y_ay, y_by, z_ax, z_bx, z_ay, z_by,
						   r_ax, r_bx, r_ay, r_by, dist_ax, dist_bx, dist_ay, dist_by, ang_ax, ang_bx, ang_ay, ang_by]
			this_camframe = vmdstruct.VmdCamFrame(f=f,
										dist=d,
										pos=[xp,yp,zp],
										rot=[math.degrees(j) for j in (xr,yr,zr)],  # angle comes in as radians, convert radians to degrees
										interp=interp_list,
										fov=fov,
										perspective=per)
			camframe_list.append(this_camframe)
			# display progress printouts
			core.print_progress_oneline(core.get_readfrom_byte() / len(raw))
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("frame=", z)
			core.MY_PRINT_FUNC("totalframes=", camframe_ct)
			core.MY_PRINT_FUNC("section=camframe")
			core.MY_PRINT_FUNC("Err: something went wrong while parsing, file is probably corrupt/malformed")
			raise RuntimeError()

	return camframe_list

def parse_vmd_lightframe(raw:bytearray, moreinfo:bool) -> List[vmdstruct.VmdLightFrame]:
	lightframe_list = []
	# is there enough file left to read a single number?
	if (len(raw) - core.get_readfrom_byte()) < struct.calcsize(fmt_number):
		core.MY_PRINT_FUNC("Warning: expected lightframe_ct field but file ended unexpectedly! Assuming 0 lightframes and continuing...")
		return lightframe_list
	############################
	# if it exists, get the number of lightframes
	lightframe_ct = core.my_unpack(fmt_number, raw)
	if moreinfo: core.MY_PRINT_FUNC("...# of lightframes         = %d" % lightframe_ct)
	for i in range(lightframe_ct):
		try:
			(f, r, g, b, x, y, z) = core.my_unpack(fmt_lightframe, raw)
			# the r g b actually come back as floats [0.0-1.0), representing (int)/256, i'll convert them back to ints
			lightframe_list.append(vmdstruct.VmdLightFrame(f=f,
												 color=[round(j*256) for j in (r,g,b)],
												 pos=[x,y,z]))
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("frame=", i)
			core.MY_PRINT_FUNC("totalframes=", lightframe_ct)
			core.MY_PRINT_FUNC("section=lightframe")
			core.MY_PRINT_FUNC("Err: something went wrong while parsing, file is probably corrupt/malformed")
			raise RuntimeError()

	return lightframe_list

def parse_vmd_shadowframe(raw:bytearray, moreinfo:bool) -> List[vmdstruct.VmdShadowFrame]:
	shadowframe_list = []
	# is there enough file left to read a single number?
	if (len(raw) - core.get_readfrom_byte()) < struct.calcsize(fmt_number):
		core.MY_PRINT_FUNC("Warning: expected shadowframe_ct field but file ended unexpectedly! Assuming 0 shadowframes and continuing...")
		return shadowframe_list

	############################
	# if it exists, get the number of shadowframes
	shadowframe_ct = core.my_unpack(fmt_number, raw)
	if moreinfo: core.MY_PRINT_FUNC("...# of shadowframes        = %d" % shadowframe_ct)
	for i in range(shadowframe_ct):
		try:
			(f, m, v) = core.my_unpack(fmt_shadowframe, raw)
			v = round(10000 - (v * 100000))
			# stored as 0.0 to 0.1 ??? why would it use this range!? also its range-inverted
			# [0,9999] -> [0.1, 0.0]
			shadowframe_list.append(vmdstruct.VmdShadowFrame(f=f, mode=m, val=v))
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("frame=", i)
			core.MY_PRINT_FUNC("totalframes=", shadowframe_ct)
			core.MY_PRINT_FUNC("section=shadowframe")
			core.MY_PRINT_FUNC("Err: something went wrong while parsing, file is probably corrupt/malformed")
			raise RuntimeError()
	return shadowframe_list

def parse_vmd_ikdispframe(raw:bytearray, moreinfo:bool) -> List[vmdstruct.VmdIkdispFrame]:
	ikdispframe_list = []
	# is there enough file left to read a single number?
	if (len(raw) - core.get_readfrom_byte()) < struct.calcsize(fmt_number):
		core.MY_PRINT_FUNC("Warning: expected ikdispframe_ct field but file ended unexpectedly! Assuming 0 ikdispframes and continuing...")
		return ikdispframe_list

	############################
	# if it exists, get the number of ikdisp frames
	ikdispframe_ct = core.my_unpack(fmt_number, raw)
	if moreinfo: core.MY_PRINT_FUNC("...# of ik/disp frames      = %d" % ikdispframe_ct)
	for i in range(ikdispframe_ct):
		try:
			(f, disp, numbones) = core.my_unpack(fmt_ikdispframe, raw)
			ikbones = []
			for j in range(numbones):
				(ikname, enable) = core.my_unpack(fmt_ikframe, raw)
				ikbones.append(vmdstruct.VmdIkbone(name=ikname, enable=enable))
			ikdispframe_list.append(vmdstruct.VmdIkdispFrame(f=f, disp=disp, ikbones=ikbones))
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("frame=",i)
			core.MY_PRINT_FUNC("totalframes=",ikdispframe_ct)
			core.MY_PRINT_FUNC("section=ikdispframe")
			core.MY_PRINT_FUNC("Err: something went wrong while parsing, file is probably corrupt/malformed")
			raise RuntimeError()
	return ikdispframe_list

########################################################################################################################
# pipeline functions for WRITING
########################################################################################################################

def encode_vmd_header(nice: vmdstruct.VmdHeader, moreinfo:bool) -> bytearray:
	output = bytearray()
	if moreinfo: core.MY_PRINT_FUNC("...model name   = JP:'%s'" % nice.modelname)
	##################################
	# header data
	# first, version: if ver==1, then use "Vocaloid Motion Data file", if ver==2, then use "Vocaloid Motion Data 0002"
	if nice.version == 2:
		writeme = ["Vocaloid Motion Data 0002", nice.modelname]
		output += core.my_pack(fmt_header + fmt_modelname_new, writeme)
	elif nice.version == 1:
		writeme = ["Vocaloid Motion Data file", nice.modelname]
		output += core.my_pack(fmt_header + fmt_modelname_old, writeme)
	else:
		core.MY_PRINT_FUNC("ERR: unsupported VMD version value", nice.version)
		raise ValueError
	
	return output

def encode_vmd_boneframe(nice:List[vmdstruct.VmdBoneFrame], moreinfo:bool) -> bytearray:
	output = bytearray()
	#############################
	# bone frames
	# first, the number of frames
	if moreinfo: core.MY_PRINT_FUNC("...# of boneframes          = %d" % len(nice))
	output += core.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	for i, frame in enumerate(nice):
		# assemble the boneframe
		# first, gotta convert from euler to quaternion!
		euler = frame.rot  # x y z
		(w, x, y, z) = core.euler_to_quaternion(euler)  # w x y z
		quat = [x, y, z, w]  # x y z w
		# then, do the part that isn't the interpolation curve (first 9 values in binary, 8 things in frame), save as frame
		try:
			# now encode/pack/append the non-interp, non-phys portion
			packme = [frame.name, frame.f, *frame.pos, *quat]
			# packme.extend(frame.pos)
			# packme.extend(quat)
			output += core.my_pack(fmt_boneframe_no_interpcurve, packme)
			# then, create one line of the interpolation curve (last 16 values of frame obj)
			interp = core.my_pack(fmt_boneframe_interpcurve_oneline, frame.interp)
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("line=", i)
			core.MY_PRINT_FUNC("section=boneframe")
			core.MY_PRINT_FUNC("Err: something went wrong while synthesizing binary output, probably the wrong type/order of values on a line")
			raise RuntimeError()
		# do the dumb copy-and-shift thing to rebuild the original 4-line structure of redundant bytes
		interp += interp[1:] + bytes(1) + interp[2:] + bytes(2) + interp[3:] + bytes(3)
		# now overwrite the odd missing bytes with physics enable/disable data
		if frame.phys_off is True:
			interp[2] = 99
			interp[3] = 15
		else:
			interp[2] = 0
			interp[3] = 0
		# append the interpolation data onto the real output
		output += interp
		# progress thing just because
		core.print_progress_oneline(ENCODE_PERCENT_BONE * i / len(nice))

	return output

def encode_vmd_morphframe(nice:List[vmdstruct.VmdMorphFrame], moreinfo:bool) -> bytearray:
	output = bytearray()
	###########################################
	# morph frames
	# first, the number of frames
	if moreinfo: core.MY_PRINT_FUNC("...# of morphframes         = %d" % len(nice))
	output += core.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	for i, frame in enumerate(nice):
		try:
			output += core.my_pack(fmt_morphframe, [frame.name, frame.f, frame.val])
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("line=", i)
			core.MY_PRINT_FUNC("section=morphframe")
			core.MY_PRINT_FUNC("Err: something went wrong while synthesizing binary output, probably the wrong type/order of values on a line")
			raise RuntimeError()

		# print a progress update every so often just because
		core.print_progress_oneline(ENCODE_PERCENT_BONE + (ENCODE_PERCENT_MORPH * i / len(nice)))
	return output

def encode_vmd_camframe(nice:List[vmdstruct.VmdCamFrame], moreinfo:bool) -> bytearray:
	output = bytearray()
	###########################################
	# cam frames
	# first, the number of frames
	if moreinfo: core.MY_PRINT_FUNC("...# of camframes           = %d" % len(nice))
	output += core.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	for i, frame in enumerate(nice):
		xyz_rads = [math.radians(j) for j in frame.rot]  # degrees to radians
		try:
			packme = [frame.f, frame.dist, *frame.pos, *xyz_rads, *frame.interp, frame.fov, frame.perspective]
			output += core.my_pack(fmt_camframe, packme)
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("line=", i)
			core.MY_PRINT_FUNC("section=camframe")
			core.MY_PRINT_FUNC("Err: something went wrong while synthesizing binary output, probably the wrong type/order of values on a line")
			raise RuntimeError()
		
		# progress thing just because
		core.print_progress_oneline(i / len(nice))
	return output

def encode_vmd_lightframe(nice:List[vmdstruct.VmdLightFrame], moreinfo:bool) -> bytearray:
	output = bytearray()
	###########################################
	# light frames
	# first, the number of frames
	if moreinfo: core.MY_PRINT_FUNC("...# of lightframes         = %d" % len(nice))
	output += core.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	for i,frame in enumerate(nice):
		# the RGB come in as ints, but are actually stored as floats... convert them back to floats for packing
		colors = [j / 256 for j in frame.color]
		try:
			output += core.my_pack(fmt_lightframe, [frame.f, *colors, *frame.pos])
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("line=", i)
			core.MY_PRINT_FUNC("section=lightframe")
			core.MY_PRINT_FUNC("Err: something went wrong while synthesizing binary output, probably the wrong type/order of values on a line")
			raise RuntimeError()
	return output

def encode_vmd_shadowframe(nice:List[vmdstruct.VmdShadowFrame], moreinfo:bool) -> bytearray:
	output = bytearray()
	###########################################
	# shadow frames
	# first, the number of frames
	if moreinfo: core.MY_PRINT_FUNC("...# of shadowframes        = %d" % len(nice))
	output += core.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	for i,frame in enumerate(nice):
		# the shadow value comes in as an int, but it actually stored as a float
		# convert it back to its natural form for packing
		val = (10000 - frame.val) / 100000
		try:
			output += core.my_pack(fmt_shadowframe, [frame.f, frame.mode, val])
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("line=", i)
			core.MY_PRINT_FUNC("section=shadowframe")
			core.MY_PRINT_FUNC("Err: something went wrong while synthesizing binary output, probably the wrong type/order of values on a line")
			raise RuntimeError()

	return output

def encode_vmd_ikdispframe(nice:List[vmdstruct.VmdIkdispFrame], moreinfo:bool) -> bytearray:
	output = bytearray()
	###########################################
	# disp/ik frames
	# first, the number of frames
	if moreinfo: core.MY_PRINT_FUNC("...# of ik/disp frames      = %d" % len(nice))
	output += core.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	for i, frame in enumerate(nice):
		try:
			# pack the first 3 args with the "ikdispframe" template
			output += core.my_pack(fmt_ikdispframe, [frame.f, frame.disp, len(frame.ikbones)])
			# for each ikbone listed in the template:
			for z in frame.ikbones:
				output += core.my_pack(fmt_ikframe, [z.name, z.enable])
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("line=", i)
			core.MY_PRINT_FUNC("section=ikdispframe")
			core.MY_PRINT_FUNC("Err: something went wrong while synthesizing binary output, probably the wrong type/order of values on a line")
			raise RuntimeError()

	return output


def parse_vmd_used_dict(frames: List[Union[vmdstruct.VmdBoneFrame, vmdstruct.VmdMorphFrame]], frametype="", moreinfo=False) -> dict:
	"""
	Generate a dictionary where keys are bones/morphs that are "actually used" and values are # of times they are used.
	"Actually used" means the first frame with a nonzero value and each frame after that. (ignore leading repeated zeros)
	
	:param frames: list of VmdBoneFrame obj or VmdMorphFrame obj
	:param frametype: str "bone" or str "morph" to indicate which kind of frames are being processed
	:param moreinfo: print extra info and stuff
	:return: dict of {name: used_ct} that only includes names of "actually used" bones/morphs
	"""
	if frametype == "bone":
		t = True
	elif frametype == "morph":
		t = False
	else:
		core.MY_PRINT_FUNC("parse_vmd_used_dict invalid mode '%s' given" % frametype)
		raise RuntimeError()
	
	bonedict = {}
	# 1, ensure frames are in sorted order
	frames_sorted = sorted(frames, key=lambda x: x.f)
	boneset = set()  # set of everything that exists, used or not
	# 2, iterate over items and count all instances except first if first has no value
	for bone in frames_sorted:
		boneset.add(bone.name)
		if bone.name not in bonedict:  # if this has not been used before,
			if t is False:
				if bone.val == 0.0:  # if it is not used now,
					continue  # do not count it.
			else:
				if list(bone.pos) == [0.0,0.0,0.0] and list(bone.rot) == [0.0,0.0,0.0]:  # if it is not used now,
					continue  # do not count it.
		core.increment_occurance_dict(bonedict, bone.name)  # if it has been used before or is used now, count it.
	# 3, if there are any "used" items then print a statement saying so
	if len(bonedict) > 0 and moreinfo:
		if t is False:
			core.MY_PRINT_FUNC("...unique morphs, used/total= %d / %d" % (len(bonedict), len(boneset)))
		else:
			core.MY_PRINT_FUNC("...unique bones, used/total = %d / %d" % (len(bonedict), len(boneset)))

	return bonedict


########################################################################################################################
# primary functions: read_vmd() and write_vmd()
########################################################################################################################

def read_vmd(vmd_filename: str, moreinfo=False) -> vmdstruct.Vmd:
	vmd_filename_clean = core.get_clean_basename(vmd_filename) + ".vmd"
	# creates object 	(header, boneframe_list, morphframe_list, camframe_list, lightframe_list, shadowframe_list, ikdispframe_list)
	# assumes the calling function already verified correct file extension
	core.MY_PRINT_FUNC("Begin reading VMD file '%s'" % vmd_filename_clean)
	vmd_bytes = core.read_binfile_to_bytes(vmd_filename)
	core.MY_PRINT_FUNC("...total size   = %sKB" % round(len(vmd_bytes) / 1024))
	core.MY_PRINT_FUNC("Begin parsing VMD file '%s'" % vmd_filename_clean)
	core.reset_unpack()
	core.set_encoding("shift_jis")
	
	# !!!! this does eliminate all the garbage data MMD used to pack strings so this isnt 100% reversable !!!
	# read the bytes object and return all the data from teh VMD broken up into a list of lists
	# also convert things from packed formats to human-readable scales
	# (quaternion to euler, radians to degrees, floats to ints, etc)
	# also generate the bonedict and morphdict
	
	core.print_progress_oneline(0)
	A = parse_vmd_header(vmd_bytes, moreinfo)
	B = parse_vmd_boneframe(vmd_bytes, moreinfo)
	C = parse_vmd_morphframe(vmd_bytes, moreinfo)
	D = parse_vmd_camframe(vmd_bytes, moreinfo)
	E = parse_vmd_lightframe(vmd_bytes, moreinfo)
	F = parse_vmd_shadowframe(vmd_bytes, moreinfo)
	G = parse_vmd_ikdispframe(vmd_bytes, moreinfo)
	if moreinfo: core.print_failed_decodes()
	
	bytes_remain = len(vmd_bytes) - core.get_readfrom_byte()
	if bytes_remain != 0:
		# padding with my SIGNATURE is acceptable, anything else is strange
		leftover = vmd_bytes[core.get_readfrom_byte():]
		if leftover == bytes(SIGNATURE, encoding="shift_jis"):
			core.MY_PRINT_FUNC("...note: this VMD file was previously modified with this tool!")
		else:
			core.MY_PRINT_FUNC("Warning: finished parsing but %d bytes are left over at the tail!" % bytes_remain)
			core.MY_PRINT_FUNC("The file may be corrupt or maybe it contains unknown/unsupported data formats")
			core.MY_PRINT_FUNC(leftover)
	
	core.MY_PRINT_FUNC("Done parsing VMD file '%s'" % vmd_filename_clean)
	
	vmd = vmdstruct.Vmd(A, B, C, D, E, F, G)
	# this is where sorting happens, if it happens
	if GUARANTEE_FRAMES_SORTED:
		# bones & morphs: primarily sorted by NAME, with FRAME# as tiebreaker. the second sort is the primary one.
		vmd.boneframes.sort(key=lambda x: x.f)  # frame#
		vmd.boneframes.sort(key=lambda x: x.name)  # name
		vmd.morphframes.sort(key=lambda x: x.f)
		vmd.morphframes.sort(key=lambda x: x.name)
		# all of these only sort by frame number.
		vmd.camframes.sort(key=lambda x: x.f)  # frame#
		vmd.lightframes.sort(key=lambda x: x.f)
		vmd.shadowframes.sort(key=lambda x: x.f)
		vmd.ikdispframes.sort(key=lambda x: x.f)
	return vmd

def write_vmd(vmd_filename: str, vmd: vmdstruct.Vmd, moreinfo=False):
	vmd_filename_clean = core.get_clean_basename(vmd_filename) + ".vmd"
	# recives object 	(header, boneframe_list, morphframe_list, camframe_list, lightframe_list, shadowframe_list, ikdispframe_list)
	# assumes the calling function already verified correct file extension
	core.MY_PRINT_FUNC("Begin encoding VMD file '%s'" % vmd_filename_clean)
	core.set_encoding("shift_jis")
	
	core.print_progress_oneline(0)
	# this is where sorting happens, if it happens
	if GUARANTEE_FRAMES_SORTED:
		# bones & morphs: primarily sorted by NAME, with FRAME# as tiebreaker. the second sort is the primary one.
		vmd.boneframes.sort(key=lambda x: x.f)  # frame#
		vmd.boneframes.sort(key=lambda x: x.name)  # name
		vmd.morphframes.sort(key=lambda x: x.f)
		vmd.morphframes.sort(key=lambda x: x.name)
		# all of these only sort by frame number.
		vmd.camframes.sort(key=lambda x: x.f)  # frame#
		vmd.lightframes.sort(key=lambda x: x.f)
		vmd.shadowframes.sort(key=lambda x: x.f)
		vmd.ikdispframes.sort(key=lambda x: x.f)
	
	global ENCODE_PERCENT_BONE
	global ENCODE_PERCENT_MORPH
	# cam is not included cuz a file contains only bone+morph OR cam
	total_bone = len(vmd.boneframes) * ENCODE_FACTOR_BONE
	total_morph = len(vmd.morphframes) * ENCODE_FACTOR_MORPH
	ALLENCODE = total_bone + total_morph
	if ALLENCODE == 0: ALLENCODE = 1  # just a bandaid to avoid zero-div error when writing empty VMD
	ENCODE_PERCENT_BONE = total_bone / ALLENCODE
	ENCODE_PERCENT_MORPH = total_morph / ALLENCODE
	
	# arg "vmd" is the same structure created by "parse_vmd()"
	# assume the object is perfect, no sanity-checking needed, it will all be done when parsing the text input
	output_bytes = bytearray()
	
	output_bytes += encode_vmd_header(vmd.header, moreinfo)
	output_bytes += encode_vmd_boneframe(vmd.boneframes, moreinfo)
	output_bytes += encode_vmd_morphframe(vmd.morphframes, moreinfo)
	output_bytes += encode_vmd_camframe(vmd.camframes, moreinfo)
	output_bytes += encode_vmd_lightframe(vmd.lightframes, moreinfo)
	output_bytes += encode_vmd_shadowframe(vmd.shadowframes, moreinfo)
	output_bytes += encode_vmd_ikdispframe(vmd.ikdispframes, moreinfo)
	
	# done encoding!!
	
	# add a cheeky little binary stamp just to prove that people actually used my tool :)
	if APPEND_SIGNATURE:
		# signature to prove that this file was created with this tool
		output_bytes += bytes(SIGNATURE, encoding="shift_jis")
	
	core.MY_PRINT_FUNC("Begin writing VMD file '%s'" % vmd_filename_clean)
	core.MY_PRINT_FUNC("...total size   = %sKB" % round(len(output_bytes) / 1024))
	core.write_bytes_to_binfile(vmd_filename, output_bytes)
	core.MY_PRINT_FUNC("Done writing VMD file '%s'" % vmd_filename_clean)
	# done with everything!
	return

########################################################################################################################
# self-test section when this file is executed
########################################################################################################################

def main():
	core.MY_PRINT_FUNC("Specify a VMD file to attempt parsing")
	core.MY_PRINT_FUNC("Because MikuMikuDance pads with garbage, but I pad with zeros, the binary file I write back will not be exactly bitwise identical")
	core.MY_PRINT_FUNC("But I can read the version I wrote and verify that the internal representation matches")
	input_filename = core.prompt_user_filename(".vmd")
	# input_filename = "vmdtest.vmd"
	Z= read_vmd(input_filename)
	write_vmd("____vmdparser_selftest_DELETEME.vmd", Z)
	ZZ = read_vmd("____vmdparser_selftest_DELETEME.vmd")
	core.MY_PRINT_FUNC("")
	bb = core.read_binfile_to_bytes(input_filename)
	bb2 = core.read_binfile_to_bytes("____vmdparser_selftest_DELETEME.vmd")
	core.MY_PRINT_FUNC("Is the binary EXACTLY identical to original?", bb == bb2)
	exact_result = Z == ZZ
	core.MY_PRINT_FUNC("Is the readback EXACTLY identical to original?", exact_result)
	if not exact_result:
		# boneframelist is different!!! but its just floating-point wibblyness caused by the quaternion transform math
		fuzzy_result = core.recursively_compare(Z, ZZ)
		core.MY_PRINT_FUNC("Is the readback ALMOST identical to the original?", not fuzzy_result)
		core.MY_PRINT_FUNC("Max difference between two floats:", core.MAXDIFFERENCE)
		core.MY_PRINT_FUNC("Number of floats that exceed reasonable threshold 0.0005:", fuzzy_result)
	core.pause_and_quit("Parsed without error")

########################################################################################################################
# after all the funtions are defined, actually execute main()
########################################################################################################################

if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 07/24/2020 - v4.63")
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
			core.MY_PRINT_FUNC(ee.__class__.__name__, ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
