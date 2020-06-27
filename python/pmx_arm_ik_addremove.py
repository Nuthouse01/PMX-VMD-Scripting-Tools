# Nuthouse01 - 06/27/2020 - v4.50
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
	from ._prune_unused_bones import apply_bone_remapping
	from ._prune_unused_vertices import delme_list_to_rangemap
except ImportError as eee:
	try:
		import nuthouse01_core as core
		import nuthouse01_pmx_parser as pmxlib
		from _prune_unused_bones import apply_bone_remapping
		from _prune_unused_vertices import delme_list_to_rangemap
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = pmxlib = None
		apply_bone_remapping = None




# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = True

helptext = '''=================================================
pmx_arm_ik_addremove:
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
	input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	# detect whether arm ik exists
	r = core.my_sublist_find(pmx[5], 0, jp_r + jp_newik, getindex=True)
	if r is None:
		r = core.my_sublist_find(pmx[5], 0, jp_r + jp_newik2, getindex=True)
	l = core.my_sublist_find(pmx[5], 0, jp_l + jp_newik, getindex=True)
	if l is None:
		l = core.my_sublist_find(pmx[5], 0, jp_l + jp_newik2, getindex=True)
	
	# decide whether to create or remove arm ik
	if r is None and l is None:
		# add IK branch
		core.MY_PRINT_FUNC(">>>> Adding arm IK <<<")
		# set output name
		if input_filename_pmx.lower().endswith(pmx_noik_suffix.lower()):
			output_filename = input_filename_pmx[0:-(len(pmx_noik_suffix))] + pmx_yesik_suffix
		else:
			output_filename = input_filename_pmx[0:-4] + pmx_yesik_suffix
		for side in [jp_l, jp_r]:
			# first find all 3 arm bones
			# even if i insert into the list, this will still be a valid reference i think
			bones = []
			for n in [jp_arm, jp_elbow, jp_wrist]:
				i = core.my_sublist_find(pmx[5], 0, side + n)
				if i is None:
					core.MY_PRINT_FUNC("ERROR1: semistandard bone '%s' is missing from the model, unable to create attached arm IK" % (side + n))
					raise RuntimeError()
				bones.append(i)
			# get parent of arm bone
			shoulder_idx = bones[0][5]
			
			# then do the "remapping" on all existing bone references, to make space for inserting 4 bones
			# don't delete any bones, just remap them
			bone_shiftmap = [[shoulder_idx+1], [-4]]
			pmx = apply_bone_remapping(pmx, [], bone_shiftmap)
			# new bones will be inserted AFTER shoulder_idx
			# newarm_idx = shoulder_idx+1
			# newelbow_idx = shoulder_idx+2
			# newwrist_idx = shoulder_idx+3
			# newik_idx = shoulder_idx+4
			
			# make copies of the 3 armchain bones
			for i, b in enumerate(bones):
				newarm = b[0:5] + [shoulder_idx + i] + b[6:8]  # copy names/pos, parent, copy deform layer
				newarm += [1, 0, 0, 0]  # rotateable, not translateable, not visible, not enabled(?)
				newarm += [1, [shoulder_idx + 2 + i], 0, 0, [], 0, []]  # tail type, no inherit, no fixed axis,
				newarm += b[19:21] + [0, [], 0, []]  # copy local axis, no ext parent, no ik
				newarm[0] += jp_ikchainsuffix  # add suffix to jp name
				newarm[1] += jp_ikchainsuffix  # add suffix to en name
				pmx[5].insert(shoulder_idx + 1 + i, newarm)
				# then change the existing arm/elbow (not the wrist) to inherit rot from them
				if i != 2:
					b[14] = 1
					b[16] = [shoulder_idx + 1 + i, 1]
			
			# copy the wrist to make the IK bone
			en_suffix = "_L" if side == jp_l else "_R"
			# get index of "upperbody" to use as parent of hand IK bone
			ikpar = core.my_sublist_find(pmx[5], 0, jp_upperbody, getindex=True)
			if ikpar is None:
				core.MY_PRINT_FUNC("ERROR1: semistandard bone '%s' is missing from the model, unable to create attached arm IK" % jp_upperbody)
				raise RuntimeError()
			
			newik = [side + jp_newik, en_newik + en_suffix] + bones[2][2:5] + [ikpar]  # new names, copy pos, new par
			newik += bones[2][6:8] + [1, 1, 1, 1]  + [0, [0,1,0]] # copy deform layer, rot/trans/vis/en, tail type
			newik += [0, 0, [], 0, [], 0, [], 0, []]  # no inherit, no fixed axis, no local axis, no ext parent, yes IK
			# add the ik info: [is_ik, [target, loops, anglelimit, [[link_idx, []]], [link_idx, []]]] ] ]
			newik += [1, [shoulder_idx+3, newik_loops, newik_angle, [[shoulder_idx+2,[]],[shoulder_idx+1,[]]] ] ]
			pmx[5].insert(shoulder_idx + 4, newik)
			
			# then add to dispframe
			# first, does the frame already exist?
			f = core.my_sublist_find(pmx[7], 0, jp_newik)
			if f is None:
				# need to create the new dispframe! easy
				newframe = [jp_newik, en_newik, 0, [[0, shoulder_idx + 4]]]
				pmx[7].append(newframe)
			else:
				# frame already exists, also easy
				f[3].append([0, shoulder_idx + 4])
	else:
		# remove IK branch
		core.MY_PRINT_FUNC(">>>> Removing arm IK <<<")
		# set output name
		if input_filename_pmx.lower().endswith(pmx_yesik_suffix.lower()):
			output_filename = input_filename_pmx[0:-(len(pmx_yesik_suffix))] + pmx_noik_suffix
		else:
			output_filename = input_filename_pmx[0:-4] + pmx_noik_suffix
		# identify all bones in ik chain of hand ik bones
		bone_dellist = []
		for b in [r, l]:
			bone_dellist.append(b) # this IK bone
			bone_dellist.append(pmx[5][r][24][0]) # the target of the bone
			for v in pmx[5][r][24][3]:
				bone_dellist.append(v[0]) # each link along the bone
		bone_dellist.sort()
		# build the remap thing
		bone_shiftmap = delme_list_to_rangemap(bone_dellist)
		# do the actual delete & shift
		pmx = apply_bone_remapping(pmx, bone_dellist, bone_shiftmap)
		
		# delete dispframe for hand ik
		# first, does the frame already exist?
		f = core.my_sublist_find(pmx[7], 0, jp_newik, getindex=True)
		if f is not None:
			# frame already exists, delete it
			pmx[7].pop(f)
		
		pass
	
	# write out
	output_filename = core.get_unused_file_name(output_filename)
	pmxlib.write_pmx(output_filename, pmx, moreinfo=moreinfo)
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 06/27/2020 - v4.50")
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
