# Nuthouse01 - 09/13/2020 - v5.01
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	# these imports work if running from GUI
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
	from . import nuthouse01_pmx_struct as pmxstruct
	from ._prune_unused_bones import insert_single_bone
except ImportError as eee:
	try:
		# these imports work if running from double-click on THIS script
		import nuthouse01_core as core
		import nuthouse01_pmx_parser as pmxlib
		import nuthouse01_pmx_struct as pmxstruct
		from _prune_unused_bones import insert_single_bone
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = pmxlib = pmxstruct = insert_single_bone = None




# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = True

helptext = '''=================================================
bone_auto_armtwist:
This will generate "automatic armtwist rigging" that will fix pinching at shoulders/elbows.
This only works on models that already have semistandard armtwist/腕捩 and wristtwist/手捩 bone rigs.
It creates a clever IK bone setup that hijacks the semistandard bones and moves them as needed to reach whatever pose you make with the arm/腕 or elbow/ひじ bones. You do not need to manually move the armtwist bones at all, you can animate all 3 axes of rotation on the arm bone and the twisting axis will be automatically extracted and transferred to the armtwist bone as needed!

If the existing semistandard armtwist rig is bad, then the results from using this script will also be bad. To re-make the armtwist rig, you can merge all existing armtwist bones into the arm bone and use the "semistandard bones" PMXE plugin to try and rebuild it. Or, you can try using [TODO SDEF SCRIPT NAME HERE] to use a fancy SDEF weights method.

This script is compatible with arm IK bones created by IKMaker X plugin for PMXE. HOWEVER, weird things can sometimes happen and it is not recommended.
To easily disable the autotwist rig and make it definitely work with arm IK bones: in the parent & partial inherit section for each armtwist/wristtwist/helper bone, replace "armD" with "arm" and replace "armT" with "armtwist". Or, just use a version of the model from before running this script.

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


jp_leg =		"足"
jp_knee =		"ひざ"
jp_foot =		"足首"
jp_leg_d =		"足D"
jp_knee_d =		"ひざD"
jp_foot_d =		"足首D"




# left and right prefixes
jp_l =    ("左", "_L")
jp_r =    ("右", "_R")
# names for relevant bones
jp_arm =		("腕", "arm")
jp_armtwist =	("腕捩", "arm twist")
jp_elbow =		("ひじ", "elbow")
jp_wristtwist = ("手捩", "wrist twist")
jp_wrist =		("手首", "wrist")
# suffixes
n_base =  ("D", "D")
n_twist = ("T", "T")
n_ik =    ("IK", "IK")
n_end =   ("先", " end")

# parameters
perpendicular_offset_dist = 1.00

ik_numloops = 100
ik_angle = 5  # degrees

ikD_lim_min = [0, -180, -180]
ikD_lim_max = [0, 180, 180]

# girls 555 L elbow
# girls 1027 R elbow R shoulder
# pink cat 464 L shoulder
# pink cat 550 R shoulder
# pink cat 574 R shoulder


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



# why bother changing the arm/armtwist relationship? just leave it where it is, how it is! just steal its weights!

def transfer_to_armtwist_sub(pmx: pmxstruct.Pmx, from_bone:int, to_bone:int) -> bool:
	# any weights currently set to "from_bone" get replaced with "to_bone"
	did_anything_change = False
	weighttype_to_len = {0:1, 1:2, 2:4, 3:2, 4:4}
	for v in pmx.verts:
		for i in range(weighttype_to_len[v.weighttype]):
			if v.weight[i] == from_bone:
				v.weight[i] = to_bone
				did_anything_change = True
	# move all rigidbodies attached to "from_bone" to "to_bone" instead
	for rb in pmx.rigidbodies:
		if rb.bone_idx == from_bone:
			rb.bone_idx = to_bone
			did_anything_change = True
	return did_anything_change


def make_autotwist_segment(pmx: pmxstruct.Pmx, side, arm_s, armtwist_s, elbow_s):
	# note: will be applicable to elbow-wristtwist-wrist as well! just named like armtwist for simplicity
	
	# 1, locate arm/armtwist/elbow idx and obj
	r = []
	for n in (arm_s, armtwist_s, elbow_s):
		n2 = side[0] + n[0]
		i = core.my_list_search(pmx.bones, lambda x: x.name_jp == n2)
		if i is None:
			core.MY_PRINT_FUNC("ERROR: standard bone '%s' not found in model, this is required!" % n2)
			return None
		r.append(i)
	arm_idx, armtwist_idx, elbow_idx = r  # unpack into named variables
	arm = pmx.bones[arm_idx]
	armtwist = pmx.bones[armtwist_idx]
	elbow = pmx.bones[elbow_idx]
	
	
	# 2, find all armtwist-sub bones
	armtwist_sub_obj = []
	# # dont forget to refresh elbow_idx
	# elbow_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == side + elbow_s)
	for d, bone in enumerate(pmx.bones):
		# anything that partial inherit from armtwist (except arm)
		if bone.inherit_rot and bone.inherit_parent_idx == armtwist_idx:
			if d == arm_idx: continue
			armtwist_sub_obj.append(bone)
		# anything that has armtwist as parent (except elbow or elbow helper (full parent armtwist, partial parent elbow))
		if bone.parent_idx == armtwist_idx:
			if d == elbow_idx: continue
			if bone.inherit_rot and bone.inherit_parent_idx == elbow_idx: continue
			armtwist_sub_obj.append(bone)
	
	
	# 3, calculate "perpendicular" location
	# get axis from arm to elbow, normalize to 1
	def normalize(foo):
		LLL = core.my_euclidian_distance(foo)
		return [t / LLL for t in foo]
	axis = [b - a for a, b in zip(arm.pos, elbow.pos)]
	axis = normalize(axis)
	# calc vector in XZ plane at 90-deg from axis
	frontback = core.my_cross_product(axis, [0,1,0])
	frontback = normalize(frontback)
	# calc vector in the same vertical plane as axis, at 90-deg from axis
	perpendicular = core.my_cross_product(axis, frontback)
	perpendicular = normalize(perpendicular)
	# if result has negative y, invert
	if perpendicular[1] < 0:
		perpendicular = [p * -1 for p in perpendicular]
	# normalize to perpendicular_offset_dist
	perpendicular = [perpendicular_offset_dist * t for t in perpendicular]
	# add this to elbow pos and save
	perp_pos = [a + b for a, b in zip(elbow.pos, perpendicular)]
	
	
	# 4, create the six ik bones
	# cannot reference other bone idxs until they are inserted!!
	start = max(arm_idx, armtwist_idx)
	armD_idx =    start + 1
	armDend_idx = start + 2
	armDik_idx =  start + 3
	armT_idx =    start + 4
	armTend_idx = start + 5
	armTik_idx =  start + 6
	
	# make armD, pos=arm.pos, parent=arm.parent, tail=armDend
	armD = pmxstruct.PmxBone(
		name_jp=side[0] + arm_s[0] + n_base[0], 
		name_en=arm_s[1] + n_base[1] + side[1],
		pos=arm.pos, parent_idx=-99, deform_layer=0, deform_after_phys=False,
		has_rotate=True, has_translate=False, has_visible=False, has_enabled=False, has_ik=False,
		tail_usebonelink=True, tail=-99, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
		has_localaxis=arm.has_localaxis, localaxis_x=arm.localaxis_x, localaxis_z=arm.localaxis_z,
		has_externalparent=False,
	)
	# make armDend, pos=elbow.pos, parent=armD_idx
	armDend = pmxstruct.PmxBone(
		name_jp=side[0] + arm_s[0] + n_base[0] + n_end[0],
		name_en=arm_s[1] + n_base[1] + side[1] + n_end[1],
		pos=elbow.pos, parent_idx=-99, deform_layer=0, deform_after_phys=False,
		has_rotate=True, has_translate=False, has_visible=False, has_enabled=False, has_ik=False,
		tail_usebonelink=True, tail=-1, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
		has_localaxis=False, has_externalparent=False,
	)
	# make armD_IK, pos=elbow.pos, parent=elbow.parent, target=armDend, link=armD
	armDik = pmxstruct.PmxBone(
		name_jp=side[0] + arm_s[0] + n_base[0] + n_ik[0],
		name_en=arm_s[1] + n_base[1] + n_ik[1] + side[1],
		pos=elbow.pos, parent_idx=-99, deform_layer=0, deform_after_phys=False,
		has_rotate=True, has_translate=True, has_visible=False, has_enabled=False, has_ik=True,
		tail_usebonelink=True, tail=-1, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
		has_localaxis=False, has_externalparent=False,
		ik_target_idx=-99, ik_numloops=ik_numloops, ik_angle=ik_angle, 
		ik_links=[pmxstruct.PmxBoneIkLink(idx=-99, limit_min=ikD_lim_min, limit_max=ikD_lim_max)]
	)
	
	# make armT, pos=elbow.pos, parent=armD_idx, tail=armTend
	armT = pmxstruct.PmxBone(
		name_jp=side[0] + arm_s[0] + n_twist[0],
		name_en=arm_s[1] + n_twist[1] + side[1],
		pos=elbow.pos, parent_idx=-99, deform_layer=0, deform_after_phys=False,
		has_rotate=True, has_translate=False, has_visible=False, has_enabled=False, has_ik=False,
		tail_usebonelink=True, tail=-99, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
		has_localaxis=False, has_externalparent=False,
	)
	# make armTend, pos=perp_pos, parent=armT_idx
	armTend = pmxstruct.PmxBone(
		name_jp=side[0] + arm_s[0] + n_twist[0] + n_end[0],
		name_en=arm_s[1] + n_twist[1] + side[1] + n_end[1],
		pos=perp_pos, parent_idx=-99, deform_layer=0, deform_after_phys=False,
		has_rotate=True, has_translate=False, has_visible=False, has_enabled=False, has_ik=False,
		tail_usebonelink=True, tail=-1, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
		has_localaxis=False, has_externalparent=False,
	)
	# make armT_IK, pos=perp_pos, parent=elbow.parent, target=armTend, link=armT
	armTik = pmxstruct.PmxBone(
		name_jp=side[0] + arm_s[0] + n_twist[0] + n_ik[0],
		name_en=arm_s[1] + n_twist[1] + n_ik[1] + side[1],
		pos=perp_pos, parent_idx=-99, deform_layer=0, deform_after_phys=False,
		has_rotate=True, has_translate=True, has_visible=False, has_enabled=False, has_ik=True,
		tail_usebonelink=True, tail=-1, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
		has_localaxis=False, has_externalparent=False,
		ik_target_idx=-99, ik_numloops=ik_numloops, ik_angle=ik_angle, ik_links=[pmxstruct.PmxBoneIkLink(idx=-99)]
	)
	
	# insert these 6 bones
	# TODO: create more efficient function for multi-insert? nah, this is fine
	insert_single_bone(pmx, armD, armD_idx)
	insert_single_bone(pmx, armDend, armDend_idx)
	insert_single_bone(pmx, armDik, armDik_idx)
	insert_single_bone(pmx, armT, armT_idx)
	insert_single_bone(pmx, armTend, armTend_idx)
	insert_single_bone(pmx, armTik, armTik_idx)
	# fix all references to other bones (-99s)
	armD.tail = armDend_idx
	armT.tail = armTend_idx
	armD.parent_idx = arm.parent_idx
	armDend.parent_idx = armD_idx
	armDik.parent_idx = elbow.parent_idx
	armT.parent_idx = armD_idx
	armTend.parent_idx = armT_idx
	armTik.parent_idx = elbow.parent_idx
	armDik.ik_target_idx = armDend_idx
	armDik.ik_links[0].idx = armD_idx
	armTik.ik_target_idx = armTend_idx
	armTik.ik_links[0].idx = armT_idx
	
	
	# 5, modify the armtwist-sub bones
	# first go back from obj to indices, since the bones moved
	armtwist_sub = [b.idx_within(pmx.bones) for b in armtwist_sub_obj]
	for b_idx in armtwist_sub:
		bone = pmx.bones[b_idx]
		# change parent from arm to armD
		bone.parent_idx = armD_idx
		# change partial inherit from armtwist to armT
		bone.inherit_parent_idx = armT_idx
	
	
	# 6, insert additional armtwist-sub bones and transfer weight to them
	
	# first, check whether armtwistX would receive any weights/RBs
	# note, transferring from armtwist to armtwist changes nothing, this is harmless, just for looking
	armtwistX_used = transfer_to_armtwist_sub(pmx, armtwist_idx, armtwist_idx)
	if armtwistX_used:
		asdf = len(armtwist_sub) + 1
		# make armtwistX, pos=armtwist.pos, parent=armD_idx, inherit armT=1.00
		armtwistX = pmxstruct.PmxBone(
			name_jp= side[0] + armtwist_s[0] + str(asdf),
			name_en= armtwist_s[1] + str(asdf) + side[1],
			pos=armtwist.pos, parent_idx=-99, deform_layer=0, deform_after_phys=False,
			has_rotate=True, has_translate=False, has_visible=False, has_enabled=True, has_ik=False,
			tail_usebonelink=True, tail=-1, inherit_rot=True, inherit_trans=False, inherit_parent_idx=-99, inherit_ratio=1.00,
			has_fixedaxis=False, has_localaxis=False, has_externalparent=False,
		)
		# insert armtwistX at max(armtwist_sub) + 1
		armtwistX_idx = max(armtwist_sub)+1
		insert_single_bone(pmx, armtwistX, armtwistX_idx)
		# fix references to other bones
		armtwistX.parent_idx = armD_idx
		armtwistX.inherit_parent_idx = armT_idx
		
		# transfer all weight and rigidbody references from armtwist to armtwistX
		# this time the return val is not needed
		transfer_to_armtwist_sub(pmx, armtwist_idx, armtwistX_idx)
		armtwist_sub_obj.append(armtwistX)
		
	# second, do the same thing for armtwist0
	armtwist0_used = transfer_to_armtwist_sub(pmx, arm_idx, arm_idx)
	if armtwist0_used:
		# make armtwist0, pos=arm.pos, parent=armD_idx, inherit armT=0.00
		armtwist0 = pmxstruct.PmxBone(
			name_jp= side[0] + armtwist_s[0] + "0",
			name_en= armtwist_s[1] + "0" + side[1],
			pos=arm.pos, parent_idx=-99, deform_layer=0, deform_after_phys=False,
			has_rotate=True, has_translate=False, has_visible=False, has_enabled=True, has_ik=False,
			tail_usebonelink=True, tail=-1, inherit_rot=True, inherit_trans=False, inherit_parent_idx=-99, inherit_ratio=0.00,
			has_fixedaxis=False, has_localaxis=False, has_externalparent=False,
		)
		# insert armtwist0 at min(armtwist_sub)
		armtwist0_idx = min(armtwist_sub)
		insert_single_bone(pmx, armtwist0, armtwist0_idx)
		# fix references to other bones
		armtwist0.parent_idx = armD_idx
		armtwist0.inherit_parent_idx = armT_idx
		
		# transfer all weight and rigidbody references from arm to armtwist0
		# this time the return val is not needed
		transfer_to_armtwist_sub(pmx, arm_idx, armtwist0_idx)
		armtwist_sub_obj.append(armtwist0)
	
	
	# 7, set the deform order of all the bones so that it doesn't break when armIK is added
	# what deform level should they start from?
	deform = max(arm.deform_layer, armtwist.deform_layer)
	armD.deform_layer = deform + 2
	armDend.deform_layer = deform + 2
	armDik.deform_layer = deform + 2
	armT.deform_layer = deform + 3
	armTend.deform_layer = deform + 3
	armTik.deform_layer = deform + 3
	for bone in armtwist_sub_obj:
		bone.deform_layer = deform + 4
	# TODO: fix deform for anything hanging off of the armtwist bones (rare but sometimes exists)
	
	
	# 8, fix shoulder-helper and elbow-helper if they exist
	# shoulder helper: parent=shoulder(C), inherit=arm
	# goto:            parent=shoulder(C), inherit=armD
	# elbow helper: parent=arm(twist), inherit=elbow
	# goto:         parent=armT,       inherit=elbowD
	
	# need to refresh elbow idx cuz it moved
	elbow_idx = elbow.idx_within(pmx.bones)
	for d, bone in enumerate(pmx.bones):
		# transfer "inherit arm" to "inherit armD"
		# this should be safe for all bones
		if bone.inherit_rot and bone.inherit_parent_idx == arm_idx:
			bone.inherit_parent_idx = armD_idx
			if d < armD_idx and bone.deform_layer <= armD.deform_layer:
				# need to ensure deform order is respected!
				bone.deform_layer = armD.deform_layer + 1
		# transfer "parent arm(twist)" to "parent armT"
		# this needs to exclude elbow, D_IK, T_IK, armtwist, arm
		if bone.parent_idx in (armtwist_idx, arm_idx):
			if d not in (elbow_idx, armDik_idx, armTik_idx, armtwist_idx, arm_idx):
				bone.parent_idx = armT_idx
				if d < armT_idx and bone.deform_layer <= armT.deform_layer:
					# need to ensure deform order is respected!
					bone.deform_layer = armT.deform_layer + 1
	
	
	# 9, detect & fix incorrect structure among primary bones
	# refresh list of armtwist_sub indixes cuz stuff was inserted
	armtwist_sub = max([b.deform_layer for b in armtwist_sub_obj])
	if elbow.parent_idx in armtwist_sub:
		newparent = max(arm_idx, armtwist_idx)
		core.MY_PRINT_FUNC("WARNING: fixing improper parenting for bone '%s'" % elbow.name_jp)
		core.MY_PRINT_FUNC("parent was '%s', changing to '%s'" % 
			(pmx.bones[elbow.parent_idx].name_jp, pmx.bones[newparent].name_jp))
		core.MY_PRINT_FUNC("if this bone has a 'helper bone' please change its parent in the same way")
		elbow.parent_idx = newparent
	
	
	# done with this function???
	return None


def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	
	core.MY_PRINT_FUNC("L upper arm...")
	make_autotwist_segment(pmx, jp_l, jp_arm, jp_armtwist, jp_elbow)
	
	core.MY_PRINT_FUNC("R upper arm...")
	make_autotwist_segment(pmx, jp_r, jp_arm, jp_armtwist, jp_elbow)
	
	core.MY_PRINT_FUNC("L lower arm...")
	make_autotwist_segment(pmx, jp_l, jp_elbow, jp_wristtwist, jp_wrist)
	
	core.MY_PRINT_FUNC("R lower arm...")
	make_autotwist_segment(pmx, jp_r, jp_elbow, jp_wristtwist, jp_wrist)
	
	# if i want to, set elbowD parent to armT...?
	# if i want to, set wrist parent to elbowT...?
	# that's what the original does, but why? why would I want that?
	# armT should have exactly the same deformations as armtwist
	# it's better to have the twist-rigs be isolated from eachother
	
	
	# TODO: examine leg system! not universal because nobody has legtwist bones to hijack but worth understanding
	
	
	# write out
	output_filename_pmx = input_filename_pmx[0:-4] + "_autotwist.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 09/13/2020 - v5.01")
	if DEBUG:
		# print info to explain the purpose of this file
		core.MY_PRINT_FUNC(helptext)
		core.MY_PRINT_FUNC("")
		
		main()
		core.pause_and_quit("Done with everything! Goodbye!")
	else:
		try:
			# print info to explain the purpose of this file
			core.MY_PRINT_FUNC(helptext)
			core.MY_PRINT_FUNC("")
			
			main()
			core.pause_and_quit("Done with everything! Goodbye!")
		except (KeyboardInterrupt, SystemExit):
			# this is normal and expected, do nothing and die normally
			pass
		except Exception as ee:
			# if an unexpected error occurs, catch it and print it and call pause_and_quit so the window stays open for a bit
			core.MY_PRINT_FUNC(ee.__class__.__name__, ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
