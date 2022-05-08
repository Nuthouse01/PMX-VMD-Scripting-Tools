from typing import Sequence, List

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.core.nuthouse01_pmx_utils import insert_single_bone
from mmd_scripting.scripts_for_gui import bone_set_arm_localaxis

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.05 - 7/12/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
# Special thanks to Quappa-El for designing the clever system, I saw his models using it and wrote this script to
# create those same structures in any generic model.
#####################


helptext = '''=================================================
bone_add_semistandard_auto_armtwist:
This will generate "automatic armtwist rigging" that will fix pinching at shoulders/elbows/wrists.
This only works on models that already have semistandard armtwist/腕捩 and wristtwist/手捩 bone rigs.
It creates a clever IK bone setup that hijacks the semistandard bones and moves them as needed to reach whatever pose you make with the arm/腕 or elbow/ひじ bones. You do not need to manually move the armtwist bones at all, you can animate all 3 axes of rotation on the arm bone and the twisting axis will be automatically extracted and transferred to the armtwist bone as needed!

If the existing semistandard armtwist rig is bad, then the results from using this script will also be bad. To re-make the armtwist rig, you can merge all existing armtwist bones into the arm bone and use the "semistandard bones" PMXE plugin to try and rebuild it. Or, you can try using [TODO SDEF SCRIPT NAME HERE] to use a fancy SDEF weights method.

This script is not guaranteed compatible with arm IK bones created by IKMaker X plugin for PMXE. It might or might not work, depending on how you animate it.
To easily disable the autotwist rig and make it work with arm IK bones: in the parent & partial inherit section for each armtwist/wristtwist/helper bone, replace "armD" with "arm" and replace "armT" with "armtwist". Or, just use a version of the model from before running this script.

Output: model PMX file '[modelname]_autotwist.pmx'
'''

'''
CRITICAL NOTE
to ensure compatability with "IK Maker X" plugin, we need to set bone deforms in a specific way.
we also need to set the IK link limits for the D-bone to prevent it from going all wacky in rare cases
overall it is recommended to NOT use auto-arm-twist rig along with arm-IK rig

the deform order thing is essential to solving "spinning wrists" when standard arm-IK is present, and perfectly harmless when arm-IK is not present
the IK link limits help to mitigate some rare issues when arm-IK exists but i'm like 1% confident they can cause issues when arm-IK is not present?
'''

# left and right prefixes
jp_l =    "左"
jp_r =    "右"
# names for relevant bones
jp_shoulder =   "肩" # "shoulder"
jp_arm =		"腕" # "arm"
jp_armtwist =	"腕捩" # "arm twist"
jp_elbow =		"ひじ" # "elbow"
jp_wristtwist = "手捩" # "wrist twist"
jp_wrist =		"手首" # "wrist"

f_armNoTwist =     "{}/{}D"
f_armNoTwistEnd =  "{}/{}D先"
f_armNoTwistIk =   "{}/{}DIK"
f_armYesTwist =    "{}/{}T"
f_armYesTwistEnd = "{}/{}T先"
f_armYesTwistIk =  "{}/{}TIK"
f_handCombine =    "{}/{}+{}"

# parameters
deformlevel_Dbones = 2
deformlevel_Tbones = 3
deformlevel_subtwist = 4

ik_numloops = 100
ik_angle = 5  # degrees

ikD_lim_min = None
ikD_lim_max = None
# ikD_lim_min = [0, -180, -180]
# ikD_lim_max = [0, 180, 180]

# dances/frames where the autotwist makes a visible difference:
# girls 555 L elbow
# girls 1027 R elbow R shoulder
# pink cat 464 L shoulder
# pink cat 550 R shoulder
# pink cat 574 R shoulder
# conqueror 513 R wrist
# conqueror 2293 R wrist
# pink cat 334 R wrist
# pink cat 1155 R wrist

"""
左腕
左腕捩
左/腕D
左/腕D先
左/腕DIK
左/腕T
左/腕T先
左/腕TIK
左腕捩0
左腕捩1
左腕捩2
左腕捩3
左腕捩4
左ひじ
左手捩
combine
左/ひじD
左/ひじD先
左/ひじDIK
foo
bar
左/ひじT
左/ひじT先
左/ひじTIK
左手捩0
左手捩1
左手捩2
左手捩3
左手捩4
左手首
左手先
hand D
hand D end
hand D IK
hand T
hand T end
hand T IK
左ダミー
"""

'''
insertion points:

shoulderC
arm
armtwist
	armD  (after greater of arm,armtwist)
	armDend
	armD_IK
	armT
	armTend
	armT_IK
	armtwist0
armtwist1
armtwist2
armtwist3
	armtwistX  (before elbow)
elbow
'''

def fix_deform_for_children(pmx: pmxstruct.Pmx, me: int, already_visited=None) -> int:
	"""
	Recursively ensure everything that inherits from the specified bone will deform after it.
	Only cares about parent and partial-inherit, doesnt try to understand IK groups.
	Return the number of bones that were changed.
	:param pmx: full PMX object
	:param me: int index of current bone
	:param already_visited: leave empty, used to prevent recursive looping
	:return: number of bones that were changed
	"""
	def guarantee_good_relationship(parent: int, child: int) -> bool:
		# check & fix the relationship between these two bones
		# if the deform layers are improper, then fix them and return True
		# if the deform layers are proper, then return False
		
		# todo: do i care about deform_after_phys?
		child_deform = pmx.bones[child].deform_layer
		parent_deform = pmx.bones[parent].deform_layer
		if child < parent:
			# if the child has lower index than parent, then the child MUST have greater deform_layer
			if child_deform <= parent_deform:
				pmx.bones[child].deform_layer = pmx.bones[parent].deform_layer + 1
				return True
			else:
				return False
		elif child > parent:
			# if the child has greater index than parent, then the child MUST have greater (or equal) deform_layer
			if child_deform < parent_deform:
				pmx.bones[child].deform_layer = pmx.bones[parent].deform_layer
				return True
			else:
				return False
		else:
			# if child == parent, idk? don't change anything tho
			return False
	
	retme = 0
	
	# safety system to prevent infinite recursion:
	if already_visited is None: already_visited = set()
	if me in already_visited: return 0
	else:                     already_visited.add(me)
	
	# check every single bone to find the ones that inherit from "me"
	for d,bone in enumerate(pmx.bones):
		# if bone d is inheriting from "me",
		if (bone.parent_idx == me) or ((bone.inherit_rot or bone.inherit_trans) and (bone.inherit_parent_idx == me)):
			# check/fix their relationship. return True if something was changed.
			if guarantee_good_relationship(me, d):
				# the check also fixes it, all thats left is to recurse
				print(d)
				retme += 1
				retme += fix_deform_for_children(pmx, d, already_visited)
	return retme

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

def calculate_perpendicular_offset_vector(delta: Sequence[float]) -> List[float]:
	"""
	When given an axis (such as elbow-to-wrist) return the perpendicular offset vector.
	This will have unit length, will have positive Y, and will lie in the same "vertical plane" as the
	input axis, i.e. when viewed from above this vector will be colinear with the input axis.
	:param delta: XYZ 3 floats
	:return: XYZ list of 3 floats
	"""
	axis = core.normalize_distance(delta)
	# calc vector in XZ plane at 90-deg from axis, i.e. Y-component is zero
	# ideally the X-component will be 0 but if the original axis is angled a little front or back that will rotate
	frontback = core.my_cross_product(axis, (0.0, 1,0, 0.0))
	frontback = core.normalize_distance(frontback)
	# calc vector in the same vertical plane as axis, at 90-deg from axis
	perpendicular = core.my_cross_product(axis, frontback)
	perpendicular = core.normalize_distance(perpendicular)  # normalize to length 1
	# if result has negative y, invert the whole thing
	if perpendicular[1] < 0:
		perpendicular = [p * -1 for p in perpendicular]
	return perpendicular

def create_twist_separator_rig(pmx: pmxstruct.Pmx,
							   side:str, arm_s:str,
							   arm_pos:List[float], elbow_pos:List[float],
							   arm_parent_idx:int, elbow_parent_idx:int,) -> List[pmxstruct.PmxBone]:
	"""
	Create & insert the 6 bones that make the twist-decomposition rig. They will be returned as a list, in the same
	order as they exist in the bonelist. "segment" refers to the bone segment being decomposed.
	:param pmx: full PMX object
	:param side: string, JP L or R prefix
	:param arm_s: string, JP name to use as base
	:param arm_pos: XYZ position of the bone at the top of the segment
	:param elbow_pos: XYZ position of the bone at the bottom of the segment
	:param arm_parent_idx: int index of the parent of the topmost bone in the segment (the bone that has NONE of the motion in this segment)
	:param elbow_parent_idx: int index of the bottommost bone in the segment (the bone that has the FULL motion of this segment)
	:return: list of all 6 created bones
	"""
	base_deform = pmx.bones[elbow_parent_idx].deform_layer
	D_deform = base_deform + deformlevel_Dbones
	T_deform = base_deform + deformlevel_Tbones
	
	# 4, calculate "perpendicular" location
	# get axis from arm to elbow... final minus initial
	axis = [b - a for a, b in zip(arm_pos, elbow_pos)]
	# find the offset where the "ik T bone" will sit
	perpendicular = calculate_perpendicular_offset_vector(axis)
	# add this to elbow pos and save
	perp_pos = [a + b for a, b in zip(elbow_pos, perpendicular)]

	# 5, create the six ik bones
	# cannot reference other bone idxs until they are inserted!! use -99 as placeholder
	# all bones have 'enabled' false, 'visible' false,
	
	# make armD, pos=arm.pos, parent=arm.parent, tail=armDend
	armD = pmxstruct.PmxBone(
		name_jp=f_armNoTwist.format(side, arm_s),
		name_en="",
		pos=arm_pos, parent_idx=-99, deform_layer=D_deform, deform_after_phys=False,
		has_rotate=True, has_translate=False, has_visible=False, has_enabled=False, has_ik=False,
		tail_usebonelink=True, tail=-99, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
		has_localaxis=False, has_externalparent=False,
	)
	# make armDend, pos=elbow.pos, parent=armD_idx
	armDend = pmxstruct.PmxBone(
		name_jp=f_armNoTwistEnd.format(side, arm_s),
		name_en="",
		pos=elbow_pos, parent_idx=-99, deform_layer=D_deform, deform_after_phys=False,
		has_rotate=True, has_translate=False, has_visible=False, has_enabled=False, has_ik=False,
		tail_usebonelink=True, tail=-1, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
		has_localaxis=False, has_externalparent=False,
	)
	# make armD_IK, pos=elbow.pos, parent=elbow.parent, target=armDend, link=armD
	armDik = pmxstruct.PmxBone(
		name_jp=f_armNoTwistIk.format(side, arm_s),
		name_en="",
		pos=elbow_pos, parent_idx=-99, deform_layer=D_deform, deform_after_phys=False,
		has_rotate=True, has_translate=True, has_visible=False, has_enabled=False, has_ik=True,
		tail_usebonelink=True, tail=-1, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
		has_localaxis=False, has_externalparent=False,
		ik_target_idx=-99, ik_numloops=ik_numloops, ik_angle=ik_angle,
		ik_links=[pmxstruct.PmxBoneIkLink(idx=-99, limit_min=ikD_lim_min, limit_max=ikD_lim_max)]
	)
	
	# make armT, pos=elbow.pos, parent=armD_idx, tail=armTend
	armT = pmxstruct.PmxBone(
		name_jp=f_armYesTwist.format(side, arm_s),
		name_en="",
		pos=elbow_pos, parent_idx=-99, deform_layer=T_deform, deform_after_phys=False,
		has_rotate=True, has_translate=False, has_visible=False, has_enabled=False, has_ik=False,
		tail_usebonelink=True, tail=-99, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
		has_localaxis=False, has_externalparent=False,
	)
	# make armTend, pos=perp_pos, parent=armT_idx
	armTend = pmxstruct.PmxBone(
		name_jp=f_armYesTwistEnd.format(side, arm_s),
		name_en="",
		pos=perp_pos, parent_idx=-99, deform_layer=T_deform, deform_after_phys=False,
		has_rotate=True, has_translate=False, has_visible=False, has_enabled=False, has_ik=False,
		tail_usebonelink=True, tail=-1, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
		has_localaxis=False, has_externalparent=False,
	)
	# make armT_IK, pos=perp_pos, parent=elbow.parent, target=armTend, link=armT
	armTik = pmxstruct.PmxBone(
		name_jp=f_armYesTwistIk.format(side, arm_s),
		name_en="",
		pos=perp_pos, parent_idx=-99, deform_layer=T_deform, deform_after_phys=False,
		has_rotate=True, has_translate=True, has_visible=False, has_enabled=False, has_ik=True,
		tail_usebonelink=True, tail=-1, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
		has_localaxis=False, has_externalparent=False,
		ik_target_idx=-99, ik_numloops=ik_numloops, ik_angle=ik_angle, ik_links=[pmxstruct.PmxBoneIkLink(idx=-99)]
	)
	
	# insert these 6 bones
	'''
	shoulderC
	arm
	armtwist
	* armtwist0
	armtwist1
	armtwist2
	armtwist3
	* armtwist4  (before elbow)
	elbow
	...
	* armD  (after greater of arm,armtwist)
	* armDend
	* armD_IK
	* armT
	* armTend
	* armT_IK
	'''
	armD_idx =    len(pmx.bones)
	armDend_idx = len(pmx.bones) + 1
	armDik_idx =  len(pmx.bones) + 2
	armT_idx =    len(pmx.bones) + 3
	armTend_idx = len(pmx.bones) + 4
	armTik_idx =  len(pmx.bones) + 5
	# TODO: create more efficient function for multi-insert? nah, this is fine
	insert_single_bone(pmx, armD, armD_idx)
	insert_single_bone(pmx, armDend, armDend_idx)
	insert_single_bone(pmx, armDik, armDik_idx)
	insert_single_bone(pmx, armT, armT_idx)
	insert_single_bone(pmx, armTend, armTend_idx)
	insert_single_bone(pmx, armTik, armTik_idx)
	# fix all references to other bones (all -99 in the constructors)
	armD.tail =              armDend_idx
	armD.parent_idx =        arm_parent_idx #
	armDend.parent_idx =     armD_idx
	armDik.parent_idx =      elbow_parent_idx #
	armDik.ik_target_idx =   armDend_idx
	armDik.ik_links[0].idx = armD_idx
	armT.tail =              armTend_idx
	armT.parent_idx =        armD_idx
	armTend.parent_idx =     armT_idx
	armTik.parent_idx =      elbow_parent_idx #
	armTik.ik_target_idx =   armTend_idx
	armTik.ik_links[0].idx = armT_idx
	
	return [armD, armDend, armDik, armT, armTend, armTik]


def make_autotwist_segment(pmx: pmxstruct.Pmx, side:str, arm_s:str, armtwist_s:str, elbow_s:str, extra_deform, moreinfo=False) -> None:
	"""
	Basically the entire script, but sorta parameterized so i can repeat it 4 times for the 4 arm segments.
	:param pmx: full PMX object
	:param side: string, JP L or R prefix
	:param arm_s: string, JP name for the arm or elbow bone, top of the segment & manipulated in VMD
	:param armtwist_s: string, JP name for the locked-axis twist bone
	:param elbow_s: string, JP name for the bone at the end of the segment
	:param extra_deform: int, add this number to the deform level of the created rig
	:param moreinfo: bool, if true then print extra stuff
	"""
	# note: will be applicable to elbow-wristtwist-wrist as well! just named like armtwist for simplicity
	
	# 1, locate the primary existing bones, idx and obj, from their semistandard names
	# arm/armtwist/elbow , all 3 MUST exist
	arm_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + arm_s))
	if arm_idx is None:
		core.MY_PRINT_FUNC("ERROR: standard bone '%s' not found in model, this is required!" % (side + arm_s))
		return None
	armtwist_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + armtwist_s))
	if armtwist_idx is None:
		core.MY_PRINT_FUNC("ERROR: standard bone '%s' not found in model, this is required!" % (side + armtwist_s))
		return None
	elbow_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + elbow_s))
	if elbow_idx is None:
		core.MY_PRINT_FUNC("ERROR: standard bone '%s' not found in model, this is required!" % (side + elbow_s))
		return None
	
	arm =      pmx.bones[arm_idx]
	armtwist = pmx.bones[armtwist_idx]
	elbow =    pmx.bones[elbow_idx]
	# locate "elbow helper bone" if it exists: (full parent armtwist, partial parent elbow), might be None
	elbowhelper = core.my_list_search(pmx.bones, lambda x: x.parent_idx==armtwist_idx and
														   x.inherit_rot and
														   x.inherit_parent_idx==elbow_idx, getitem=True)

	# 2, find all armtwist-sub bones (armtwist1, armtwist2, armtwist3 usually. sometimes there are more or less.)
	armtwist_sub_obj = []
	for d, bone in enumerate(pmx.bones):
		# anything that partial inherit from armtwist (except arm)
		if bone.inherit_rot and bone.inherit_parent_idx == armtwist_idx:
			if bone is arm: continue
			armtwist_sub_obj.append(bone)
		# anything that has armtwist as parent (except elbow or elbow helper)
		if bone.parent_idx == armtwist_idx:
			if bone is elbow: continue
			if bone is elbowhelper: continue
			armtwist_sub_obj.append(bone)
	# get the indexes of all of them
	armtwist_sub_idx = [b.idx_within(pmx.bones) for b in armtwist_sub_obj]
	if len(armtwist_sub_idx) == 0:
		core.MY_PRINT_FUNC("ERROR: unable to find sub-twist bones! (左腕捩1, 左腕捩2, 左腕捩3, etc)")
		core.MY_PRINT_FUNC("This script requires semistandard sub-twist bones to properly run!")
		return None
	
	# 3, detect & fix incorrect structure among primary bones
	# elbow should be a child of arm or armtwist, NOT any of the armtwist-sub bones
	# this is to prevent deform layers from getting all fucky
	if elbow.parent_idx in armtwist_sub_idx:
		newparent = max(arm_idx, armtwist_idx)
		core.MY_PRINT_FUNC("WARNING: fixing improper parenting for bone '%s'" % elbow.name_jp)
		core.MY_PRINT_FUNC("parent was '%s', changing to '%s'" %
						   (pmx.bones[elbow.parent_idx].name_jp, pmx.bones[newparent].name_jp))
		core.MY_PRINT_FUNC("if this bone has a 'helper bone' please change its parent in the same way")
		elbow.parent_idx = newparent
		
		
	# 4, create the 6 bones of the twist-separator rig
	armD, armDend, armDik, armT, armTend, armTik = create_twist_separator_rig(
		pmx, side, arm_s, arm.pos, elbow.pos, arm.parent_idx, elbow.parent_idx,
	)
	# additionally modify the deform layer of each bone
	for b in [armD, armDend, armDik, armT, armTend, armTik]:
		b.deform_layer += extra_deform
	# turn the objects into their indexes
	armD_idx = armD.idx_within(pmx.bones)
	armT_idx = armT.idx_within(pmx.bones)
	
	# 5, modify the existing armtwist-sub bones
	# first go back from obj to indices, since the bones moved
	base_deform = pmx.bones[elbow.parent_idx].deform_layer
	subtwist_deform = base_deform + deformlevel_subtwist + extra_deform
	armtwist_sub_idx = [b.idx_within(pmx.bones) for b in armtwist_sub_obj]
	for b_sub in armtwist_sub_obj:
		# change parent from arm to armD
		b_sub.parent_idx = armD_idx
		# change partial inherit from armtwist to armT
		b_sub.inherit_parent_idx = armT_idx
		# set the deform layer
		b_sub.deform_layer = subtwist_deform
	
	
	# 6, insert additional armtwist-sub bones and transfer weight to them
	
	# first, check whether armtwistX would receive any weights/RBs
	# note, transferring from armtwist to armtwist changes nothing, this is harmless, just for looking
	armtwistX_used = transfer_to_armtwist_sub(pmx, armtwist_idx, armtwist_idx)
	if armtwistX_used:
		finalnum = str(len(armtwist_sub_idx) + 1)
		# make armtwistX, pos=armtwist.pos, parent=armD_idx, inherit armT=1.00
		armtwistX = pmxstruct.PmxBone(
			name_jp= side + armtwist_s + finalnum,
			name_en="",
			pos=armtwist.pos, parent_idx=-99, deform_layer=subtwist_deform, deform_after_phys=False,
			has_rotate=True, has_translate=False, has_visible=False, has_enabled=True, has_ik=False,
			tail_usebonelink=True, tail=-1, inherit_rot=True, inherit_trans=False, inherit_parent_idx=-99, inherit_ratio=1.00,
			has_fixedaxis=False, has_localaxis=False, has_externalparent=False,
		)
		# insert armtwistX at max(armtwist_sub_idx) + 1
		armtwistX_idx = max(armtwist_sub_idx)+1
		insert_single_bone(pmx, armtwistX, armtwistX_idx)
		# fix references to other bones
		armtwistX.parent_idx = armD.idx_within(pmx.bones)
		armtwistX.inherit_parent_idx = armT.idx_within(pmx.bones)
		
		# transfer all weight and rigidbody references from armtwist to armtwistX
		# this time the return val is not needed
		transfer_to_armtwist_sub(pmx, armtwist_idx, armtwistX_idx)
		armtwist_sub_obj.append(armtwistX)
		
	# second, do the same thing for armtwist0
	armtwist0_used = transfer_to_armtwist_sub(pmx, arm_idx, arm_idx)
	if armtwist0_used:
		# make armtwist0, pos=arm.pos, parent=armD_idx, inherit armT=0.00
		armtwist0 = pmxstruct.PmxBone(
			name_jp= side + armtwist_s + "0",
			name_en="",
			pos=arm.pos, parent_idx=-99, deform_layer=subtwist_deform, deform_after_phys=False,
			has_rotate=True, has_translate=False, has_visible=False, has_enabled=True, has_ik=False,
			tail_usebonelink=True, tail=-1, inherit_rot=True, inherit_trans=False, inherit_parent_idx=-99, inherit_ratio=0.00,
			has_fixedaxis=False, has_localaxis=False, has_externalparent=False,
		)
		# insert armtwist0 at min(armtwist_sub_idx)
		armtwist0_idx = min(armtwist_sub_idx)
		insert_single_bone(pmx, armtwist0, armtwist0_idx)
		# fix references to other bones
		armtwist0.parent_idx = armD.idx_within(pmx.bones)
		armtwist0.inherit_parent_idx = armT.idx_within(pmx.bones)
		
		# transfer all weight and rigidbody references from arm to armtwist0
		# this time the return val is not needed
		transfer_to_armtwist_sub(pmx, arm_idx, armtwist0_idx)
		armtwist_sub_obj.append(armtwist0)
	
	
	# 7, fix shoulder-helper and elbow-helper if they exist
	# shoulder helper: parent=shoulder(C), inherit=arm
	# goto:            parent=shoulder(C), inherit=armD
	# elbow helper: parent=arm(twist), inherit=elbow
	# goto:         parent=armT,       inherit=elbowD
	
	# need to refresh elbow idx cuz it moved
	armD_idx = armD.idx_within(pmx.bones)
	armDik_idx = armDik.idx_within(pmx.bones)
	armT_idx = armT.idx_within(pmx.bones)
	armTik_idx = armTik.idx_within(pmx.bones)
	elbow_idx = elbow.idx_within(pmx.bones)
	for d, bone in enumerate(pmx.bones):
		# transfer "inherit arm" to "inherit armD"
		# this should be safe for all bones
		if bone.inherit_rot and bone.inherit_parent_idx == arm_idx:
			bone.inherit_parent_idx = armD_idx
		# transfer "parent armtwist" to "parent armT"
		# this needs to exclude elbow, D_IK, T_IK, armtwist, arm
		if bone.parent_idx == armtwist_idx:
			if d not in (elbow_idx, armDik_idx, armTik_idx, armtwist_idx, arm_idx):
				bone.parent_idx = armT_idx
		if bone.parent_idx == arm_idx:
			if d not in (elbow_idx, armDik_idx, armTik_idx, armtwist_idx, arm_idx):
				bone.parent_idx = armD_idx
	
	
	# 8, fix deform for anything hanging off of the armtwist or subtwist bones (rare but sometimes exists)
	deform_changed = 0
	deform_changed += fix_deform_for_children(pmx, armD_idx)
	deform_changed += fix_deform_for_children(pmx, armT_idx)
	for idx in armtwist_sub_idx:
		deform_changed += fix_deform_for_children(pmx, idx)
		
	if moreinfo and deform_changed:
		core.MY_PRINT_FUNC("modified deform order for %d existing bones" % deform_changed)
		
	
	# done with this function???
	return None

def make_handtwist_addon(pmx: pmxstruct.Pmx, side:str) -> None:
	"""
	Add one more twist separator rig for the hand & copy the twist portion of that up into the lowerarm.
	This fixes wrist crimping problem! :)
	:param pmx: full PMX object
	:param side: string, JP L or R prefix
	"""
	
	# 1, find the relevant bones
	# find the elbow bone
	elbow_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + jp_elbow))
	# # find the elbowtwist bone
	# elbowtwist_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + jp_wristtwist))
	# find the wrist bone
	wrist_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + jp_wrist))
	# turn the indices into real objects
	elbow = pmx.bones[elbow_idx]
	# elbowtwist = pmx.bones[elbowtwist_idx]
	wrist = pmx.bones[wrist_idx]
	
	# 2, derive the position of the "D" bone
	# subtract their positions to get the axis, final minus initial
	axis = [b-a for a,b in zip(elbow.pos, wrist.pos)]
	# normalize to length of 1
	axis = core.normalize_distance(axis)
	# extend this axis beyond the wrist bone to create the "D" position
	d_pos = [a+b for a,b in zip(axis, wrist.pos)]

	# 3, create the 6 bones of the twist-separator rig
	wristD, wristDend, wristDik, wristT, wristTend, wristTik = create_twist_separator_rig(
		pmx, side, jp_wrist, wrist.pos, d_pos, wrist.parent_idx, wrist_idx,
	)
	# turn the objects into their indexes
	# wristD_idx = wristD.idx_within(pmx.bones)
	# wristDend_idx = wristDend.idx_within(pmx.bones)
	# wristDik_idx = wristDik.idx_within(pmx.bones)
	wristT_idx = wristT.idx_within(pmx.bones)
	# wristTend_idx = wristTend.idx_within(pmx.bones)
	# wristTik_idx = wristTik.idx_within(pmx.bones)
	
	# 4, create the "combiner" bone
	# first, gotta find elbowDik and elbowTik
	elbowDik = core.my_list_search(pmx.bones, lambda x: x.name_jp == f_armNoTwistIk.format(side, jp_elbow), getitem=True)
	elbowTik = core.my_list_search(pmx.bones, lambda x: x.name_jp == f_armYesTwistIk.format(side, jp_elbow), getitem=True)
	# now start creating the new bone!
	# parent is the current parent of elbowDik
	# position is ^ + 1
	# partial inheirt from wristT
	# layer is pmx.bones[wrist_idx].deform_layer + deformlevel_Tbones + 1
	# position is the current parent of elbowDik
	newbone = pmxstruct.PmxBone(
		name_jp=f_handCombine.format(side, jp_elbow, jp_wrist),
		name_en="",
		pos=pmx.bones[elbowDik.parent_idx].pos, parent_idx=elbowDik.parent_idx,
		deform_layer=pmx.bones[wrist_idx].deform_layer + deformlevel_Tbones + 1, deform_after_phys=False,
		has_rotate=True, has_translate=False, has_visible=False, has_enabled=False, has_ik=False,
		tail_usebonelink=True, tail=-1,
		inherit_rot=True, inherit_trans=False, inherit_ratio=1.0, inherit_parent_idx=wristT_idx,
		has_fixedaxis=False, has_localaxis=False, has_externalparent=False,
	)
	
	# insert at the current position of elbowD
	elbowD_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == f_armNoTwist.format(side, jp_elbow))
	newbone_idx = elbowD_idx
	insert_single_bone(pmx, newbone, newbone_idx)
	
	# 5, then, elbowDik and elbowTik are set to use "combiner" as parent
	# TODO: is there any difference between changing D or not changing D ?
	elbowDik.parent_idx = newbone_idx
	elbowTik.parent_idx = newbone_idx
	
	return None


def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	bone_set_arm_localaxis.set_all_arm_localaxis(pmx, moreinfo)
	
	core.MY_PRINT_FUNC("L upper arm...")
	make_autotwist_segment(pmx, jp_l, jp_arm, jp_armtwist, jp_elbow, 0, moreinfo)
	
	core.MY_PRINT_FUNC("L lower arm...")
	make_autotwist_segment(pmx, jp_l, jp_elbow, jp_wristtwist, jp_wrist, 3, moreinfo)
	
	core.MY_PRINT_FUNC("L handtwist...")
	make_handtwist_addon(pmx, jp_l)
	
	core.MY_PRINT_FUNC("R upper arm...")
	make_autotwist_segment(pmx, jp_r, jp_arm, jp_armtwist, jp_elbow, 0, moreinfo)
	
	core.MY_PRINT_FUNC("R lower arm...")
	make_autotwist_segment(pmx, jp_r, jp_elbow, jp_wristtwist, jp_wrist, 3, moreinfo)
	
	core.MY_PRINT_FUNC("R handtwist...")
	make_handtwist_addon(pmx, jp_r)
	
	# if i want to, set elbowD parent to armT...?
	# if i want to, set wrist parent to elbowT...?
	# that's what the original does, but why? why would I want that?
	# armT should have exactly the same deformations as armtwist
	# it's better to have the twist-rigs be isolated from eachother
	
	
	# TODO: examine leg system! not universal because nobody has legtwist bones to hijack but worth understanding
	
	
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_autotwist")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
