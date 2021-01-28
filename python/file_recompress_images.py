# Nuthouse01 - 1/24/2021 - v5.06
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# first, system imports
import os

Image = None
# NOTE: i comment this block before compiling the EXE cuz the Pillow library is gigantic & makes the exe version like 200K
try:
	from PIL import Image
except ImportError:
	Image = None

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	# these imports work if running from GUI
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
	from . import file_sort_textures
except ImportError as eee:
	try:
		# these imports work if running from double-click on THIS script
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
DEBUG = False


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
It creates a zipfile backup of the entire folder, just in case.
This script does NOT ask for permission beforehand, it just creates a backup and does its thing, then afterwards it reports what it did.
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
	input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")
	
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
	
	filerecord_list = file_sort_textures.categorize_files(all_pmx_obj, relevant_exist_files, moreinfo)
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# DETERMINE NEW NAMES FOR FILES
	
	# first, create a backup of the folder
	# save the name, so that i can delete it if i didn't make any changes
	zipfile_name = ""
	if MAKE_BACKUP_ZIPFILE:
		r = file_sort_textures.make_zipfile_backup(startpath, BACKUP_SUFFIX)
		if not r:
			# this happens if the backup failed somehow AND the user decided to quit
			core.MY_PRINT_FUNC("Aborting: no files were changed")
			return None
		zipfile_name = r
		
	# name used for temporary location
	tempfilename = os.path.join(startpath,"temp_image_file_just_delete_me.png")
	
	pil_cannot_inspect = 0
	pil_cannot_inspect_list = []
	pil_imgext_mismatch = 0
	
	num_recompressed = 0
	
	# list of memory saved by recompressing each file. same order/length as "image_filerecords"
	mem_saved = []
	
	# make image persistient, so I know it always exists and I can always call "close" before open
	im = None
	
	# only iterate over images that exist, obviously
	image_filerecords = [f for f in filerecord_list if f.exists]
	# iterate over the images
	for i, p in enumerate(image_filerecords):
		abspath = os.path.join(startpath, p.name)
		orig_size = os.path.getsize(abspath)

		# if not moreinfo, then each line overwrites the previous like a progress printout does
		# if moreinfo, then each line is printed permanently
		core.MY_PRINT_FUNC("...analyzing {:>3}/{:>3}, file='{}', size={}                ".format(
			i+1, len(image_filerecords), p.name, core.prettyprint_file_size(orig_size)), is_progress=(not moreinfo))
		mem_saved.append(0)

		# before opening, try to close it just in case
		if im is not None:
			im.close()
		# open the image & catch all possible errors
		try:
			im = Image.open(abspath)
		except FileNotFoundError as eeee:
			core.MY_PRINT_FUNC("FILESYSTEM MALFUNCTION!!", eeee.__class__.__name__, eeee)
			core.MY_PRINT_FUNC("os.walk created a list of all filenames on disk, but then this filename doesn't exist when i try to open it?")
			im = None
		except OSError as eeee:
			# this has 2 causes, "Unsupported BMP bitfields layout" or "cannot identify image file"
			if DEBUG:
				print("CANNOT INSPECT!1", eeee.__class__.__name__, eeee, p.name)
			im = None
		except NotImplementedError as eeee:
			# this is because there's some DDS format it can't make sense of
			if DEBUG:
				print("CANNOT INSPECT!2", eeee.__class__.__name__, eeee, p.name)
			im = None
		if im is None:
			pil_cannot_inspect += 1
			pil_cannot_inspect_list.append(p.name)
			continue
			
		if im.format not in IMG_TYPE_TO_EXT:
			core.MY_PRINT_FUNC("WARNING: file '%s' has unusual image format '%s', attempting to continue" % (p.name, im.format))
		# now the image is successfully opened!

		newname = p.name
		base, currext = os.path.splitext(newname)

		# 1, depending on image format, attempt to re-save as PNG
		if im.format not in IM_FORMAT_ALWAYS_SKIP:
			# delete temp file if it still exists
			if os.path.exists(tempfilename):
				try:
					os.remove(tempfilename)
				except OSError as e:
					core.MY_PRINT_FUNC(e.__class__.__name__, e)
					core.MY_PRINT_FUNC("ERROR1: failed to delete temp image file '%s' during processing" % tempfilename)
					break
			# save to tempfilename with png format, use optimize=true
			try:
				im.save(tempfilename, format="PNG", optimize=True)
			except OSError as e:
				core.MY_PRINT_FUNC(e.__class__.__name__, e)
				core.MY_PRINT_FUNC("ERROR2: failed to re-compress image '%s', original not modified" % p.name)
				continue
			# measure & compare file size
			new_size = os.path.getsize(tempfilename)
			diff = orig_size - new_size
			
			# if using a 16-bit BMP format, re-save back to bmp with same name
			is_bad_bmp = False
			if im.format == "BMP":
				try:
					# this might fail, images are weird, sometimes they don't have the attributes i expect
					if im.tile[0][3][0] in KNOWN_BAD_FORMATS:
						is_bad_bmp = True
				except Exception as e:
					if DEBUG:
						print(e.__class__.__name__, e, "BMP THING", p.name, im.tile)

			if diff > (REQUIRED_COMPRESSION_AMOUNT_KB * 1024) \
					or is_bad_bmp\
					or im.format in IM_FORMAT_ALWAYS_CONVERT:
				# if it frees up at least XXX kb, i will keep it!
				# also keep it if it is a bmp encoded with 15-bit or 16-bit colors
				# set p.newname = png, and delete original and move tempname to base.png
				try:
					# delete original
					os.remove(os.path.join(startpath, p.name))
				except OSError as e:
					core.MY_PRINT_FUNC(e.__class__.__name__, e)
					core.MY_PRINT_FUNC("ERROR3: failed to delete old image '%s' after recompressing" % p.name)
					continue
				
				newname = base + ".png"
				# resolve potential collisions by adding numbers suffix to file names
				# first need to make path absolute so get_unused_file_name can check the disk.
				newname = os.path.join(startpath, newname)
				# then check uniqueness against files on disk
				newname = core.get_unused_file_name(newname)
				# now dest path is guaranteed unique against other existing files
				# make the path no longer absolute: undo adding "startpath" above
				newname = os.path.relpath(newname, startpath)
				
				try:
					# move new into place
					os.rename(tempfilename, os.path.join(startpath, newname))
				except OSError as e:
					core.MY_PRINT_FUNC(e.__class__.__name__, e)
					core.MY_PRINT_FUNC("ERROR4: after deleting original '%s', failed to move recompressed version into place!" % p.name)
					continue
				num_recompressed += 1
				p.newname = newname
				mem_saved[-1] = diff
				continue # if succesfully re-saved, do not do the extension-checking below
			# if this is not sufficiently compressed, do not use "continue", DO hit the extension-checking below
			
		# 2, if the file extension doesn't match with the image type, then make it match
		# this only happens if the image was not re-saved above
		if im.format in IMG_TYPE_TO_EXT and currext not in IMG_TYPE_TO_EXT[im.format]:
			newname = base + IMG_TYPE_TO_EXT[im.format][0]
			# resolve potential collisions by adding numbers suffix to file names
			# first need to make path absolute so get_unused_file_name can check the disk.
			newname = os.path.join(startpath, newname)
			# then check uniqueness against files on disk
			newname = core.get_unused_file_name(newname)
			# now dest path is guaranteed unique against other existing files
			# make the path no longer absolute: undo adding "startpath" above
			newname = os.path.relpath(newname, startpath)
			
			# do the actual rename here & now
			try:
				# os.renames creates all necessary intermediate folders needed for the destination
				# it also deletes the source folders if they become empty after the rename operation
				os.renames(os.path.join(startpath, p.name), os.path.join(startpath, newname))
			except OSError as e:
				core.MY_PRINT_FUNC(e.__class__.__name__, e)
				core.MY_PRINT_FUNC("ERROR5: unable to rename file '%s' --> '%s', attempting to continue with other file rename operations"
					% (p.name, newname))
				continue
				
			pil_imgext_mismatch += 1
			p.newname = newname
			continue
	
	# these must be the same length after iterating
	assert len(mem_saved) == len(image_filerecords)
	# if the image is still open, close it
	if im is not None:
		im.close()
	
	# delete temp file if it still exists
	if os.path.exists(tempfilename):
		try:
			os.remove(tempfilename)
		except OSError as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("WARNING: failed to delete temp image file '%s' after processing" % tempfilename)
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================

	# are there any with proposed renaming?
	if not any(u.newname is not None for u in image_filerecords):
		core.MY_PRINT_FUNC("No proposed file changes")
		# if nothing was changed, delete the backup zip!
		core.MY_PRINT_FUNC("Deleting backup archive")
		if os.path.exists(zipfile_name):
			try:
				os.remove(zipfile_name)
			except OSError as e:
				core.MY_PRINT_FUNC(e.__class__.__name__, e)
				core.MY_PRINT_FUNC("WARNING: failed to delete pointless zip file '%s'" % zipfile_name)
		core.MY_PRINT_FUNC("Aborting: no files were changed")
		return None

	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================

	# finally, do the actual renaming:
	
	# do all renaming in PMXes
	file_sort_textures.apply_file_renaming(all_pmx_obj, image_filerecords, startpath, skipdiskrename=True)
	
	# write out
	for this_pmx_name, this_pmx_obj in all_pmx_obj.items():
		# NOTE: this is OVERWRITING THE PREVIOUS PMX FILE, NOT CREATING A NEW ONE
		# because I make a zipfile backup I don't need to feel worried about preserving the old version
		output_filename_pmx = os.path.join(startpath, this_pmx_name)
		# output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
		pmxlib.write_pmx(output_filename_pmx, this_pmx_obj, moreinfo=moreinfo)
	
	# =========================================================================================================
	# =========================================================================================================
	# =========================================================================================================
	# NOW PRINT MY RENAMINGS and other findings
	
	filerecord_with_savings = zip(image_filerecords, mem_saved)
	changed_files = [u for u in filerecord_with_savings if u[0].newname is not None]

	core.MY_PRINT_FUNC("="*60)
	if pil_cannot_inspect:
		core.MY_PRINT_FUNC("WARNING: failed to inspect %d image files, these must be handled manually" % pil_cannot_inspect)
		core.MY_PRINT_FUNC(pil_cannot_inspect_list)
	if num_recompressed:
		core.MY_PRINT_FUNC("Recompressed %d images! %s of disk space has been freed" % (num_recompressed, core.prettyprint_file_size(sum(mem_saved))))
	if pil_imgext_mismatch:
		core.MY_PRINT_FUNC("Renamed %d images that had incorrect extensions (included below)" % pil_imgext_mismatch)
	oldname_list = [p[0].name for p in changed_files]
	oldname_list_j = core.MY_JUSTIFY_STRINGLIST(oldname_list)
	newname_list = [p[0].newname for p in changed_files]
	newname_list_j = core.MY_JUSTIFY_STRINGLIST(newname_list)
	savings_list = [("" if p[1]==0 else "saved " + core.prettyprint_file_size(p[1])) for p in changed_files]
	zipped = list(zip(oldname_list_j, newname_list_j, savings_list))
	zipped_and_sorted = sorted(zipped, key=lambda y: file_sort_textures.sortbydirdepth(y[0]))
	for o,n,s in zipped_and_sorted:
		# print 'from' with the case/separator it uses in the PMX
		core.MY_PRINT_FUNC("   {:s} --> {:s} | {:s}".format(o, n, s))
		
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 1/24/2021 - v5.06")
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
