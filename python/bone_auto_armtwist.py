# Nuthouse01 - 09/13/2020 - v5.01
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
	from . import nuthouse01_pmx_struct as pmxstruct
	from ._prune_unused_bones import insert_single_bone
except ImportError as eee:
	try:
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
pmx_magic_armtwist_bones:
This will generate "magic armtwist bones" that will automatically fix pinching at shoulders/elbows.
You can also create these twist rigs for the upper legs if you wish.

For best results, this requires that all "helper" bones be "flattened" into their parents.
If the standard 3-bone armtwist rig exists, they will automatically be flattened & removed.

Output: model PMX file '[modelname]_magictwist.pmx'
'''

# left and right prefixes
jp_l = "左"
jp_r = "右"
# names for relevant bones
jp_arm =		"腕"
jp_armtwist =	"腕捩"
jp_elbow =		"ひじ"
jp_wristtwist = "手捩"
jp_wrist =		"手首"

jp_leg =		"足"
jp_knee =		"ひざ"
jp_foot =		"足首"
jp_leg_d =		"足D"
jp_knee_d =		"ひざD"
jp_foot_d =		"足首D"



# parameters
n_base = "D"
n_twist = "T"
n_ik = "_IK"
n_end = "先"

perpendicular_offset_dist = 1.00

ik_numloops = 100
ik_angle = 5  # degrees


'''
initial bone order:

shoulderC
arm
armtwist
armtwist1
armtwist2
armtwist3
elbow

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

def transfer_weight_references(pmx: pmxstruct.Pmx, from_bone:int, to_bone:int):
	# any weights currently set to "from_bone" get replaced with "to_bone"
	weighttype_to_len = {0:1, 1:2, 2:4, 3:2, 4:4}
	for v in pmx.verts:
		for i in range(weighttype_to_len[v.weighttype]):
			if v.weight[i] == from_bone:
				v.weight[i] = to_bone
	return None

def transfer_rigidbody_references(pmx: pmxstruct.Pmx, from_bone:int, to_bone:int):
	# move all rigidbodies attached to "from_bone" to "to_bone" instead
	for rb in pmx.rigidbodies:
		if rb.bone_idx == from_bone:
			rb.bone_idx = to_bone
	return None


def make_autotwist_segment(pmx: pmxstruct.Pmx, side:str, arm_s:str, armtwist_s:str, elbow_s:str):
	# note: will be applicable to elbow-wristtwist-wrist as well! just named like armtwist for simplicity
	
	# 1, locate arm/armtwist/elbow idx and obj
	r = []
	for n in (arm_s, armtwist_s, elbow_s):
		n2 = side + n
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
	armtwist_sub = []
	# # dont forget to refresh elbow_idx
	# elbow_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == side + elbow_s)
	for d, bone in enumerate(pmx.bones):
		# anything that partial inherit from armtwist (except arm)
		if bone.inherit_rot == True and bone.inherit_parent_idx == armtwist_idx:
			if d == arm_idx: continue
			armtwist_sub.append(d)
		# anything that has armtwist as parent (except elbow or elbow helper (full parent armtwist, partial parent elbow))
		if bone.parent_idx == armtwist_idx:
			if d == elbow_idx: continue
			if bone.inherit_rot == True and bone.inherit_parent_idx == elbow_idx: continue
			armtwist_sub.append(d)
	armtwist_sub = list(set(armtwist_sub))  # just in case idk
	# convert to names
	armtwist_sub_names = [pmx.bones[b].name_jp for b in armtwist_sub]
	
	
	# 3, calculate "perpendicular" location
	# get axis from arm to elbow, normalize to 1
	delta = [b - a for a, b in zip(arm.pos, elbow.pos)]
	# normalize
	length = core.my_euclidian_distance(delta)
	unit = [t / length for t in delta]
	# calc cross-product between this and [0,0,1]
	perpendicular = core.my_cross_product(unit, [0, 0, 1])
	# if result has negative y, invert
	if perpendicular[1] < 0:
		perpendicular = [p * -1 for p in perpendicular]
	# normalize to perpendicular_offset_dist
	length = core.my_euclidian_distance(perpendicular)
	perpendicular = [perpendicular_offset_dist * t / length for t in perpendicular]
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
		name_jp=side + arm_s + n_base, name_en="",
		pos=arm.pos, parent_idx=-99, deform_layer=0, deform_after_phys=False,
		has_rotate=True, has_translate=False, has_visible=False, has_enabled=True, has_ik=False,
		tail_usebonelink=True, tail=-99, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
		has_localaxis=arm.has_localaxis, localaxis_x=arm.localaxis_x, localaxis_z=arm.localaxis_z,
		has_externalparent=False,
	)
	# make armDend, pos=elbow.pos, parent=armD_idx
	armDend = pmxstruct.PmxBone(
		name_jp=side + arm_s + n_base + n_end, name_en="",
		pos=elbow.pos, parent_idx=-99, deform_layer=0, deform_after_phys=False,
		has_rotate=True, has_translate=False, has_visible=False, has_enabled=True, has_ik=False,
		tail_usebonelink=True, tail=-1, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
		has_localaxis=False, has_externalparent=False,
	)
	# make armD_IK, pos=elbow.pos, parent=elbow.parent, target=armDend, link=armD
	armDik = pmxstruct.PmxBone(
		name_jp=side + arm_s + n_base + n_ik, name_en="",
		pos=elbow.pos, parent_idx=-99, deform_layer=0, deform_after_phys=False,
		has_rotate=True, has_translate=True, has_visible=False, has_enabled=True, has_ik=True,
		tail_usebonelink=True, tail=-1, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
		has_localaxis=False, has_externalparent=False,
		ik_target_idx=-99, ik_numloops=ik_numloops, ik_angle=ik_angle, ik_links=[pmxstruct.PmxBoneIkLink(idx=-99)]
	)
	
	# make armT, pos=elbow.pos, parent=armD_idx, tail=armTend
	armT = pmxstruct.PmxBone(
		name_jp=side + arm_s + n_twist, name_en="",
		pos=elbow.pos, parent_idx=-99, deform_layer=0, deform_after_phys=False,
		has_rotate=True, has_translate=False, has_visible=False, has_enabled=True, has_ik=False,
		tail_usebonelink=True, tail=-99, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
		has_localaxis=False, has_externalparent=False,
	)
	# make armTend, pos=perp_pos, parent=armT_idx
	armTend = pmxstruct.PmxBone(
		name_jp=side + arm_s + n_twist + n_end, name_en="",
		pos=perp_pos, parent_idx=-99, deform_layer=0, deform_after_phys=False,
		has_rotate=True, has_translate=False, has_visible=False, has_enabled=True, has_ik=False,
		tail_usebonelink=True, tail=-1, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
		has_localaxis=False, has_externalparent=False,
	)
	# make armT_IK, pos=perp_pos, parent=elbow.parent, target=armTend, link=armT
	armTik = pmxstruct.PmxBone(
		name_jp=side + arm_s + n_twist + n_ik, name_en="",
		pos=perp_pos, parent_idx=-99, deform_layer=0, deform_after_phys=False,
		has_rotate=True, has_translate=True, has_visible=False, has_enabled=True, has_ik=True,
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
	# first go back from names to indices, since the bones moved
	armtwist_sub = [core.my_list_search(pmx.bones, lambda x: x.name_jp == n) for n in armtwist_sub_names]
	for b_idx in armtwist_sub:
		bone = pmx.bones[b_idx]
		# change parent from arm to armD
		bone.parent_idx = armD_idx
		# change partial inherit from armtwist to armT
		bone.inherit_parent_idx = armT_idx
	
	
	# 6, insert additional armtwist-sub bones and transfer weight to them
	# just assume they are needed, if they're useless they're harmless
	asdf = len(armtwist_sub) + 1
	# todo: do i want pos to be armtwist or elbow ?
	# make armtwistX, pos=armtwist.pos, parent=armD_idx, inherit armT=1.00
	armtwistX = pmxstruct.PmxBone(
		name_jp= side + armtwist_s + str(asdf), name_en="",
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
	
	# transfer all weight from armtwist to armtwistX
	transfer_weight_references(pmx, armtwist_idx, armtwistX_idx)
	# transfer all rigidbody references from armtwist to armtwistX
	transfer_rigidbody_references(pmx, armtwist_idx, armtwistX_idx)
	
	# make armtwist0, pos=arm.pos, parent=armD_idx, inherit armT=0.00
	armtwist0 = pmxstruct.PmxBone(
		name_jp= side + armtwist_s + "0", name_en="",
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

	# transfer all weight from arm to armtwist0
	transfer_weight_references(pmx, arm_idx, armtwist0_idx)
	# transfer all rigidbody references from arm to armtwist0
	transfer_rigidbody_references(pmx, arm_idx, armtwist0_idx)

	# done with this function???
	return None


def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")
	# input_filename_pmx = "../../python_scripts/grasstest_better.pmx"
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	##################################
	# user flow:
	# first ask whether they want to add armtwist, yes/no
	# second ask whether they want to add legtwist, yes/no
	# then do it
	# then write out to file
	##################################
	
	core.MY_PRINT_FUNC("Left upper arm...")
	make_autotwist_segment(pmx, jp_l, jp_arm, jp_armtwist, jp_elbow)
	
	core.MY_PRINT_FUNC("Right upper arm...")
	make_autotwist_segment(pmx, jp_r, jp_arm, jp_armtwist, jp_elbow)
	
	core.MY_PRINT_FUNC("Left lower arm...")
	make_autotwist_segment(pmx, jp_l, jp_elbow, jp_wristtwist, jp_wrist)
	
	core.MY_PRINT_FUNC("Right lower arm...")
	make_autotwist_segment(pmx, jp_r, jp_elbow, jp_wristtwist, jp_wrist)
	
	# todo: if i want to, set elbowD parent to armT...?
	
	# todo: if i want to, set wrist parent to elbowT...?
	
	
	
	# TODO: examine leg system! not universal because nobody has legtwist bones to hijack but worth understanding
	
	
	# 11. write out
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
