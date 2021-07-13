from mmd_scripting.core import nuthouse01_core as core
from mmd_scripting.core import nuthouse01_pmx_parser as pmxlib
from mmd_scripting.core import nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.overall_cleanup import alphamorph_correct
from mmd_scripting.overall_cleanup import bonedeform_fix
from mmd_scripting.overall_cleanup import dispframe_fix
from mmd_scripting.overall_cleanup import morph_winnow
from mmd_scripting.overall_cleanup import prune_invalid_faces
from mmd_scripting.overall_cleanup import prune_unused_bones
from mmd_scripting.overall_cleanup import prune_unused_vertices
from mmd_scripting.overall_cleanup import translate_to_english
from mmd_scripting.overall_cleanup import uniquify_names
from mmd_scripting.overall_cleanup import weight_cleanup

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.00 - 6/10/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


# what is the max # of items to show in the "warnings" section before concatenating?
MAX_WARNING_LIST = 15



def find_crashing_joints(pmx: pmxstruct.Pmx) -> list:
	# check for invalid joints that would crash MMD, this is such a small operation that it shouldn't get its own file
	# return a list of the joints that are bad
	retme = []
	for d,joint in enumerate(pmx.joints):
		if joint.rb1_idx == -1 or joint.rb2_idx == -1:
			retme.append(d)
	return retme

def find_boneless_bonebodies(pmx: pmxstruct.Pmx) -> list:
	# check for rigidbodies that aren't attached to any bones, this usually doesn't cause crashes but is definitely a mistake
	retme = []
	for d,body in enumerate(pmx.rigidbodies):
		# if this is a bone body
		if body.phys_mode == pmxstruct.RigidBodyPhysMode.BONE:
			# if there is no bone associated with it
			if body.bone_idx == -1:
				retme.append(d)
	return retme

def find_toolong_bonemorph(pmx: pmxstruct.Pmx) -> (list,list):
	# check for morphs with JP names that are too long and will not be successfully saved/loaded with VMD files
	# for each morph, convert from string to bytes encoding to determine its length
	core.set_encoding("shift_jis")
	toolong_list_bone = []
	for d,b in enumerate(pmx.bones):
		try:
			bb = core.encode_string_with_escape(b.name_jp)
			if len(bb) > 15:
				toolong_list_bone.append("%d[%d]" % (d, len(bb)))
		except UnicodeEncodeError:
			# if shift-jis cannot the chars in this name, then report that in find_shiftjis_unsupported_names()
			pass
	toolong_list_morph = []
	for d,m in enumerate(pmx.morphs):
		try:
			mb = core.encode_string_with_escape(m.name_jp)
			if len(mb) > 15:
				toolong_list_morph.append("%d[%d]" % (d, len(mb)))
		except UnicodeEncodeError:
			# if shift-jis cannot the chars in this name, then report that in find_shiftjis_unsupported_names()
			pass
	return toolong_list_bone, toolong_list_morph

def find_shiftjis_unsupported_names(pmx: pmxstruct.Pmx, filepath: str) -> int:
	# checks that bone/morph names can be stored in shift_jis for VMD usage
	# also check the model name and the filepath
	core.set_encoding("shift_jis")
	failct = 0
	print(filepath)
	# first, full absolute file path:
	try:
		_ = core.encode_string_with_escape(filepath)
	except UnicodeEncodeError as e:
		core.MY_PRINT_FUNC("Filepath")
		# note: UnicodeEncodeError.reason has been overwritten with the string I was trying to encode, other fields unchanged
		newerrstr = "%s: '%s' codec cannot encode char '%s' within string '%s'" % (
			e.__class__.__name__, e.encoding, e.reason[e.start:e.end], e.reason)
		core.MY_PRINT_FUNC(newerrstr)
		failct += 1
	# second, JP model name:
	try:
		_ = core.encode_string_with_escape(pmx.header.name_jp)
	except UnicodeEncodeError as e:
		core.MY_PRINT_FUNC("Model Name")
		# note: UnicodeEncodeError.reason has been overwritten with the string I was trying to encode, other fields unchanged
		newerrstr = "%s: '%s' codec cannot encode char '%s' within string '%s'" % (
			e.__class__.__name__, e.encoding, e.reason[e.start:e.end], e.reason)
		core.MY_PRINT_FUNC(newerrstr)
		failct += 1

	# third, bones
	for d,b in enumerate(pmx.bones):
		try:
			_ = core.encode_string_with_escape(b.name_jp)
		except UnicodeEncodeError as e:
			core.MY_PRINT_FUNC("Bone %d" % d)
			# note: UnicodeEncodeError.reason has been overwritten with the string I was trying to encode, other fields unchanged
			newerrstr = "%s: '%s' codec cannot encode char '%s' within string '%s'" % (
				e.__class__.__name__, e.encoding, e.reason[e.start:e.end], e.reason)
			core.MY_PRINT_FUNC(newerrstr)
			failct += 1
	# fourth, morphs
	for d,m in enumerate(pmx.morphs):
		try:
			_ = core.encode_string_with_escape(m.name_jp)
		except UnicodeEncodeError as e:
			core.MY_PRINT_FUNC("Morph %d" % d)
			# note: UnicodeEncodeError.reason has been overwritten with the string I was trying to encode, other fields unchanged
			newerrstr = "%s: '%s' codec cannot encode char '%s' within string '%s'" % (
				e.__class__.__name__, e.encoding, e.reason[e.start:e.end], e.reason)
			core.MY_PRINT_FUNC(newerrstr)
			failct += 1
	return failct

def find_shadowy_materials(pmx: pmxstruct.Pmx) -> list:
	# identify materials that start transparent but still have edging
	retme = []
	for d,mat in enumerate(pmx.materials):
		# if opacity is zero AND edge is enabled AND edge has nonzero opacity AND edge has nonzero size
		if mat.alpha == 0 \
				and pmxstruct.MaterialFlags.USE_EDGING in mat.matflags \
				and mat.edgealpha != 0 \
				and mat.edgesize != 0:
			retme.append(d)
	return retme

def find_jointless_physbodies(pmx: pmxstruct.Pmx)-> list:
	# check for rigidbodies with physics enabled that are NOT the dependent-body of any joint
	# these will just wastefully roll around on the floor draining processing power
	
	# NEW IDEA: complete overkill but whatever whos gonna stop me
	# do a recursive space-filling algorithm starting from each bone body walking along joints
	# then I can find each body that is bone or linked to bone
	# which lets me determine which ones are NOT linked!
	
	def recursively_walk_along_joints(target: int, known_anchors: set):
		if target in known_anchors or target == -1:
			# stop condition: if this RB idx is already known to be anchored, i have already ran recursion from this node. don't do it again.
			# also abort if the target is -1 which means invalid RB
			return
		# if not already in the set, but recursion is being called on this, then this bone is an "anchor" and should be added.
		known_anchors.add(target)
		# now, get all joints which include this RB
		linked_joints = [j for j in pmx.joints if (j.rb1_idx == target) or (j.rb2_idx == target)]
		for joint in linked_joints:
			# walk to every body this joint is connected to
			if joint.rb1_idx != target: recursively_walk_along_joints(joint.rb1_idx, known_anchors)
			if joint.rb2_idx != target: recursively_walk_along_joints(joint.rb2_idx, known_anchors)
		return
	
	bonebodies = [d for d,body in enumerate(pmx.rigidbodies) if body.phys_mode == pmxstruct.RigidBodyPhysMode.BONE]
	anchored_bodies = set()
	for bod in bonebodies:
		recursively_walk_along_joints(bod, anchored_bodies)
	# now, see which body indices are not in the anchored set!
	retme = [i for i in range(len(pmx.rigidbodies)) if i not in anchored_bodies]
	return retme
	


########################################################################################################################

myhelptext = '''=================================================
model_overall_cleanup:
This file will run through a series of first-pass cleanup operations to detect/fix obvious issues in a model.
This includes: translating missing english names, correcting alphamorphs, normalizing vertex weights, pruning invalid faces & orphan vertices, removing bones that serve no purpose, pruning imperceptible vertex morphs, fixing bone deformation order, and cleaning up display frames.
This also scans for several issues that I can detect but not fix, such as improper joints that will crash MMD, and alerts you if it finds them.
These operations will reduce file size (sometimes 30-50%!) and improve overall model health & usability.
However, these are only first-pass fixes. The model will definitely require more time and effort to search for and fix all potential issues.

Outputs: PMX file "[model]_better.pmx"
'''

allhelp = [
	myhelptext,
	"="*20,
	"="*20,
	prune_invalid_faces.helptext,
	prune_unused_vertices.helptext,
	prune_unused_bones.helptext,
	bonedeform_fix.helptext,
	weight_cleanup.helptext,
	morph_winnow.helptext,
	alphamorph_correct.helptext,
	dispframe_fix.helptext,
	translate_to_english.helptext,
	uniquify_names.helptext
]

helptext = '\n'.join(allhelp)


def main(moreinfo=False):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX model file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	#### how should these operations be ordered?
	# faces before verts, because faces define what verts are used
	# verts before weights, so i operate on fewer vertices & run faster
	# weights before bones, because weights determine what bones are used
	# verts before morph winnow, so i operate on fewer vertices & run faster
	# translate after bones/disp groups/morph winnow because they reduce the # of things to translate
	# uniquify after translate, because translate can map multiple different JP to same EN names
	# alphamorphs after translate, so it uses post-translate names for printing
	# deform order after translate, so it uses post-translate names for printing
	
	# if ANY stage returns True then it has made changes
	# final file-write is skipped only if NO stage has made changes
	is_changed = False
	core.MY_PRINT_FUNC("\n>>>> Deleting invalid & duplicate faces <<<<")
	pmx, is_changed_t = prune_invalid_faces.prune_invalid_faces(pmx, moreinfo)
	is_changed |= is_changed_t	# or-equals: if any component returns true, then ultimately this func returns true
	core.MY_PRINT_FUNC("\n>>>> Deleting orphaned/unused vertices <<<<")
	pmx, is_changed_t = prune_unused_vertices.prune_unused_vertices(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC("\n>>>> Deleting unused bones <<<<")
	pmx, is_changed_t = prune_unused_bones.prune_unused_bones(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC("\n>>>> Normalizing vertex weights & normals <<<<")
	pmx, is_changed_t = weight_cleanup.weight_cleanup(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC("\n>>>> Pruning imperceptible vertex morphs <<<<")
	pmx, is_changed_t = morph_winnow.morph_winnow(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC("\n>>>> Fixing display groups: duplicates, empty groups, missing items <<<<")
	pmx, is_changed_t = dispframe_fix.dispframe_fix(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC("\n>>>> Adding missing English names <<<<")
	pmx, is_changed_t = translate_to_english.translate_to_english(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC("\n>>>> Ensuring all names in the model are unique <<<<")
	pmx, is_changed_t = uniquify_names.uniquify_names(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC("\n>>>> Fixing bone deform order <<<<")
	pmx, is_changed_t = bonedeform_fix.bonedeform_fix(pmx, moreinfo)
	is_changed |= is_changed_t
	core.MY_PRINT_FUNC("\n>>>> Standardizing alphamorphs and accounting for edging <<<<")
	pmx, is_changed_t = alphamorph_correct.alphamorph_correct(pmx, moreinfo)
	is_changed |= is_changed_t

	core.MY_PRINT_FUNC("")
	core.MY_PRINT_FUNC("++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
	core.MY_PRINT_FUNC("++++      Scanning for other potential issues      ++++")
	core.MY_PRINT_FUNC("")
	
	num_badnames = find_shiftjis_unsupported_names(pmx, input_filename_pmx)
	if num_badnames:
		core.MY_PRINT_FUNC("WARNING: found %d JP names that cannot be encoded with SHIFT-JIS, please replace the bad characters in the strings printed above!" % num_badnames)
		core.MY_PRINT_FUNC("If the filepath contains bad characters, then MMD project files (.pmm .emm) will not properly store/load model data between sessions.")
		core.MY_PRINT_FUNC("If the modelname/bones/morphs contain bad characters, then they will work just fine in MMD but will not properly save/load in VMD motion files.")
	
	longbone, longmorph = find_toolong_bonemorph(pmx)
	# also checks that bone/morph names can be stored in shift_jis for VMD usage
	if longmorph or longbone:
		core.MY_PRINT_FUNC("")
		core.MY_PRINT_FUNC("Minor warning: this model contains bones/morphs with JP names that are too long (>15 bytes).")
		core.MY_PRINT_FUNC("These will work just fine in MMD but will not properly save/load in VMD motion files.")
		if longbone:
			ss = "[" + ", ".join(longbone[0:MAX_WARNING_LIST]) + "]"
			if len(longbone) > MAX_WARNING_LIST:
				ss = ss[0:-1] + ", ...]"
			core.MY_PRINT_FUNC("These %d bones are too long (index[length]): %s" % (len(longbone), ss))
		if longmorph:
			ss = "[" + ", ".join(longmorph[0:MAX_WARNING_LIST]) + "]"
			if len(longmorph) > MAX_WARNING_LIST:
				ss = ss[0:-1] + ", ...]"
			core.MY_PRINT_FUNC("These %d morphs are too long (index[length]): %s" % (len(longmorph), ss))
	
	shadowy_mats = find_shadowy_materials(pmx)
	if shadowy_mats:
		core.MY_PRINT_FUNC("")
		core.MY_PRINT_FUNC("Minor warning: this model contains transparent materials with visible edging.")
		core.MY_PRINT_FUNC("Edging is visible even if the material is transparent, so this will look like an ugly silhouette.")
		core.MY_PRINT_FUNC("Either disable edging in MMD when using this model, or reduce the edge parameters to 0 and re-add them in the morph that restores its opacity.")
		ss = str(shadowy_mats[0:MAX_WARNING_LIST])
		if len(shadowy_mats) > MAX_WARNING_LIST:
			ss = ss[0:-1] + ", ...]"
		core.MY_PRINT_FUNC("These %d materials need edging disabled (index): %s" % (len(shadowy_mats), ss))
	
	boneless_bodies = find_boneless_bonebodies(pmx)
	if boneless_bodies:
		core.MY_PRINT_FUNC("")
		core.MY_PRINT_FUNC("WARNING: this model has bone-type rigidbodies that aren't anchored to any bones.")
		core.MY_PRINT_FUNC("This won't crash MMD but it is probably a mistake that needs corrected.")
		ss = str(boneless_bodies[0:MAX_WARNING_LIST])
		if len(boneless_bodies) > MAX_WARNING_LIST:
			ss = ss[0:-1] + ", ...]"
		core.MY_PRINT_FUNC("These %d bodies are boneless (index): %s" % (len(boneless_bodies), ss))
		
	jointless_bodies = find_jointless_physbodies(pmx)
	if jointless_bodies:
		core.MY_PRINT_FUNC("")
		core.MY_PRINT_FUNC("WARNING: this model has physics-type rigidbodies that aren't constrained by joints.")
		core.MY_PRINT_FUNC("These will just roll around on the floor wasting processing power in MMD.")
		ss = str(jointless_bodies[0:MAX_WARNING_LIST])
		if len(jointless_bodies) > MAX_WARNING_LIST:
			ss = ss[0:-1] + ", ...]"
		core.MY_PRINT_FUNC("These %d bodies are jointless (index): %s" % (len(jointless_bodies), ss))
		
	crashing_joints = find_crashing_joints(pmx)
	if crashing_joints:
		# make the biggest fucking alert i can cuz this is a critical issue
		core.MY_PRINT_FUNC("")
		core.MY_PRINT_FUNC("! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ")
		core.MY_PRINT_FUNC("CRITICAL WARNING: this model contains invalid joints which WILL cause MMD to crash!")
		core.MY_PRINT_FUNC("These must be manually deleted or repaired using PMXE.")
		core.MY_PRINT_FUNC("These %d joints are invalid (index): %s" % (len(crashing_joints), crashing_joints))
	
	core.MY_PRINT_FUNC("")
	core.MY_PRINT_FUNC("++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
	if not is_changed:
		core.MY_PRINT_FUNC("++++             No writeback required              ++++")
		core.MY_PRINT_FUNC("Done!")
		return
	
	core.MY_PRINT_FUNC("++++ Done with cleanup, saving improvements to file ++++")
	
	# write out
	# output_filename_pmx = "%s_better.pmx" % core.get_clean_basename(input_filename_pmx)
	output_filename_pmx = input_filename_pmx[0:-4] + "_better.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	print(_SCRIPT_VERSION)
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
