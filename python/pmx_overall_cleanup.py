# Nuthouse01 - 03/30/2020 - v3.51
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	import nuthouse01_core as core
	import nuthouse01_pmx_parser as pmxlib
	import _alphamorph_correct
	import _morph_winnow
	import _prune_invalid_faces
	import _prune_unused_vertices
	import _prune_unused_bones
	import _translate_to_english
	import _weight_cleanup
	import _uniquify_names
	import _dispframe_fix
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	core = pmxlib = None
	alphamorph_correct = morph_winnow = prune_unused_vertices = prune_invalid_faces = translate_to_english = None
	weight_cleanup = uniquify_names = prune_unused_bones = dispframe_fix = None


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


# TODO: fix bad normals (hard)


def find_crashing_joints(pmx):
	# check for invalid joints that would crash MMD, this is such a small operation that it shouldn't get its own file
	# return a list of the joints that are bad
	retme = []
	for d,joint in enumerate(pmx[9]):
		if joint[3] == -1 or joint[4] == -1:
			retme.append(d)
	return retme

def find_unattached_rigidbodies(pmx):
	# check for rigidbodies that aren't attached to any bones, this usually doesn't cause crashes but is definitely a mistake
	retme = []
	for d,body in enumerate(pmx[8]):
		if body[2] == -1:
			retme.append(d)
	return retme

########################################################################################################################

helptext = '''pmx_overall_cleanup:
This file will run through a series of first-pass cleanup operations to fix obvious issues in a model.
This includes: translating missing english names, correcting alphamorphs, normalizing vertex weights, pruning invalid faces & orphan vertices, removing bones that serve no purpose, pruning imperceptible vertex morphs, and cleaning up display frames.
This also scans for some issues that I can detect but not fix, such as improper joints that will crash MMD, and alerts you if it finds them.
These operations will reduce file size (sometimes massively!) and improve overall model health & usability.
However, these are only first-pass fixes. The model will definitely require more time and effort to search for and fix all potential issues.
'''

iotext = '''Inputs:  PMX file "[model].pmx"\nOutputs: PMX file "[model]_better.pmx"
'''

def showallhelp():
	# print info to explain the purpose of this file
	core.MY_PRINT_FUNC(helptext)
	core.MY_PRINT_FUNC("====================")
	core.MY_PRINT_FUNC("====================")
	core.MY_PRINT_FUNC("====================")
	_prune_invalid_faces.showhelp()
	core.MY_PRINT_FUNC("====================")
	_prune_unused_vertices.showhelp()
	core.MY_PRINT_FUNC("====================")
	_prune_unused_bones.showhelp()
	core.MY_PRINT_FUNC("====================")
	_weight_cleanup.showhelp()
	core.MY_PRINT_FUNC("====================")
	_morph_winnow.showhelp()
	core.MY_PRINT_FUNC("====================")
	_alphamorph_correct.showhelp()
	core.MY_PRINT_FUNC("====================")
	_dispframe_fix.showhelp()
	core.MY_PRINT_FUNC("====================")
	_translate_to_english.showhelp()
	core.MY_PRINT_FUNC("====================")
	_uniquify_names.showhelp()

def showhelp():
	# print info to explain the purpose of this file
	core.MY_PRINT_FUNC(helptext)
def showprompt():
	# print info to explain what inputs/outputs it needs/creates
	core.MY_PRINT_FUNC(iotext)
	
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX model file:")
	input_filename_pmx = core.prompt_user_filename(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx)
	return pmx, input_filename_pmx

def pmx_overall_cleanup(pmx, moreinfo=False):
	
	# verts after faces
	# weights after verts, but before bones
	# bones after verts
	# translate after bones because it reduces the # of things to translate
	# translate after display groups cuz it reduces the # of things to translate
	# translate after morph winnow cuz it can delete morphs
	# uniquify after translate
	
	is_changed = False
	core.MY_PRINT_FUNC(">>>> Deleting invalid faces <<<<")
	pmx, is_changed_t = _prune_invalid_faces.prune_invalid_faces(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC(">>>> Deleting orphaned/unused vertices <<<<")
	pmx, is_changed_t = _prune_unused_vertices.prune_unused_vertices(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC(">>>> Deleting unused bones <<<<")
	pmx, is_changed_t = _prune_unused_bones.prune_unused_bones(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC(">>>> Normalizing weights <<<<")
	pmx, is_changed_t = _weight_cleanup.weight_cleanup(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC(">>>> Pruning imperceptible vertex morphs <<<<")
	pmx, is_changed_t = _morph_winnow.morph_winnow(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC(">>>> Fixing alphamorphs that don't account for edging <<<<")
	pmx, is_changed_t = _alphamorph_correct.alphamorph_correct(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC(">>>> Display groups that contain duplicates, empty groups, or missing bones/morphs <<<<")
	pmx, is_changed_t = _dispframe_fix.dispframe_fix(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC(">>>> Fixing missing english names <<<<")
	pmx, is_changed_t = _translate_to_english.translate_to_english(pmx, moreinfo)
	is_changed |= is_changed_t	# or-equals: if any component returns true, then ultimately this func returns true
	core.MY_PRINT_FUNC(">>>> Ensuring all names in the model are unique <<<<")
	pmx, is_changed_t = _uniquify_names.uniquify_names(pmx, moreinfo)
	is_changed |= is_changed_t

	bad_bodies = find_unattached_rigidbodies(pmx)
	if bad_bodies:
		core.MY_PRINT_FUNC("")
		core.MY_PRINT_FUNC("Warning: this model contains rigidbodies that aren't anchored to any bones")
		core.MY_PRINT_FUNC("This won't crash MMD but it is definitely a mistake that needs corrected")
		core.MY_PRINT_FUNC("The following bodies are unanchored: ", bad_bodies)
		core.MY_PRINT_FUNC("")
	
	crashing_joints = find_crashing_joints(pmx)
	if crashing_joints:
		# make the biggest fucking alert i can cuz this is a critical issue
		core.MY_PRINT_FUNC("")
		core.MY_PRINT_FUNC("! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ")
		core.MY_PRINT_FUNC("CRITICAL WARNING: this model contains invalid joints which WILL cause MMD to crash!")
		core.MY_PRINT_FUNC("These must be manually deleted or repaired using PMXE")
		core.MY_PRINT_FUNC("The following joints are invalid: ", crashing_joints)
		core.MY_PRINT_FUNC("! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ")
		core.MY_PRINT_FUNC("")

	core.MY_PRINT_FUNC(">>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<")
	if not is_changed:
		core.MY_PRINT_FUNC(">>>> OVERALL RESULT: No changes are required <<<<")
	else:
		core.MY_PRINT_FUNC(">>>> Done with overall cleanup procedures <<<<")
	
	return pmx, is_changed

def end(pmx, input_filename_pmx):
	# write out
	# output_filename_pmx = "%s_better.pmx" % core.get_clean_basename(input_filename_pmx)
	output_filename_pmx = input_filename_pmx[0:-4] + "_better.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx)
	return None

def main():
	showhelp()
	pmx, name = showprompt()
	pmx, is_changed = pmx_overall_cleanup(pmx)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")

if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 03/30/2020 - v3.51")
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
			core.MY_PRINT_FUNC(ee.__class__.__name__, ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
