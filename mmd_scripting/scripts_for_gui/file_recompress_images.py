import os
import shutil

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_io as io
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
from mmd_scripting.scripts_for_gui import file_sort_textures

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.03 - 8/9/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

Image = None
# NOTE: i comment this block before compiling the EXE cuz the Pillow library is gigantic & makes the exe version like 200K
try:
	from PIL import Image
except ImportError:
	Image = None

# print extra messages when certain things fail in certain ways
DEBUG = False

TEMPORARY_RECOMPRESS_LOCATION = "../TEMPORARY_RECOMPRESS_LOCATION/"

# this is recommended true, for obvious reasons
MAKE_BACKUP_ZIPFILE = True
# note: zipper automatically appends .zip onto whatever output name i give it, so dont give it a .zip suffix here
BACKUP_SUFFIX = "beforePNG"

IM_FORMAT_ALWAYS_CONVERT = ("DDS", "TIFF", "TGA")
IM_FORMAT_ALWAYS_SKIP = ("JPEG", "GIF")

# these are rare BMP formats that are known to be incompatible with MocuMocuDance
KNOWN_BAD_FORMATS = ("BGR;15", "BGR;16")

# if recompression saves less than XXX KB, then don't save the result
REQUIRED_COMPRESSION_AMOUNT_KB = 100

# how PIL reads things:
# PNG, JPEG, BMP, DDS, TIFF, GIF
IMG_TYPE_TO_EXT = file_sort_textures.IMG_TYPE_TO_EXT
IMG_EXT = file_sort_textures.IMG_EXT

helptext = '''=================================================
file_recompress_images:
This tool will try to re-compress all image files in the file tree.
Generally this means converting BMP/TGA/other images to PNG format, for maximum lossless image compression.
JPEG image compression is more aggressive than PNG, so JPEG images will stay as JPEG. GIFs are weird so they are also not modified.
This requires a PMX file to use as a root so it knows where to start reading files from.
Before actually changing anything, it will list all proposed file renames and ask for final confirmation.
It also creates a zipfile backup of the entire folder, just in case.
Bonus: this can process all "neighbor" pmx files in addition to the target, this highly recommended because neighbors usually reference similar sets of files.

Note: this script requires the Python library 'Pillow' to be installed.

Note: unlike my other scripts, this overwrites the original input PMX file(s) instead of creating a new file with a suffix. This is because I already create a zipfile that contains the original input PMX, so that serves as a good backup.
'''

# dds/tga/tiff will always be converted to png
# jpeg/gif will always be skipped (jpeg is already lossy & therefore compresses better than png, gif is animated & complex)
# bmp will be re-compressed to png if the original bmp is in 15-bit or 16-bit encoding (mocumocudance compatability)
# other image types are re-compressed to png if doing so saves 100kb or more
# also, all images are renamed so that the file extension matches the actual image data format

def main(moreinfo=False):
	# step zero: verify that Pillow exists
	if Image is None:
		core.MY_PRINT_FUNC("ERROR: Python library 'Pillow' not found. This script requires this library to run!")
		core.MY_PRINT_FUNC("This script cannot be ran from the EXE version, the Pillow library is too large to package into the executable.")
		core.MY_PRINT_FUNC("To install Pillow, please use the command 'pip install Pillow' in the Windows command prompt and then run the Python scripts directly.")
		return None
	# print pillow version just cuz
	core.MY_PRINT_FUNC("Using Pillow version '%s'" % Image.__version__)
	
	core.MY_PRINT_FUNC("Please enter name of PMX model file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	
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
	core.MY_PRINT_FUNC("NEIGHBOR PMX FILES:", len(neighbor_pmx))
	
	# filter down to just image files
	relevant_exist_files = [f for f in relative_all_exist_files if f.lower().endswith(IMG_EXT)]
	core.MY_PRINT_FUNC("RELEVANT EXISTING FILES:", len(relevant_exist_files))

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
	
	# note: need to put this tempdire ONE LEVEL UP or else it will be included in the zip! lol
	tempdir = os.path.join(startpath, TEMPORARY_RECOMPRESS_LOCATION)
	tempdir = os.path.normpath(tempdir)
	os.makedirs(tempdir, exist_ok=True)
	
	pil_cannot_inspect_list = []
	pil_imgext_mismatch = 0
	
	num_recompressed = 0
	
	# list of memory saved by recompressing each file. same order/length as "image_filerecords"
	mem_saved = []
	mem_original = []
	
	# only iterate over images that exist, obviously
	image_filerecords = [f for f in filerecord_list if f.exists]
	
	virtual_nameset = set([f.name for f in image_filerecords])
	
	# iterate over the images
	for i, p in enumerate(image_filerecords):
		abspath = os.path.join(startpath, p.name)
		orig_size = os.path.getsize(abspath)
		mem_original.append(orig_size)
		mem_saved.append(0)  # if i succesfully recompress this image, I will overwrite this 0

		# if not moreinfo, then each line overwrites the previous like a progress printout does
		# if moreinfo, then each line is printed permanently
		core.MY_PRINT_FUNC("...analyzing {:>3}/{:>3}, file='{}', size={}                          ".format(
			i+1, len(image_filerecords), p.name, core.prettyprint_file_size(orig_size)), is_progress=(not moreinfo))

		# open the image & catch all possible errors
		try:
			im = Image.open(abspath)
		except FileNotFoundError as eeee:
			core.MY_PRINT_FUNC("FILESYSTEM MALFUNCTION!!", eeee.__class__.__name__, eeee)
			core.MY_PRINT_FUNC("os.walk created a list of all filenames on disk, but then this filename doesn't exist when i try to open it?")
			pil_cannot_inspect_list.append(p.name)
			continue
		except OSError as eeee:
			# this has 2 causes, "Unsupported BMP bitfields layout" or "cannot identify image file"
			if DEBUG:
				print("CANNOT INSPECT!1", eeee.__class__.__name__, eeee, p.name)
			pil_cannot_inspect_list.append(p.name)
			continue
		except NotImplementedError as eeee:
			# this is because there's some DDS format it can't make sense of
			if DEBUG:
				print("CANNOT INSPECT!2", eeee.__class__.__name__, eeee, p.name)
			pil_cannot_inspect_list.append(p.name)
			continue
			
		if im.format not in IMG_TYPE_TO_EXT:
			core.MY_PRINT_FUNC("WARNING: file '%s' has unusual image format '%s', attempting to continue" % (p.name, im.format))
			
		##################################################
		# now the image is successfully opened!

		base, currext = os.path.splitext(p.name)
		newname_as_png = base + ".png"
		if p.name != newname_as_png:
			# if the newname is going to be the same, it came from the disk so it's already guaranteed unique
			# if the newname is going to be different, it might collide with something else getting renamed to png!
			# i might not end up going thru with the rename, but I should get the unique name figured out now.
			# since I am simulating a rename, remove the original from the list.
			virtual_nameset.remove(p.name)
			newname_as_png = core.filepath_get_unused_name(newname_as_png, checkdisk=False, namelist=virtual_nameset)
		newname_as_png_full = os.path.join(tempdir, newname_as_png)

		# 1, depending on image format, attempt to re-save as PNG
		if im.format not in IM_FORMAT_ALWAYS_SKIP:
			try:
				# create all needed subfolders for the destination
				os.makedirs(os.path.dirname(newname_as_png_full), exist_ok=True)
			except OSError as e:
				core.MY_PRINT_FUNC(e.__class__.__name__, e)
				core.MY_PRINT_FUNC("ERROR1: failed to create intermediate folders for '%s'" % newname_as_png_full)
				virtual_nameset.add(p.name)  # aborted the rename, so put the original name back!
				continue
				
			try:
				# save to tempfilename with png format, use optimize=true
				im.save(newname_as_png_full, format="PNG", optimize=True)
			except OSError as e:
				core.MY_PRINT_FUNC(e.__class__.__name__, e)
				core.MY_PRINT_FUNC("ERROR2: failed to re-compress image '%s', original not modified" % p.name)
				virtual_nameset.add(p.name)  # aborted the rename, so put the original name back!
				continue
				
			##################################################################
			# now i have succesfully re-saved the image as a PNG!
			# next question, do I want to keep this result or the original?
			
			# the new version is kept if:
			# 1) the new version is sufficiently smaller,
			# 2) the old version is a filetype I specifically hate (dds, tga, tiff)
			# 3) the old version is a known-bad BMP type,
			
			# measure & compare file size
			new_size = os.path.getsize(newname_as_png_full)
			diff = orig_size - new_size
			
			is_sufficiently_smaller = (diff > (REQUIRED_COMPRESSION_AMOUNT_KB * 1024))
			is_alwaysconvert_format = (im.format in IM_FORMAT_ALWAYS_CONVERT)
			
			# if using a 16-bit BMP format, i want to re-compress it
			is_bad_bmp = False
			if im.format == "BMP":
				try:
					# this might fail, images are weird, sometimes they don't have the attributes i expect
					if im.tile[0][3][0] in KNOWN_BAD_FORMATS:
						is_bad_bmp = True
				except Exception as e:
					if DEBUG:
						print(e.__class__.__name__, e, "BMP CHECK FAILED", p.name, im.tile)

			if is_sufficiently_smaller or is_bad_bmp or is_alwaysconvert_format:
				# if any of these 3 is true, then I am going to keep it!
				num_recompressed += 1
				p.newname = newname_as_png
				virtual_nameset.add(newname_as_png)  # i'm keeping this rename, so add the new name to the set
				mem_saved[-1] = diff  # overwrite the 0 at the end of the list with the correct value
				continue # if succesfully re-saved, do not do the extension-checking below
			# 	# if this is not sufficiently compressed, do not use "continue", DO hit the extension-checking below
			
		# 2, if the file extension doesn't match with the image type, then make it match
		# this only happens if the image was not re-saved above
		if im.format in IMG_TYPE_TO_EXT and currext not in IMG_TYPE_TO_EXT[im.format]:
			newname = base + IMG_TYPE_TO_EXT[im.format][0]
			# resolve potential collisions by adding numbers suffix to file names
			newname = core.filepath_get_unused_name(newname, checkdisk=False, namelist=virtual_nameset)
			
			pil_imgext_mismatch += 1
			p.newname = newname
			virtual_nameset.add(newname)  # i'm keeping this rename, so add the new name to the set
			continue
		# since i didn't commit to any of the rename ideas, put the original name back
		virtual_nameset.add(p.name)
		pass
	
	# these must be the same length after iterating
	assert len(mem_saved) == len(image_filerecords)
	# if the image is still open, close it
	if im is not None:
		im.close()
	
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================

	# are there any with proposed renaming?
	if not any(u.newname is not None for u in image_filerecords):
		core.MY_PRINT_FUNC("No proposed file changes")
		core.MY_PRINT_FUNC("Aborting: no files were changed")
		# also delete the tempspace!
		try:
			shutil.rmtree(tempdir)
		except OSError as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("ERROR3: failed to delete temporary folder '%s'" % tempdir)
		return None

	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================

	# now, display all the proposed changes...
	mem_new = [original - saved for original, saved in zip(mem_original, mem_saved)]
	
	# attach the mem-savings to the name and stuff
	filerecord_with_savings = list(zip(image_filerecords, mem_saved))
	# sort descending by savings, most savings first
	filerecord_with_savings.sort(key=core.get2nd, reverse=True)
	# filter it
	changed_files = [u for u in filerecord_with_savings if u[0].newname is not None]

	core.MY_PRINT_FUNC("="*60)
	if pil_cannot_inspect_list:
		core.MY_PRINT_FUNC("WARNING: failed to inspect %d image files, these must be handled manually" % len(pil_cannot_inspect_list))
		core.MY_PRINT_FUNC(pil_cannot_inspect_list)
	if num_recompressed:
		core.MY_PRINT_FUNC("Recompressed %d images! %s of disk space has been freed" % (num_recompressed, core.prettyprint_file_size(sum(mem_saved))))
		core.MY_PRINT_FUNC("Reduction = {:.1%}... initial size = {:s}, new size = {:s}".format(
			sum(mem_saved)/sum(mem_original),
			core.prettyprint_file_size(sum(mem_original)),
			core.prettyprint_file_size(sum(mem_new)),))
	if pil_imgext_mismatch:
		core.MY_PRINT_FUNC("Renamed %d images that had incorrect extensions (included below)" % pil_imgext_mismatch)
	oldname_list = []
	newname_list = []
	savings_list = []
	for C,saved in changed_files:
		oldname_list.append(C.name)
		if saved == 0:  savings_list.append("")
		elif saved > 0: savings_list.append("reduced " + core.prettyprint_file_size(saved))
		else:           savings_list.append("increased " + core.prettyprint_file_size(abs(saved)))
		# if newname == oldname, then just display "SAME-NAME" instead
		if C.newname == C.name: newname_list.append("SAME-NAME")
		else:                   newname_list.append(C.newname)
	# justify the first 2 columns
	oldname_list_j = core.MY_JUSTIFY_STRINGLIST(oldname_list)
	newname_list_j = core.MY_JUSTIFY_STRINGLIST(newname_list)
	# zip everything for easy iter
	zipped = zip(oldname_list_j, newname_list_j, savings_list)
	for o,n,s in zipped:
		# print 'from' with the case/separator it uses in the PMX
		core.MY_PRINT_FUNC("   {:s} --> {:s} | {:s}".format(o, n, s))
	
	info = ["Do you accept these new names/locations?",
			"1 = Yes, 2 = No (abort)"]
	r = core.MY_SIMPLECHOICE_FUNC((1, 2), info)
	if r == 2:
		core.MY_PRINT_FUNC("Aborting: no files were changed")
		# also delete the tempspace!
		try:
			shutil.rmtree(tempdir)
		except OSError as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("ERROR4: failed to delete temporary folder '%s'" % tempdir)
		return None

	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# NOW do the actual renaming!
	
	# first, create a backup of the folder
	if MAKE_BACKUP_ZIPFILE:
		r = file_sort_textures.make_zipfile_backup(startpath, BACKUP_SUFFIX)
		if not r:
			# this happens if the backup failed somehow AND the user decided to quit
			core.MY_PRINT_FUNC("Aborting: no files were changed")
			# also delete the tempspace!
			try:
				shutil.rmtree(tempdir)
			except OSError as e:
				core.MY_PRINT_FUNC(e.__class__.__name__, e)
				core.MY_PRINT_FUNC("ERROR6: failed to delete temporary folder '%s'" % tempdir)
			return None
		
	# then, replace the original images with the new versions
	core.MY_PRINT_FUNC("...renaming files on disk...")
	for C,saved in changed_files:
		# if this file exists on disk and there is a new name for this file,
		if C.exists and C.newname is not None:
			path_original = os.path.join(startpath, C.name)
			path_newfrom = os.path.join(tempdir, C.newname)
			path_newto = os.path.join(startpath, C.newname)
			
			# 1. delete C.name
			try:
				io.check_and_fix_readonly(path_original)
				os.remove(path_original)
			except OSError as e:
				core.MY_PRINT_FUNC(e.__class__.__name__, e)
				core.MY_PRINT_FUNC("ERROR: failed to delete original image file '%s'" % path_original)
				core.MY_PRINT_FUNC("I will try to continue.")
			
			# 2. move C.newname from tempdir to proper dir
			try:
				# os.renames creates all necessary intermediate folders needed for the destination
				# it also deletes the source folders if they become empty after the rename operation
				os.renames(path_newfrom, path_newto)
			except OSError as e:
				# ending the operation halfway through is unacceptable! attempt to continue
				core.MY_PRINT_FUNC(e.__class__.__name__, e)
				core.MY_PRINT_FUNC("ERROR: failed to move newly-compressed file '%s' to location '%s'" % (path_newfrom, path_newto))
				core.MY_PRINT_FUNC("I will try to continue.")
				# change this to empty to signify that it didn't actually get moved, check this before changing PMX paths
				C.newname = None
	
	# lastly, do all renaming in PMXes, but only if some of the names changed!
	# if i renamed a few .pngs to the same names, no point in re-writing the PMXs
	if any((u.newname != u.name and u.newname is not None)for u in image_filerecords):
		file_sort_textures.apply_file_renaming(all_pmx_obj, image_filerecords, startpath, skipdiskrename=True)
		# write out
		for this_pmx_name, this_pmx_obj in all_pmx_obj.items():
			# NOTE: this is OVERWRITING THE PREVIOUS PMX FILE, NOT CREATING A NEW ONE
			# because I make a zipfile backup I don't need to feel worried about preserving the old version
			output_filename_pmx = os.path.join(startpath, this_pmx_name)
			# output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
			pmxlib.write_pmx(output_filename_pmx, this_pmx_obj, moreinfo=moreinfo)
	else:
		core.MY_PRINT_FUNC("No names were changed, no need to re-write the PMX.")
	
	# also delete the tempspace!
	try:
		shutil.rmtree(tempdir)
	except OSError as e:
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		core.MY_PRINT_FUNC("ERROR5: failed to delete temporary folder '%s'" % tempdir)
	
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
