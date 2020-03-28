# Nuthouse01 - 03/28/2020 - v3.5
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
	from _alphamorph_correct import alphamorph_correct
	from _morph_winnow import morph_winnow
	from _prune_invalid_faces import prune_invalid_faces
	from _prune_unused_vertices import prune_unused_vertices
	from _translate_to_english import translate_to_english
	from _weight_cleanup import weight_cleanup
	from _uniquify_names import uniquify_names
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	core = pmxlib = None
	alphamorph_correct = morph_winnow = prune_unused_vertices = prune_invalid_faces = translate_to_english = None
	weight_cleanup = uniquify_names = None


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


# TODO: check for (but probably don't try to fix) broken joints that would cause MMD to crash


def begin():
	# print info to explain the purpose of this file
	print("This file will run through a series of first-pass cleanup operations to fix obvious issues in a model.")
	print("This includes: translating missing english names, correcting alphamorphs, normalizing vertex weights, pruning invalid faces & orphan vertices, and pruning imperceptible vertex morphs.")
	print("These operations will reduce file size (sometimes massively!) and improve overall model health & usability.")
	print("However, these are only first-pass fixes. The model will definitely require more time and effort to search for and fix all potential issues.")
	# print info to explain what inputs it needs
	print("Inputs: PMX file 'model.pmx'")
	# print info to explain what outputs it creates
	print("Outputs: PMX file '[model]_better.pmx'")
	print("")
	
	# prompt PMX name
	print("Please enter name of PMX model file:")
	input_filename_pmx = core.prompt_user_filename(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx)
	return pmx, input_filename_pmx

def pmx_overall_cleanup(pmx):
	
	is_changed = False
	print(">>>> Fixing missing english names <<<<")
	pmx, is_changed_t = translate_to_english(pmx)
	is_changed |= is_changed_t	# or-equals: if any component returns true, then ultimately this func returns true
	print(">>>> Ensuring all names in the model are unique <<<<")
	pmx, is_changed_t = uniquify_names(pmx)
	is_changed |= is_changed_t
	print(">>>> Deleting invalid faces <<<<")
	pmx, is_changed_t = prune_invalid_faces(pmx)
	is_changed |= is_changed_t
	print(">>>> Deleting orphaned/unused vertices <<<<")
	pmx, is_changed_t = prune_unused_vertices(pmx)
	is_changed |= is_changed_t
	print(">>>> Normalizing weights <<<<")
	pmx, is_changed_t = weight_cleanup(pmx)
	is_changed |= is_changed_t
	print(">>>> Pruning imperceptible vertex morphs <<<<")
	pmx, is_changed_t = morph_winnow(pmx)
	is_changed |= is_changed_t
	print(">>>> Fixing alphamorphs that don't account for edging <<<<")
	pmx, is_changed_t = alphamorph_correct(pmx)
	is_changed |= is_changed_t
	
	print(">>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<")
	if not is_changed:
		print(">>>> OVERALL RESULT: No changes are required <<<<")
	else:
		print(">>>> Done with overall cleanup procedures <<<<")
	
	return pmx, is_changed

def end(pmx, input_filename_pmx):
	# write out
	# output_filename_pmx = "%s_better.pmx" % core.get_clean_basename(input_filename_pmx)
	output_filename_pmx = input_filename_pmx[0:-4] + "_better.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(pmx, output_filename_pmx)
	
	return None

def main():
	pmx, name = begin()
	pmx, is_changed = pmx_overall_cleanup(pmx)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")

if __name__ == '__main__':
	print("Nuthouse01 - 03/28/2020 - v3.5")
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
