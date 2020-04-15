# Nuthouse01 - 04/15/2020 - v4.02
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
	from . import _alphamorph_correct
	from . import _morph_winnow
	from . import _prune_invalid_faces
	from . import _prune_unused_vertices
	from . import _prune_unused_bones
	from . import _translate_to_english
	from . import _weight_cleanup
	from . import _uniquify_names
	from . import _dispframe_fix
except ImportError as eee:
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
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = pmxlib = None
		_alphamorph_correct = _morph_winnow = _prune_unused_vertices = _prune_invalid_faces = _translate_to_english = None
		_weight_cleanup = _uniquify_names = _prune_unused_bones = _dispframe_fix = None


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

def find_toolong_morphs(pmx):
	# check for morphs with JP names that are too long and will not be successfully saved/loaded with VMD files
	# for each morph, convert from string to bytes encoding to determine its length
	core.set_encoding("shift_jis")
	bones_bytes = [core.encode_string_with_escape(m[0]) for m in pmx[5]]
	toolong_list_bone = ["%d/%d" % (d, len(mb)) for d,mb in enumerate(bones_bytes) if len(mb) > 15]
	morphs_bytes = [core.encode_string_with_escape(m[0]) for m in pmx[6]]
	toolong_list_morph = ["%d/%d" % (d, len(mb)) for d,mb in enumerate(morphs_bytes) if len(mb) > 15]

	return toolong_list_bone, toolong_list_morph

########################################################################################################################

myhelptext = '''=================================================
pmx_overall_cleanup:
This file will run through a series of first-pass cleanup operations to detect/fix obvious issues in a model.
This includes: translating missing english names, correcting alphamorphs, normalizing vertex weights, pruning invalid faces & orphan vertices, removing bones that serve no purpose, pruning imperceptible vertex morphs, and cleaning up display frames.
This also scans for some issues that I can detect but not fix, such as improper joints that will crash MMD, and alerts you if it finds them.
These operations will reduce file size (sometimes massively!) and improve overall model health & usability.
However, these are only first-pass fixes. The model will definitely require more time and effort to search for and fix all potential issues.

Outputs: PMX file "[model]_better.pmx"
'''

allhelp = [
	myhelptext,
	"="*20,
	"="*20,
	_prune_invalid_faces.helptext,
	_prune_unused_vertices.helptext,
	_prune_unused_bones.helptext,
	_weight_cleanup.helptext,
	_morph_winnow.helptext,
	_alphamorph_correct.helptext,
	_dispframe_fix.helptext,
	_translate_to_english.helptext,
	_uniquify_names.helptext
]

helptext = '\n'.join(allhelp)


def main(moreinfo=False):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX model file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	# verts after faces
	# weights after verts, but before bones
	# bones after verts
	# translate after bones because it reduces the # of things to translate
	# translate after display groups cuz it reduces the # of things to translate
	# translate after morph winnow cuz it can delete morphs
	# uniquify after translate
	
	is_changed = False
	core.MY_PRINT_FUNC("\n>>>> Deleting invalid faces <<<<")
	pmx, is_changed_t = _prune_invalid_faces.prune_invalid_faces(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC("\n>>>> Deleting orphaned/unused vertices <<<<")
	pmx, is_changed_t = _prune_unused_vertices.prune_unused_vertices(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC("\n>>>> Deleting unused bones <<<<")
	pmx, is_changed_t = _prune_unused_bones.prune_unused_bones(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC("\n>>>> Normalizing weights <<<<")
	pmx, is_changed_t = _weight_cleanup.weight_cleanup(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC("\n>>>> Pruning imperceptible vertex morphs <<<<")
	pmx, is_changed_t = _morph_winnow.morph_winnow(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC("\n>>>> Fixing alphamorphs that don't account for edging <<<<")
	pmx, is_changed_t = _alphamorph_correct.alphamorph_correct(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC("\n>>>> Display groups that contain duplicates, empty groups, or missing bones/morphs <<<<")
	pmx, is_changed_t = _dispframe_fix.dispframe_fix(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC("\n>>>> Fixing missing english names <<<<")
	pmx, is_changed_t = _translate_to_english.translate_to_english(pmx, moreinfo)
	is_changed |= is_changed_t	# or-equals: if any component returns true, then ultimately this func returns true
	core.MY_PRINT_FUNC("\n>>>> Ensuring all names in the model are unique <<<<")
	pmx, is_changed_t = _uniquify_names.uniquify_names(pmx, moreinfo)
	is_changed |= is_changed_t
	
	longbone, longmorph = find_toolong_morphs(pmx)
	if longmorph or longbone:
		core.MY_PRINT_FUNC("")
		core.MY_PRINT_FUNC("Minor warning: this model contains bones/morphs with JP names that are too long (>15 bytes)")
		core.MY_PRINT_FUNC("These will work just fine in MMD but will not properly save/load in VMD motion files")
		if longbone:
			longbone_str = "[" + ", ".join(longbone[0:20]) + "]"
			if len(longbone) > 20:
				longbone_str = longbone_str[0:-1] + ", ...]"
			core.MY_PRINT_FUNC("These %d bones are too long (index/length): %s" % (len(longbone), longbone_str))
		if longmorph:
			longmorph_str = "[" + ", ".join(longmorph[0:20]) + "]"
			if len(longmorph) > 20:
				longmorph_str = longmorph_str[0:-1] + ", ...]"
			core.MY_PRINT_FUNC("These %d morphs are too long (index/length): %s" % (len(longmorph), longmorph_str))

	bad_bodies = find_unattached_rigidbodies(pmx)
	if bad_bodies:
		core.MY_PRINT_FUNC("")
		core.MY_PRINT_FUNC("Minor warning: this model contains rigidbodies that aren't anchored to any bones")
		core.MY_PRINT_FUNC("This won't crash MMD but it is probably a mistake that needs corrected")
		bad_body_str = str(bad_bodies[0:20])
		if len(bad_bodies) > 20:
			bad_body_str = bad_body_str[0:-1] + ", ...]"
		core.MY_PRINT_FUNC("These %d bodies are unanchored (index): %s" % (len(bad_bodies), bad_body_str))
	
	crashing_joints = find_crashing_joints(pmx)
	if crashing_joints:
		# make the biggest fucking alert i can cuz this is a critical issue
		core.MY_PRINT_FUNC("")
		core.MY_PRINT_FUNC("! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ")
		core.MY_PRINT_FUNC("CRITICAL WARNING: this model contains invalid joints which WILL cause MMD to crash!")
		core.MY_PRINT_FUNC("These must be manually deleted or repaired using PMXE")
		core.MY_PRINT_FUNC("These %d joints are invalid (index): %s" % (len(crashing_joints), crashing_joints))
	
	core.MY_PRINT_FUNC("\n>>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<")
	if not is_changed:
		core.MY_PRINT_FUNC(">>>> No writeback required <<<<")
		return
	
	core.MY_PRINT_FUNC(">>>> Done with cleanup, saving improvements to file <<<<")
	
	# write out
	# output_filename_pmx = "%s_better.pmx" % core.get_clean_basename(input_filename_pmx)
	output_filename_pmx = input_filename_pmx[0:-4] + "_better.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 04/15/2020 - v4.02")
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
			core.MY_PRINT_FUNC(ee.__class__.__name__, ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
