_SCRIPT_VERSION = "Nuthouse01 - 10/10/2020 - v5.03"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

try:
	# these imports work if running from GUI
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
	from . import nuthouse01_pmx_struct as pmxstruct
	from . import morph_scale
except ImportError as eee:
	try:
		# these imports work if running from double-click on THIS script
		import nuthouse01_core as core
		import nuthouse01_pmx_parser as pmxlib
		import nuthouse01_pmx_struct as pmxstruct
		import morph_scale
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = pmxlib = pmxstruct = morph_scale = None

# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


helptext = '''=================================================
bone_endpoint_addremove:
This will create or remove hidden bone 'endpoints' for other bones to visually link to. It will swap tail mode from offset->bonelink or bonelink->offset.
When swapping offset->bonelink, it creates new hidden endpoint bones for the parent to point at.
When swapping bonelink->offset, the endpoint bones are NOT DELETED, they are simply not used for visual linking.

Output: PMX file '[modelname]_endpoints.pmx'
'''


endpoint_suffix_jp = "先"
endpoint_suffix_en = " end"


def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	# usually want to add/remove endpoints for many bones at once, so put all this in a loop
	num_changed = 0
	while True:
		core.MY_PRINT_FUNC("")
		# valid input is any string that can matched aginst a bone idx
		s = core.MY_GENERAL_INPUT_FUNC(lambda x: (morph_scale.get_idx_in_pmxsublist(x, pmx.bones) is not None),
		   ["Please specify the target bone: bone #, JP name, or EN name (names are not case sensitive).",
			"Empty input will quit the script."])
		# do it again, cuz the lambda only returns true/false
		target_index = morph_scale.get_idx_in_pmxsublist(s, pmx.bones)
		
		# when given empty text, done!
		if target_index == -1 or target_index is None:
			core.MY_PRINT_FUNC("quitting")
			break
		target_bone = pmx.bones[target_index]
		
		# print the bone it found
		core.MY_PRINT_FUNC("Found bone #{}: '{}' / '{}'".format(
			target_index, target_bone.name_jp, target_bone.name_en))
		
		if target_bone.tail_usebonelink:
			core.MY_PRINT_FUNC("Was tailmode 'bonelink', changing to mode 'offset'")
			if target_bone.tail == -1:
				core.MY_PRINT_FUNC("Error: bone is not linked to anything, skipping")
				continue
			# find the location of the bone currently pointing at
			endpos = pmx.bones[target_bone.tail].pos
			# determine the equivalent offset vector
			offset = [endpos[i] - target_bone.pos[i] for i in range(3)]
			# write it into the bone
			target_bone.tail_usebonelink = False
			target_bone.tail = offset
			# done unlinking endpoint!
			pass
			
		else:
			core.MY_PRINT_FUNC("Was tailmode 'offset', changing to mode 'bonelink' and adding new endpoint bone")
			if target_bone.tail == [0,0,0]:
				core.MY_PRINT_FUNC("Error: bone has offset of [0,0,0], skipping")
				continue
			# determine the position of the new endpoint bone
			endpos = [target_bone.pos[i] + target_bone.tail[i] for i in range(3)]
			# create the new bone
			newbone = pmxstruct.PmxBone(
				name_jp=target_bone.name_jp + endpoint_suffix_jp, name_en=target_bone.name_en + endpoint_suffix_en,
				pos=endpos, parent_idx=target_index, deform_layer=target_bone.deform_layer,
				deform_after_phys=target_bone.deform_after_phys, has_rotate=False, has_translate=False,
				has_visible=False, has_enabled=True, has_ik=False, has_localaxis=False, has_fixedaxis=False,
				has_externalparent=False, inherit_rot=False, inherit_trans=False, tail_usebonelink=True, tail=-1
			)
			# set the target to point at the new bone
			target_bone.tail_usebonelink = True
			target_bone.tail = len(pmx.bones)
			# append the new bone
			pmx.bones.append(newbone)
			# done adding endpoint!
			pass
		
		num_changed += 1
		pass
	
	if num_changed == 0:
		core.MY_PRINT_FUNC("Nothing was changed")
		return None
	
	core.MY_PRINT_FUNC("")
	
	# write out
	output_filename_pmx = input_filename_pmx[0:-4] + "_endpoints.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	print(_SCRIPT_VERSION)
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
			print(ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
