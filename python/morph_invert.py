# Nuthouse01 - 07/24/2020 - v4.63
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

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


helptext = '''=================================================
morph_invert:
Swap the "base" and "morphed" states of a model.
Modify the default mesh to look like the morph is always applied, and modify the morph so that when it is enabled the model returns to what was previously the default.
This script will work for vertex morph or UV morph, and does only 1 morph at a time.

Output: PMX file '[modelname]_[morph#]inv.pmx'
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
	
	morphtype = pmx.morphs[target_index].morphtype
	# 1=vert
	# 3=UV
	# 8=material
	core.MY_PRINT_FUNC("Found {} morph #{}: '{}' / '{}'".format(
		mtype_dict[morphtype], target_index, pmx.morphs[target_index].name_jp, pmx.morphs[target_index].name_en))
	
	if morphtype == 1: # vertex
		# for each item in this morph:
		for d, item in enumerate(pmx.morphs[target_index].items):
			# apply the offset
			pmx.verts[item.vert_idx].pos[0] += item.move[0]
			pmx.verts[item.vert_idx].pos[1] += item.move[1]
			pmx.verts[item.vert_idx].pos[2] += item.move[2]
			# invert the morph
			item.move = [m * -1 for m in item.move]
	elif morphtype == 3: # UV
		for d, item in enumerate(pmx.morphs[target_index].items):
			# (vert_idx, A, B, C, D)
			# apply the offset
			pmx.verts[item.vert_idx].uv[0] += item.move[0]
			pmx.verts[item.vert_idx].uv[1] += item.move[1]
			# invert the morph
			item.move = [m * -1 for m in item.move]
	elif morphtype in (4,5,6,7): # UV1 UV2 UV3 UV4
		whichuv = morphtype - 4
		for d, item in enumerate(pmx.morphs[target_index].items):
			# apply the offset
			pmx.verts[item.vert_idx].addl_vec4s[whichuv][0] += item.move[0]
			pmx.verts[item.vert_idx].addl_vec4s[whichuv][1] += item.move[1]
			pmx.verts[item.vert_idx].addl_vec4s[whichuv][2] += item.move[2]
			pmx.verts[item.vert_idx].addl_vec4s[whichuv][3] += item.move[3]
			# invert the morph
			item.move = [m * -1 for m in item.move]
	elif morphtype == 8: # material
		core.MY_PRINT_FUNC("WIP")
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
