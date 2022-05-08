import os

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
from mmd_scripting.scripts_for_gui import file_sort_textures

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.00 - 6/10/2021"
# this one is for you, syblomic-dash



def main():
	print("Open all PMX files at the selected level and replace usages of texure file XXXXX with YYYYY")
	
	core.MY_PRINT_FUNC("Please enter name of PMX model file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	
	# absolute path to directory holding the pmx
	input_filename_pmx_abs = os.path.normpath(os.path.abspath(input_filename_pmx))
	startpath, input_filename_pmx_rel = os.path.split(input_filename_pmx_abs)
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# first, build the list of ALL files that actually exist, then filter it down to neighbor PMXs
	relative_all_exist_files = file_sort_textures.walk_filetree_from_root(startpath)
	# now fill "neighbor_pmx" by finding files without path separator that end in PMX
	# these are relative paths tho
	pmx_filenames = [f for f in relative_all_exist_files if
					(f.lower().endswith(".pmx")) and
					(os.path.sep not in f)]
	
	# now read all the PMX objects & store in dict alongside the relative name
	# dictionary where keys are filename and values are resulting pmx objects
	all_pmx_obj = {}
	for this_pmx_name in pmx_filenames:
		this_pmx_obj = pmxlib.read_pmx(os.path.join(startpath, this_pmx_name), moreinfo=False)
		all_pmx_obj[this_pmx_name] = this_pmx_obj
	
	core.MY_PRINT_FUNC("ALL PMX FILES:")
	for pmxname in pmx_filenames:
		core.MY_PRINT_FUNC("    " + pmxname)
	
	core.MY_PRINT_FUNC("\n\n\n")
	core.MY_PRINT_FUNC("WARNING: this script will overwrite all PMX files it operates on. This does NOT create a backup. Be very careful what you type!")
	core.MY_PRINT_FUNC("\n\n\n")

	findme = core.MY_GENERAL_INPUT_FUNC(lambda x: True, "Please specify which filepath to find:")
	findme = os.path.normpath(findme.strip()) # sanitize it
	# if empty, quit
	if findme == "" or findme is None:
		core.MY_PRINT_FUNC("quitting")
		return None

	replacewith = core.MY_GENERAL_INPUT_FUNC(lambda x: True, "Please specify which filepath to replace it with:")
	replacewith = os.path.normpath(replacewith.strip()) # sanitize it

	# if empty, quit
	if replacewith == "" or replacewith is None:
		core.MY_PRINT_FUNC("quitting")
		return None
	
	core.MY_PRINT_FUNC("Replacing '%s' with '%s'" % (findme, replacewith))
	
	# now do find & replace!
	# for each pmx,
	for this_pmx_name, this_pmx_obj in all_pmx_obj.items():
		# do find-and-replace
		howmany = file_sort_textures.texname_find_and_replace(this_pmx_obj, findme, replacewith, sanitize=True)
		# then report how many
		core.MY_PRINT_FUNC("")
		core.MY_PRINT_FUNC("'%s': replaced %d" % (this_pmx_name, howmany))
		
		if howmany != 0:
			# NOTE: this is OVERWRITING THE PREVIOUS PMX FILE, NOT CREATING A NEW ONE
			# because I make a zipfile backup I don't need to feel worried about preserving the old version
			output_filename_pmx = os.path.join(startpath, this_pmx_name)
			# output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
			pmxlib.write_pmx(output_filename_pmx, this_pmx_obj, moreinfo=False)

	
	core.MY_PRINT_FUNC("Done!")
	return None
	

if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.RUN_WITH_TRACEBACK(main)
