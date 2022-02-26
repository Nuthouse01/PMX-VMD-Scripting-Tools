from collections import defaultdict
from typing import List

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.core.nuthouse01_pmx_utils import delete_multiple_bones, delme_list_to_rangemap

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.00 - 6/10/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


########################################
# bones are used when:
# 	other !used! bones use as parent, AKA has children
# 	other !used! bones use as link point
# 	other !used! bones use for "append" (partial parent)
# 	is IK
#	is the target of an IK bone
# 	connected to rigid bodies
# 	any vertex has nonzero weight for that bone

# read b.csv, v.csv, rb.csv, print results
#	output list of useless bones





# when this is true, it also prints a list of the number of vertices controlled by each bone. not recommended.
PRINT_VERTICES_CONTROLLED_BY_EACH_BONE = False


# when this is true, list the number and names of each bone i am deleting
PRINT_FOUND_UNUSED_BONES = False


# these are common bones that are unused but should not be deleted
# glasses, dummy_L, dummy_R, view cnt, motherbone, edge adjust
BONES_TO_PROTECT = ["メガネ", "左ダミー", "右ダミー", "左手ダミー", "右手ダミー",
					"操作中心", "全ての親", "エッジ調整", "LS_Center", ]

helptext = '''====================
prune_unused_bones:
This file identifies and deletes all bones in a PMX model that are NOT being used.
A bone is USED if any of the following are true:
    any vertex has nonzero weight with that bone
    rigid bodies use it as an anchor
    other used bones use it as parent, AKA it has children
    other used bones use it as a visual link point
    other used bones use it for 'append' (inherit movement and/or rotation)
    it is an IK bone or a link in the IK chain of an IK bone
A bone is UNUSED if none of these conditions are met.
All unused bones can be safely removed without affecting the current function of the model.
The common bones "dummy_L","dummy_R","glasses" are exceptions: they are semistandard accessory attachment points so they will not be removed even if they otherwise fit the definition of "unused" bones.
'''

iotext = '''Inputs:  PMX file "[model].pmx"\nOutputs: PMX file "[model]_boneprune.pmx"
'''


def showhelp():
	# print info to explain the purpose of this file
	core.MY_PRINT_FUNC(helptext)
def showprompt():
	# print info to explain what inputs/outputs it needs/creates
	core.MY_PRINT_FUNC(iotext)
	
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX model file:")
	input_filename_pmx = core.prompt_user_filename("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=True)
	return pmx, input_filename_pmx
	
	
def identify_unused_bones(pmx: pmxstruct.Pmx, moreinfo: bool) -> List[int]:
	"""
	Process the PMX and return a list of all unused bone indicies in the model.
	1. get bones used by a rigidbody.
	2. get bones that have weight on at least 1 vertex.
	3. mark "exception" bones, done here so parents of exception bones are kept too.
	4. inheritance, aka "bones used by bones", recursively climb the tree & get all bones the "true" used bones depend on.
	5. tails or point-ats.
	6. invert used to get set of unused.

	:param pmx: PMX list-of-lists object
	:param moreinfo: print extra info for debug or whatever
	:return: list of bone indices that are not used
	"""
	# python set: no duplicates! .add(newbone), "in", .discard(delbone)
	# true_used_bones is set of BONE INDEXES
	true_used_bones = set()  # exception bones + rigidbody bones + vertex bones
	vertex_ct = defaultdict(lambda: 0)  # how many vertexes does each bone control? sometimes useful info

	# first: bones used by a rigidbody
	for body in pmx.rigidbodies:
		true_used_bones.add(body.bone_idx)

	# second: bones used by a vertex i.e. has nonzero weight
	# any vertex that has nonzero weight for that bone
	for vert in pmx.verts:
		for boneidx, weightval in vert.weight:
			if weightval != 0:
				true_used_bones.add(boneidx)
				vertex_ct[boneidx] += 1
				
	# NOTE: some vertices/rigidbodies depend on "invalid" (-1) bones, clean that up here
	true_used_bones.discard(-1)
	
	# third: mark the "exception" bones as "used" if they are in the model
	for protect in BONES_TO_PROTECT:
		# get index from JP name
		i = core.my_list_search(pmx.bones, lambda x: x.name_jp == protect)
		if i is not None:
			true_used_bones.add(i)
	
	# build ik groups here
	# IKbone + chain + target are treated as a group... if any 1 is used, all of them are used. build those groups now.
	ik_groups = [] # list of sets
	for d,bone in enumerate(pmx.bones):
		if bone.has_ik:  # if ik enabled for this bone,
			ik_set = set()
			ik_set.add(d)  # this bone
			ik_set.add(bone.ik_target_idx)  # this bone's target
			for link in bone.ik_links:
				ik_set.add(link.idx)  # all this bone's IK links
			ik_groups.append(ik_set)
	
	# fourth: NEW APPROACH FOR SOLVING INHERITANCE: RECURSION!
	# for each bone that we know to be used, run UP the inheritance tree and collect everything that it depends on
	# recursion inputs: pmx bonelist, ik groups, set of already-known-used, and the bone to start from
	# bonelist is readonly, ik groups are readonly
	# set of already-known-used overlaps with set-being-built, probably just use one global ref to save time merging sets
	# standard way: input is set-of-already-known, return set-built-from-target, that requires merging results after each call tho
	# BUT each function level adds exactly 1 or 0 bones to the set, therefore can just modify the set that is being passed around
	
	def recursive_climb_inherit_tree(target: int, set_being_built):
		# implicitly inherits variables pmx, ik_groups from outer scope
		if target in set_being_built or target == -1:
			# stop condition: if this bone idx is already known to be used, i have already ran recursion from this node. don't do it again.
			# also abort if the target is -1 which means invalid bone
			return
		# if not already in the set, but recursion is being called on this, then this bone is a "parent" of a used bone and should be added.
		set_being_built.add(target)
		# now the parents of THIS bone are also used, so recurse into those.
		bb = pmx.bones[target]
		# acutal parent
		recursive_climb_inherit_tree(bb.parent_idx, set_being_built)
		# partial inherit: if partial rot or partial move, and ratio is nonzero and parent is valid
		if (bb.inherit_rot or bb.inherit_trans) and bb.inherit_ratio != 0 and bb.inherit_parent_idx != -1:
			recursive_climb_inherit_tree(bb.inherit_parent_idx, set_being_built)
		# IK groups: if in an IK group, recurse to all members of that IK group
		for group in ik_groups:
			if target in group:
				for ik_member in group:
					recursive_climb_inherit_tree(ik_member, set_being_built)
					
	parent_used_bones = set()  # true_used_bones + parents + point-at links
	# now that the recursive function is defined, actually invoke the function from every truly-used bone
	for tu in true_used_bones:
		recursive_climb_inherit_tree(tu, parent_used_bones)
	
	# fifth: "tail" or point-at links
	# propogate DOWN the inheritance tree exactly 1 level, no more.
	# also get all bones these tails depend on, it shouldn't depend on anything new but it theoretically can.
	final_used_bones = set()
	for bidx in parent_used_bones:
		b = pmx.bones[bidx]
		# if this bone has a tail,
		if b.tail_usebonelink:
			# add it and anything it depends on to the set.
			recursive_climb_inherit_tree(b.tail, final_used_bones)
	# now merge the two sets
	final_used_bones = final_used_bones.union(parent_used_bones)
	
	# sixth: assemble the final "unused" set by inverting
	# set of all bones, for inverting purposes
	all_bones_list = list(range(len(pmx.bones)))
	all_bones_set = set(all_bones_list)
	
	unused_bones = all_bones_set.difference(final_used_bones)
	unused_bones_list = sorted(list(unused_bones))
	
	# print neat stuff
	if moreinfo:
		if unused_bones_list:
			core.MY_PRINT_FUNC("Bones: total=%d, true_used=%d, parents=%d, tails=%d, unused=%d" %
							   (len(pmx.bones), len(true_used_bones), len(parent_used_bones)-len(true_used_bones),
								len(final_used_bones)-len(parent_used_bones), len(unused_bones_list)))
		# debug aid
		if PRINT_VERTICES_CONTROLLED_BY_EACH_BONE:
			core.MY_PRINT_FUNC("Number of vertices controlled by each bone:")
			for bp in all_bones_list:
				if bp in vertex_ct:
					core.MY_PRINT_FUNC("#: %d    ct: %d" % (bp, vertex_ct[bp]))
	
	return unused_bones_list


def prune_unused_bones(pmx: pmxstruct.Pmx, moreinfo=False):
	# first build the list of bones to delete
	unused_list = identify_unused_bones(pmx, moreinfo)
	
	if not unused_list:
		core.MY_PRINT_FUNC("No changes are required")
		return pmx, False
	
	if moreinfo:
		# convert the list of individual bones to remove into a list of ranges
		delme_rangemap = delme_list_to_rangemap(unused_list)
		core.MY_PRINT_FUNC("Detected %d unused bones arranged in %d contiguous blocks" % (len(unused_list), len(delme_rangemap[0])))
		for d in unused_list:
			core.MY_PRINT_FUNC("bone #{:<3} JP='{}' / EN='{}'".format(
				d, pmx.bones[d].name_jp, pmx.bones[d].name_en))
	
	num_bones_before = len(pmx.bones)
	delete_multiple_bones(pmx, unused_list)
	
	# print("Done deleting unused bones")
	core.MY_PRINT_FUNC("Found and deleted {} / {} = {:.1%} unused bones".format(
		len(unused_list), num_bones_before, len(unused_list) / num_bones_before))
	
	return pmx, True


def end(pmx, input_filename_pmx):
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_boneprune")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=True)
	return None


def main():
	showhelp()
	pmx, name = showprompt()
	pmx, is_changed = prune_unused_bones(pmx, PRINT_FOUND_UNUSED_BONES)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
