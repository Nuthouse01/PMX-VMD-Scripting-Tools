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
morph_hide:
For each specified morph, set its group to 0 so it does not show up in the eye/lip/brow/other menus.
Also removes it from the display panels to prevent MMD from crashing.

Output: PMX file '[modelname]_morphhide.pmx'
'''

mtype_dict = {0:"group", 1:"vertex", 2:"bone", 3:"UV",
			  4:"UV1", 5:"UV2", 6:"UV3", 7:"UV4",
			  8:"material", 9:"flip", 10:"impulse"}

def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	# usually want to hide many morphs at a time, so put all this in a loop
	num_hidden = 0
	while True:
		# loop until an existing morph is specified, or given empty input
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
				else: core.MY_PRINT_FUNC("valid morph indexes are 0-'%d'" % (len(pmx[6]) - 1))
			except ValueError:
				pass
			core.MY_PRINT_FUNC("unable to find matching morph for '%s'" % s)
		
		# when given empty text, done!
		if target_index == -1:
			core.MY_PRINT_FUNC("quitting")
			break
		
		# determine the morph type
		morphtype = pmx[6][target_index][3]
		core.MY_PRINT_FUNC("Found {} morph #{}: '{}' / '{}'".format(mtype_dict[morphtype], target_index, pmx[6][target_index][0], pmx[6][target_index][1]))
		core.MY_PRINT_FUNC("Was group# = {}".format(pmx[6][target_index][2]))
		# make the actual change
		pmx[6][target_index][2] = 0
		num_hidden += 1
	
	core.MY_PRINT_FUNC("done!")
	
	if num_hidden == 0:
		core.MY_PRINT_FUNC("nothing was changed")
		return None
	
	# last step: remove all invalid morphs from all display panels
	for d, frame in enumerate(pmx[7]):  # for each display group,
		i = 0
		while i < len(frame[3]):  # for each item in that display group,
			item = frame[3][i]
			if item[0]:  # if it is a morph
				# figure out what panel of this morph is
				panel = pmx[6][item[1]][2]
				# if this is an invalid panel #, delete it here
				if not 1 <= panel <= 4:
					frame[3].pop(i)
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
