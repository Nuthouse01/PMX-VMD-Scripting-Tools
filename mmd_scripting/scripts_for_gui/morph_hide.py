import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.scripts_for_gui import morph_scale

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.00 - 6/10/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################



helptext = '''=================================================
morph_hide:
For each specified morph, set its group to 0 so it does not show up in the eye/lip/brow/other menus.
Also removes it from the display panels to prevent MMD from crashing.

Output: PMX file '[modelname]_morphhide.pmx'
'''


def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	# usually want to hide many morphs at a time, so put all this in a loop
	num_hidden = 0
	while True:
		core.MY_PRINT_FUNC("")
		# valid input is any string that can matched aginst a morph idx
		s = core.MY_GENERAL_INPUT_FUNC(lambda x: (morph_scale.get_idx_in_pmxsublist(x, pmx.morphs) is not None),
									   ["Please specify the target morph: morph #, JP name, or EN name (names are not case sensitive).",
			"Empty input will quit the script."])
		# do it again, cuz the lambda only returns true/false
		target_index = morph_scale.get_idx_in_pmxsublist(s, pmx.morphs)
		
		# when given empty text, done!
		if target_index == -1 or target_index is None:
			core.MY_PRINT_FUNC("quitting")
			break
		
		# determine the morph type
		morphtype = pmx.morphs[target_index].morphtype
		core.MY_PRINT_FUNC("Found {} morph #{}: '{}' / '{}'".format(
			morphtype, target_index, pmx.morphs[target_index].name_jp, pmx.morphs[target_index].name_en))
		core.MY_PRINT_FUNC("Was group {}, now group {}".format(
			pmx.morphs[target_index].panel, pmxstruct.MorphPanel.HIDDEN))
		# make the actual change
		pmx.morphs[target_index].panel = pmxstruct.MorphPanel.HIDDEN
		num_hidden += 1
		pass
	
	if num_hidden == 0:
		core.MY_PRINT_FUNC("Nothing was changed")
		return None
	
	# last step: remove all invalid morphs from all display panels
	for d, frame in enumerate(pmx.frames):  # for each display group,
		i = 0
		while i < len(frame.items):  # for each item in that display group,
			item = frame.items[i]
			if item.is_morph:  # if it is a morph
				# look up the morph
				morph = pmx.morphs[item.idx]
				# figure out what panel of this morph is
				# if it has an invalid panel #, delete it here
				if morph.panel == pmxstruct.MorphPanel.HIDDEN:
					frame.items.pop(i)
				else:
					i += 1
			else:
				i += 1
	
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_morphhide")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
