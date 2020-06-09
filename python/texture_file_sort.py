# Nuthouse01 - 06/08/2020 - v4.07
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# os.path, os.walk, os.renames
import os
# shutil.make_archive
import shutil

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
	from ._prune_unused_vertices import newval_from_range_map, delme_list_to_rangemap
except ImportError as eee:
	try:
		import nuthouse01_core as core
		import nuthouse01_pmx_parser as pmxlib
		from _prune_unused_vertices import newval_from_range_map, delme_list_to_rangemap
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = pmxlib = None
		newval_from_range_map = delme_list_to_rangemap = None

# in "memo" section, spaces are backslash-escaped, how does this affect printing? what about spaces in file path?
# just dont touch memo, its read back just fine
# for file paths, use doublebackslash, they are read just fine too


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = True


# fun fact: SPH and SPA files are just BMP files with the wrong file extension
# if this is true, all SPH/SPA files will be converted to BMP
# this is so its easier to read/see the sphere map files
# this is recommended true
CONVERT_SPA_SPH_TO_BMP = True


# this is recommended true, for decluttering
MOVE_TOPLEVEL_UNUSED_IMG = True
# this is recommended false, to make only the minimum necessary changes
MOVE_ALL_UNUSED_IMG = False

# this is recommended true, for obvious reasons
MAKE_BACKUP_BEFORE_RENAMES = True
# note: zipper automatically appends .zip onto whatever output name i give it, so dont give it a .zip suffix here
BACKUP_SUFFIX = ".renamebackup"


# these are the names of the folders that the files will be sorted into, these can be changed to whatever you want
# they cannot use the same names as eachother, however, all must be unique
FOLDER_TEX =    "tex"
FOLDER_SPH =    "sph"
FOLDER_TOON =   "toon"
FOLDER_MULTI =  "multi"
FOLDER_UNUSED = "unused"

IMG_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".spa", ".sph", ".tga", ".xcf", ".dds", ".gif", ".psd")
KEEP_FOLDERS_TEX = ("cloth", "outfit", "uniform", "wear", "body", "tex", "weapon", "acc", "face", "tx")
KEEP_FOLDERS_TOON = ("tn", "toon")
KEEP_FOLDERS_SPH = ("sph", "spa", "sp")
# all files I expect to find alongside a PMX and don't want to touch/move
IGNORE_FILETYPES = (".pmx", ".x", ".txt", ".vmd", ".vpd", ".csv")
# all folders I expect to find alongside a PMX and don't want to touch/move any of their contents
IGNORE_FOLDERS = ("fx", "effect", "readme")



def match_in_top_folder(s: str, keep: tuple) -> bool:
	# search for keepnames in only first folder level
	v = s.find("\\")
	if v == -1:
		# if there is no toplevel folder, just naked file, then return false
		return False
	# take only the part before the first path sep, also lowercase
	s_top = s[0:v].lower()
	for k in keep:
		# not exact match, looking for any case-insensitive substring
		if k in s_top:
			# if any of them match return true.
			return True
	# if no match, return false
	return False


def sortbydirdepth(s: str) -> str:
	# pipe gets sorted last, so prepend end-of-unicode char to make something get sorted lower
	# more slashes in name = more subdirectories = lower on the tree
	return (chr(0x10FFFF) * s.count("\\")) + s.lower()


def remove_pattern(s: str) -> str:
	# remove a specific pattern in filenames that were ported by a specific tool
	# return the version
	v = s.find("(Instance)")
	if v == -1:
		return s
	slice_start = v
	slice_end = v + 10
	if v != 0 and s[v-1] == " ":
		slice_start += -1
	v = s.find("(", slice_end)
	if v == -1:
		return s[:slice_start] + s[slice_end+1:]
	slice_end = v
	v = s.find(")", slice_end)
	if v == -1:
		return s[:slice_start] + s[slice_end+1:]
	return s[:slice_start] + s[v+1:]


# represent a file that appears in a PMX, may/maynot actually exist on disk
class pmxfile:
	def __init__(self, orig, index, sourcefile):
		self.orig = orig
		self.norm = os.path.normpath(orig)
		self.norm_lower = self.norm.lower()
		self.index_per_file = {sourcefile: index}
		self.exists = False
		self.dupe = None
		self.numused = 0
		self.usage = set()
		self.mapto = ""
		
	def __str__(self) -> str:
		p = "'%s': used as %s, %d times, among %d files" % (
			self.orig, self.usage, self.numused, len(self.index_per_file))
		return p
	

# represent a file that actually exist on disk, may/may not be used in a PMX
class existfile:
	# never delete items from the list of existing files, just keep adding more info
	def __init__(self, abspath, relpath):
		self.abs = abspath
		self.orig = relpath
		self.norm = relpath
		self.norm_lower = self.norm.lower()
		self.numused = 0
		# self.usage = set()
		self.mapto = ""
		self.istop = not bool(relpath.count("\\"))
	

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
	
	# absolute path to directory holding the pmx
	startpath = os.path.dirname(os.path.normpath(os.path.abspath(input_filename_pmx)))
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# first, build the list of ALL files that actually exist
	
	# os.walk: returns (path to the folder i'm in),(list of folders in this folder),(list of files in this folder)
	absolue_files_that_exist = []
	neighbor_pmx = []
	for where, subfolders, files in os.walk(startpath):
		# only fill neighbor_pmx once, only pmx files at same level as initial target
		# it will always find the target pmx so it will always become not empty
		if not neighbor_pmx:
			neighbor_pmx = [os.path.join(where, f) for f in files if f.lower().endswith(".pmx")]
		absolue_files_that_exist += [os.path.join(where, f) for f in files]
	core.MY_PRINT_FUNC("ALL EXISTING FILES:", len(absolue_files_that_exist))
	# "neighbor_pmx" has absolute paths of top-level pmx files, including the target
	# "absolue_files_that_exist" has absolute paths of ALL files, including target and neighbors
	files_that_exist = []
	for f in absolue_files_that_exist:
		# ignore all files I expect to find alongside a PMX and don't want to touch or move
		if f.lower().endswith(IGNORE_FILETYPES): continue
		rel = os.path.relpath(f, startpath)
		# ignore any files under a folder that is exactly "fx/"
		if match_in_top_folder(rel.lower(), IGNORE_FOLDERS): continue
		# create the object that will hold all the relevent information as processing goes on
		files_that_exist.append(existfile(f, rel))
		
	core.MY_PRINT_FUNC("RELEVANT EXISTING FILES:", len(files_that_exist))
	# for x in files_that_exist:
	# 	core.MY_PRINT_FUNC("  " , x)
	
	# remove self from neighbor_pmx
	neighbor_pmx.remove(os.path.abspath(input_filename_pmx))
	core.MY_PRINT_FUNC("NEIGHBOR PMX FILES:", len(neighbor_pmx))
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# now process the texture names that appear in the PMX(es)
	
	pmx_filenames = [input_filename_pmx]
	
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
			
		
	# ===================== begin for-each-pmx section
	# dictionary where keys are filename and values are resulting pmx objects
	all_pmx_obj = {}
	# holds all textures that are referenced by all PMX files
	files_in_pmx = []
	for this_pmx_name in pmx_filenames:
		this_pmx_obj = pmxlib.read_pmx(this_pmx_name, moreinfo=moreinfo)
		all_pmx_obj[this_pmx_name] = this_pmx_obj
		# pmx[3] is list of all filepaths used in the model
		
		files_in_this_pmx = []
		for d,orig in enumerate(this_pmx_obj[3]):
			# orig, norm, norm-lower, index, exists, dupeidx, usage-modes, mapto...
			files_in_this_pmx.append(pmxfile(orig, d, this_pmx_name))
			
		# doing usage-check BEFORE dupe-check? so i can unify usages of the dupes?
		
		# used files get sorted by HOW they are used... so go find that info
		# files are only used in materials pmx[4], and only tex=19/sph=20/toon=23 (only if 22==0)
		# material > index > files_in_pmx
		for mat in this_pmx_obj[4]:
			texid = mat[19]
			# filter out -1 which means "no file reference"
			if texid != -1:
				files_in_this_pmx[texid].usage.add(FOLDER_TEX)
				files_in_this_pmx[texid].numused += 1
			sphid = mat[20]
			if sphid != -1:
				files_in_this_pmx[sphid].usage.add(FOLDER_SPH)
				files_in_this_pmx[sphid].numused += 1
			if mat[22] == 0:
				toonid = mat[23]
				if toonid != -1:
					files_in_this_pmx[toonid].usage.add(FOLDER_TOON)
					files_in_this_pmx[toonid].numused += 1
		
		# now remove theoretical duplicates from the PMX... not likely but possible. cases can be different.
		for pj in files_in_this_pmx:
			for pk in files_in_this_pmx:
				if pj is pk:
					# skip, don't compare self with self
					continue
				if pj.norm_lower != pk.norm_lower:  # compare lower with lower
					# no match, skip
					continue
				# matched!
				if pj.dupe is None and pk.dupe is None:
					# if neither acknowledges the dupe, then mark one as such
					# this is rather rare, might as well print something for it
					if moreinfo:
						core.MY_PRINT_FUNC("unify dupe within pmx: idx%d='%s', idx%d='%s'" % (pj.index_per_file[this_pmx_name], pj.orig,
																				 pk.index_per_file[this_pmx_name], pk.orig))
					# the greater-index one has dupe set to reference the lower-index one
					pk.dupe = pj.index_per_file[this_pmx_name]
					# combine their "usage" sets
					pj.usage = pj.usage.union(pk.usage)
					# combine their "numused" counts, not actually used anywhere but w/e
					pj.numused += pk.numused
		# now all within-pmx dupes have been found & marked with their master
		# first build a dict of each dupe ID and what master ID it maps to
		dupe_to_master_map = {}
		for p in files_in_this_pmx:
			if p.dupe is not None:
				dupe_to_master_map[p.index_per_file[this_pmx_name]] = p.dupe
		if dupe_to_master_map:
			# now modify this PMX to resolve/consolidate/unify the duplicates:
			# first: make dellist & idx_shift_map
			dellist = list(dupe_to_master_map.keys())
			# make the idx_shift_map
			idx_shift_map = delme_list_to_rangemap(dellist)
			# second: delete the acutal textures from the actual texture list and my files_in_this_pmx list
			# at this point they guaranteed correspond 1-to-1
			for i in reversed(dellist):
				this_pmx_obj[3].pop(i)
				files_in_this_pmx.pop(i)
			# third: iter over materials, use dupe_to_master_map to replace dupe with master and newval_from_range_map to account for dupe deletion
			for mat in this_pmx_obj[4]:
				# no need to filter for -1s, because -1 isn't in the dupe_to_master_map and wont be changed by idx_shift_map
				if mat[19] in dupe_to_master_map: # tex id
					mat[19] = dupe_to_master_map[mat[19]]
				# remap regardless of whether it is replaced with master or not
				mat[19] = newval_from_range_map(mat[19], idx_shift_map)
				if mat[20] in dupe_to_master_map: # sph id
					mat[20] = dupe_to_master_map[mat[20]]
				mat[20] = newval_from_range_map(mat[20], idx_shift_map)
				if mat[22] == 0:
					if mat[23] in dupe_to_master_map: # toon id
						mat[23] = dupe_to_master_map[mat[23]]
					mat[23] = newval_from_range_map(mat[23], idx_shift_map)
			# fourth: remap indices in the files_in_this_pmx list too
			for p in files_in_this_pmx:
				p.index_per_file[this_pmx_name] = newval_from_range_map(p.index_per_file[this_pmx_name], idx_shift_map)
		
		# while I'm here I should modify thier path separators too, make them all consistient
		# not worth notifying user about this
		# NOTE: this step is technically optional and can be disabled if I have some reason to do so
		for p in files_in_this_pmx:
			this_pmx_obj[3][p.index_per_file[this_pmx_name]] = p.norm
			p.orig = p.norm
		
		# now each tex in this PMX has been uniquified within this PMX, and this PMX has been modified accordingly
		# the index_per_file dict has length of exactly 1 guaranteed
		# "dupe" field no longer has any meaning
		
		# add all the tex in this pmx file to the list of textures in all pmx files
		files_in_pmx += files_in_this_pmx
	# ===================== end for-each-pmx section
	
	# next, unify all tex among all pmx that reference the same file: basically the same approach as unifying tex within a pmx file
	# there is only one actual file on disk, even if each PMX references it. therefore there should only be one entry.
	j = 0
	while j < len(files_in_pmx):
		pj = files_in_pmx[j]
		k = 0
		while k < len(files_in_pmx):
			pk = files_in_pmx[k]
			if j != k and pj.norm_lower == pk.norm_lower:
				# matched! unify & pop
				# combine index_per_file dicts
				pj.index_per_file = dict(list(pj.index_per_file.items()) + list(pk.index_per_file.items()))
				# combine their "usage" sets, could be used as a tex in one file and used as a sph in another
				pj.usage = pj.usage.union(pk.usage)
				# combine their "numused" counts, not actually used anywhere but w/e
				pj.numused += pk.numused
				# delete it
				files_in_pmx.pop(k)
			else:
				# different, keep counting
				k += 1
		j += 1
	
	core.MY_PRINT_FUNC("PMX SOURCE FILES:", len(files_in_pmx))
	if moreinfo:
		for x in files_in_pmx:
			core.MY_PRINT_FUNC("  " + str(x))
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# now check which files are used/unused/dont exist
	
	for t in files_in_pmx:
		# try to match it against an existing file
		for ex in files_that_exist:
			if t.norm_lower == ex.norm_lower:
				# file exists! flag it in files_in_pmx
				t.exists = True
				# file is used! count it in files_that_exist
				ex.numused += 1
				break
	
	# now break this into used/notused/notexist lists for simplicity sake
	used =           [q for q in files_in_pmx if q.exists]
	notexist =       [q for q in files_in_pmx if not q.exists]
	notused_img =    [p for p in files_that_exist if p.numused == 0 and p.norm_lower.endswith(IMG_EXT)]
	notused_notimg = [p for p in files_that_exist if p.numused == 0 and not p.norm_lower.endswith(IMG_EXT)]
	
	# now:
	# all duplicates have been resolved within PMX, including modifying the PMX
	# all duplicates have been resolved across PMXes
	# all pmxfile exist/notexist status is known
	# all pmxfile usage mode is known
	# all exist file used/unused is known
	
	global MOVE_TOPLEVEL_UNUSED_IMG
	global MOVE_ALL_UNUSED_IMG
	# only ask what files to move if there are files that could potentially be moved
	if notused_img:
		# count the number of toplevel vs not-toplevel in "notused_img"
		num_toplevel = len([p for p in notused_img if p.istop])
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
		newname = remove_pattern(p.norm)
		if (p.istop and MOVE_TOPLEVEL_UNUSED_IMG) or MOVE_ALL_UNUSED_IMG:
			# this deserves to be moved to 'unused' folder!
			newname = os.path.join(FOLDER_UNUSED, os.path.basename(newname))
		
		# ensure the extension is lowercase, for cleanliness
		dot = newname.rfind(".")
		newname = newname[:dot] + newname[dot:].lower()
		if CONVERT_SPA_SPH_TO_BMP and newname.endswith((".spa",".sph")):
			newname = newname[:-4] + ".bmp"
		# if the name I build is not the name it already has, queue it for actual rename
		if newname != p.norm:
			# resolve potential collisions by adding numbers suffix to file names
			# first, check against whats on disk. need to make path absolute so get_unused_file_name can check the disk.
			newname = core.get_unused_file_name(os.path.join(startpath, newname))
			# make the path no longer absolute: undo adding "startpath" above
			newname = os.path.relpath(newname, startpath)
			# second, check against other proposed rename targets
			newname = core.get_unused_file_name(newname, all_new_names)
			# now dest path is guaranteed unique against other existing files & other proposed name changes
			all_new_names.add(newname.lower())
			p.mapto = newname
	
	# used files get sorted into tex/toon/sph/multi (unless tex and already in a folder that says clothes, etc)
	# all SPH/SPA get renamed to BMP, used or unused
	for p in used:
		newname = remove_pattern(p.norm)
		usage_list = list(p.usage)
		if len(p.usage) != 1:
			# this is a rare multiple-use file
			newname = os.path.join(FOLDER_MULTI, os.path.basename(newname))
		elif usage_list[0] == FOLDER_SPH:
			# this is an sph, duh
			if not match_in_top_folder(p.norm_lower, KEEP_FOLDERS_SPH):
				# if its name isn't already good, then move it to my new location
				newname = os.path.join(FOLDER_SPH, os.path.basename(newname))
		elif usage_list[0] == FOLDER_TOON:
			# this is a toon, duh
			if not match_in_top_folder(p.norm_lower, KEEP_FOLDERS_TOON):
				# if its name isn't already good, then move it to my new location
				newname = os.path.join(FOLDER_TOON, os.path.basename(newname))
		elif usage_list[0] == FOLDER_TEX:
			# if a tex AND already in a folder like body, clothes, wear, tex, etc then keep that folder
			if not match_in_top_folder(p.norm_lower, KEEP_FOLDERS_TEX):
				# if its name isn't already good, then move it to my new location
				newname = os.path.join(FOLDER_TEX, os.path.basename(newname))
		
		# ensure the extension is lowercase, for cleanliness
		dot = newname.rfind(".")
		newname = newname[:dot] + newname[dot:].lower()
		if CONVERT_SPA_SPH_TO_BMP and newname.lower().endswith((".spa", ".sph")):
			newname = newname[:-4] + ".bmp"
		# if the name I build is not the name it already has, queue it for actual rename
		if newname != p.norm:
			# resolve potential collisions by adding numbers suffix to file names
			# first, check against whats on disk. need to make path absolute so get_unused_file_name can check the disk.
			newname = core.get_unused_file_name(os.path.join(startpath, newname))
			# make the path no longer absolute: undo adding "startpath" above
			newname = os.path.relpath(newname, startpath)
			# second, check against other proposed rename targets
			newname = core.get_unused_file_name(newname, all_new_names)
			# now dest path is guaranteed unique against other existing files & other proposed name changes
			all_new_names.add(newname.lower())
			p.mapto = newname
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# NOW PRINT MY PROPOSED RENAMINGS and other findings
	
	# isolate the ones with proposed renaming
	used_rename = [u for u in used if u.mapto != ""]
	notused_img_rename = [u for u in notused_img if u.mapto != ""]
	notused_img_norename = [u for u in notused_img if u.mapto == ""]
	
	# bonus goal: if ALL files under a folder are unused, replace its name with a star
	relative_allfilesthatexist = [os.path.relpath(f, startpath) for f in absolue_files_that_exist]
	# first build dict of each dirs to each file any depth below that dir
	all_dirnames = {}
	for f in relative_allfilesthatexist:
		d = os.path.dirname(f)
		while d != "":
			try:				all_dirnames[d].append(f)
			except KeyError:	all_dirnames[d] = [f]
			d = os.path.dirname(d)
	unused_dirnames = []
	all_notused_searchable = [x.orig for x in notused_img_norename] + [x.orig for x in notused_notimg]
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
	
	if notexist:
		core.MY_PRINT_FUNC("="*60)
		core.MY_PRINT_FUNC("Found %d references to images that don't exist (no proposed changes)" % len(notexist))
		for p in sorted(notexist, key=lambda y: sortbydirdepth(y.orig)):
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
				if p.orig.startswith(d):
					# add this dir, not this file, to the print set
					printme.add(os.path.join(d, "***"))
					t = True
			if not t:
				# if not encompassed by an unused dir, add the filename
				printme.add(p.orig)
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
				if p.orig.startswith(d):
					# add this dir, not this file, to the print set
					printme.add(os.path.join(d, "***"))
					t = True
			if not t:
				# if not encompassed by an unused dir, add the filename
				printme.add(p.orig)
		# convert set back to sorted list
		printme = sorted(list(printme), key=sortbydirdepth)
		for s in printme:
			core.MY_PRINT_FUNC("   " + s)
	# print with all "from" file names left-justified so all the arrows are nicely lined up (unless they use jp characters)
	longest_name_len = 0
	for p in used_rename:
		longest_name_len = max(longest_name_len, len(p.orig))
	for p in notused_img_rename:
		longest_name_len = max(longest_name_len, len(p.orig))
	if used_rename:
		core.MY_PRINT_FUNC("="*60)
		core.MY_PRINT_FUNC("Found %d used files to be moved/renamed:" % len(used_rename))
		for p in sorted(used_rename, key=lambda y: sortbydirdepth(y.orig)):
			# print 'from' with the case/separator it uses in the PMX
			core.MY_PRINT_FUNC("   {0:<{size}} --> {1:s}".format(p.orig, p.mapto, size=longest_name_len))
	if notused_img_rename:
		core.MY_PRINT_FUNC("="*60)
		core.MY_PRINT_FUNC("Found %d not-used images to be moved/renamed:" % len(notused_img_rename))
		for p in sorted(notused_img_rename, key=lambda y: sortbydirdepth(y.orig)):
			core.MY_PRINT_FUNC("   {0:<{size}} --> {1:s}".format(p.orig, p.mapto, size=longest_name_len))
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
		# need to add .zip for checking against already-exising files and for printing
		zipname = startpath + BACKUP_SUFFIX + ".zip"
		zipname = core.get_unused_file_name(zipname)
		core.MY_PRINT_FUNC("...making backup archive:")
		core.MY_PRINT_FUNC(zipname)
		try:
			root_dir = os.path.dirname(startpath)
			base_dir = os.path.basename(startpath)
			# need to remove .zip suffix because zipper forcefully adds .zip whether its already on the name or not
			shutil.make_archive(zipname[:-4], 'zip', root_dir, base_dir)
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			info = ["ERROR3! Unable to create zipfile for backup.",
					"Do you want to continue without a zipfile backup?",
					"1 = Yes, 2 = No (abort)"]
			r = core.MY_SIMPLECHOICE_FUNC((1, 2), info)
			if r == 2:
				core.MY_PRINT_FUNC("Aborting: no files were changed")
				return None
	
	core.MY_PRINT_FUNC("...renaming files on disk...")
	# second, notused_img_rename on disk: norm -> mapto
	for i,p in enumerate(notused_img_rename):
		try:
			# os.renames creates all necessary intermediate folders needed for the destination
			# it also deletes the source folders if they become empty after the rename operation
			os.renames(os.path.join(startpath, p.norm), os.path.join(startpath, p.mapto))
		except OSError as e:
			# if this fails for some reason, i may have moved some number of the files...
			# ending the operation halfway through is unacceptable! attempt to continue
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("ERROR1!: unable to rename file '%s' --> '%s', attempting to continue with other file rename operations"
				  % (p.norm, p.mapto))
	
	# third, used_rename on disk: norm -> mapto
	for i,p in enumerate(used_rename):
		try:
			os.renames(os.path.join(startpath, p.norm), os.path.join(startpath, p.mapto))
		except OSError as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("ERROR2!: unable to rename file '%s' --> '%s', attempting to continue with other file rename operations"
				  % (p.norm, p.mapto))
			# change this to empty to signify that it didn't actually get moved, check this before changing PMX paths
			p.mapto = ""
			
	# fourth, used_rename in PMX file(s)
	for p in used_rename:
		if p.mapto == "":
			continue  # this means that i tried to rename on disk but failed, so don't change this in the PMX either
		for this_pmx_name, this_pmx_obj in all_pmx_obj.items():
			try:
				# get the index within this PMX object that corresponds to this rename-object
				index = p.index_per_file[this_pmx_name]
			except KeyError:
				continue  # if the key does not exist, then this rename-object doesn't apply to this pmx
			# acutally write the new name into the correct location within this pmx obj
			this_pmx_obj[3][index] = p.mapto
	
	core.MY_PRINT_FUNC("...done renaming!")
	
	# write out
	for this_pmx_name, this_pmx_obj in all_pmx_obj.items():
		# NOTE: this is OVERWRITING THE PREVIOUS PMX FILE, NOT CREATING A NEW ONE
		# because I make a zipfile backup I don't need to feel worried about preserving the old version
		output_filename_pmx = this_pmx_name
		# output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
		pmxlib.write_pmx(output_filename_pmx, this_pmx_obj, moreinfo=moreinfo)
	
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 06/08/2020 - v4.07")
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
