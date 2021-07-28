import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.scripts_for_gui import morph_scale

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.5.03 - 10/10/2020"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################



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
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
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
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_endpoints")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
