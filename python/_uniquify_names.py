# Nuthouse01 - 03/30/2020 - v3.51
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

import sys
# first, version check: verify that this is using python3
# i don't know if it will actually work in 3.4 but i know it will fail in any python2 version
# actually written/tested with 3.6.6 so guaranteed to work on that or higher
# between 3.4 and 3.6, who knows
if sys.version_info < (3, 4):
	print("Your version of Python is too old to run this script, please update!")
	print("Your current version = " + sys.version)
	print("...press ENTER to exit...")
	input()
	exit()

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	import nuthouse01_core as core
	import nuthouse01_pmx_parser as pmxlib
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	core = pmxlib = None


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


# by default, don't unquify empty names, cuz this just turns them into "*1" "*2" "*3" etc
# which is argubaly even less useful than the default "Null_01" "Null_02" "Null_03" MMD turns them into
# but you can turn this on if you want i guess
ALSO_UNIQUIFY_NULL_NAMES = False


def uniquify_one_category(used_names: set, new_name: str) -> str:
	# translation occurred! attempt to uniquify the new name by appending *2 *3 etc
	while new_name in used_names:
		starpos = new_name.rfind("*")
		if starpos == -1:  # suffix does not exist
			new_name = new_name + "*1"
		else:  # suffix does exist
			try:
				suffixval = int(new_name[starpos + 1:])
			except ValueError:
				suffixval = 1
			new_name = new_name[:starpos] + "*" + str(suffixval + 1)
	# one leaving that loop, we finally have a unique name
	return new_name





def begin():
	# print info to explain the purpose of this file
	print("This will uniquify all names of materials/bones/morphs/displayframes in the model. Bad things happen when names are not unique.")
	# print info to explain what inputs it needs
	print("Inputs: PMX file 'model.pmx'")
	# print info to explain what outputs it creates
	print("Outputs: PMX file '[model]_unique.pmx'")
	print("")
	
	# prompt PMX name
	print("Please enter name of PMX model file:")
	input_filename_pmx = core.prompt_user_filename(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx)
	return pmx, input_filename_pmx

def uniquify_names(pmx):
	
	# just uniquify the names
	# return counts of how many en/jp from each category were changed
	# but don't print out the actual before/after, don't ask for approval
	
	counts = [0] * 8
	counts_labels = ["material_JP","material_EN","bone_JP","bone_EN","morph_JP","morph_EN","dispframe_JP","dispframe_EN"]
	
	for cat_id in range(4, 8):
		category = pmx[cat_id]
		used_en_names = set()
		used_jp_names = set()
		for i, item in enumerate(category):
			jp_name = item[0]
			en_name = item[1]
			# first, uniquify the jp name
			if jp_name != "" or ALSO_UNIQUIFY_NULL_NAMES:
				new_jp_name = uniquify_one_category(used_jp_names, jp_name)
				used_jp_names.add(new_jp_name)
				if new_jp_name != jp_name:
					# count & store into the structure
					item[0] = new_jp_name
					counts[cat_id - 4] += 1
			# second, uniquify the en name
			if en_name != "" or ALSO_UNIQUIFY_NULL_NAMES:
				new_en_name = uniquify_one_category(used_en_names, en_name)
				used_en_names.add(new_en_name)
				if new_en_name != en_name:
					# count & store into the structure
					item[1] = new_en_name
					counts[cat_id - 3] += 1
	
	counts_dict = {x:y for x,y in zip(counts_labels, counts) if y != 0}

	if not counts_dict:
		print("No changes are required")
		return pmx, False
	
	# list how many of what were changed
	print("The following numbers in each category/language were uniquified:")
	print(counts_dict)
	
	return pmx, True
	
def end(pmx, input_filename_pmx):
	# write out
	output_filename_pmx = "%s_unique.pmx" % core.get_clean_basename(input_filename_pmx)
	# output_filename_pmx = input_filename_pmx[0:-4] + "_translate.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(pmx, output_filename_pmx)
	
	return None

def main():
	pmx, name = begin()
	pmx, is_changed = uniquify_names(pmx)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")


if __name__ == '__main__':
	print("Nuthouse01 - 03/30/2020 - v3.51")
	if DEBUG:
		main()
	else:
		try:
			main()
		except (KeyboardInterrupt, SystemExit):
			# this is normal and expected, do nothing and die normally
			pass
		except Exception as ee:
			# if an unexpected error occurs, catch it and print it and call pause_and_quit so the window stays open for a bit
			print(ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
