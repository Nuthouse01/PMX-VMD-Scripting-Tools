import os

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
from mmd_scripting.core import translation_functions
from mmd_scripting.scripts_for_gui import file_sort_textures

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.00 - 6/10/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


# sometimes chinese translation gives better results than japanese translation
# when false, force input to be interpreted as Japanese. When true, autodetect input language.
GOOGLE_AUTODETECT_LANGUAGE = True


# this is recommended true, for obvious reasons
MAKE_BACKUP_BEFORE_RENAMES = True
# note: zipper automatically appends .zip onto whatever output name i give it, so dont give it a .zip suffix here
BACKUP_SUFFIX = "beforetranslate"

# build a dict that will fix windows-forbidden characters in file names
invalid_windows_chars = ':*?"<>|'  # specific invalid characters
invalid_windows_chars_ord = dict((ord(c), "_") for c in invalid_windows_chars)
for cc in range(32):  # non-printing control characters
	invalid_windows_chars_ord[cc] = ""


helptext = '''=================================================
file_translate_filenames:
This tool will translate any JP components of file/folder names to EN names.
This requires a PMX file to use as a root so it knows where to start reading files from.
This DOES NOT translate the name of the folder that the target PMX is sitting inside.
Before actually changing anything, it will list all proposed file renames and ask for final confirmation.
It also creates a zipfile backup of the entire folder, just in case.
Bonus: this can process all "neighbor" pmx files in addition to the target, this highly recommended because neighbors usually reference similar sets of files.

Note: unlike my other scripts, this overwrites the original input PMX file(s) instead of creating a new file with a suffix. This is because I already create a zipfile that contains the original input PMX, so that serves as a good backup.
'''

def main(moreinfo=False):
	core.MY_PRINT_FUNC("Please enter name of PMX model file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	
	# # step zero: set up the translator thingy
	# translation_functions.init_googletrans()
	
	# texture sorting plan:
	# 1. get startpath = basepath of input PMX
	# 2. get lists of relevant files
	# 	2a. extract top-level 'neighbor' pmx files from all-set
	# 3. ask about modifying neighbor PMX
	# 4. read PMX: either target or target+all neighbor
	# 5. "categorize files & normalize usages within PMX", NEW FUNC!!!
	# 6. translate all names via Google Trans, don't even bother with local dict
	# 7. mask out invalid windows filepath chars just to be safe
	# 8. print proposed names & other findings
	# 	for unused files under a folder, combine & replace with ***
	# 9. ask for confirmation
	# 10. zip backup (NEW FUNC!)
	# 11. apply renaming, NEW FUNC! rename all including old PMXes on disk
	# 12. get new names for PMXes, write PMX from mem to disk if any of its contents changed
	#	i.e. of all FileRecord with a new name, create a set of all the PMX that use them

	
	# absolute path to directory holding the pmx
	input_filename_pmx_abs = os.path.normpath(os.path.abspath(input_filename_pmx))
	startpath, input_filename_pmx_rel = os.path.split(input_filename_pmx_abs)
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# first, build the list of ALL files that actually exist, then filter it down to neighbor PMXs and relevant files
	relative_all_exist_files = file_sort_textures.walk_filetree_from_root(startpath)
	core.MY_PRINT_FUNC("ALL EXISTING FILES:", len(relative_all_exist_files))
	# now fill "neighbor_pmx" by finding files without path separator that end in PMX
	# these are relative paths tho
	neighbor_pmx = [f for f in relative_all_exist_files if 
					(f.lower().endswith(".pmx")) and
					(os.path.sep not in f) and
					f != input_filename_pmx_rel]
	
	# no filtering, all files are relevant
	relevant_exist_files = relative_all_exist_files
	
	core.MY_PRINT_FUNC("NEIGHBOR PMX FILES:", len(neighbor_pmx))
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# now ask if I care about the neighbors and read the PMXes into memory
	
	pmx_filenames = [input_filename_pmx_rel]
	
	if neighbor_pmx:
		core.MY_PRINT_FUNC("")
		info = [
			"Detected %d top-level neighboring PMX files, these probably share the same filebase as the target." % len(neighbor_pmx),
			"If files are moved/renamed but the neighbors are not processed, the neighbor texture references will probably break.",
			"Do you want to process all neighbors in addition to the target? (highly recommended)",
			"1 = Yes, 2 = No"]
		r = core.MY_SIMPLECHOICE_FUNC((1, 2), info)
		if r == 1:
			core.MY_PRINT_FUNC("Processing target + all neighbor files")
			# append neighbor PMX files onto the list of files to be processed
			pmx_filenames += neighbor_pmx
		else:
			core.MY_PRINT_FUNC("WARNING: Processing only target, ignoring %d neighbor PMX files" % len(neighbor_pmx))
	# now read all the PMX objects & store in dict alongside the relative name
	# dictionary where keys are filename and values are resulting pmx objects
	all_pmx_obj = {}
	for this_pmx_name in pmx_filenames:
		this_pmx_obj = pmxlib.read_pmx(os.path.join(startpath, this_pmx_name), moreinfo=moreinfo)
		all_pmx_obj[this_pmx_name] = this_pmx_obj
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# 	for each pmx, for each file on disk, match against files used in textures (case-insensitive) and replace with canonical name-on-disk
	#	also fill out how much and how each file is used, and unify dupes between files, all that good stuff
	
	filerecord_list = file_sort_textures.build_filerecord_list(all_pmx_obj, relevant_exist_files, moreinfo)
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# DETERMINE NEW NAMES FOR FILES
	
	# how to remap: build a list of all destinations (lowercase) to see if any proposed change would lead to collision
	all_new_names = set()
	
	# get new names via google
	# force it to use chunk-wise translate
	newname_list = translation_functions.google_translate([p.name for p in filerecord_list],
														  autodetect_language=GOOGLE_AUTODETECT_LANGUAGE,
														  chunks_only_kanji=False)
	
	# now repair any windows-forbidden symbols that might have shown up after translation
	newname_list = [n.translate(invalid_windows_chars_ord) for n in newname_list]
	
	# iterate over the results in parallel with the FileRecord items
	for p, newname in zip(filerecord_list, newname_list):
		if newname != p.name:
			# resolve potential collisions by adding numbers suffix to file names
			# first need to make path absolute so filepath_get_unused_name can check the disk.
			# then check uniqueness against files on disk and files in namelist (files that WILL be on disk)
			newname = core.filepath_get_unused_name(os.path.join(startpath, newname), namelist=all_new_names)
			# now dest path is guaranteed unique against other existing files & other proposed name changes
			all_new_names.add(newname.lower())
			# make the path no longer absolute: undo adding "startpath" above
			newname = os.path.relpath(newname, startpath)
			p.newname = newname
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# NOW PRINT MY PROPOSED RENAMINGS and other findings
	
	# isolate the ones with proposed renaming
	translated_file = [u for u in filerecord_list if u.newname is not None]
	
	if translated_file:
		core.MY_PRINT_FUNC("="*60)
		core.MY_PRINT_FUNC("Found %d JP filenames to be translated:" % len(translated_file))
		oldname_list = core.MY_JUSTIFY_STRINGLIST([p.name for p in translated_file])
		newname_list = [p.newname for p in translated_file]
		zipped = list(zip(oldname_list, newname_list))
		zipped_and_sorted = sorted(zipped, key=lambda y: file_sort_textures.sortbydirdepth(y[0]))
		for o,n in zipped_and_sorted:
			# print 'from' with the case/separator it uses in the PMX
			core.MY_PRINT_FUNC("   {:s} --> {:s}".format(o, n))
		core.MY_PRINT_FUNC("="*60)
	else:
		core.MY_PRINT_FUNC("No proposed file changes")
		core.MY_PRINT_FUNC("Aborting: no files were changed")
		return None
	
	info = ["Do you accept these new names/locations?",
			"1 = Yes, 2 = No (abort)"]
	r = core.MY_SIMPLECHOICE_FUNC((1, 2), info)
	if r == 2:
		core.MY_PRINT_FUNC("Aborting: no files were changed")
		return None
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# finally, do the actual renaming:
	
	# first, create a backup of the folder
	if MAKE_BACKUP_BEFORE_RENAMES:
		r = file_sort_textures.make_zipfile_backup(startpath, BACKUP_SUFFIX)
		if not r:
			# this happens if the backup failed somehow AND the user decided to quit
			core.MY_PRINT_FUNC("Aborting: no files were changed")
			return None
	
	# do all renaming on disk and in PMXes, and also handle the print statements
	file_sort_textures.apply_file_renaming(all_pmx_obj, filerecord_list, startpath)
	
	# write out
	for this_pmx_name, this_pmx_obj in all_pmx_obj.items():
		# what name do i write this pmx to? it may be different now! find it in the FileRecord!
		# this script does not filter filerecord_list so it is guaranteed to hae a record
		rec = None
		for r in filerecord_list:
			if r.name == this_pmx_name:
				rec = r
				break
		if rec.newname is None:
			# if there is no new name, write back to the name it had previously
			new_pmx_name = rec.name
		else:
			# if there is a new name, write to the new name
			new_pmx_name = rec.newname
		# make the name absolute
		output_filename_pmx = os.path.join(startpath, new_pmx_name)
		# write it, overwriting the existing file at that name
		pmxlib.write_pmx(output_filename_pmx, this_pmx_obj, moreinfo=moreinfo)
	
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
