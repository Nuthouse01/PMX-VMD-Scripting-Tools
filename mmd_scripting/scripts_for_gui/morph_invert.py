from mmd_scripting.core import nuthouse01_core as core
from mmd_scripting.core import nuthouse01_pmx_parser as pmxlib
from mmd_scripting.core import nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.scripts_for_gui import morph_scale

_SCRIPT_VERSION = "Script version:  Nuthouse01 - 6/10/2021 - v6.00"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


helptext = '''=================================================
morph_invert:
Swap the "base" and "morphed" states of a model.
Modify the default mesh to look like the morph is always applied, and modify the morph so that when it is enabled the model returns to what was previously the default.
This script will work for vertex morph or UV morph, and does only 1 morph at a time.

Output: PMX file '[modelname]_[morph#]inv.pmx'
'''

def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	core.MY_PRINT_FUNC("")
	# valid input is any string that can matched aginst a morph idx
	s = core.MY_GENERAL_INPUT_FUNC(lambda x: morph_scale.get_idx_in_pmxsublist(x, pmx.morphs) is not None,
								   ["Please specify the target morph: morph #, JP name, or EN name (names are not case sensitive).",
		"Empty input will quit the script."])
	# do it again, cuz the lambda only returns true/false
	target_index = morph_scale.get_idx_in_pmxsublist(s, pmx.morphs)
	
	# when given empty text, done!
	if target_index == -1 or target_index is None:
		core.MY_PRINT_FUNC("quitting")
		return None
	
	morphtype = pmx.morphs[target_index].morphtype
	# 1=vert
	# 3=UV
	# 8=material
	core.MY_PRINT_FUNC("Found {} morph #{}: '{}' / '{}'".format(
		morphtype, target_index, pmx.morphs[target_index].name_jp, pmx.morphs[target_index].name_en))
	
	if morphtype == pmxstruct.MorphType.VERTEX: # vertex
		# for each item in this morph:
		item:pmxstruct.PmxMorphItemVertex  # type annotation for pycharm
		for d, item in enumerate(pmx.morphs[target_index].items):
			# apply the offset
			pmx.verts[item.vert_idx].pos[0] += item.move[0]
			pmx.verts[item.vert_idx].pos[1] += item.move[1]
			pmx.verts[item.vert_idx].pos[2] += item.move[2]
			# invert the morph
		morph_scale.morph_scale(pmx.morphs[target_index], -1)
	elif morphtype == pmxstruct.MorphType.UV: # UV
		item:pmxstruct.PmxMorphItemUV  # type annotation for pycharm
		for d, item in enumerate(pmx.morphs[target_index].items):
			# (vert_idx, A, B, C, D)
			# apply the offset
			pmx.verts[item.vert_idx].uv[0] += item.move[0]
			pmx.verts[item.vert_idx].uv[1] += item.move[1]
			# invert the morph
		morph_scale.morph_scale(pmx.morphs[target_index], -1)
	elif morphtype in (pmxstruct.MorphType.UV_EXT1, pmxstruct.MorphType.UV_EXT2,
					   pmxstruct.MorphType.UV_EXT3, pmxstruct.MorphType.UV_EXT4): # UV1 UV2 UV3 UV4
		whichuv = morphtype.value - pmxstruct.MorphType.UV_EXT1.value
		item:pmxstruct.PmxMorphItemUV  # type annotation for pycharm
		for d, item in enumerate(pmx.morphs[target_index].items):
			# apply the offset
			pmx.verts[item.vert_idx].addl_vec4s[whichuv][0] += item.move[0]
			pmx.verts[item.vert_idx].addl_vec4s[whichuv][1] += item.move[1]
			pmx.verts[item.vert_idx].addl_vec4s[whichuv][2] += item.move[2]
			pmx.verts[item.vert_idx].addl_vec4s[whichuv][3] += item.move[3]
			# invert the morph
		morph_scale.morph_scale(pmx.morphs[target_index], -1)
	elif morphtype == pmxstruct.MorphType.MATERIAL: # material
		core.MY_PRINT_FUNC("WIP")
		# todo
		# to invert a material morph means inverting the material's visible/notvisible state as well as flipping the morph
		# hide morph add -> show morph add
		# hide morph mult -> show morph add
		# show morph add -> hide morph mult
		core.MY_PRINT_FUNC("quitting")
		return None
	else:
		core.MY_PRINT_FUNC("Unhandled morph type")
		core.MY_PRINT_FUNC("quitting")
		return None
	
	# write out
	output_filename_pmx = input_filename_pmx[0:-4] + ("_%dinv.pmx" % target_index)
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
