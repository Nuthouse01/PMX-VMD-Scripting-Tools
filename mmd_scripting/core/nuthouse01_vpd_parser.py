import re

import mmd_scripting.core.nuthouse01_io as io
import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_vmd_struct as vmdstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.5.03 - 10/10/2020"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


########################################################################################################################
# constants & options
########################################################################################################################




################################################################
# regular expressions compiled ahead of time for efficiency
n = r"\s*([-0-9\.]+)\s*"
title_pattern = r"(.*)\.osm;"
title_re = re.compile(title_pattern)
# bone_pattern = r"Bone(\d+)\{(.*)"  # ver 1: name is everything up to end-of-line
# bone_pattern = r"Bone(\d+)\{(.*?)\s*$"  # ver 2: name is everything up to end-of-line, except trailing whitespace
bone_pattern = r"Bone(\d+)\{(.*?)\s*(//.*)?$"  # ver 3: name is everything before comment or end-of-line, except trailing whitespace
bone_re = re.compile(bone_pattern)
morph_pattern = r"Morph(\d+)\{(.*?)\s*(//.*)?$"
morph_re = re.compile(morph_pattern)
close_pattern = r"\s*\}"
close_re = re.compile(close_pattern)
f1_pattern = n + ";"
f1_re = re.compile(f1_pattern)
f3_pattern = n + "," + n + "," + n + ";"
f3_re = re.compile(f3_pattern)
f4_pattern = n + "," + n + "," + n + "," + n + ";"
f4_re = re.compile(f4_pattern)


########################################################################################################################
# primary functions: read_vpd() and write_vpd()
########################################################################################################################

def read_vpd(vpd_filepath: str, moreinfo=False) -> vmdstruct.Vmd:
	"""
	Read a VPD text file and convert it to a VMD object with all boneframes and morphframes at time=0.
	
	:param vpd_filepath: destination filepath/name, relative from CWD or absolute
	:param moreinfo: if true, get extra printouts with more info about stuff
	:return: VMD object
	"""
	cleanname = core.filepath_splitdir(vpd_filepath)[1]
	core.MY_PRINT_FUNC("Begin reading VPD file '%s'" % cleanname)
	
	# read textfile to linelist, no CSV fields to untangle here
	lines = io.read_txtfile_to_list(vpd_filepath, use_jis_encoding=True)
	
	# verify magic header "Vocaloid Pose Data file"
	if lines[0] != "Vocaloid Pose Data file":
		core.MY_PRINT_FUNC("warning: did not find expected magic header! this might not be a real VPD file!")
	# get rid of the header
	lines.pop(0)
	
	# this var is a state machine that keeps track of what I expect to find next
	# if i find anything other than blankspace or what I expect, then err & die
	parse_state = 0
	
	# save this so I know when I'm done reading all the bones the header promised
	num_bones = 0
	
	# temp vars to hold stuff from previous lines
	temp_title = "qwertyuiop"
	temp_name = "foobar"
	temp_pos = tuple()
	temp_rot = tuple()
	temp_value = 0.0
	
	# this is the VMD object that will be ultimately returned
	vmd_boneframes = []
	vmd_morphframes = []
	
	# iterate over the remaining lines until end-of-file
	for d,line in enumerate(lines):
		# vertical whitespace is always acceptable
		if not line or line.isspace(): continue
		
		# if line is not blank, it had better be something good:
		if parse_state == 0:  # 0 = model title
			m = title_re.match(line)  # regex match from beginning of line
			if m is None:
				core.MY_PRINT_FUNC("Parse err line %d state %d: failed to find model title" % (d + 2, parse_state))
				core.MY_PRINT_FUNC("line = '%s'" % line)
				raise RuntimeError()
			temp_title = m.group(1)  # if valid match, then grab the actual title
			if moreinfo: core.MY_PRINT_FUNC("...model name   = JP:'%s'" % temp_title)
			parse_state = 10  # next thing to look for is #bones
		
		elif parse_state == 10:  # 10 = #bones
			m = f1_re.match(line)  # regex match from beginning of line
			if m is None:
				core.MY_PRINT_FUNC("Parse err line %d state %d: failed to find number of bones" % (d + 2, parse_state))
				core.MY_PRINT_FUNC("line = '%s'" % line)
				raise RuntimeError()
			num_bones = int(float(m.group(1)))  # if a valid match, then grab the actual # of bones
			if moreinfo: core.MY_PRINT_FUNC("...# of boneframes          = %d" % num_bones)
			if num_bones == 0:	parse_state = 30  # if there are 0 bones then immediately begin with the morphs
			else:				parse_state = 20  # otherwise look for bones next
		
		elif parse_state == 20:  # 20 = boneA, name
			m = bone_re.match(line)  # regex match from beginning of line
			if m is None:
				core.MY_PRINT_FUNC("Parse err line %d state %d: failed to find bone name" % (d + 2, parse_state))
				core.MY_PRINT_FUNC("line = '%s'" % line)
				raise RuntimeError()
			idx, name = m.group(1,2)  # get idx and name
			temp_name = name
			# can i use idx for anything? or is it totally useless?
			parse_state = 21  # next look for quaternion rotation
		
		elif parse_state == 21:  # 21 = boneB, xyz pos
			m = f3_re.match(line)  # regex match from beginning of line
			if m is None:
				core.MY_PRINT_FUNC("Parse err line %d state %d: failed to find bone XYZ position" % (d + 2, parse_state))
				core.MY_PRINT_FUNC("line = '%s'" % line)
				raise RuntimeError()
			pos = m.group(1,2,3)  # get all 3 components
			temp_pos = [float(f) for f in pos]  # convert strings to floats
			parse_state = 22  # next look for quaternion rotation
		
		elif parse_state == 22:  # 22 = boneC, xyzw quaternion rotation
			m = f4_re.match(line)  # regex match from beginning of line
			if m is None:
				core.MY_PRINT_FUNC("Parse err line %d state %d: failed to find bone XYZW rotation" % (d + 2, parse_state))
				core.MY_PRINT_FUNC("line = '%s'" % line)
				raise RuntimeError()
			quat = m.group(1,2,3,4)  # get all 4 components
			quat = [float(f) for f in quat]  # convert strings to floats
			X,Y,Z,W = quat  # expand the quat to its XYZW components
			quat = W,X,Y,Z  # repack it in a different WXYZ order
			temp_rot = core.quaternion_to_euler(quat)  # convert quaternion to euler angles
			parse_state = 23  # next look for closing curly
		
		elif parse_state == 23:  # 23 = boneD, closing curly
			m = close_re.match(line)  # regex match from beginning of line
			if m is None:
				core.MY_PRINT_FUNC("Parse err line %d state %d: bone item not properly closed" % (d + 2, parse_state))
				core.MY_PRINT_FUNC("line = '%s'" % line)
				raise RuntimeError()
			# finish the bone-obj and add to VMD structure
			# this_boneframe = [bname_str, f, xp, yp, zp, xrot, yrot, zrot, phys_off, x_ax, y_ax, z_ax, r_ax, x_ay, y_ay,
			# 				  z_ay, r_ay, x_bx, y_bx, z_bx, r_bx, x_by, y_by, z_by, r_by]
			newframe = vmdstruct.VmdBoneFrame(
				name=temp_name, f=0, pos=temp_pos, rot=list(temp_rot), phys_off=False,
			)
			vmd_boneframes.append(newframe)
			if len(vmd_boneframes) == num_bones:	parse_state = 30  # if i got all the bones i expected, move to morphs
			else:									parse_state = 20  # otherwise, get another bone
		
		elif parse_state == 30:  # 30 = morphA, name
			m = morph_re.match(line)  # regex match from beginning of line
			if m is None:
				core.MY_PRINT_FUNC("Parse err line %d state %d: failed to find morph name" % (d + 2, parse_state))
				core.MY_PRINT_FUNC("line = '%s'" % line)
				raise RuntimeError()
			idx, name = m.group(1,2)  # get idx and name
			temp_name = name
			# can i use idx for anything? or is it totally useless?
			parse_state = 31  # next look for value
		
		elif parse_state == 31:  # 31 = morphB, value
			m = f1_re.match(line)  # regex match from beginning of line
			if m is None:
				core.MY_PRINT_FUNC("Parse err line %d state %d: failed to find morph value" % (d + 2, parse_state))
				core.MY_PRINT_FUNC("line = '%s'" % line)
				raise RuntimeError()
			v = m.group(1)  # get value
			temp_value = float(v)  # convert strings to floats
			parse_state = 32  # next look for close
		
		elif parse_state == 32:  # 32 = morphC, closing curly
			m = close_re.match(line)  # regex match from beginning of line
			if m is None:
				core.MY_PRINT_FUNC("Parse err line %d state %d: morph item not properly closed" % (d + 2, parse_state))
				core.MY_PRINT_FUNC("line = '%s'" % line)
				raise RuntimeError()
			# finish the morph-obj and add to VMD structure
			# morphframe_list.append([mname_str, f, v])
			newframe = vmdstruct.VmdMorphFrame(name=temp_name, f=0, val=temp_value)
			vmd_morphframes.append(newframe)
			parse_state = 30  # loop morphs until end-of-file
		
		else:
			core.MY_PRINT_FUNC("this should not happen, err & die")
			raise RuntimeError()
	
	if moreinfo: core.MY_PRINT_FUNC("...# of morphframes         = %d" % len(vmd_morphframes))

	# verify we did not hit end-of-file unexpectedly, looking-for-morphA is only valid ending state
	if parse_state != 30:
		core.MY_PRINT_FUNC("Parse err state %d: hit end-of-file unexpectedly" % parse_state)
		raise RuntimeError()
	
	# after hitting end-of-file, assemble the parts of the final returnable VMD-list thing
	# builds object 	(header, boneframe_list, morphframe_list, camframe_list, lightframe_list, shadowframe_list, ikdispframe_list)
	vmd_retme = vmdstruct.Vmd(
		vmdstruct.VmdHeader(version=2, modelname=temp_title),
		vmd_boneframes,
		vmd_morphframes,
		list(), list(), list(), list())
	
	core.MY_PRINT_FUNC("Done reading VPD file '%s'" % cleanname)
	
	return vmd_retme

def write_vpd(vpd_filepath: str, vmd: vmdstruct.Vmd, moreinfo=False):
	"""
	Grab all bone/morph frames at time=0 in a VMD object and write them to a properly-formatted VPD text file.
	
	:param vpd_filepath: destination filepath/name, relative from CWD or absolute
	:param vmd: input VMD object
	:param moreinfo: if true, get extra printouts with more info about stuff
	"""
	cleanname = core.filepath_splitdir(vpd_filepath)[1]
	core.MY_PRINT_FUNC("Begin writing VPD file '%s'" % cleanname)

	# first, lets partition boneframes & morphframes into those at/notat time=0
	pose_bones, otherbones = core.my_list_partition(vmd.boneframes, lambda b: b.f == 0)
	pose_morphs, othermorphs = core.my_list_partition(vmd.morphframes, lambda b: b.f == 0)
	
	# if there are frames not on time=0, raise a warning but continue
	if otherbones or othermorphs:
		core.MY_PRINT_FUNC("Warning: input VMD contains %d frames not at time=0, these will not be captured in the resulting pose!" % (len(otherbones) + len(othermorphs)))
	
	if moreinfo: core.MY_PRINT_FUNC("...model name   = JP:'%s'" % vmd.header.modelname)
	# init printlist with magic header, title, and numbones
	printlist = ["Vocaloid Pose Data file",
				 "",
				 "{:s}.osm;".format(vmd.header.modelname),
				 "{:d};".format(len(pose_bones)),
				 "",]
	
	# now iterate over all bones
	# bone-floats always have exactly 6 digits
	if moreinfo: core.MY_PRINT_FUNC("...# of boneframes          = %d" % len(pose_bones))
	for d, pb in enumerate(pose_bones):
		quat = core.euler_to_quaternion(pb.rot)  # returns quat WXYZ
		W,X,Y,Z = quat  # expand the quat to its WXYZ components
		quat = X,Y,Z,W  # repack it in a different XYZW order
		newitem = ["Bone{:d}{{{:s}".format(d, pb.name),
				   "  {:.6f},{:.6f},{:.6f};".format(*pb.pos),
				   "  {:.6f},{:.6f},{:.6f},{:.6f};".format(*quat),
				   "}",
				   "",]
		printlist.extend(newitem)
	
	# now iterate over all morphs
	# morph-floats are flexible, need to TEST how long they can be!
	# lets say max precision is 3, but strip any trailing zeros and reduce "1." to "1"
	if moreinfo: core.MY_PRINT_FUNC("...# of morphframes         = %d" % len(pose_morphs))
	for d, pm in enumerate(pose_morphs):
		newitem = ["Morph{:d}{{{:s}".format(d, pm.name),
				   "  {:.3f}".format(pm.val).rstrip("0").rstrip(".") + ";",
				   "}",
				   ""]
		printlist.extend(newitem)
	
	# ok, now i'm done building the printlist! now actually write it!
	io.write_list_to_txtfile(vpd_filepath, printlist, use_jis_encoding=True)
	core.MY_PRINT_FUNC("Done writing VPD file '%s'" % cleanname)

	return None


########################################################################################################################
# self-test section when this file is executed
########################################################################################################################

def main():
	core.MY_PRINT_FUNC("Specify a vpd file to attempt parsing")
	input_filename = core.prompt_user_filename("VPD file", ".vpd")
	# input_filename = "vpdtest.vpd"
	Z= read_vpd(input_filename)
	write_vpd("____vpdparser_selftest_DELETEME.vpd", Z)
	ZZ = read_vpd("____vpdparser_selftest_DELETEME.vpd")
	core.MY_PRINT_FUNC("")
	bb = io.read_binfile_to_bytes(input_filename)
	bb2 = io.read_binfile_to_bytes("____vpdparser_selftest_DELETEME.vpd")
	# now compare bb (original binary) with bb2 (read-write)
	# now compare Z (first read) wtih ZZ (read-write-read)
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
