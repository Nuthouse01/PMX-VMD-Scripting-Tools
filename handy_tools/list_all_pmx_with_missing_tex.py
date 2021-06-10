# Nuthouse01 - 6/3/2021 - v5.08
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# first, system imports
import os
import sys
sys.path.append("../")

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	# these imports work if running from GUI
	from python import nuthouse01_core as core
	from python import nuthouse01_pmx_parser as pmxlib
	from python import file_sort_textures
except ImportError as eee:
	try:
		# these imports work if running from double-click on THIS script
		import nuthouse01_core as core
		import nuthouse01_pmx_parser as pmxlib
		import file_sort_textures
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = pmxlib = file_sort_textures = None


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = True

FAILED_LIST_FILE =     "all_pmx_that_failed_to_read.txt"
MISSINGTEX_LIST_FILE = "all_pmx_with_missing_tex.txt"

IMG_EXT = file_sort_textures.IMG_EXT


helptext = '''=================================================
list_all_pmx_with_missing_tex:
input: the folder that contains all folders containing models
i.e. "username/Documents/mmd/models", NOT "username/Documents/mmd/models/vocaloid/miku v123"
output: write a text file with every fucking pmx that references at least 1 texture file not on disk
'''


def main(moreinfo=False):
	
	# 1. user input
	core.MY_PRINT_FUNC("Current dir = '%s'" % os.getcwd())
	core.MY_PRINT_FUNC("Enter the path to the root folder that contains ALL models:")
	while True:
		name = input("root folder = ")
		if not os.path.isdir(name):
			core.MY_PRINT_FUNC(os.path.abspath(name))
			core.MY_PRINT_FUNC("Err: given folder does not exist, did you type it wrong?")
		else:
			break
	# it exists, so make it absolute
	rootdir = os.path.abspath(os.path.normpath(name))
	
	core.MY_PRINT_FUNC("root folder = '%s'" % rootdir)
	
	core.MY_PRINT_FUNC("")
	
	core.MY_PRINT_FUNC("... beginning to index file tree...")
	# 2. build list of ALL file on the system within this folder
	relative_all_exist_files = file_sort_textures.walk_filetree_from_root(rootdir)
	core.MY_PRINT_FUNC("... total # of files:", len(relative_all_exist_files))
	relative_all_pmx = [f for f in relative_all_exist_files if f.lower().endswith(".pmx")]
	core.MY_PRINT_FUNC("... total # of PMX models:", len(relative_all_pmx))
	relative_exist_img_files = [f for f in relative_all_exist_files if f.lower().endswith(IMG_EXT)]
	core.MY_PRINT_FUNC("... total # of image sources:", len(relative_exist_img_files))

	core.MY_PRINT_FUNC("")
	
	# this will accumulate the list of PMXes
	list_of_pmx_with_missing_tex = []
	
	list_of_pmx_that_somehow_failed = []
	
	# 3. for each pmx,
	for d, pmx_name in enumerate(relative_all_pmx):
		# progress print
		core.MY_PRINT_FUNC("\n%d / %d" % (d+1, len(relative_all_pmx)))
		# wrap the actual work with a try-catch just in case
		# this is a gigantic time investment and I dont want it to fail halfway thru and lose everything
		try:
			# 4. read the pmx, gotta store it in the dict like this cuz shut up thats why
			# dictionary where keys are filename and values are resulting pmx objects
			all_pmx_obj = {}
			this_pmx_obj = pmxlib.read_pmx(os.path.join(rootdir, pmx_name), moreinfo=False)
			all_pmx_obj[pmx_name] = this_pmx_obj
			
			# 5. filter images down to only images underneath the same folder as the pmx
			pmx_folder = os.path.dirname(pmx_name).lower()
			possible_img_sources = [f for f in relative_exist_img_files if
									f.lower().startswith(pmx_folder)]
			# trim the leading "pmx_folder" portion from these names
			possible_img_sources = [os.path.relpath(f, pmx_folder) for f in possible_img_sources]
			
			# 6. make filerecord_list
			# for each pmx, for each file on disk, match against files used in textures (case-insensitive) and replace with canonical name-on-disk
			# also fill out how much and how each file is used, and unify dupes between files, all that good stuff
			filerecord_list = file_sort_textures.build_filerecord_list(all_pmx_obj, possible_img_sources, False)
			
			# 7. if within filerecordlist, any filerecord is used but does not exist,
			if any(((fr.numused != 0) and (not fr.exists)) for fr in filerecord_list):
				# then save this pmx name
				list_of_pmx_with_missing_tex.append(pmx_name)
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("ERROR! some kind of exception interrupted reading pmx '%s'" % pmx_name)
			list_of_pmx_that_somehow_failed.append(pmx_name)
	
	core.MY_PRINT_FUNC("\n\n")
	
	# make the paths absolute
	list_of_pmx_that_somehow_failed = [os.path.join(rootdir, p) for p in list_of_pmx_that_somehow_failed]
	list_of_pmx_with_missing_tex = [os.path.join(rootdir, p) for p in list_of_pmx_with_missing_tex]
	
	# print & write-to-file
	if list_of_pmx_that_somehow_failed:
		core.MY_PRINT_FUNC("WARNING: failed in some way on %d PMX files" % len(list_of_pmx_that_somehow_failed))
		core.MY_PRINT_FUNC("Writing the full list to text file:")
		output_filename_failures = core.get_unused_file_name(FAILED_LIST_FILE)
		core.write_list_to_txtfile(output_filename_failures, list_of_pmx_that_somehow_failed)
	core.MY_PRINT_FUNC("Found %d / %d PMX files that are missing at least one texture source" %
					   (len(list_of_pmx_with_missing_tex), len(relative_all_pmx)))
	core.MY_PRINT_FUNC("Writing the full list to text file:")
	output_filename_missingtex = core.get_unused_file_name(MISSINGTEX_LIST_FILE)
	core.write_list_to_txtfile(output_filename_missingtex, list_of_pmx_with_missing_tex)
	
	# print(list_of_pmx_with_missing_tex)
	
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 1/29/2021 - v5.07")
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
			core.MY_PRINT_FUNC(ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
