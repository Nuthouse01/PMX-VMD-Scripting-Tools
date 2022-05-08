import os
import re
import shutil
from typing import List, Dict

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.00 - 6/10/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################



# fun fact: SPH and SPA files are just BMP files with the wrong file extension
# if this is true, all SPH/SPA files will be converted to BMP
# this is so its easier to read/see the sphere map files
# this is recommended true
CONVERT_SPA_SPH_TO_BMP = True


# this is recommended true, for obvious reasons
MAKE_BACKUP_BEFORE_RENAMES = True
# note: zipper automatically appends .zip onto whatever output name i give it, so dont give it a .zip suffix here
BACKUP_SUFFIX = "beforesort"


# these are the names of the folders that the files will be sorted into, these can be changed to whatever you want
# they cannot use the same names as eachother, however, all must be unique
FOLDER_TEX =    "tex"
FOLDER_SPH =    "sph"
FOLDER_TOON =   "toon"
FOLDER_MULTI =  "multi"
FOLDER_UNUSED = "unused"

# how PIL reads things:
# PNG, JPEG, BMP, DDS, TIFF, GIF
IMG_TYPE_TO_EXT = {
	"PNG": (".png",),
	"TGA": (".tga",),
	"JPEG": (".jpg", ".jpeg",),
	"BMP": (".bmp",), #".spa", ".sph",
	"DDS": (".dds",),
	"GIF": (".gif",),
	"TIFF": (".tif", ".tiff",),
	"WEBP": (".webp",),
	"SPH": (".spa", ".sph",), # this isn't a "real" file type so this is just to get these extensions in IMG_EXT
}

# IMG_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".spa", ".sph", ".gif", ".tga", ".dds", ".tif", ".tiff")
IMG_EXT = tuple([item for sublist in IMG_TYPE_TO_EXT.values() for item in sublist])

KEEP_FOLDERS_TEX = ("cloth", "outfit", "uniform", "wear", "body", "tex", "weapon", "acc", "face", "tx")
KEEP_FOLDERS_TOON = ("tn", "toon")
KEEP_FOLDERS_SPH = ("sph", "spa", "sp")
# all files I expect to find alongside a PMX and don't want to touch/move
IGNORE_FILETYPES = (".pmx", ".x", ".txt", ".vmd", ".vpd", ".csv")
# all folders I expect to find alongside a PMX and don't want to touch/move any of their contents
IGNORE_FOLDERS = ("fx", "effect", "readme")

remove_pattern = r" ?\(Instance\)_?(\([-0-9]*\))?"
remove_re = re.compile(remove_pattern)


# a struct to bundle all the relevant info about a file that is on disk or used by PMX
class FileRecord:
	def __init__(self, name, exists):
		# the "current name" name this file uses in the PMX: relative to startpath and separator-normalized 
		# (because these are made after normalize_texture_paths() is called).
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

def walk_filetree_from_root(startpath: str) -> List[str]:
	absolute_all_exist_files = []
	# os.walk: returns (path to the folder i'm in),(list of folders in this folder),(list of files in this folder)
	for where, subfolders, files in os.walk(startpath):
		absolute_all_exist_files += [os.path.join(where, f) for f in files]
	relative_all_exist_files = [os.path.relpath(f, startpath) for f in absolute_all_exist_files]
	return relative_all_exist_files


def match_folder_anylevel(s: str, matchlist: tuple, toponly=False) -> bool:
	# break apart each folder level
	broken = s.split(os.path.sep)
	# discard the file name, guaranteed to exist but 'broken' might be empty after this
	broken.pop(-1)
	# verify it isn't empty
	if broken:
		# check only the top level (alt idea: check all levels?)
		for k in matchlist:
			if toponly:
				# check only the topmost path segment
				if k.lower() == broken[0].lower():
					# if a case-insensitive match is found, return true
					return True
			else:
				# check all levels of path segments
				for b in broken:
					if k.lower() == b.lower():
						# if a case-insensitive match is found, return true
						return True
	return False


def sortbydirdepth(s: str) -> str:
	# how I want things to be sorted:
	# folders are sorted alphabetically at all levels, but files at a level are listed before folders that go deeper
	# also case-insensitive
	# z.
	# a/f.
	# a/bbb/e.
	# a/bbb/f.
	# a/bbb/d/f.
	# a/c/e/g.
	return os.path.join(os.path.dirname(s), chr(1) + os.path.basename(s)).lower()


def remove_pattern(s: str) -> str:
	# remove a specific pattern in filenames that were ported by a specific tool
	# ex: "acs_m_meka_c (Instance)_(-412844).png"
	return remove_re.sub("", s)


def make_zipfile_backup(startpath: str, backup_suffix: str) -> str:
	"""
	Make a .zip backup of the folder 'startpath' and all its contents. Returns True if all goes well, False if it should abort.
	Resulting zip will be adjacent to the folder it is backing up with a slightly different name.
	
	:param startpath: absolute path of the folder you want to zip
	:param backup_suffix: segment inserted between the foldername and .zip extension
	:return: zipfile path if things went well, empty if i should abort
	"""
	# need to add .zip for checking against already-exising files and for printing
	zipname = startpath + "." + backup_suffix + ".zip"
	zipname = core.filepath_get_unused_name(zipname)
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
			return "" # false
		else:
			return "zipfile_missing"
	return zipname


def apply_file_renaming(pmx_dict: Dict[str, pmxstruct.Pmx], filerecord_list: List[FileRecord], startpath: str, skipdiskrename=False):
	"""
	Apply all the renaming operations to files on the disk and in any PMX objects where they are used.
	First, try to rename all files on disk. If any raise exceptions, those files will not be changed in PMXes.
	Then, change the file references in the PMX to match the new locations on disk for all files that succeeded.
	
	:param pmx_dict: dict of PMX objects, key is path relative to startpath, value is actual PMX obj
	:param filerecord_list: list of FileRecord obj, all completely processed & filled out
	:param startpath: absolute path that all filepaths are relative to
	:param skipdiskrename: when true, only modify what PMX is pointing at. assume something else already took care of renaming on disk.
	"""
	if not skipdiskrename:
		# first, rename files on disk:
		core.MY_PRINT_FUNC("...renaming files on disk...")
		for i, p in enumerate(filerecord_list):
			# if this file exists on disk and there is a new name for this file,
			if p.exists and p.newname is not None:
				try:
					# os.renames creates all necessary intermediate folders needed for the destination
					# it also deletes the source folders if they become empty after the rename operation
					os.renames(os.path.join(startpath, p.name), os.path.join(startpath, p.newname))
				except OSError as e:
					# ending the operation halfway through is unacceptable! attempt to continue
					core.MY_PRINT_FUNC(e.__class__.__name__, e)
					core.MY_PRINT_FUNC(
						"ERROR1!: unable to rename file '%s' --> '%s', attempting to continue with other file rename operations"
						% (p.name, p.newname))
					# change this to empty to signify that it didn't actually get moved, check this before changing PMX paths
					p.newname = None
	
	# second, rename entries in PMX file(s)
	for pmxpath, pmx in pmx_dict.items():  					      # for every pmx,
		for p in filerecord_list:                                 # for every file,
			if p.newname is not None and pmxpath in p.used_pmx:   # is that file used in that pmx? if yes,
				find = p.used_pmx[pmxpath]                        # get how it is actually used in the pmx
				replace = p.newname                               # get the name i want it to have
				if find != replace:                               # if they do not match,
					texname_find_and_replace(pmx, find, replace)  # do the find and replace
					p.used_pmx[pmxpath] = replace                 # update the 'how this is used' dict
	core.MY_PRINT_FUNC("...done renaming!")
	return

def texname_find_and_replace(pmx: pmxstruct.Pmx, find:str, replace:str, sanitize=False) -> int:
	"""
	Look thru all filepaths in given pmx, if any EXACTLY match 'find' then replace them with 'replace'.
	If 'find' is one of the builtin toons it WILL match it & replace it everywher in the model.
	:param pmx: pmx obj to update/modify
	:param find: filepath to look for in PmxMaterial.tex_path/sph_path/toon_path
	:param replace: new filepath to replace the old one
	:param sanitize: default false. if true, call strip/normpath/lower on both before comparing equality.
	:return: number of places that were changed
	"""
	if find == replace:
		return 0
	count = 0
	if sanitize:
		find = os.path.normpath(find.strip()).lower()
	filepath_member_names = ["tex_path","sph_path","toon_path"]
	for mat in pmx.materials:
		for member in filepath_member_names:
			curr = getattr(mat, member)
			if sanitize:
				curr = os.path.normpath(curr.strip()).lower()
			if curr == find:
				setattr(mat, member, replace)
				count += 1
	return count

# every possible permutation for referring to a specific real file on disk will be renamed to the exact same string
def normalize_texture_paths(pmx: pmxstruct.Pmx, exist_files: List[str]) -> int:
	"""
	Normalize all filepaths that the PMX uses to reference textures. Strip whitespace and standardize the folder
	separators. If it references a real file on disk, match the case of that real filepath. If not, match the case
	of the first reference to that non-existent file.
	:param pmx: pmx obj to update/modify
	:param exist_files: list of strings which are relative filepaths for files I located on disk
	:return: number of unique textures that were changed
	"""
	# TODO: return number unified? or number changed?
	start_tex_list = pmxlib.build_texture_list(pmx)
	tex_update_map = {}
	for d,starttex in enumerate(start_tex_list):
		tex = starttex
		# first, strip leading/trailing whitespace
		# NOTE: mmd will work just fine if the texture has trailing whitespace, but my system will not!
		tex = tex.strip()
		# standardize the file separators
		tex = os.path.normpath(tex)
		# if it matches an existing file, replace it with that clean existing file path
		# that way it matches the case of the file on disk
		match = False
		for ef in exist_files:
			# Windows doesn't care about case when resolving file paths, so neither do i
			if tex.lower() == ef.lower():
				tex = ef
				match = True
				break
		# if it does not match a file on disk, compare against other tex paths in teh PMX and try to unify with one of them
		if not match:
			# compare against each tex reference that comes before this
			for i in range(d):
				other = start_tex_list[i]
				other_norm = os.path.normpath(other.strip())
				if other_norm.lower() == tex.lower():
					# if both paths are the same after normalize & lower, then its a match!
					# set this one to the strip/normalize version of other
					# print("*", tex, other)
					tex = other_norm
					break
		# if it changed, count it and add an entry in the map
		if starttex != tex:
			tex_update_map[starttex] = tex
	# now i have an entry in the map! so, use this map to find-and-replace
	# this skips over the builtin toons, also, since those aren't returned by pmxlib.build_texture_list()
	# it's safe to do the find-and-replace right now, silently, because none of these changes 
	# are FUNCTIONAL, all the filepaths are still equivalent as far as windows is concerned.
	num_replaced = 0
	for find,replace in tex_update_map.items():
		num_replaced += texname_find_and_replace(pmx, find, replace)
	# for pair in tex_update_map.items():
	# 	print(pair)
	# stats
	num_modified = len(tex_update_map)
	# num_unified = len(tex_update_map) - len(set(tex_update_map.values()))
	return num_modified


def build_filerecord_list(pmx_dict: Dict[str, pmxstruct.Pmx], exist_files: List[str], moreinfo: bool) -> List[FileRecord]:
	"""
	Build the FileRecord list that describes every file on disk + every file referenced in every PMX, as well as
	how and how many times each is used. NOTE: this silently makes minor changes to the PMX objects, such as changing
	the case/separators for each filepath. But these changes should be Windows-equivalent.
	1) Normalize cases & separators within each file, 2) count the times/ways each file is used, 3) unify cases &
	separators across multiple files, 4) return.
	
	:param pmx_dict: dict of PMX objects, key is path relative to startpath, value is actual PMX obj
	:param exist_files: list of strings which are relative filepaths for files I located on disk
	:param moreinfo: bool moreinfo from main layer
	:return: list of FileRecord obj which are completely filled out except for destination names.
	"""
	
	recordlist = []
	num_unify_within_pmx = 0
	merge_across_pmx = 0
	
	for pmxpath, pmx in pmx_dict.items():
		
		###################################################################
		###################################################################
		# 1. normalize the texture paths to match the files on disk and make them """unique""" within this one pmx
		num_unify_within_pmx += normalize_texture_paths(pmx, exist_files)
		
		###################################################################
		###################################################################
		# 2. build the filerecord items for this pmx
		thispmx_recordlist = []
		# create (again) the ordered list of unique texpaths in this pmx
		thispmx_texpaths = pmxlib.build_texture_list(pmx)
		# now that they are unique, for each tex:
		for tex in thispmx_texpaths:
			# create the actual "FileRecord" entry, whether it exists or not doesnt matter yet.
			record = FileRecord(tex, False)
			# THIS is the actual string used in the pmx, and which pmx used it like that
			record.used_pmx[pmxpath] = tex
			# add it to the list
			thispmx_recordlist.append(record)
			
		###################################################################
		###################################################################
		# 3. populate the filerecord items with the number-used and how-used data
		for mat in pmx.materials:
			if mat.tex_path != "":
				try:
					idx = thispmx_texpaths.index(mat.tex_path)
					thispmx_recordlist[idx].numused += 1
					thispmx_recordlist[idx].usage.add(FOLDER_TEX)
				except ValueError:
					pass
			if mat.sph_path != "":
				try:
					idx = thispmx_texpaths.index(mat.sph_path)
					thispmx_recordlist[idx].numused += 1
					thispmx_recordlist[idx].usage.add(FOLDER_SPH)
				except ValueError:
					pass
			if mat.toon_path != "" and mat.toon_path not in pmxlib.BUILTIN_TOON_DICT:
				try:
					idx = thispmx_texpaths.index(mat.toon_path)
					thispmx_recordlist[idx].numused += 1
					thispmx_recordlist[idx].usage.add(FOLDER_TOON)
				except ValueError:
					pass
		# append the this-pmx data onto the all-pmx data
		recordlist.extend(thispmx_recordlist)
	###################################################################
	###################################################################
	# 4. add filerecords for all the files I know exist
	exist_not_used_list = [FileRecord(f, exists=True) for f in exist_files]
	recordlist.extend(exist_not_used_list)
	
	###################################################################
	###################################################################
	# 5. unify FileRecord objects across all PMXes
	# now i have the list of filerecords for all PMXes
	# next search them for duplicates & unify the "used_pmx" member when i do
	for L,Lfile in enumerate(recordlist):
		# apply lower
		Llower = Lfile.name.lower()
		# count backward so i can safely pop by index
		# compare L against everything after it
		for R in reversed(range(L+1, len(recordlist))):
			Rfile = recordlist[R]
			Rlower = Rfile.name.lower()
			# are they referring to the same file?
			if Llower == Rlower:
				# then unify their data (into L) and discard R
				Lfile.used_pmx.update(Rfile.used_pmx)  # this is a dict, and the keys should be unique, so unison them
				Lfile.exists |= Rfile.exists  # exists is true if either is true
				Lfile.usage.update(Rfile.usage)  # this is a set, unison
				Lfile.numused += Rfile.numused  # numused is a number, sum
				recordlist.pop(R)
				
	###################################################################
	###################################################################
	# 6. apply any changes that come from unifying across all PMXes
	# next i need to update the references in each PMX
	for record in recordlist:                                     # for every file,
		for pmxpath, pmx in pmx_dict.items():                     # for every pmx,
			if pmxpath in record.used_pmx:                        # is that file used in that pmx? if yes,
				find = record.used_pmx[pmxpath]                   # get how it is actually used in the pmx
				replace = record.name                             # get the name i want it to have
				if find != replace:                               # if they do not match,
					texname_find_and_replace(pmx, find, replace)  # do the find and replace
					record.used_pmx[pmxpath] = replace            # update the 'how this is used' dict
					merge_across_pmx += 1                         # count it
	# done!

	# stats
	if moreinfo:
		if num_unify_within_pmx: core.MY_PRINT_FUNC("Unified %d tex references within PMXes" % num_unify_within_pmx)
		if merge_across_pmx: core.MY_PRINT_FUNC("Unified %d tex references across PMXes" % merge_across_pmx)
	return recordlist


helptext = '''=================================================
file_sort_textures:
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
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	
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
	
	filerecord_list = build_filerecord_list(all_pmx_obj, relevant_exist_files, moreinfo)
	
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
	
	move_toplevel_unused_img = True
	move_all_unused_img = False
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
		if c == 2:
			move_toplevel_unused_img = True
			move_all_unused_img = False
		elif c == 3:
			move_toplevel_unused_img = True
			move_all_unused_img = True
		else: # c == 1:
			move_toplevel_unused_img = False
			move_all_unused_img = False

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
		if ((os.path.sep not in p.name) and move_toplevel_unused_img) or move_all_unused_img:
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
			# first need to make path absolute so filepath_get_unused_name can check the disk.
			# then check uniqueness against files on disk and files in namelist (files that WILL be on disk)
			newname = core.filepath_get_unused_name(os.path.join(startpath, newname), namelist=all_new_names)
			# now dest path is guaranteed unique against other existing files & other proposed name changes
			all_new_names.add(newname.lower())
			# make the path no longer absolute: undo adding "startpath" above
			newname = os.path.relpath(newname, startpath)
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
	unused_dirnames = sorted(unused_dirnames, key=lambda y: y.count(os.path.sep), reverse=True)
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
		oldname_list = core.MY_JUSTIFY_STRINGLIST([p.name for p in used_rename])
		newname_list = [p.newname for p in used_rename]
		zipped = list(zip(oldname_list, newname_list))
		zipped_and_sorted = sorted(zipped, key=lambda y: sortbydirdepth(y[0]))
		for o,n in zipped_and_sorted:
			# print 'from' with the case/separator it uses in the PMX
			core.MY_PRINT_FUNC("   {:s} --> {:s}".format(o, n))
	if notused_img_rename:
		core.MY_PRINT_FUNC("="*60)
		core.MY_PRINT_FUNC("Found %d not-used images to be moved/renamed:" % len(notused_img_rename))
		oldname_list = core.MY_JUSTIFY_STRINGLIST([p.name for p in notused_img_rename])
		newname_list = [p.newname for p in notused_img_rename]
		zipped = list(zip(oldname_list, newname_list))
		zipped_and_sorted = sorted(zipped, key=lambda y: sortbydirdepth(y[0]))
		for o,n in zipped_and_sorted:
			# print 'from' with the case/separator it uses in the PMX
			core.MY_PRINT_FUNC("   {:s} --> {:s}".format(o, n))
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
		# output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
		pmxlib.write_pmx(output_filename_pmx, this_pmx_obj, moreinfo=moreinfo)
	
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
