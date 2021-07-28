import math
from collections import defaultdict

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.overall_cleanup.weight_cleanup import normalize_weights
from mmd_scripting.wip.merge_bones import transfer_bone_weights

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.00 - 6/10/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


helptext = '''=================================================
bone_make_sdef_auto_armtwist:
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
# suffix used for new magicarmtwist bones
yz_suffix =		"YZ"
# these are the bones to collapse for each stage
# collapse existing 3-bone armtwist rigs or magic armtwist rigs
old_armtwist_rigs =		(jp_armtwist, "腕捩1", "腕捩2", "腕捩3", "腕捩１", "腕捩２", "腕捩３", jp_arm + yz_suffix)
old_wristtwist_rigs =	(jp_wristtwist, "手捩1", "手捩2", "手捩3", "手捩１", "手捩２", "手捩３", jp_elbow + yz_suffix)
old_legtwist_rigs =		(jp_leg + yz_suffix, jp_leg_d + yz_suffix)

# bezier control points given as (x,y) where values are from 0-128
# you probably want point1 to be less than point2 in both axes but I'm not your boss
BEZIER_POINTS_ARM = 	(25,25),(103,103)
BEZIER_POINTS_WRIST = 	(25,25),(103,103)
BEZIER_POINTS_LEG = 	(25,25),(103,103)

# startpoint, endpoint, preferredparent, bonestocollapse
armset =	(jp_arm,	jp_elbow,	jp_armtwist,	old_armtwist_rigs,		BEZIER_POINTS_ARM)
wristset =	(jp_elbow,	jp_wrist,	jp_wristtwist,	old_wristtwist_rigs,	BEZIER_POINTS_WRIST)
legset =	(jp_leg,	jp_knee,	jp_leg,			old_legtwist_rigs,		BEZIER_POINTS_LEG)
legset_d =	(jp_leg_d,	jp_knee_d,	jp_leg_d,		old_legtwist_rigs,		BEZIER_POINTS_LEG)

newik_loops = 40
newik_angle = 90
# IK params:
# in legs, loops=40, angle=114.5916
# in armYZ, loops=10, angle=57


# 1 = A = overwrite, just replace weights with blended weights
# 2 = B = dont touch, just leave as-is
# 3 = CA = subdivide limb weight w/ BDEF if possible, use A if not possible
# 4 = CB = subdivide limb weight w/ BDEF if possible, use B if not possible
BLEED_HANDLING_MODE = 3


# 1 = liberal bounds, select all good points but also some bad points (bleeding)
# 0 = conservative bounds, select bounds such that NO bad points are selected, but some good points are missed
# this selects where between the two extremes you want to draw the border
ENDPOINT_AVERAGE_FACTOR = 0.7


# TODO: endpoint average factor: 7?
# TODO: bleed handling mode: C
# TODO: legs
# TODO: how to handle 5-dict: trim
# TODO: how to handle SDEF elbows: dont touch
# TODO: help text


weight_type_to_len = {0:1, 1:2, 2:4, 3:2, 4:4}

def dict_from_weights(w):
	wd = defaultdict(float)
	for pair in w:
		wd[pair[0]] += pair[1]
	return wd

	

'''
NEW PLAN:
*1. verify that start/end exist
*2. decide if 'preferred' exists and whether it should be used
*3. attempt to collapse known armtwist rig names onto 'parent' so that the base case is further automated
*4. run the weight-cleanup function
*5. create new bones: armYZ, armYZend, armYZIK
*6. build the bezier curve
*7. find relevant verts & determine unbounded percentile for each
	trig rotation stuff
	calculate centerpoint here so i don't need to re-do the trig
	return [relavant], [percentile], [centers]
	dont need trig anywhere else for anything else
8. use X or Y to choose border points, print for debugging
*9. divvy weights
	% < start means above shoulder, just replace arm with armYZ
	% > end means below elbow, do nothing
	if vert ONLY has weight for arm bone, then it is "normal case"
		1 weight ==> 2 weights, therefore safely set to SDEF
	otherwise, then it is a "bleeder"
		use A/B/C to handle, or maybe dynamically choose between them?
10. final weight cleanup
11. write to file
'''

def calculate_percentiles(pmx: pmxstruct.Pmx, bone_arm: int, bone_elbow: int, bone_hasweight: int):
	retme_verts = []
	retme_percents = []
	retme_centers = []
	
	axis_start = pmx.bones[bone_arm].pos
	axis_end = pmx.bones[bone_elbow].pos
	
	# 1. determine the axis from arm to elbow
	deltax, deltay, deltaz = [e - s for e, s in zip(axis_end, axis_start)]
	startx, starty, startz = axis_start
	axis_length = core.my_euclidian_distance((deltax, deltay, deltaz))
	
	# 2. determine y-rot and z-rot needed to make elbow have same Y/Z, elbowX > armX... first y-rotate, THEN z-rotate
	# ay = -atan2(dz, dx)
	theta_y = -math.atan2(deltaz, deltax)
	# apply 2d Y-rotation
	inter1x, inter1z = core.rotate2d(origin=(startx, startz), angle=theta_y, point=(axis_end[0], axis_end[2]))
	# az = -atan2(dy, dx)........ x position has changed, delta needs recalculated! y delta was untouched tho
	theta_z = -math.atan2(deltay, inter1x - startx)
	# now have found theta_y and theta_z
	
	# 3. collect all vertices controlled by bone_hasweight
	for d, vert in enumerate(pmx.verts):
		weightidx = [foo for foo,_ in vert.weight]
		if bone_hasweight in weightidx:
			# if this vert is controlled by bone_hasweight, then it is relevant! save it!
			# most of the verts aren't going to have 0 weight for a bone, dont worry about checking that
			retme_verts.append(d)
			
			# 4. calculate how far along the axis each vertex lies
			# percentile: 0.0 means at the startpoint, 1.0 means at the endpoint
			# apply 2d Y-rotation: ignore Y-axis, this will cause Z==Z
			inter1x, inter1z = core.rotate2d(origin=(startx, startz), angle=theta_y, point=(vert.pos[0], vert.pos[2]))
			# apply 2d Z-rotation: ignore Z-axis, this will cause Y==Y
			finalx, finaly = core.rotate2d(origin=(startx, starty), angle=theta_z, point=(inter1x, vert.pos[1]))
			# calculate the actual percentile
			v_percentile = (finalx - startx) / axis_length
			retme_percents.append(v_percentile)
			
			# 5. calculate the centerpoint for if this bone is determined to use SDEF
			# c should lie on this start-end axis
			# to get c, after applying yrot zrot to a vertex, keep x unchanged and set y/z to match the startbone pos (point being rotated around)
			# center_before = finalx, starty, startz
			# then apply trig in reverse order: zrot, yrot
			# apply 2d Z-rotation: ignore Z-axis
			inter2x, inter2y = core.rotate2d(origin=(startx, starty), angle=-theta_z, point=(finalx, starty))
			# apply 2d Y-rotation: ignore Y-axis
			centerx, centerz = core.rotate2d(origin=(startx, startz), angle=-theta_y, point=(inter2x, startz))
			center = centerx, inter2y, centerz
			# result is the point along the axis that is closest to the vertex
			retme_centers.append(center)
		pass  # close the loop
	return retme_verts, retme_percents, retme_centers


# pop all entries from the dict with value==0
def trim_dict(wdict):
	keys = list(wdict.keys())
	for k in keys:
		if wdict[k] == 0:
			wdict.pop(k)
	return wdict

# !!! how to divvy the weights !!! make this a function(pmx, arm#, arm[twist]#, elbow#) !!!
def divvy_weights(pmx: pmxstruct.Pmx, vert_zip, axis_limits, bone_hasweight, bone_getsweight, bezier):
	
	# (verts, percentiles, centers) = vert_zip
	# (axis_start, axis_end) = axis_limits # (for SDEF params only)
	# (percent_start, percent_end) = percent_limits
	
	num_modified_verts = 0
	num_bleeders = 0
	for d, (vidx, percentile, center) in enumerate(vert_zip):
		# 1. if % >= 1.0 means the vert is below the elbow... do nothing
		if percentile >= 1.0: continue
		
		vert = pmx.verts[vidx]
		vert: pmxstruct.PmxVertex
		
		# 2. % <= 0.0 means above shoulder, just replace arm with armYZ, don't change anything else
		if percentile <= 0.0:
			for pair in vert.weight:
				if pair[0] == bone_hasweight:
					pair[0] = bone_getsweight
			continue
			
		wdict = dict_from_weights(vert.weight)
		# this is a rare case but it should still be handled
		if wdict[bone_hasweight] == 0: continue
		
		# 3. use percentile as input to bezier curve, [0.0-1.0]->bezier->[0.0-1.0]
		bez_percentile = bezier.approximate(percentile)
		
		####################################################
		# now I am left with only percentiles between 0,1 but not including 0,1: these verts will be blended!
		# however there may be some "bleeder" weight verts that need dealt with
		
		num_modified_verts += 1
		if len(wdict) == 1:
			# 4. if this has 100% weight on HAS, then handle it the normal way: divide weights between HAS and GETS and save as SDEF
			# blend ratio: replace HAS with (HAS = HAS*blend) + (GETS = HAS*(1-blend))
			vert.weighttype = pmxstruct.WeightMode.SDEF  # type = SDEF = (b1, b2, b1w, c1, c2, c3, r01, r02, r03, r11, r12, r13)
			# set the component bones and the blend ratio, dont worry about order
			wnew = [[bone_hasweight, bez_percentile], [bone_getsweight, 1-bez_percentile]]
			vert.weight = wnew
			# c = center
			# r0 = axis start = armbone
			# r1 = axis end = elbowbone
			wsdefnew = [center, axis_limits[0], axis_limits[1]]
			vert.weight_sdef = wsdefnew
		else:
			# 5. if this is a bleeder, it has weights from other 'helper' bones inside what i defined as the rotation-blend region
			# decide how to handle it
			# TODO: decide what the best handling method is
			num_bleeders += 1
			
			if BLEED_HANDLING_MODE == 1:
				# A. overwrite/ignore: pretend it was not a bleeder, set to blended SDEF anyway
				vert.weighttype = pmxstruct.WeightMode.SDEF  # type = SDEF = (b1, b2, b1w, c1, c2, c3, r01, r02, r03, r11, r12, r13)
				# set the component bones and the blend ratio, dont worry about order
				wnew = [[bone_hasweight, bez_percentile], [bone_getsweight, 1 - bez_percentile]]
				vert.weight = wnew
				# c = center
				# r0 = axis start = armbone
				# r1 = axis end = elbowbone
				wsdefnew = [center, axis_limits[0], axis_limits[1]]
				vert.weight_sdef = wsdefnew
				continue
			if BLEED_HANDLING_MODE == 2:
				# B. dont touch: do nothing! leave as-is!
				continue
			# else:
			# C. subdivide components: if BDEF, subdivide components like i originally planned
			
			# blend ratio: replace HAS with HAS = HAS*blend + GETS = HAS*(1-blend)
			wcurr = wdict[bone_hasweight]
			# bez==1 and bez==0 conditions are impossible here, they were handled earlier
			wdict[bone_hasweight] = wcurr * bez_percentile  # new value for old bone 'HAS' = twistbone
			wdict[bone_getsweight] = wcurr * (1 - bez_percentile)  # new value for new bone 'GETS' = armYZ
			
			# reduce wdict to only 'real'/nonzero weights, cuz i need to know how long it is
			if len(wdict) > 4:
				wdict = trim_dict(wdict)
				# confirm that this is good enough, if not then warn & trim the lowest-weight item... hopefully this never happens
				if len(wdict) > 4:
					core.MY_PRINT_FUNC("something has gone horribly wrong")
					print(vidx)
					print(wdict)
					together = list(wdict.items())  # zip
					together.sort(reverse=True, key=lambda x: x[1])  # sort
					wdict.pop(together[-1][0])
						
			# 7. now rebuild the weight vector & write it into the vertex
			blend_vector = sorted(list(wdict.items()), key=lambda x: x[1], reverse=True)
			if vert.weighttype == pmxstruct.WeightMode.SDEF:  # SDEF
				print("forcing BDEF but input is SDEF, i'll just ignore it!")
				pass
			else:  # QDEF
				# qdef -> qdef
				# blend_vector is a list of key-value pairs, key=idx value=weight, so its already good!
				vert.weight = [list(a) for a in blend_vector]
				if vert.weighttype != pmxstruct.WeightMode.QDEF:
					# BDEF1 BDEF2 BDEF4 -> BDEF4, but QDEF stays QDEF
					vert.weighttype = pmxstruct.WeightMode.BDEF4
			pass  # end bleeder section
		pass  # end for-loop
	
	# done! return only stats, modifies PMX list directly
	return num_modified_verts, num_bleeders


def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	# input_filename_pmx = "../../python_scripts/grasstest_better.pmx"
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	##################################
	# user flow:
	# first ask whether they want to add armtwist, yes/no
	# second ask whether they want to add legtwist, yes/no
	# then do it
	# then write out to file
	##################################
	
	working_queue = []
	
	s = core.MY_SIMPLECHOICE_FUNC((1,2), ["Do you wish to add magic twistbones to the ARMS?","1 = Yes, 2 = No"])
	if s == 1:
		# add upperarm set and lowerarm set to the queue
		working_queue.append(armset)
		working_queue.append(wristset)
		pass
	s = core.MY_SIMPLECHOICE_FUNC((1, 2), ["Do you wish to add magic twistbones to the LEGS?", "1 = Yes, 2 = No"])
	if s == 1:
		# TODO detect whether d-bones exist or not
		# add legs or d-legs set to the queue
		pass
	
	if not working_queue:
		core.MY_PRINT_FUNC("Nothing was changed")
		core.MY_PRINT_FUNC("Done")
		return None
	
	# for each set in the queue,
	for boneset in working_queue:
		# boneset = (start, end, preferred, oldrigs, bezier)
		for side in [jp_l, jp_r]:
			# print(side)
			# print(boneset)
			# 1. first, validate that start/end exist, these are required
			# NOTE: remember to prepend 'side' before all jp names!
			start_jp = side+boneset[0]
			start_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == start_jp)
			if start_idx is None:
				core.MY_PRINT_FUNC("ERROR: standard bone '%s' not found in model, this is required!" % start_jp)
				continue
			end_jp = side+boneset[1]
			end_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == end_jp)
			if end_idx is None:
				core.MY_PRINT_FUNC("ERROR: standard bone '%s' not found in model, this is required!" % end_jp)
				continue
			
			# 2. determine whether the 'preferredparent' exists and therefore what to acutally use as the parent
			parent_jp = side+boneset[2]
			parent_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == parent_jp)
			if parent_idx is None:
				parent_idx = start_idx
			
			# 3. attempt to collapse known armtwist rig names onto 'parent' so that the base case is further automated
			# for each bonename in boneset[3], if it exists, collapse onto boneidx parent_idx
			for bname in boneset[3]:
				rig_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == side+bname)
				if rig_idx is None: continue  # if not found, try the next
				# when it is found, what 'factor' do i use?
				# print(side+bname)
				if pmx.bones[rig_idx].inherit_rot and pmx.bones[rig_idx].inherit_parent_idx == parent_idx and pmx.bones[rig_idx].inherit_ratio != 0:
					# if using partial rot inherit AND inheriting from parent_idx AND ratio != 0, use that
					# think this is good, if twistbones exist they should be children of preferred
					f = pmx.bones[rig_idx].inherit_ratio
				elif pmx.bones[rig_idx].parent_idx == parent_idx:
					# this should be just in case?
					f = 1
				elif pmx.bones[rig_idx].parent_idx == start_idx:
					# this should catch magic armtwist bones i previously created
					f = 1
				else:
					core.MY_PRINT_FUNC("Warning, found unusual relationship when collapsing old armtwist rig, assuming ratio=1")
					f = 1
				transfer_bone_weights(pmx, parent_idx, rig_idx, f)
				pass
			# also collapse 'start' onto 'preferredparent' if it exists... want to transfer weight from 'arm' to 'armtwist'
			# if start == preferredparent this does nothing, no harm done
			transfer_bone_weights(pmx, parent_idx, start_idx, scalefactor=1)
			
			# 4. run the weight-cleanup function
			normalize_weights(pmx)
			
			# 5. append 3 new bones to end of bonelist
			# 	armYZ gets pos = start pos & parent = start parent
			basename_jp = pmx.bones[start_idx].name_jp
			armYZ_new_idx = len(pmx.bones)
			# armYZ = [basename_jp + yz_suffix, local_translate(basename_jp + yz_suffix)]  # name_jp,en
			# armYZ += pmx[5][start_idx][2:]					# copy the whole rest of the bone
			# armYZ[10:12] = [False, False]					# visible=false, enabled=false
			# armYZ[12:14] = [True, [armYZ_new_idx + 1]]		# tail type = tail, tail pointat = armYZend
			# armYZ[14:19] = [False, False, [], False, []]	# disable partial inherit + fixed axis
			# # local axis is copy
			# armYZ[21:25] = [False, [], False, []]			# disable ext parent + ik
			armYZ = pmxstruct.PmxBone(
				name_jp=basename_jp + yz_suffix,
				name_en="",
				pos=pmx.bones[start_idx].pos,
				parent_idx=pmx.bones[start_idx].parent_idx,
				deform_layer=pmx.bones[start_idx].deform_layer,
				deform_after_phys=pmx.bones[start_idx].deform_after_phys,
				has_localaxis=pmx.bones[start_idx].has_localaxis,
				localaxis_x=pmx.bones[start_idx].localaxis_x, localaxis_z=pmx.bones[start_idx].localaxis_z,
				tail_usebonelink=True, tail=armYZ_new_idx+1,
				has_rotate=True, has_translate=True, has_visible=False, has_enabled=True,
				has_ik=False, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
				has_externalparent=False,
			)
			
			# 	armYZend gets pos = end pos & parent = armYZ
			# armYZend = [basename_jp + yz_suffix + "先", local_translate(basename_jp + yz_suffix + "先")]  # name_jp,en
			# armYZend += pmx[5][end_idx][2:]					# copy the whole rest of the bone
			# armYZend[5] = armYZ_new_idx						# parent = armYZ
			# armYZend[10:12] = [False, False]				# visible=false, enabled=false
			# armYZend[12:14] = [True, [-1]]					# tail type = tail, tail pointat = none
			# armYZend[14:19] = [False, False, [], False, []]	# disable partial inherit + fixed axis
			# # local axis is copy
			# armYZend[21:25] = [False, [], False, []]		# disable ext parent + ik
			armYZend = pmxstruct.PmxBone(
				name_jp=basename_jp + yz_suffix + "先",
				name_en="",
				pos=pmx.bones[end_idx].pos,
				parent_idx=armYZ_new_idx,
				deform_layer=pmx.bones[end_idx].deform_layer,
				deform_after_phys=pmx.bones[end_idx].deform_after_phys,
				has_localaxis=pmx.bones[end_idx].has_localaxis,
				localaxis_x=pmx.bones[end_idx].localaxis_x, localaxis_z=pmx.bones[end_idx].localaxis_z,
				tail_usebonelink=True, tail=-1,
				has_rotate=True, has_translate=True, has_visible=False, has_enabled=True,
				has_ik=False, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
				has_externalparent=False,
			)


			# # 	elbowIK gets pos = end pos & parent = end parent
			# armYZIK = [basename_jp + yz_suffix + "IK", local_translate(basename_jp + yz_suffix + "IK")]  # name_jp,en
			# armYZIK += pmx[5][end_idx][2:]					# copy the whole rest of the bone
			# armYZIK[10:12] = [False, False]					# visible=false, enabled=false
			# armYZIK[12:14] = [True, [-1]]					# tail type = tail, tail pointat = none
			# armYZIK[14:19] = [False, False, [], False, []]	# disable partial inherit + fixed axis
			# # local axis is copy
			# armYZIK[21:23] = [False, []]					# disable ext parent
			# armYZIK[23] = True								# ik=true
			# # add the ik info: [target, loops, anglelimit, [[link_idx, []], [link_idx, []]] ]
			# armYZIK[24] = [armYZ_new_idx+1, newik_loops, newik_angle, [[armYZ_new_idx, []]]]
			armYZIK = pmxstruct.PmxBone(
				name_jp=basename_jp + yz_suffix + "IK",
				name_en="",
				pos=pmx.bones[end_idx].pos,
				parent_idx=pmx.bones[end_idx].parent_idx,
				deform_layer=pmx.bones[end_idx].deform_layer,
				deform_after_phys=pmx.bones[end_idx].deform_after_phys,
				has_localaxis=pmx.bones[end_idx].has_localaxis,
				localaxis_x=pmx.bones[end_idx].localaxis_x, localaxis_z=pmx.bones[end_idx].localaxis_z,
				tail_usebonelink=True, tail=-1,
				has_rotate=True, has_translate=True, has_visible=False, has_externalparent=False,
				has_enabled=True, inherit_rot=False, inherit_trans=False, has_fixedaxis=False,
				has_ik=True,
				ik_target_idx=armYZ_new_idx+1, ik_numloops=newik_loops, ik_angle=newik_angle,
				ik_links=[pmxstruct.PmxBoneIkLink(idx=armYZ_new_idx)]
			)

			
			
			
			# now append them to the bonelist
			pmx.bones.append(armYZ)
			pmx.bones.append(armYZend)
			pmx.bones.append(armYZIK)
			
			# 6. build the bezier curve
			bezier_curve = core.MyBezier(boneset[4][0], boneset[4][1], resolution=50)
			
			# 7. find relevant verts & determine unbounded percentile for each
			(verts, percentiles, centers) = calculate_percentiles(pmx, start_idx, end_idx, parent_idx)
			
			if moreinfo:
				core.MY_PRINT_FUNC("Blending between bones '{}'/'{}'=ZEROtwist and '{}'/'{}'=FULLtwist".format(
					armYZ.name_jp, armYZ.name_en,
					pmx.bones[parent_idx].name_jp, pmx.bones[parent_idx].name_en
				))
				core.MY_PRINT_FUNC("   Found %d potentially relevant vertices" % len(verts))
			
			# 8. use X or Y to choose border points, print for debugging, also scale the percentiles
			# first sort ascending by percentile value
			vert_zip = list(zip(verts, percentiles, centers))
			vert_zip.sort(key=lambda x: x[1])
			verts, percentiles, centers = zip(*vert_zip)  # unzip
			
			# X. highest point mode
			# "liberal" endpoints: extend as far as i can, include all good stuff even if i include some bad stuff with it
			# start at each end and work inward until i find a vert controlled by only parent_idx
			i_min_liberal = 0
			i_max_liberal = len(verts) - 1
			i_min_conserv = -1
			i_max_conserv = len(verts)
			for i_min_liberal in range(0, len(verts)):		# start at head and work down,
				if pmx.verts[verts[i_min_liberal]].weighttype == pmxstruct.WeightMode.BDEF1:  	# if the vertex is BDEF1 type,
					break  									# then stop looking,
			p_min_liberal = percentiles[i_min_liberal]		# and save the percentile it found.
			for i_max_liberal in reversed(range(0, len(verts))): # start at tail and work up,
				if pmx.verts[verts[i_max_liberal]].weighttype == pmxstruct.WeightMode.BDEF1:  	# if the vertex is BDEF1 type,
					break  									# then stop looking,
			p_max_liberal = percentiles[i_max_liberal]		# and save the percentile it found.
			# Y. lowest highest point mode
			# "conservative" endpoints: define ends such that no bad stuff exists within bounds, even if i miss some good stuff
			# start in the middle and work outward until i find a vert NOT controlled by only parent_idx, then back off 1
			# where is the middle? use "bisect_left"
			middle = core.bisect_left(percentiles, 0.5)
			for i_min_conserv in reversed(range(middle - 1)): # start in middle, work toward head,
				if pmx.verts[verts[i_min_conserv]].weighttype != pmxstruct.WeightMode.BDEF1:  	# if the vertex is NOT BDEF1 type,
					break  									# then stop looking,
			i_min_conserv += 1								# and step back 1 to find the last vert that was good BDEF1,
			p_min_conserv = percentiles[i_min_conserv]		# and save the percentile it found.
			for i_max_conserv in range(middle + 1, len(verts)):  # start in middle, work toward tail,
				if pmx.verts[verts[i_max_conserv]].weighttype != pmxstruct.WeightMode.BDEF1:	# if the vertex is NOT BDEF1 type,
					break  									# then stop looking,
			i_max_conserv -= 1								# and step back 1 to find the last vert that was good BDEF1,
			p_max_conserv = percentiles[i_max_conserv]		# and save the percentile it found.
			
			foobar = False
			if not (i_min_liberal <= i_min_conserv <= i_max_conserv <= i_max_liberal):
				core.MY_PRINT_FUNC("ERROR: bounding indexes do not follow the expected relationship, results may be bad!")
				foobar = True
			if foobar or moreinfo:
				core.MY_PRINT_FUNC("   Max liberal bounds:      idx = %d to %d, %% = %f to %f" %
								   (i_min_liberal, i_max_liberal, p_min_liberal, p_max_liberal))
				core.MY_PRINT_FUNC("   Max conservative bounds: idx = %d to %d, %% = %f to %f" %
								   (i_min_conserv, i_max_conserv, p_min_conserv, p_max_conserv))
			
			
			# IDEA: WEIGHTED BLEND! sliding scale!
			avg_factor = core.clamp(ENDPOINT_AVERAGE_FACTOR, 0.0, 1.0)
			if p_min_liberal != p_min_conserv: p_min = (p_min_liberal * avg_factor) + (p_min_conserv * (1 - avg_factor))
			else:                              p_min = p_min_liberal
			if p_max_liberal != p_max_conserv: p_max = (p_max_liberal * avg_factor) + (p_max_conserv * (1 - avg_factor))
			else:                              p_max = p_max_liberal
			# clamp just in case
			p_min = core.clamp(p_min, 0.0, 1.0)
			p_max = core.clamp(p_max, 0.0, 1.0)
			if moreinfo:
				i_min = core.bisect_left(percentiles, p_min)
				i_max = core.bisect_left(percentiles, p_max)
				core.MY_PRINT_FUNC("   Compromise bounds:       idx = %d to %d, %% = %f to %f" %
								   (i_min, i_max, p_min, p_max))
				
			# now normalize the percentiles to these endpoints
			p_len = p_max - p_min
			percentiles = [(p - p_min) / p_len for p in percentiles]
			
			# 9. divide weight between preferredparent (or parent) and armYZ
			vert_zip = list(zip(verts, percentiles, centers))
			num_modified, num_bleeders = divvy_weights(pmx=pmx,
													  vert_zip=vert_zip,
													  axis_limits=(pmx.bones[start_idx].pos, pmx.bones[end_idx].pos),
													  bone_hasweight=parent_idx,
													  bone_getsweight=armYZ_new_idx,
													  bezier=bezier_curve)
			if moreinfo:
				core.MY_PRINT_FUNC("  Modified %d verts to use blending, %d are questionable 'bleeding' points" %
								   (num_modified, num_bleeders))
			pass
		pass
	
	# 10. run final weight-cleanup
	normalize_weights(pmx)
	
	# 11. write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_sdefautotwist")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
