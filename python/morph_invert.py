# Nuthouse01 - 07/09/2020 - v4.60
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

try:
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
except ImportError as eee:
	try:
		import nuthouse01_core as core
		import nuthouse01_pmx_parser as pmxlib
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = pmxlib = None




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
	
	while True:
		# any input is considered valid
		s = core.MY_GENERAL_INPUT_FUNC(lambda x: True,
									   ["Please specify the target morph: morph #, JP name, or EN name (names are case sensitive)",
									   "Empty input will quit the script"])
		# if empty, leave & do nothing
		if s == "":
			target_index = -1
			break
		# then get the morph index from this
		# search JP names first
		target_index = core.my_sublist_find(pmx[6], 0, s, getindex=True)
		if target_index is not None: break  # did i find a match?
		# search EN names next
		target_index = core.my_sublist_find(pmx[6], 1, s, getindex=True)
		if target_index is not None: break  # did i find a match?
		# try to cast to int next
		try:
			target_index = int(s)
			if 0 <= target_index < len(pmx[6]): break  # is this within the proper bounds?
			else: core.MY_PRINT_FUNC("valid morph indexes are 0-'%d'" % (len(pmx[6])-1))
		except ValueError:
			pass
		core.MY_PRINT_FUNC("unable to find matching morph for '%s'" % s)
	
	if target_index == -1:
		core.MY_PRINT_FUNC("quitting")
		return None
	
	morphtype = pmx[6][target_index][3]
	# 1=vert
	# 3=UV
	# 8=material
	core.MY_PRINT_FUNC("Found {} morph #{}: '{}' / '{}'".format(mtype_dict[morphtype], target_index, pmx[6][target_index][0], pmx[6][target_index][1]))
	
	if morphtype == 1: # vertex
		# for each item in this morph:
		for d, item in enumerate(pmx[6][target_index][4]):
			# apply the offset
			pmx[1][item[0]][0] += item[1]
			pmx[1][item[0]][1] += item[2]
			pmx[1][item[0]][2] += item[3]
			# invert the morph
			item[1] *= -1
			item[2] *= -1
			item[3] *= -1
	elif morphtype == 3: # UV
		for d, item in enumerate(pmx[6][target_index][4]):
			# (vert_idx, A, B, C, D)
			# apply the offset
			pmx[1][item[0]][6] += item[1]
			pmx[1][item[0]][7] += item[2]
			# invert the morph
			item[1] *= -1
			item[2] *= -1
	elif morphtype in (4,5,6,7): # UV1 UV2 UV3 UV4
		whichuv = morphtype - 4
		for d, item in enumerate(pmx[6][target_index][4]):
			# apply the offset
			pmx[1][item[0]][8][whichuv][0] += item[1]
			pmx[1][item[0]][8][whichuv][1] += item[2]
			pmx[1][item[0]][8][whichuv][2] += item[3]
			pmx[1][item[0]][8][whichuv][3] += item[4]
			# invert the morph
			item[1] *= -1
			item[2] *= -1
			item[3] *= -1
			item[4] *= -1
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
	print("Nuthouse01 - 07/09/2020 - v4.60")
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
