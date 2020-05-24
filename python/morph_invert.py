# Nuthouse01 - 04/17/2020 - v4.04
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
pmx_morph_invert:
Swap the "base" and "morphed" states of a model.
This script will work for vertex morph or UV morph, and does only 1 morph at a time.
TODO: material morph?

Output: PMX file '[modelname]_[morph#]inv.pmx'
'''


def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	target_index = 0
	while True:
		# TODO: write generic string input function that goes thru the GUI
		# any input is considered valid
		s = core.MY_GENERAL_INPUT_FUNC(lambda x: True, "Please specify the morph to invert: morph number, JP name, or EN name (names are case sensitive)")
		s = s.rstrip()
		# if empty, leave & do nothing
		if s == "":
			core.MY_PRINT_FUNC("quitting")
			return None
		# then get the morph index from this
		# search JP names first
		target_index = core.my_sublist_find(pmx[6], 0, s, getindex=True)
		if target_index is not None: break # did i find a match?
		# search EN names next
		target_index = core.my_sublist_find(pmx[6], 1, s, getindex=True)
		if target_index is not None: break # did i find a match?
		# try to cast to int next
		try:
			target_index = int(s)
			if 0 <= target_index < len(pmx[6]): break # is this within the proper bounds?
		except ValueError:
			pass
		core.MY_PRINT_FUNC("unable to find matching morph for '%s'" % s)
	
	
	morphtype = pmx[6][target_index][3]
	# 1=vert
	# 3=UV
	# 8=material
	
	if morphtype == 1: # vertex
		core.MY_PRINT_FUNC("Type=Vertex")
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
		core.MY_PRINT_FUNC("Type=UV")
		for d, item in enumerate(pmx[6][target_index][4]):
			# (vert_idx, A, B, C, D)
			# TODO: TEST WHETHER TO USE AB OR CD
			# apply the offset
			pmx[1][item[0]][6] += item[1]
			pmx[1][item[0]][7] += item[2]
			# invert the morph
			item[1] *= -1
			item[2] *= -1
	elif morphtype in (4,5,6,7): # UV1 UV2 UV3 UV4
		whichuv = morphtype - 4
		core.MY_PRINT_FUNC("Type=UV%d" % (whichuv+1))
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
		core.MY_PRINT_FUNC("Type=Material")
		core.MY_PRINT_FUNC("WIP")
		core.MY_PRINT_FUNC("quitting")
		return None
	else:
		core.MY_PRINT_FUNC("Unhandled morph type")
		core.MY_PRINT_FUNC("quitting")
		return None
	
	core.MY_PRINT_FUNC("Done inverting morph #{}: '{}' / '{}'".format(target_index, pmx[6][target_index][0], pmx[6][target_index][1]))
	
	# write out
	output_filename_pmx = input_filename_pmx[0:-4] + "_%dinv.pmx" % target_index
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	return None


if __name__ == '__main__':
	print("Nuthouse01 - 04/17/2020 - v4.04")
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
