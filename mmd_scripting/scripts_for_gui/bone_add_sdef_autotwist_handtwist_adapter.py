from typing import List

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.core.nuthouse01_pmx_utils import insert_single_bone

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.01 - 7/12/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
# Special thanks to Tamo for coming up with this idea! I saw his models using it and found a way to copy the technique
# onto other models.
#####################


helptext = '''=================================================
bone_add_sdef_autotwist_handtwist_adapter:
This script is designed to work with models that already have SDEF-based automatic-arm-twist rigging.
The most common SDEF autotwist setup I've seen does not account for "wrist pinching". Ideally twisting motion on the wrist should be distributed from the wrist to the elbow.
This script will add some extra bones that will fix the wrist pinching problem!

If the existing armtwist rig is bad, then the results from using this script will also be bad. To re-make the armtwist rig, you can merge all existing armtwist bones into the arm bone and use the "semistandard bones" PMXE plugin to try and rebuild it. Or, you can try using [TODO SDEF SCRIPT NAME HERE] to use a fancy SDEF weights method.

I don't know how this script will interact with hand-IK rigs.

Output: model PMX file '[modelname]_sdefhandtwist.pmx'
'''



# left and right prefixes
jp_l =    "左"
jp_r =    "右"
# names for relevant bones
jp_arm =		"腕" # "arm"
jp_armtwist =	"腕捩" # "arm twist"
jp_elbow =		"ひじ" # "elbow"
jp_wristtwist = "手捩" # "wrist twist"
jp_wrist =		"手首" # "wrist"

# parameters
ik_numloops = 100
ik_angle = 5  # degrees

ikD_lim_min = None
ikD_lim_max = None
# ikD_lim_min = [0, -180, -180]
# ikD_lim_max = [0, 180, 180]

# dances/frames where the autotwist makes a visible difference:
# conqueror 513 R wrist
# conqueror 2293 R wrist
# pink cat 334 R wrist
# pink cat 1155 R wrist


def transfer_to_armtwist_sub(pmx: pmxstruct.Pmx, from_bone:int, to_bone:int) -> bool:
	"""
	Transfer everything that refers to "from_bone" to refer to "to_bone" instead!
	Only looks at vertex weight and rigid bodies.
	:param pmx: full PMX object
	:param from_bone: int index of bone to be found
	:param to_bone: int index of bone to replace with
	:return:
	"""
	# any weights currently set to "from_bone" get replaced with "to_bone"
	# i don't care what the weight type is i just find-and-replace
	did_anything_change = False
	for v in pmx.verts:
		for pair in v.weight:
			if pair[0] == from_bone:
				pair[0] = to_bone
				did_anything_change = True
	# move all rigidbodies attached to "from_bone" to "to_bone" instead
	for rb in pmx.rigidbodies:
		if rb.bone_idx == from_bone:
			rb.bone_idx = to_bone
			did_anything_change = True
	return did_anything_change


def make_handtwist_addon(pmx: pmxstruct.Pmx, side:str, currbone_name:str):

	# find the hand
	wrist = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + jp_wrist), getitem=True)
	wrist_idx = wrist.idx_within(pmx.bones)
	# find the elbow
	elbow = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + jp_elbow), getitem=True)
	elbow_idx = elbow.idx_within(pmx.bones)

	# i am creating 3 bones that hold the twist component of the lowerarm motion
	name_handtwist =     side + "/手+ひじ捩"
	name_handtwist_end = side + "/手+ひじ捩先"
	name_handtwist_ik =  side + "/手+ひじ捩IK"
	
	base_deform = max(wrist.deform_layer, elbow.deform_layer)
	
	deform_offset = base_deform + 2
	
	# handtwist: pos = hand, parent = hand, tail = name_end, holds all the responsibilities of currbone_name, inserted after hand
	# replace the -99 after the bone is inserted
	handtwist = pmxstruct.PmxBone(
		name_jp=name_handtwist,
		name_en="",
		pos=wrist.pos, parent_idx=wrist_idx, deform_layer=deform_offset, deform_after_phys=False,
		has_rotate=False, has_translate=False, has_visible=False, has_enabled=False, has_ik=False,
		tail_usebonelink=True, tail=-99, inherit_rot=False, inherit_trans=False,
		has_fixedaxis=False, has_localaxis=False, has_externalparent=False,
	)
	# handtwist_end: pos = elbow, parent = handtwist, tail = none
	handtwist_end = pmxstruct.PmxBone(
		name_jp=name_handtwist_end,
		name_en="",
		pos=elbow.pos, parent_idx=-99, deform_layer=deform_offset, deform_after_phys=False,
		has_rotate=False, has_translate=False, has_visible=False, has_enabled=False, has_ik=False,
		tail_usebonelink=True, tail=-1, inherit_rot=False, inherit_trans=False,
		has_fixedaxis=False, has_localaxis=False, has_externalparent=False,
	)
	# handtwist_ik: pos = elbow, parent = elbow,
	handtwist_ik = pmxstruct.PmxBone(
		name_jp=name_handtwist_ik,
		name_en="",
		pos=elbow.pos, parent_idx=elbow_idx, deform_layer=deform_offset, deform_after_phys=False,
		has_rotate=False, has_translate=False, has_visible=False, has_enabled=False, has_ik=True,
		tail_usebonelink=True, tail=-1, inherit_rot=False, inherit_trans=False,
		has_fixedaxis=False, has_localaxis=False, has_externalparent=False,
		ik_target_idx=-99, ik_numloops=ik_numloops, ik_angle=ik_angle,
		ik_links=[pmxstruct.PmxBoneIkLink(idx=-99, limit_min=ikD_lim_min, limit_max=ikD_lim_max)]
	)
	
	# now insert these 3 bones into the bonelist
	handtwist_idx =     wrist_idx + 1
	handtwist_end_idx = wrist_idx + 2
	handtwist_ik_idx =  wrist_idx + 3
	insert_single_bone(pmx, handtwist, handtwist_idx)
	insert_single_bone(pmx, handtwist_end, handtwist_end_idx)
	insert_single_bone(pmx, handtwist_ik, handtwist_ik_idx)
	# now repair where they reference eachother
	handtwist.tail =               handtwist_end_idx
	handtwist_end.parent_idx =     handtwist_idx
	handtwist_ik.ik_target_idx =   handtwist_end_idx
	handtwist_ik.ik_links[0].idx = handtwist_idx
	
	
	
	# now transfer all the weights on currbone onto handtwist!
	# find the wristtwist, aka the bone that currently has the lower-lower-arm weight
	currbone = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + currbone_name), getitem=True)
	currbone_idx = currbone.idx_within(pmx.bones)
	# do the transfer
	transfer_to_armtwist_sub(pmx, currbone_idx, handtwist_idx)
	
	# thats it, now i'm done
	return None



# function that takes a string & returns INDEX if it can match one, or None otherwise
def get_item_from_string(s: str, pmxlist: List):
	# search JP names first
	t = core.my_list_search(pmxlist, lambda x: x.name_jp.lower() == s.lower(), getitem=True)
	if t is not None: return t
	# search EN names next
	t = core.my_list_search(pmxlist, lambda x: x.name_en.lower() == s.lower(), getitem=True)
	if t is not None: return t
	# try to cast to int next
	try:
		t = int(s)
		if 0 <= t < len(pmxlist):
			return pmxlist[t]
		else:
			core.MY_PRINT_FUNC("valid indexes are [0-'%d']" % (len(pmxlist) - 1))
			return None
	except ValueError:
		core.MY_PRINT_FUNC("unable to find matching item for input '%s'" % s)
		return None


def main(moreinfo=True):
	# 1, load the pmx
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	# 2, ask which bone holds the weight for the lower part of the lowerarm segment
	def valid_input_check(x: str) -> bool:
		# if input is empty that counts as valid cuz that's the "ok now go do it" signal
		if x == "": return True
		# is x a valid identifier?
		B = get_item_from_string(x, pmx.bones)
		if B is None:
			return False
		return True
	
	s = core.MY_GENERAL_INPUT_FUNC(valid_input_check,
								   ["Which bone holds the weight on the LOWER SECTION (near the wrist) of the RIGHT LOWER ARM segment?",
									"This is probably '右手捩'/'wrist twist_R' but I need to ask just in case.",
									"A bone can be specified by JP name, EN name, or index #.",])
	# if the input is empty string, then we break and begin executing with current args
	if s == "" or s is None:
		core.MY_PRINT_FUNC("no input was given, aborting")
		return None
	
	# turn the given string into the bone, guaranteed to succeed.
	bone = get_item_from_string(s, pmx.bones)
	# should I assert that the name begins with 右 ? nah....
	# strip off the first char
	bone_basename = bone.name_jp[1:]
	# check whether any vertexes actually have weight on this bone
	given_index = bone.idx_within(pmx.bones)
	if not transfer_to_armtwist_sub(pmx, given_index, given_index):
		core.MY_PRINT_FUNC("err: given bone does not control any vertices?")
		return None
	
	core.MY_PRINT_FUNC("R handtwist...")
	make_handtwist_addon(pmx, jp_r, bone_basename)
	core.MY_PRINT_FUNC("L handtwist...")
	make_handtwist_addon(pmx, jp_l, bone_basename)
	
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_sdefhandtwist")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
