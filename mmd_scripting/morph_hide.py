from mmd_scripting import morph_scale
from mmd_scripting import nuthouse01_core as core
from mmd_scripting import nuthouse01_pmx_parser as pmxlib
from mmd_scripting import nuthouse01_pmx_struct as pmxstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - 6/10/2021 - v6.00"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


helptext = '''=================================================
morph_hide:
For each specified morph, set its group to 0 so it does not show up in the eye/lip/brow/other menus.
Also removes it from the display panels to prevent MMD from crashing.

Output: PMX file '[modelname]_morphhide.pmx'
'''


def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")
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
	output_filename_pmx = input_filename_pmx[0:-4] + "_morphhide.pmx"
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
