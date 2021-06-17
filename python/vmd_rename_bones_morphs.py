_SCRIPT_VERSION = "Script version:  Nuthouse01 - 6/17/2021 - v6.01"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# read vmd, prompt "find", prompt "replace", do find-replace, repeat, writeout


# second, wrap custom imports with a try-except to catch it if files are missing
try:
	# these imports work if running from GUI
	from . import nuthouse01_core as core
	from . import nuthouse01_vmd_parser as vmdlib
except ImportError as eee:
	try:
		# these imports work if running from double-click on THIS script
		import nuthouse01_core as core
		import nuthouse01_vmd_parser as vmdlib
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = vmdlib = None


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False



helptext = '''=================================================
vmd_rename_bones_morphs:
This script will do simple find-and-replace on the names within a VMD.
If you use the "check_model_compatability" script and find that the VMD uses wink morph 'ウィンク右2' but your model contains the morph 'ｳｨﾝｸ右2', the frames will not properly load. This script can be used to retarget the VMD frames onto the correct name.

Output: dance VMD file '[dancename]_renamed.vmd'
'''

def main(moreinfo=True):
	###################################################################################
	# prompt VMD file name
	core.MY_PRINT_FUNC("Please enter name of VMD dance input file:")
	input_filename_vmd = core.MY_FILEPROMPT_FUNC(".vmd")
	vmd = vmdlib.read_vmd(input_filename_vmd, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("")
	
	# ask for all find-replace pairs
	core.MY_PRINT_FUNC("Please specify all find/replace pairs, for bones or for morphs:")
	find_replace_map = {}
	while True:
		# ask for both ik and target at same time
		# valid input is any string that contains a forwardslash
		def two_item_valid_input_check(x: str) -> bool:
			# if input is empty that counts as valid cuz that's the "ok now go do it" signal
			if x == "": return True
			# valid input must contain a forwardslash
			sp = x.split('/')
			if len(sp) != 2:
				core.MY_PRINT_FUNC("invalid input: must contain exactly 2 terms separated by a forwardslash")
				return False
			return True
		
		s = core.MY_GENERAL_INPUT_FUNC(two_item_valid_input_check,
									   ["What bone/morph names do you want to search for, and what should they be replaced with?",
										"Please give the JP names of both bones/morphs separated by a forwardslash: find/replace",
										"Empty input will begin forward kinematics simulation."])
		# if the input is empty string, then we break and begin executing with current args
		if s == "" or s is None:
			break
		
		# because of two_item_valid_input_check() it should be guaranteed safe to call split here
		f, r = s.split('/')
		
		find_replace_map[f] = r
		core.MY_PRINT_FUNC("")
		pass
	
	for f,r in find_replace_map.items():
		core.MY_PRINT_FUNC("finding '%s' to replace with '%s'" % (f,r))
	core.MY_PRINT_FUNC("")
	
	# init num_replaced dict with same keys as find_replace_map but all values are int zeros
	num_replaced = dict([(f,0) for f in find_replace_map.keys()])
	
	# now do actual substitution in bones
	for boneframe in vmd.boneframes:
		if boneframe.name in find_replace_map:
			num_replaced[boneframe.name] += 1
			boneframe.name = find_replace_map[boneframe.name]
	# now do actual substituion in morphs
	for morphframe in vmd.morphframes:
		if morphframe.name in find_replace_map:
			num_replaced[morphframe.name] += 1
			morphframe.name = find_replace_map[morphframe.name]
	# now done modifying in-place, report how many i changed
	num_replaced = list(num_replaced.items())
	num_replaced.sort(reverse=True, key=core.get2nd)  # sort descending by number replaced
	for pair in num_replaced:
		core.MY_PRINT_FUNC("    ", str(pair))
	
	core.MY_PRINT_FUNC("")
	# write out the VMD
	output_filename_vmd = "%s_renamed.vmd" % input_filename_vmd[0:-4]
	output_filename_vmd = core.get_unused_file_name(output_filename_vmd)
	vmdlib.write_vmd(output_filename_vmd, vmd, moreinfo=moreinfo)
	
	core.MY_PRINT_FUNC("Done!")
	return None

if __name__ == '__main__':
	print(_SCRIPT_VERSION)
	# print info to explain the purpose of this file
	core.MY_PRINT_FUNC(helptext)
	core.MY_PRINT_FUNC("")
	if DEBUG:
		main()
	else:
		try:
			# print info to explain the purpose of this file
			core.MY_PRINT_FUNC(helptext)
			core.MY_PRINT_FUNC("")
			
			main()
		except (KeyboardInterrupt, SystemExit):
			# this is normal and expected, do nothing and die normally
			pass
		except Exception as ee:
			# if an unexpected error occurs, catch it and print it and call pause_and_quit so the window stays open for a bit
			core.MY_PRINT_FUNC(ee.__class__.__name__, ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
	core.pause_and_quit("Done with everything! Goodbye!")
