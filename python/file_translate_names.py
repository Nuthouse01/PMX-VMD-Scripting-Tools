# Nuthouse01 - 06/10/2020 - v4.08
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# os.path, os.walk, os.renames
import os

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
	from . import file_sort_textures
except ImportError as eee:
	try:
		import nuthouse01_core as core
		import nuthouse01_pmx_parser as pmxlib
		import file_sort_textures
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = pmxlib = file_sort_textures = None


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = True


# this is recommended true, for obvious reasons
MAKE_BACKUP_BEFORE_RENAMES = True
# note: zipper automatically appends .zip onto whatever output name i give it, so dont give it a .zip suffix here
BACKUP_SUFFIX = "beforetranslate"


# a struct to bundle all the relevant info about a file that is on disk or used by PMX
class filerecord:
	def __init__(self, name, exists):
		# the "clean" name this file uses on disk: relative to startpath and separator-normalized
		# or, if it does not exist on disk, whatever name shows up in the PMX entry
		self.name = name
		# true if this is a real file that exists on disk
		self.exists = exists
		# dict of all PMX that reference this file at least once:
		# keys are strings which are filepath relative to startpath and separator-normalized
		# values are index it appears at, saves searching time
		self.used_pmx = dict()
		# set of all ways this file is used within PMXes
		self.usage = set()
		# total number of times this file is used... not required for the script, just interesting stats
		self.numused = 0
		# the name this file will be renamed to
		self.newname = None

	def __str__(self) -> str:
		p = "'%s': used as %s, %d times among %d files" % (
			self.name, self.usage, self.numused, len(self.used_pmx))
		return p



helptext = '''=================================================
texture_file_sort:
This tool will sort the tex/spheremap/toon files used by a model into folders for each category.
Unused image files can be moved into an "unused" folder, to declutter things.
Any files referenced by the PMX that do not exist on disk will be listed.
Before actually changing anything, it will list all proposed file renames and ask for final confirmation.
It also creates a zipfile backup of the entire folder, just in case.
Bonus: this can process all "neighbor" pmx files in addition to the target, this highly recommended because neighbors usually reference similar sets of files.

Note: *** means "all files within this folder"
Note: unfortunately, any "preview" images that exist cannot be distinguished from clutter, and will be moved into the "unused" folder. Remember to move them back!
Note: unlike my other scripts, this overwrites the original input PMX file(s) instead of creating a new file with a suffix. This is because I already create a zipfile that contains the original input PMX, so that serves as a good backup.
'''

def main(moreinfo=False):
	core.MY_PRINT_FUNC("Please enter name of PMX model file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")
	
	# texture sorting plan:
	# 1. get startpath = basepath of input PMX
	# 2. get lists of relevant files
	# 	2a. get list of ALL files within the tree, relative to startpath
	# 	2b. extract top-level 'neighbor' pmx files from all-set
	# 	2c. remove files i intend to ignore (filter by file ext or containing folder)
	# 3. ask about modifying neighbor PMX
	# 4. read PMX: either target or target+all neighbor
	# 5. "categorize files & normalize usages within PMX", NEW FUNC!!!
	# 	inputs: list of PMX obj, list of relevant files
	# 	outputs: list of structs that bundle all relevant info about the file (replace 2 structs currently used)
	# 	for each pmx, for each file on disk, match against files used in textures (case-insensitive) and replace with canonical name-on-disk
	# now have all files, know their states!
	# 6. ask for "aggression level" to control how files will be moved
	# 7. determine new names for files
	# 	this is the big one, slightly different logic for different categories
	# 8. print proposed names & other findings
	# 	for unused files under a folder, combine & replace with ***
	# 9. ask for confirmation
	# 10. zip backup (NEW FUNC!)
	# 11. apply renaming, NEW FUNC!
	# 	first try to rename all files
	# 		could plausibly fail, if so, set to-name to None/blank
	# 	then, in the PMXs, rename all files that didn't fail

	
	# absolute path to directory holding the pmx
	input_filename_pmx_abs = os.path.normpath(os.path.abspath(input_filename_pmx))
	startpath, input_filename_pmx_rel = os.path.split(input_filename_pmx_abs)
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# first, build the list of ALL files that actually exist, then filter it down to neighbor PMXs and relevant files
	relative_all_exist_files = walk_filetree_from_root(startpath)
	core.MY_PRINT_FUNC("ALL EXISTING FILES:", len(relative_all_exist_files))
	# now fill "neighbor_pmx" by finding files without path separator that end in PMX
	# these are relative paths tho
	neighbor_pmx = [f for f in relative_all_exist_files if 
					(f.lower().endswith(".pmx")) and
					(os.path.sep not in f) and
					f != input_filename_pmx_rel]
	
	relevant_exist_files = []
	for f in relative_all_exist_files:
		# ignore all files I expect to find alongside a PMX and don't want to touch or move
		if f.lower().endswith(IGNORE_FILETYPES): continue
		# ignore any files living below/inside 'special' folders like "fx/"
		if match_folder_anylevel(f, IGNORE_FOLDERS, toponly=False): continue
		# create the list of files we know exist and we know we care about
		relevant_exist_files.append(f)

	core.MY_PRINT_FUNC("RELEVANT EXISTING FILES:", len(relevant_exist_files))
	
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
	
	filerecord_list = categorize_files(all_pmx_obj, relevant_exist_files, moreinfo)
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# now check which files are used/unused/dont exist
	
	# break this into used/notused/notexist lists for simplicity sake
	# all -> used + notused
	# used -> used_exist + used_notexist
	# notused -> notused_img + notused_notimg
	used, notused =               core.my_list_partition(filerecord_list, lambda q: q.numused != 0)
	used_exist, used_notexist =   core.my_list_partition(used, lambda q: q.exists)
	notused_img, notused_notimg = core.my_list_partition(notused, lambda q: q.name.lower().endswith(IMG_EXT))
	
	core.MY_PRINT_FUNC("PMX TEXTURE SOURCES:", len(used))
	if moreinfo:
		for x in used:
			core.MY_PRINT_FUNC("  " + str(x))
	
	# now:
	# all duplicates have been resolved within PMX, including modifying the PMX
	# all duplicates have been resolved across PMXes
	# all file exist/notexist status is known
	# all file used/notused status is known (via numused), or used_pmx
	# all ways a file is used is known
	
	global MOVE_TOPLEVEL_UNUSED_IMG
	global MOVE_ALL_UNUSED_IMG
	# only ask what files to move if there are files that could potentially be moved
	if notused_img:
		# count the number of toplevel vs not-toplevel in "notused_img"
		num_toplevel = len([p for p in notused_img if (os.path.sep not in p.name)])
		num_nontoplevel = len(notused_img) - num_toplevel
		# ask the user what "aggression" level they want
		showinfo = ["Detected %d unused top-level files and %d unused files in directories." % (num_toplevel, num_nontoplevel),
					"Which files do you want to move to 'unused' folder?",
					"1 = Do not move any, 2 = Move only top-level unused, 3 = Move all unused"]
		c = core.MY_SIMPLECHOICE_FUNC((1,2,3), showinfo)
		if c == 1:
			MOVE_TOPLEVEL_UNUSED_IMG = False
			MOVE_ALL_UNUSED_IMG = False
		if c == 2:
			MOVE_TOPLEVEL_UNUSED_IMG = True
			MOVE_ALL_UNUSED_IMG = False
		if c == 3:
			MOVE_TOPLEVEL_UNUSED_IMG = True
			MOVE_ALL_UNUSED_IMG = True
		
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# DETERMINE NEW NAMES FOR FILES
	
	# how to remap: build a list of all destinations (lowercase) to see if any proposed change would lead to collision
	all_new_names = set()
	
	# don't touch the unused_notimg files at all, unless some flag is set
	
	# not-used top-level image files get moved to 'unused' folder
	# also all spa/sph get renamed to .bmp (but remember these are all unused so i don't need to update them in the pmx)
	for p in notused_img:
		newname = remove_pattern(p.name)
		if ((os.path.sep not in p.name) and MOVE_TOPLEVEL_UNUSED_IMG) or MOVE_ALL_UNUSED_IMG:
			# this deserves to be moved to 'unused' folder!
			newname = os.path.join(FOLDER_UNUSED, os.path.basename(newname))
		
		# ensure the extension is lowercase, for cleanliness
		dot = newname.rfind(".")
		newname = newname[:dot] + newname[dot:].lower()
		if CONVERT_SPA_SPH_TO_BMP and newname.endswith((".spa",".sph")):
			newname = newname[:-4] + ".bmp"
		# if the name I build is not the name it already has, queue it for actual rename
		if newname != p.name:
			# resolve potential collisions by adding numbers suffix to file names
			# first, check against whats on disk. need to make path absolute so get_unused_file_name can check the disk.
			newname = core.get_unused_file_name(os.path.join(startpath, newname))
			# make the path no longer absolute: undo adding "startpath" above
			newname = os.path.relpath(newname, startpath)
			# second, check against other proposed rename targets
			newname = core.get_unused_file_name(newname, all_new_names)
			# now dest path is guaranteed unique against other existing files & other proposed name changes
			all_new_names.add(newname.lower())
			p.newname = newname
	
	# used files get sorted into tex/toon/sph/multi (unless tex and already in a folder that says clothes, etc)
	# all SPH/SPA get renamed to BMP, used or unused
	for p in used_exist:
		newname = remove_pattern(p.name)
		usage_list = list(p.usage)
		if len(p.usage) != 1:
			# this is a rare multiple-use file
			newname = os.path.join(FOLDER_MULTI, os.path.basename(newname))
		elif usage_list[0] == FOLDER_SPH:
			# this is an sph, duh
			if not match_folder_anylevel(p.name, KEEP_FOLDERS_SPH, toponly=True):
				# if its name isn't already good, then move it to my new location
				newname = os.path.join(FOLDER_SPH, os.path.basename(newname))
		elif usage_list[0] == FOLDER_TOON:
			# this is a toon, duh
			if not match_folder_anylevel(p.name, KEEP_FOLDERS_TOON, toponly=True):
				# if its name isn't already good, then move it to my new location
				newname = os.path.join(FOLDER_TOON, os.path.basename(newname))
		elif usage_list[0] == FOLDER_TEX:
			# if a tex AND already in a folder like body, clothes, wear, tex, etc then keep that folder
			if not match_folder_anylevel(p.name, KEEP_FOLDERS_TEX, toponly=True):
				# if its name isn't already good, then move it to my new location
				newname = os.path.join(FOLDER_TEX, os.path.basename(newname))
		
		# ensure the extension is lowercase, for cleanliness
		dot = newname.rfind(".")
		newname = newname[:dot] + newname[dot:].lower()
		if CONVERT_SPA_SPH_TO_BMP and newname.lower().endswith((".spa", ".sph")):
			newname = newname[:-4] + ".bmp"
		# if the name I build is not the name it already has, queue it for actual rename
		if newname != p.name:
			# resolve potential collisions by adding numbers suffix to file names
			# first, check against whats on disk. need to make path absolute so get_unused_file_name can check the disk.
			newname = core.get_unused_file_name(os.path.join(startpath, newname))
			# make the path no longer absolute: undo adding "startpath" above
			newname = os.path.relpath(newname, startpath)
			# second, check against other proposed rename targets
			newname = core.get_unused_file_name(newname, all_new_names)
			# now dest path is guaranteed unique against other existing files & other proposed name changes
			all_new_names.add(newname.lower())
			p.newname = newname
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# NOW PRINT MY PROPOSED RENAMINGS and other findings
	
	# isolate the ones with proposed renaming
	used_rename =          [u for u in used_exist if u.newname is not None]
	notused_img_rename =   [u for u in notused_img if u.newname is not None]
	notused_img_norename = [u for u in notused_img if u.newname is None]
	
	# bonus goal: if ALL files under a folder are unused, replace its name with a star
	# first build dict of each dirs to each file any depth below that dir
	all_dirnames = {}
	for f in relative_all_exist_files:
		d = os.path.dirname(f)
		while d != "":
			try:				all_dirnames[d].append(f)
			except KeyError:	all_dirnames[d] = [f]
			d = os.path.dirname(d)
	unused_dirnames = []
	all_notused_searchable = [x.name for x in notused_img_norename] + [x.name for x in notused_notimg]
	for d,files_under_d in all_dirnames.items():
		# if all files beginning with d are notused (either type), this dir can be replaced with *
		# note: min crashes if input list is empty, but this is guaranteed to not be empty
		dir_notused = min([(f in all_notused_searchable) for f in files_under_d])
		if dir_notused:
			unused_dirnames.append(d)
	# print("allundir", unused_dirnames)
	# now, remove all dirnames that are encompassed by another dirname
	j = 0
	while j < len(unused_dirnames):
		dj = unused_dirnames[j]
		k = 0
		while k < len(unused_dirnames):
			dk = unused_dirnames[k]
			if dj != dk and dk.startswith(dj):
				unused_dirnames.pop(k)
			else:
				k += 1
		j += 1
	# make sure unused_dirnames has the deepest directories first
	unused_dirnames = sorted(unused_dirnames, key=sortbydirdepth, reverse=True)
	# print("unqundir", unused_dirnames)
	# then as I go to print notused_img_norename or notused_notimg, collapse them?
	
	# for each section, if it exists, print its names sorted first by directory depth then alphabetically (case insensitive)
	
	if used_notexist:
		core.MY_PRINT_FUNC("="*60)
		core.MY_PRINT_FUNC("Found %d references to images that don't exist (no proposed changes)" % len(used_notexist))
		for p in sorted(used_notexist, key=lambda y: sortbydirdepth(y.name)):
			# print orig name, usage modes, # used, and # files that use it
			core.MY_PRINT_FUNC("   " + str(p))
	if notused_img_norename:
		core.MY_PRINT_FUNC("="*60)
		core.MY_PRINT_FUNC("Found %d not-used images in the file tree (no proposed changes)" % len(notused_img_norename))
		printme = set()
		for p in notused_img_norename:
			# is this notused-file anywhere below any unused dir?
			t = False
			for d in unused_dirnames:
				if p.name.startswith(d):
					# add this dir, not this file, to the print set
					printme.add(os.path.join(d, "***"))
					t = True
			if not t:
				# if not encompassed by an unused dir, add the filename
				printme.add(p.name)
		# convert set back to sorted list
		printme = sorted(list(printme), key=sortbydirdepth)
		for s in printme:
			core.MY_PRINT_FUNC("   " + s)
	if notused_notimg:
		core.MY_PRINT_FUNC("="*60)
		core.MY_PRINT_FUNC("Found %d not-used not-images in the file tree (no proposed changes)" % len(notused_notimg))
		printme = set()
		for p in notused_notimg:
			# is this notused-file anywhere below any unused dir?
			t = False
			for d in unused_dirnames:
				if p.name.startswith(d):
					# add this dir, not this file, to the print set
					printme.add(os.path.join(d, "***"))
					t = True
			if not t:
				# if not encompassed by an unused dir, add the filename
				printme.add(p.name)
		# convert set back to sorted list
		printme = sorted(list(printme), key=sortbydirdepth)
		for s in printme:
			core.MY_PRINT_FUNC("   " + s)
	# print with all "from" file names left-justified so all the arrows are nicely lined up (unless they use jp characters)
	longest_name_len = 0
	for p in used_rename:
		longest_name_len = max(longest_name_len, len(p.name))
	for p in notused_img_rename:
		longest_name_len = max(longest_name_len, len(p.name))
	if used_rename:
		core.MY_PRINT_FUNC("="*60)
		core.MY_PRINT_FUNC("Found %d used files to be moved/renamed:" % len(used_rename))
		for p in sorted(used_rename, key=lambda y: sortbydirdepth(y.name)):
			# print 'from' with the case/separator it uses in the PMX
			core.MY_PRINT_FUNC("   {0:<{size}} --> {1:s}".format(p.name, p.newname, size=longest_name_len))
	if notused_img_rename:
		core.MY_PRINT_FUNC("="*60)
		core.MY_PRINT_FUNC("Found %d not-used images to be moved/renamed:" % len(notused_img_rename))
		for p in sorted(notused_img_rename, key=lambda y: sortbydirdepth(y.name)):
			core.MY_PRINT_FUNC("   {0:<{size}} --> {1:s}".format(p.name, p.newname, size=longest_name_len))
	core.MY_PRINT_FUNC("="*60)
	
	if not (used_rename or notused_img_rename):
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
		r = make_zipfile_backup(startpath, BACKUP_SUFFIX)
		if not r:
			# this happens if the backup failed somehow AND the user decided to quit
			core.MY_PRINT_FUNC("Aborting: no files were changed")
			return None
	
	# do all renaming on disk and in PMXes, and also handle the print statements
	apply_file_renaming(all_pmx_obj, filerecord_list, startpath)
	
	# write out
	for this_pmx_name, this_pmx_obj in all_pmx_obj.items():
		# NOTE: this is OVERWRITING THE PREVIOUS PMX FILE, NOT CREATING A NEW ONE
		# because I make a zipfile backup I don't need to feel worried about preserving the old version
		output_filename_pmx = os.path.join(startpath, this_pmx_name)
		# output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
		pmxlib.write_pmx(output_filename_pmx, this_pmx_obj, moreinfo=moreinfo)
	
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 06/10/2020 - v4.08")
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
