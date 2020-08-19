# Nuthouse01 - 07/24/2020 - v4.63
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


import copy

try:
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
	from . import morph_hide
except ImportError as eee:
	try:
		import nuthouse01_core as core
		import nuthouse01_pmx_parser as pmxlib
		import morph_hide
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = pmxlib = morph_hide = None


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False

# if this is false, the original morph is preserved and a new morph is created with a different name.
# if this is true, then there will be no renaming. the scaled morph will replace the original morph.
SCALE_MORPH_IN_PLACE = False


helptext = '''=================================================
morph_scale:
Scale the magnitude of a morph by a given value. The result is appended as a new, separate morph.
Example: increase the strength of a vertex morph by 2.5x, or reduce its strength to 0.7x what it was.
For bone morphs, you can scale the rotation component separately from the motion (translation) component.
This script will work for vertex morph, UV morph, or bone morph, and does only 1 morph at a time.

Output: PMX file '[modelname]_[morph#]scal.pmx'
'''

mtype_dict = {0:"group", 1:"vertex", 2:"bone", 3:"UV",
			  4:"UV1", 5:"UV2", 6:"UV3", 7:"UV4",
			  8:"material", 9:"flip", 10:"impulse"}


def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	core.MY_PRINT_FUNC("")
	# valid input is any string that can matched aginst a morph idx
	s = core.MY_GENERAL_INPUT_FUNC(lambda x: morph_hide.get_morphidx_from_name(x, pmx) is not None,
								   ["Please specify the target morph: morph #, JP name, or EN name (names are case sensitive).",
									"Empty input will quit the script."])
	# do it again, cuz the lambda only returns true/false
	target_index = morph_hide.get_morphidx_from_name(s, pmx)
	
	# when given empty text, done!
	if target_index == -1 or target_index is None:
		core.MY_PRINT_FUNC("quitting")
		return None
	
	# determine the morph type
	morphtype = pmx.morphs[target_index].morphtype
	core.MY_PRINT_FUNC("Found {} morph #{}: '{}' / '{}'".format(
		mtype_dict[morphtype], target_index, pmx.morphs[target_index].name_jp, pmx.morphs[target_index].name_en))
	
	# if it is a bone morph, ask for translation/rotation/both
	bone_mode = 0
	if morphtype == 2:
		bone_mode = core.MY_SIMPLECHOICE_FUNC((1,2,3),
											  ["Bone morph detected: do you want to scale the motion(translation), rotation, or both?",
											   "1 = motion(translation), 2 = rotation, 3 = both"])
	
	# ask for factor: keep looping this prompt until getting a valid float
	def is_float(x):
		try:
			v = float(x)
			return True
		except ValueError:
			core.MY_PRINT_FUNC("Please enter a decimal number")
			return False
	factor_str = core.MY_GENERAL_INPUT_FUNC(is_float, "Enter the factor that you want to scale this morph by:")
	if factor_str == "":
		core.MY_PRINT_FUNC("quitting")
		return None
	factor = float(factor_str)
	
	# important values: target_index, factor, morphtype, bone_mode
	# first create the new morph that is a copy of current
	newmorph = copy.deepcopy(pmx.morphs[target_index])
	# then modify the names
	name_suffix = "*" + (str(factor)[0:6])
	newmorph.name_jp += name_suffix
	newmorph.name_en += name_suffix
	# now scale the actual values
	if morphtype == 2:  # bone
		# bone_mode: 1 = motion(translation), 2 = rotation, 3 = both
		if bone_mode in (2,3):  # if ==2 or ==3, then do rotation
			for d, item in enumerate(newmorph.items):
				# i guess scaling in euclid-space is good enough? assuming all resulting components are <180
				# most bone morphs only rotate around one axis anyways
				item.rot = [e * factor for e in item.rot]
		if bone_mode in (1,3):  # if ==1 or ==3, then do translation
			for d, item in enumerate(newmorph.items):
				# scale the morph XYZ
				item.move = [m * factor for m in item.move]
	elif morphtype == 1:  # vertex
		# for each item in this morph:
		for d, item in enumerate(newmorph.items):
			# scale the morph XYZ
			item.move = [m * factor for m in item.move]
	elif morphtype in (3, 4, 5, 6, 7):  # UV  UV1 UV2 UV3 UV4
		for d, item in enumerate(newmorph.items):
			# scale the morph UV
			item.move = [m * factor for m in item.move]
	else:
		core.MY_PRINT_FUNC("Unhandled morph type")
		core.MY_PRINT_FUNC("quitting")
		return None
	
	pmx.morphs.append(newmorph)
	
	# write out
	output_filename_pmx = input_filename_pmx[0:-4] + ("_%dscal.pmx" % target_index)
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	print("Nuthouse01 - 07/24/2020 - v4.63")
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
