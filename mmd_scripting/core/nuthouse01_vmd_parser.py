import math
import struct
import time
from typing import List

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_io as io
import mmd_scripting.core.nuthouse01_packer as pack
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


########################################################################################################################
# constants & options
########################################################################################################################



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
fmt_number = "I"
fmt_boneframe_no_interpcurve = "I 7f"
fmt_boneframe_interpcurve = "bb bb 12b xbb 45x"
fmt_boneframe_interpcurve_oneline = "16b"
fmt_morphframe = "I f"
fmt_camframe = "I 7f 24b I ?"
fmt_lightframe = "I 3f 3f"
fmt_shadowframe = "I b f"
fmt_ikdispframe = "I ? I"
fmt_ikframe = "?"



########################################################################################################################
# pipeline functions for READING
########################################################################################################################

def parse_vmd_header(raw:bytearray, moreinfo:bool) -> vmdstruct.VmdHeader:
	############################
	# unpack the header, get file version and model name
	# version only affects the length of the model name text field, but i'll return it anyway
	try:
		header = pack.my_string_unpack(raw, L=30)
	except Exception as e:
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		core.MY_PRINT_FUNC("section=header")
		core.MY_PRINT_FUNC("Err: something went wrong while parsing, file is probably corrupt/malformed")
		raise
	
	if header == "Vocaloid Motion Data 0002":
		# if this matches, this is version >= 1.30
		# but i will just return "2"
		version = 2
		# model name string is 20-chars long
		namelength = 20
	elif header == "Vocaloid Motion Data file":
		# this is actually untested & unverified, but according to the docs this is how it's labelled
		# if this matches, this is version < 1.30
		# but i will just return "1"
		version = 1
		# model name string is 10-chars long
		namelength = 10
	else:
		raise RuntimeError("ERR: found unsupported file version identifier string, '%s'" % header)
	
	try:
		modelname = pack.my_string_unpack(raw, L=namelength)
	except Exception as e:
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		core.MY_PRINT_FUNC("section=modelname")
		core.MY_PRINT_FUNC("Err: something went wrong while parsing, file is probably corrupt/malformed")
		raise
	
	if moreinfo: core.MY_PRINT_FUNC("...model name   = JP:'%s'" % modelname)
	
	return vmdstruct.VmdHeader(version=version, modelname=modelname)

def parse_vmd_boneframe(raw:bytearray, moreinfo:bool) -> List[vmdstruct.VmdBoneFrame]:
	# get all the bone-frames, store in a list of lists
	boneframe_list = []
	# verify that there is enough file left to read a single number
	if (len(raw) - pack.UNPACKER_READFROM_BYTE) < struct.calcsize(fmt_number):
		core.MY_PRINT_FUNC("Warning: expected boneframe_ct field but file ended unexpectedly! Assuming 0 boneframes and continuing...")
		return boneframe_list

	############################
	# get the number of bone-frames
	boneframe_ct = pack.my_unpack(fmt_number, raw)
	if moreinfo: core.MY_PRINT_FUNC("...# of boneframes          = %d" % boneframe_ct)
	for z in range(boneframe_ct):
		try:
			# unpack the bone-frame into variables
			bname_str = pack.my_string_unpack(raw, L=15)
			(f, xp, yp, zp, xrot_q, yrot_q, zrot_q, wrot_q) = pack.my_unpack(fmt_boneframe_no_interpcurve, raw)
			# break inter_curve into its individual pieces, knowing that the 3rd and 4th bytes in line1 are overwritten with phys
			# therefore we need to get their data from line2 which is left-shifted by 1 byte, but otherwise a copy
			(x_ax, y_ax, phys1, phys2, x_ay, y_ay, z_ay, r_ay, x_bx, y_bx, z_bx, r_bx, x_by, y_by, z_by, r_by,
			 z_ax, r_ax) = pack.my_unpack(fmt_boneframe_interpcurve, raw)
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
			# create the boneframe object
			this_boneframe = vmdstruct.VmdBoneFrame(
				name=bname_str, f=f, pos=[xp,yp,zp], rot=[xrot,yrot,zrot], phys_off=phys_off, 
				interp_x=[x_ax, x_ay, x_bx, x_by],
				interp_y=[y_ax, y_ay, y_bx, y_by],
				interp_z=[z_ax, z_ay, z_bx, z_by],
				interp_r=[r_ax, r_ay, r_bx, r_by],
			)
			boneframe_list.append(this_boneframe)
			# display progress printouts
			core.print_progress_oneline(pack.UNPACKER_READFROM_BYTE / len(raw))
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("frame=", z)
			core.MY_PRINT_FUNC("totalframes=", boneframe_ct)
			core.MY_PRINT_FUNC("section=boneframe")
			core.MY_PRINT_FUNC("Err: something went wrong while parsing, file is probably corrupt/malformed")
			raise
	
	return boneframe_list

def parse_vmd_morphframe(raw:bytearray, moreinfo:bool) -> List[vmdstruct.VmdMorphFrame]:
	# get all the morph-frames, store in a list of lists
	morphframe_list = []
	# is there enough file left to read a single number?
	if (len(raw) - pack.UNPACKER_READFROM_BYTE) < struct.calcsize(fmt_number):
		core.MY_PRINT_FUNC("Warning: expected morphframe_ct field but file ended unexpectedly! Assuming 0 morphframes and continuing...")
		return morphframe_list
	
	############################
	# get the number of morph frames
	morphframe_ct = pack.my_unpack(fmt_number, raw)
	if moreinfo: core.MY_PRINT_FUNC("...# of morphframes         = %d" % morphframe_ct)
	for z in range(morphframe_ct):
		try:
			# unpack the morphframe
			mname_str = pack.my_string_unpack(raw, L=15)
			(f, v) = pack.my_unpack(fmt_morphframe, raw)
			morphframe_list.append(vmdstruct.VmdMorphFrame(name=mname_str, f=f, val=v))
			
			# display progress printouts
			core.print_progress_oneline(pack.UNPACKER_READFROM_BYTE / len(raw))
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
	if (len(raw) - pack.UNPACKER_READFROM_BYTE) < struct.calcsize(fmt_number):
		core.MY_PRINT_FUNC("Warning: expected camframe_ct field but file ended unexpectedly! Assuming 0 camframes and continuing...")
		return camframe_list
	############################
	# get the number of cam frames
	camframe_ct = pack.my_unpack(fmt_number, raw)
	if moreinfo: core.MY_PRINT_FUNC("...# of camframes           = %d" % camframe_ct)
	for z in range(camframe_ct):
		try:
			# unpack into variables
			(f, d, xp, yp, zp, xr, yr, zr,
			 x_ax, x_bx, x_ay, x_by, y_ax, y_bx, y_ay, y_by, z_ax, z_bx, z_ay, z_by, r_ax, r_bx, r_ay, r_by,
			 dist_ax, dist_bx, dist_ay, dist_by, ang_ax, ang_bx, ang_ay, ang_by,
			 fov, per) = pack.my_unpack(fmt_camframe, raw)
			
			rot_degrees = [math.degrees(j) for j in (xr,yr,zr)]  # angle comes in as radians, convert radians to degrees
			this_camframe = vmdstruct.VmdCamFrame(f=f,
												  dist=d,
												  pos=[xp,yp,zp],
												  rot=rot_degrees,
												  fov=fov,
												  perspective=per,
												  interp_x=[x_ax, x_ay, x_bx, x_by],
												  interp_y=[y_ax, y_ay, y_bx, y_by],
												  interp_z=[z_ax, z_ay, z_bx, z_by],
												  interp_r=[r_ax, r_ay, r_bx, r_by],
												  interp_dist=[dist_ax, dist_ay, dist_bx, dist_by],
												  interp_fov=[ang_ax, ang_ay, ang_bx, ang_by],
												  )
			camframe_list.append(this_camframe)
			# display progress printouts
			core.print_progress_oneline(pack.UNPACKER_READFROM_BYTE / len(raw))
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
	if (len(raw) - pack.UNPACKER_READFROM_BYTE) < struct.calcsize(fmt_number):
		core.MY_PRINT_FUNC("Warning: expected lightframe_ct field but file ended unexpectedly! Assuming 0 lightframes and continuing...")
		return lightframe_list
	############################
	# if it exists, get the number of lightframes
	lightframe_ct = pack.my_unpack(fmt_number, raw)
	if moreinfo: core.MY_PRINT_FUNC("...# of lightframes         = %d" % lightframe_ct)
	for i in range(lightframe_ct):
		try:
			(f, r, g, b, x, y, z) = pack.my_unpack(fmt_lightframe, raw)
			# the r g b actually come back as floats [0.0 - 1.0]
			lightframe_list.append(vmdstruct.VmdLightFrame(f=f,
												 color=[r,g,b],
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
	if (len(raw) - pack.UNPACKER_READFROM_BYTE) < struct.calcsize(fmt_number):
		core.MY_PRINT_FUNC("Warning: expected shadowframe_ct field but file ended unexpectedly! Assuming 0 shadowframes and continuing...")
		return shadowframe_list

	############################
	# if it exists, get the number of shadowframes
	shadowframe_ct = pack.my_unpack(fmt_number, raw)
	if moreinfo: core.MY_PRINT_FUNC("...# of shadowframes        = %d" % shadowframe_ct)
	for i in range(shadowframe_ct):
		try:
			(f, m, v) = pack.my_unpack(fmt_shadowframe, raw)
			v = round(10000 - (v * 100000))
			# stored as 0.0 to 0.1 ??? why would it use this range!? also its range-inverted
			# [0,9999] -> [0.1, 0.0]
			shadowmode = vmdstruct.ShadowMode(m)
			shadowframe_list.append(vmdstruct.VmdShadowFrame(f=f, mode=shadowmode, val=v))
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
	if (len(raw) - pack.UNPACKER_READFROM_BYTE) < struct.calcsize(fmt_number):
		core.MY_PRINT_FUNC("Warning: expected ikdispframe_ct field but file ended unexpectedly! Assuming 0 ikdispframes and continuing...")
		return ikdispframe_list

	############################
	# if it exists, get the number of ikdisp frames
	ikdispframe_ct = pack.my_unpack(fmt_number, raw)
	if moreinfo: core.MY_PRINT_FUNC("...# of ik/disp frames      = %d" % ikdispframe_ct)
	for i in range(ikdispframe_ct):
		try:
			(f, disp, numbones) = pack.my_unpack(fmt_ikdispframe, raw)
			ikbones = []
			for j in range(numbones):
				ikname_str = pack.my_string_unpack(raw, L=20)
				enable = pack.my_unpack(fmt_ikframe, raw)
				ikbones.append(vmdstruct.VmdIkbone(name=ikname_str, enable=enable))
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
		output += pack.my_string_pack("Vocaloid Motion Data 0002", L=30)
		output += pack.my_string_pack(nice.modelname, L=20)
	elif nice.version == 1:
		output += pack.my_string_pack("Vocaloid Motion Data file", L=30)
		output += pack.my_string_pack(nice.modelname, L=10)
	else:
		raise RuntimeError("ERR: unsupported VMD version value", nice.version)
	
	return output

def encode_vmd_boneframe(nice:List[vmdstruct.VmdBoneFrame], moreinfo:bool) -> bytearray:
	output = bytearray()
	#############################
	# bone frames
	# first, the number of frames
	if moreinfo: core.MY_PRINT_FUNC("...# of boneframes          = %d" % len(nice))
	output += pack.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	for i, frame in enumerate(nice):
		# assemble the boneframe
		# gotta convert from euler to quaternion!
		quat = core.euler_to_quaternion(frame.rot)  # w x y z
		W, X, Y, Z = quat  # expand the quat to its WXYZ components
		quat = X, Y, Z, W  # repack it in a different XYZW order
		
		# then, organize the interpolation curve data into one line
		x_ax, x_ay, x_bx, x_by = frame.interp_x
		y_ax, y_ay, y_bx, y_by = frame.interp_y
		z_ax, z_ay, z_bx, z_by = frame.interp_z
		r_ax, r_ay, r_bx, r_by = frame.interp_r
		interp_list = x_ax, y_ax, z_ax, r_ax, x_ay, y_ay, z_ay, r_ay, x_bx, y_bx, z_bx, r_bx, x_by, y_by, z_by, r_by
		
		try:
			output += pack.my_string_pack(frame.name, L=15)
			# now encode/pack/append the non-interp, non-phys portion
			output += pack.my_pack(fmt_boneframe_no_interpcurve, [frame.f, *frame.pos, *quat])
			# pack this one line of interpolation data, DO NOT APPEND ONTO OUTPUT YET!
			interp = pack.my_pack(fmt_boneframe_interpcurve_oneline, interp_list)
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("line=", i)
			core.MY_PRINT_FUNC("section=boneframe")
			core.MY_PRINT_FUNC("Err: something went wrong while synthesizing binary output, probably the wrong type/order of values on a line")
			raise
		# do the dumb copy-and-shift thing to rebuild the original 4-line structure of redundant bytes
		interp += interp[1:] + bytes(1) + \
				  interp[2:] + bytes(2) + \
				  interp[3:] + bytes(3)
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
	output += pack.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	for i, frame in enumerate(nice):
		try:
			output += pack.my_string_pack(frame.name, L=15)
			output += pack.my_pack(fmt_morphframe, [frame.f, frame.val])
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("line=", i)
			core.MY_PRINT_FUNC("section=morphframe")
			core.MY_PRINT_FUNC("Err: something went wrong while synthesizing binary output, probably the wrong type/order of values on a line")
			raise

		# print a progress update every so often just because
		core.print_progress_oneline(ENCODE_PERCENT_BONE + (ENCODE_PERCENT_MORPH * i / len(nice)))
	return output

def encode_vmd_camframe(nice:List[vmdstruct.VmdCamFrame], moreinfo:bool) -> bytearray:
	output = bytearray()
	###########################################
	# cam frames
	# first, the number of frames
	if moreinfo: core.MY_PRINT_FUNC("...# of camframes           = %d" % len(nice))
	output += pack.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	for i, frame in enumerate(nice):
		xyz_rads = [math.radians(j) for j in frame.rot]  # degrees to radians
		# unpack all the interp lists to named fields
		x_ax, x_ay, x_bx, x_by = frame.interp_x
		y_ax, y_ay, y_bx, y_by = frame.interp_y
		z_ax, z_ay, z_bx, z_by = frame.interp_z
		r_ax, r_ay, r_bx, r_by = frame.interp_r
		dist_ax, dist_ay, dist_bx, dist_by = frame.interp_dist
		fov_ax, fov_ay, fov_bx, fov_by = frame.interp_fov
		# reassemble them in a very specific order
		interp_list = [x_ax, x_bx, x_ay, x_by,
					   y_ax, y_bx, y_ay, y_by,
					   z_ax, z_bx, z_ay, z_by,
					   r_ax, r_bx, r_ay, r_by,
					   dist_ax, dist_bx, dist_ay, dist_by,
					   fov_ax, fov_bx, fov_ay, fov_by]
		try:
			packme = [frame.f, frame.dist, *frame.pos, *xyz_rads, *interp_list, frame.fov, frame.perspective]
			output += pack.my_pack(fmt_camframe, packme)
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
	output += pack.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	for i,frame in enumerate(nice):
		try:
			output += pack.my_pack(fmt_lightframe, [frame.f, *frame.color, *frame.pos])
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
	output += pack.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	for i,frame in enumerate(nice):
		# the shadow value comes in as an int, but it actually stored as a float
		# convert it back to its natural form for packing
		val = (10000 - frame.val) / 100000
		try:
			output += pack.my_pack(fmt_shadowframe, [frame.f, frame.mode.value, val])
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
	output += pack.my_pack(fmt_number, len(nice))
	# then, all the actual frames
	for i, frame in enumerate(nice):
		try:
			# pack the first 3 args with the "ikdispframe" template
			output += pack.my_pack(fmt_ikdispframe, [frame.f, frame.disp, len(frame.ikbones)])
			# for each ikbone listed in the template:
			for z in frame.ikbones:
				output += pack.my_string_pack(z.name, L=20)
				output += pack.my_pack(fmt_ikframe, z.enable)
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("line=", i)
			core.MY_PRINT_FUNC("section=ikdispframe")
			core.MY_PRINT_FUNC("Err: something went wrong while synthesizing binary output, probably the wrong type/order of values on a line")
			raise

	return output



########################################################################################################################
# primary functions: read_vmd() and write_vmd()
########################################################################################################################

def read_vmd(vmd_filename: str, moreinfo=False) -> vmdstruct.Vmd:
	vmd_filename_clean = core.filepath_splitdir(vmd_filename)[1]
	# creates object 	(header, boneframe_list, morphframe_list, camframe_list, lightframe_list, shadowframe_list, ikdispframe_list)
	# assumes the calling function already verified correct file extension
	core.MY_PRINT_FUNC("Begin reading VMD file '%s'" % vmd_filename_clean)
	vmd_bytes = io.read_binfile_to_bytes(vmd_filename)
	core.MY_PRINT_FUNC("...total size   = %s" % core.prettyprint_file_size(len(vmd_bytes)))
	core.MY_PRINT_FUNC("Begin parsing VMD file '%s'" % vmd_filename_clean)
	pack.reset_unpack()
	pack.set_encoding("shift_jis")
	
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
	if moreinfo: pack.print_failed_decodes()
	
	bytes_remain = len(vmd_bytes) - pack.UNPACKER_READFROM_BYTE
	if bytes_remain != 0:
		# padding with my SIGNATURE is acceptable, anything else is strange
		leftover = vmd_bytes[pack.UNPACKER_READFROM_BYTE:]
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
	vmd_filename_clean = core.filepath_splitdir(vmd_filename)[1]
	# recives object 	(header, boneframe_list, morphframe_list, camframe_list, lightframe_list, shadowframe_list, ikdispframe_list)
	
	# first, verify that the data is valid before trying to write
	vmd.validate()
	
	# assumes the calling function already verified correct file extension
	core.MY_PRINT_FUNC("Begin encoding VMD file '%s'" % vmd_filename_clean)
	pack.set_encoding("shift_jis")
	
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
	core.MY_PRINT_FUNC("...total size   = %s" % core.prettyprint_file_size(len(output_bytes)))
	io.write_bytes_to_binfile(vmd_filename, output_bytes)
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
	
	TEMPNAME = "____vmdparser_selftest_DELETEME.vmd"
	input_filename = core.MY_FILEPROMPT_FUNC("VMD file", ".vmd")
	# input_filename = "vmdtest.vmd"
	Z= read_vmd(input_filename)
	write_vmd(TEMPNAME, Z)
	ZZ = read_vmd(TEMPNAME)
	bb = io.read_binfile_to_bytes(input_filename)
	bb2 = io.read_binfile_to_bytes(TEMPNAME)
	core.MY_PRINT_FUNC("")
	core.MY_PRINT_FUNC("TIMING TEST:")
	readtime = []
	writetime = []
	for i in range(10):
		core.MY_PRINT_FUNC(i)
		start = time.time()
		_ = read_vmd(input_filename)
		end = time.time()
		readtime.append(end - start)
	for i in range(10):
		core.MY_PRINT_FUNC(i)
		start = time.time()
		write_vmd(TEMPNAME, Z)
		end = time.time()
		writetime.append(end - start)
	core.MY_PRINT_FUNC("TIMING TEST RESULTS:", input_filename)
	core.MY_PRINT_FUNC("READ")
	core.MY_PRINT_FUNC("Avg = %f, min = %f, max = %f" % (sum(readtime)/len(readtime), min(readtime), max(readtime)))
	core.MY_PRINT_FUNC("WRITE")
	core.MY_PRINT_FUNC("Avg = %f, min = %f, max = %f" % (sum(writetime)/len(writetime), min(writetime), max(writetime)))
	core.MY_PRINT_FUNC("")
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
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.RUN_WITH_TRACEBACK(main)
