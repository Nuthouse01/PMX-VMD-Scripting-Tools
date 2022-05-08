from typing import List

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.core.nuthouse01_pmx_utils import insert_single_bone, delete_multiple_bones

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.00 - 6/10/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


helptext = '''=================================================
bone_armik_addremove:
This very simple script will generate "arm IK bones" if they do not exist, or delete them if they do exist.
The output suffix will be "_IK" if it added IK, or "_noIK" if it removed them.
'''

# copy arm/elbow/wrist, wrist is target of IK bone
# my improvement: make arm/elbow/wrist hidden and disabled
# ik has 20 loops, 45 deg, "左腕ＩＫ"
# original arm/elbow set to inherit 100% rot from their copies
# tricky: arm IK must be inserted between the shoulder and the arm, requires remapping all bone references ugh.
# if i use negative numbers for length, can I reuse the code for mass-delete?
# also add to dispframe


jp_left_arm =         "左腕"
jp_left_elbow =       "左ひじ"
jp_left_wrist =       "左手首"
jp_right_arm =        "右腕"
jp_right_elbow =      "右ひじ"
jp_right_wrist =      "右手首"
jp_sourcebones =   [jp_left_arm, jp_left_elbow, jp_left_wrist, jp_right_arm, jp_right_elbow, jp_right_wrist]
jp_l = "左"
jp_r = "右"
jp_arm =         "腕"
jp_elbow =       "ひじ"
jp_wrist =       "手首"
jp_upperbody = "上半身"  # this is used as the parent of the hand IK bone
jp_ikchainsuffix = "+" # appended to jp and en names of thew arm/elbow/wrist copies

newik_loops = 20
newik_angle = 45

jp_newik = "腕ＩＫ"
jp_newik2 = "腕IK"  # for detecting only, always create with ^
en_newik = "armIK"

pmx_yesik_suffix = " IK.pmx"
pmx_noik_suffix =  " no-IK.pmx"


def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	# detect whether arm ik exists
	r = core.my_list_search(pmx.bones, lambda x: x.name_jp == jp_r + jp_newik)
	if r is None:
		r = core.my_list_search(pmx.bones, lambda x: x.name_jp == jp_r + jp_newik2)
	l = core.my_list_search(pmx.bones, lambda x: x.name_jp == jp_l + jp_newik)
	if l is None:
		l = core.my_list_search(pmx.bones, lambda x: x.name_jp == jp_l + jp_newik2)
	
	# decide whether to create or remove arm ik
	if r is None and l is None:
		# add IK branch
		core.MY_PRINT_FUNC(">>>> Adding arm IK <<<")
		# set output name
		SUFFIX = pmx_yesik_suffix
		for side in [jp_l, jp_r]:
			# first find all 3 arm bones
			# even if i insert into the list, this will still be a valid reference i think
			bones = []
			bones: List[pmxstruct.PmxBone]
			for n in [jp_arm, jp_elbow, jp_wrist]:
				i = core.my_list_search(pmx.bones, lambda x: x.name_jp == side + n, getitem=True)
				if i is None:
					core.MY_PRINT_FUNC("ERROR1: semistandard bone '%s' is missing from the model, unable to create attached arm IK" % (side + n))
					raise RuntimeError()
				bones.append(i)
			# get parent of arm bone (shoulder bone), new bones will be inserted after this
			shoulder_idx = bones[0].parent_idx
			
			# new bones will be inserted AFTER shoulder_idx
			# newarm_idx = shoulder_idx+1
			# newelbow_idx = shoulder_idx+2
			# newwrist_idx = shoulder_idx+3
			# newik_idx = shoulder_idx+4
			
			# make copies of the 3 armchain bones
			
			# arm: parent is shoulder
			newarm = pmxstruct.PmxBone(
				name_jp=bones[0].name_jp + jp_ikchainsuffix, name_en=bones[0].name_en + jp_ikchainsuffix, 
				pos=bones[0].pos, parent_idx=shoulder_idx, deform_layer=bones[0].deform_layer, 
				deform_after_phys=bones[0].deform_after_phys,
				has_rotate=True, has_translate=False, has_visible=False, has_enabled=True, has_ik=False,
				tail_usebonelink=True, tail=0,  # want arm tail to point at the elbow, can't set it until elbow is created
				inherit_rot=False, inherit_trans=False,
				has_localaxis=bones[0].has_localaxis, localaxis_x=bones[0].localaxis_x, localaxis_z=bones[0].localaxis_z,
				has_externalparent=False, has_fixedaxis=False, 
			)
			insert_single_bone(pmx, newarm, shoulder_idx + 1)
			# change existing arm to inherit rot from this
			bones[0].inherit_rot = True
			bones[0].inherit_parent_idx = shoulder_idx + 1
			bones[0].inherit_ratio = 1
			
			# elbow: parent is newarm
			newelbow = pmxstruct.PmxBone(
				name_jp=bones[1].name_jp + jp_ikchainsuffix, name_en=bones[1].name_en + jp_ikchainsuffix, 
				pos=bones[1].pos, parent_idx=shoulder_idx+1, deform_layer=bones[1].deform_layer, 
				deform_after_phys=bones[1].deform_after_phys,
				has_rotate=True, has_translate=False, has_visible=False, has_enabled=True, has_ik=False,
				tail_usebonelink=True, tail=0,  # want elbow tail to point at the wrist, can't set it until wrist is created
				inherit_rot=False, inherit_trans=False,
				has_localaxis=bones[1].has_localaxis, localaxis_x=bones[1].localaxis_x, localaxis_z=bones[1].localaxis_z,
				has_externalparent=False, has_fixedaxis=False, 
			)
			insert_single_bone(pmx, newelbow, shoulder_idx + 2)
			# change existing elbow to inherit rot from this
			bones[1].inherit_rot = True
			bones[1].inherit_parent_idx = shoulder_idx + 2
			bones[1].inherit_ratio = 1
			# now that newelbow exists, change newarm tail to point to this
			newarm.tail = shoulder_idx + 2
			
			# wrist: parent is newelbow
			newwrist = pmxstruct.PmxBone(
				name_jp=bones[2].name_jp + jp_ikchainsuffix, name_en=bones[2].name_en + jp_ikchainsuffix, 
				pos=bones[2].pos, parent_idx=shoulder_idx+2, deform_layer=bones[2].deform_layer, 
				deform_after_phys=bones[2].deform_after_phys,
				has_rotate=True, has_translate=False, has_visible=False, has_enabled=True, has_ik=False,
				tail_usebonelink=True, tail=-1,  # newwrist has no tail
				inherit_rot=False, inherit_trans=False,
				has_localaxis=bones[2].has_localaxis, localaxis_x=bones[2].localaxis_x, localaxis_z=bones[2].localaxis_z,
				has_externalparent=False, has_fixedaxis=False, 
			)
			insert_single_bone(pmx, newwrist, shoulder_idx + 3)
			# now that newwrist exists, change newelbow tail to point to this
			newelbow.tail = shoulder_idx + 3
			
			# copy the wrist to make the IK bone
			en_suffix = "_L" if side == jp_l else "_R"
			# get index of "upperbody" to use as parent of hand IK bone
			ikpar = core.my_list_search(pmx.bones, lambda x: x.name_jp == jp_upperbody)
			if ikpar is None:
				core.MY_PRINT_FUNC("ERROR1: semistandard bone '%s' is missing from the model, unable to create attached arm IK" % jp_upperbody)
				raise RuntimeError()
			
			# newik = [side + jp_newik, en_newik + en_suffix] + bones[2][2:5] + [ikpar]  # new names, copy pos, new par
			# newik += bones[2][6:8] + [1, 1, 1, 1]  + [0, [0,1,0]] # copy deform layer, rot/trans/vis/en, tail type
			# newik += [0, 0, [], 0, [], 0, [], 0, []]  # no inherit, no fixed axis, no local axis, no ext parent, yes IK
			# # add the ik info: [is_ik, [target, loops, anglelimit, [[link_idx, []]], [link_idx, []]]] ] ]
			# newik += [1, [shoulder_idx+3, newik_loops, newik_angle, [[shoulder_idx+2,[]],[shoulder_idx+1,[]]] ] ]
			newik = pmxstruct.PmxBone(
				name_jp=side + jp_newik, name_en=en_newik + en_suffix, pos=bones[2].pos,
				parent_idx=ikpar, deform_layer=bones[2].deform_layer, deform_after_phys=bones[2].deform_after_phys,
				has_rotate=True, has_translate=True, has_visible=True, has_enabled=True,
				tail_usebonelink=False, tail=[0,1,0], inherit_rot=False, inherit_trans=False,
				has_fixedaxis=False, has_localaxis=False, has_externalparent=False, has_ik=True,
				ik_target_idx=shoulder_idx+3, ik_numloops=newik_loops, ik_angle=newik_angle,
				ik_links=[pmxstruct.PmxBoneIkLink(idx=shoulder_idx+2), pmxstruct.PmxBoneIkLink(idx=shoulder_idx+1)]
			)
			insert_single_bone(pmx, newik, shoulder_idx + 4)
			
			# then add to dispframe
			# first, does the frame already exist?
			f = core.my_list_search(pmx.frames, lambda x: x.name_jp == jp_newik, getitem=True)
			newframeitem = pmxstruct.PmxFrameItem(is_morph=False, idx=shoulder_idx + 4)
			if f is None:
				# need to create the new dispframe! easy
				newframe = pmxstruct.PmxFrame(name_jp=jp_newik, name_en=en_newik, is_special=False, items=[newframeitem])
				pmx.frames.append(newframe)
			else:
				# frame already exists, also easy
				f.items.append(newframeitem)
	else:
		# remove IK branch
		core.MY_PRINT_FUNC(">>>> Removing arm IK <<<")
		# set output name
		SUFFIX = pmx_noik_suffix
		# identify all bones in ik chain of hand ik bones
		bone_dellist = []
		for b in [r, l]:
			bone_dellist.append(b) # this IK bone
			bone_dellist.append(pmx.bones[b].ik_target_idx) # the target of the bone
			for v in pmx.bones[b].ik_links:
				bone_dellist.append(v.idx) # each link along the bone
		bone_dellist.sort()
		# do the actual delete & shift
		delete_multiple_bones(pmx, bone_dellist)
		
		# delete dispframe for hand ik
		# first, does the frame already exist?
		f = core.my_list_search(pmx.frames, lambda x: x.name_jp == jp_newik)
		if f is not None:
			# frame already exists, delete it
			pmx.frames.pop(f)
		
		pass
	
	# write out
	output_filename = core.filepath_insert_suffix(input_filename_pmx, SUFFIX)
	output_filename = core.filepath_get_unused_name(output_filename)
	pmxlib.write_pmx(output_filename, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
