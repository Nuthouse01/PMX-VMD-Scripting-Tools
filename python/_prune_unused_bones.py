# Nuthouse01 - 07/09/2020 - v4.60
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



# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
	from ._prune_unused_vertices import newval_from_range_map, delme_list_to_rangemap, binary_search_isin
except ImportError as eee:
	try:
		import nuthouse01_core as core
		import nuthouse01_pmx_parser as pmxlib
		from _prune_unused_vertices import newval_from_range_map, delme_list_to_rangemap, binary_search_isin
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = pmxlib = None
		newval_from_range_map = delme_list_to_rangemap = binary_search_isin = None


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = True


# when this is true, it also prints a list of the number of vertices controlled by each bone. not recommended.
PRINT_VERTICES_CONTROLLED_BY_EACH_BONE = False


# when this is true, list the number and names of each bone i am deleting
PRINT_FOUND_UNUSED_BONES = False


# these are common bones that are unused but should not be deleted
# glasses, dummy_L, dummy_R, view cnt, motherbone
BONES_TO_PROTECT = ["メガネ", "左ダミー", "右ダミー", "操作中心", "全ての親"]

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
	input_filename_pmx = core.prompt_user_filename(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=True)
	return pmx, input_filename_pmx
	

def identify_unused_bones(pmx, moreinfo=False):
	#############################
	# THE PLAN:
	# 1. get bones used by a rigidbody
	# 2. get bones that have weight on at least 1 vertex
	# 3. mark "exception" bones, done here so parents of exception bones are kept too
	# 4. inheritance, aka "bones used by bones", recursively climb the tree & get all bones the "true" used bones depend on
	# 5. tails
	# 6. invert to get set of unused

	# python set: no duplicates! .add(newbone), "in", .discard(delbone)
	# true_used_bones is set of BONE INDEXES
	true_used_bones = set()  # exception bones + rigidbody bones + vertex bones
	vertex_ct = {}  # how many vertexes does each bone control? sometimes useful info

	# first: bones used by a rigidbody
	for body in pmx[8]:
		true_used_bones.add(body[2])

	# second: bones used by a vertex i.e. has nonzero weight
	# any vertex that has nonzero weight for that bone
	for vert in pmx[1]:
		weighttype = vert[9]
		weights = vert[10]
		if weighttype==0:
			true_used_bones.add(weights[0])
			core.increment_occurance_dict(vertex_ct,weights[0])
		elif weighttype==1 or weighttype==3:
			# b1, b2, b1w
			# if b1w = 0, then skip b1
			if weights[2] != 0:
				true_used_bones.add(weights[0])
				core.increment_occurance_dict(vertex_ct,weights[0])
			# if b1w = 1, then skip b2
			if weights[2] != 1:
				true_used_bones.add(weights[1])
				core.increment_occurance_dict(vertex_ct,weights[1])
		elif weighttype==2 or weighttype==4:
			for i in range(4):
				if weights[i+4] != 0:
					true_used_bones.add(weights[i])
					core.increment_occurance_dict(vertex_ct, weights[i])
		
	# NOTE: some vertices/rigidbodies depend on "invalid" (-1) bones, clean that up here
	true_used_bones.discard(-1)
	
	# third: mark the "exception" bones as "used" if they are in the model
	for protect in BONES_TO_PROTECT:
		# get index from JP name
		i = core.my_sublist_find(pmx[5], 0, protect, getindex=True)
		if i is not None:
			true_used_bones.add(i)
	
	# build ik groups here
	# IK + chain + target are treated as a group... if any 1 is used, all of them are used. build those groups now.
	ik_groups = [] # list of sets
	for d,bone in enumerate(pmx[5]):
		if bone[23]:  # if ik enabled for this bone,
			ik_set = set()
			ik_set.add(d)  # this bone
			ik_set.add(bone[24][0])  # this bone's target
			for iklink in bone[24][3]:
				ik_set.add(iklink[0])  # all this bone's IK links
			ik_groups.append(ik_set)
	
	# fourth: NEW APPROACH FOR SOLVING INHERITANCE: RECURSION!
	# for each bone that we know to be used, run UP the inheritance tree and collect everything that it depends on
	# recursion inputs: pmx bonelist, ik groups, set of already-known-used, and the bone to start from
	# bonelist is readonly, ik groups are readonly
	# set of already-known-used overlaps with set-being-built, probably just use one global ref to save time merging sets
	# standard way: input is set-of-already-known, return set-built-from-target, that requires merging results after each call tho
	# BUT each function level adds exactly 1 or 0 bones to the set, therefore can just modify the set that is being passed around
	
	def recursive_climb_inherit_tree(target, set_being_built):
		# implicitly inherits variables pmx, ik_groups from outer scope
		if target in set_being_built or target == -1:
			# stop condition: if this bone idx is already known to be used, i have already ran recursion from this node. don't do it again.
			# also abort if the target is -1 which means invalid bone
			return
		# if not already in the set, but recursion is being called on this, then this bone is a "parent" of a used bone and should be added.
		set_being_built.add(target)
		# now the parents of THIS bone are also used, so recurse into those.
		bb = pmx[5][target]
		# acutal parent
		recursive_climb_inherit_tree(bb[5], set_being_built)
		# partial inherit: if partial rot or partial move, and ratio is nonzero
		if (bb[14] or bb[15]) and bb[16][1] != 0:
			recursive_climb_inherit_tree(bb[16][0], set_being_built)
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
		b = pmx[5][bidx]
		# if this bone has a tail,
		if b[12]:
			# add it and anything it depends on to the set.
			recursive_climb_inherit_tree(b[13][0], final_used_bones)
	# now merge the two sets
	final_used_bones = final_used_bones.union(parent_used_bones)
	
	# sixth: assemble the final "unused" set by inverting
	# set of all bones, for inverting purposes
	all_bones_list = []
	all_bones_list.extend(range(len(pmx[5])))
	all_bones_set = set(all_bones_list)
	
	unused_bones = all_bones_set.difference(final_used_bones)
	unused_bones_list = sorted(list(unused_bones))
	
	# print neat stuff
	if moreinfo:
		core.MY_PRINT_FUNC("Bones: total=%d, true_used=%d, parents=%d, tails=%d, unused=%d" %
						   (len(pmx[5]), len(true_used_bones), len(parent_used_bones)-len(true_used_bones),
							len(final_used_bones)-len(parent_used_bones), len(unused_bones_list)))
		# debug aid
		if PRINT_VERTICES_CONTROLLED_BY_EACH_BONE:
			core.MY_PRINT_FUNC("Number of vertices controlled by each bone:")
			for bp in all_bones_list:
				if bp in vertex_ct:
					core.MY_PRINT_FUNC("#: %d    ct: %d" % (bp, vertex_ct[bp]))
	
	return unused_bones_list
	

def apply_bone_remapping(pmx, bone_dellist, bone_shiftmap):
	# where are all places bones are used in the model?
	
	# !vertex weight
	# 	vertices will have 0 weight, and have thier now-invalid index set to 0
	# !morph bone: delete that entry
	# !dispframes: delete that entry
	# rigidbody anchor: remap only
	# !bone point-at target: set to -1 ? set to offset 0,0,0 ?
	# bone partial append: remap only
	# bone external parent: remap only
	# bone ik stuff: remap only
	
	# acutally delete the bones
	for f in reversed(bone_dellist):
		pmx[5].pop(f)

	core.print_progress_oneline(0 / 5)
	# VERTICES:
	# just remap the bones that have weight
	# any references to bones being deleted will definitely have 0 weight
	for d, vert in enumerate(pmx[1]):
		weighttype = vert[9]
		weights = vert[10]
		if weighttype == 0:
			# just remap, this cannot have 0 weight
			weights[0] = newval_from_range_map(weights[0], bone_shiftmap)
		elif weighttype == 1 or weighttype == 3:
			# b1, b2, b1w
			# if b1w == 0, zero out b1
			if weights[2] == 0:
				weights[0] = 0
			else:
				weights[0] = newval_from_range_map(weights[0], bone_shiftmap)
			# if b1w == 1, then b2w == 0 so zero out b2
			if weights[2] == 1:
				weights[1] = 0
			else:
				weights[1] = newval_from_range_map(weights[1], bone_shiftmap)
		elif weighttype == 2 or weighttype == 4:
			for i in range(4):
				# if weight == 0, then change its bone to 0. otherwise, remap
				if weights[i + 4] == 0:
					weights[i] = 0
				else:
					weights[i] = newval_from_range_map(weights[i], bone_shiftmap)
	# done with verts
	
	core.print_progress_oneline(1 / 5)
	# MORPHS:
	for d, morph in enumerate(pmx[6]):
		# only operate on bone morphs
		if morph[3] != 2:
			continue
		# first, it is plausible that bone morphs could reference otherwise unused bones, so I should check for and delete those
		i = 0
		while i < len(morph[4]):
			# if the bone being manipulated is in the list of bones being deleted, delete it here too. otherwise remap.
			if binary_search_isin(morph[4][i][0], bone_dellist):
				morph[4].pop(i)
			else:
				morph[4][i][0] = newval_from_range_map(morph[4][i][0], bone_shiftmap)
				i += 1
	# done with morphs
	
	core.print_progress_oneline(2 / 5)
	# DISPLAY FRAMES
	for d, frame in enumerate(pmx[7]):
		i = 0
		while i < len(frame[3]):
			item = frame[3][i]
			# if this item is a morph, skip it
			if item[0]:
				i += 1
			else:
				# if this is one of the bones being deleted, delete it here too. otherwise remap.
				if binary_search_isin(item[1], bone_dellist):
					frame[3].pop(i)
				else:
					item[1] = newval_from_range_map(item[1], bone_shiftmap)
					i += 1
	# done with frames
	
	core.print_progress_oneline(3 / 5)
	# RIGIDBODY
	for d, body in enumerate(pmx[8]):
		# only remap, no possibility of one of these bones being deleted
		body[2] = newval_from_range_map(body[2], bone_shiftmap)
	# done with bodies
	
	core.print_progress_oneline(4 / 5)
	# BONES: point-at target, true parent, external parent, partial append, ik stuff
	for d, bone in enumerate(pmx[5]):
		# point-at link:
		if bone[12]:
			if binary_search_isin(bone[13][0], bone_dellist):
				# if pointing at a bone that will be deleted, instead change to offset with offset 0,0,0
				bone[12] = 0
				bone[13] = [0, 0, 0]
			else:
				# otherwise, remap
				bone[13][0] = newval_from_range_map(bone[13][0], bone_shiftmap)
		# other 4 categories only need remapping
		# true parent:
		bone[5] = newval_from_range_map(bone[5], bone_shiftmap)
		# partial append:
		if (bone[14] or bone[15]) and bone[16][1] != 0:
			if binary_search_isin(bone[16][0], bone_dellist):
				# if a bone is getting partial append from a bone getting deleted, break that relationship
				bone[14] = 0
				bone[15] = 0
			else:
				bone[16][0] = newval_from_range_map(bone[16][0], bone_shiftmap)
		# # external parent: i don't think external parent cares about the values of bones INSIDE the model?
		# if bone[21]:
		# 	bone[22] = newval_from_range_map(bone[22], bone_shiftmap)
		# ik stuff:
		if bone[23]:
			bone[24][0] = newval_from_range_map(bone[24][0], bone_shiftmap)
			for iklink in bone[24][3]:
				iklink[0] = newval_from_range_map(iklink[0], bone_shiftmap)
	# done with bones
	return pmx


def prune_unused_bones(pmx, moreinfo=False):
	# first build the list of bones to delete
	unused_list = identify_unused_bones(pmx, moreinfo)
	
	if not unused_list:
		core.MY_PRINT_FUNC("No changes are required")
		return pmx, False
	
	# convert the list of individual bones to remove into a list of ranges
	delme_rangemap = delme_list_to_rangemap(unused_list)
	if moreinfo:
		core.MY_PRINT_FUNC("Detected %d unused bones arranged in %d contiguous blocks" % (len(unused_list), len(delme_rangemap[0])))
		for d in unused_list:
			core.MY_PRINT_FUNC("bone #{:<3} JP='{}' / EN='{}'".format(d, pmx[5][d][0], pmx[5][d][1]))
	
	num_bones_before = len(pmx[5])
	pmx = apply_bone_remapping(pmx, unused_list, delme_rangemap)
	
	# print("Done deleting unused bones")
	core.MY_PRINT_FUNC("Found and deleted {} / {} = {:.1%} unused bones".format(
		len(unused_list), num_bones_before, len(unused_list) / num_bones_before))
	
	return pmx, True


def end(pmx, input_filename_pmx):
	# write out
	# output_filename_pmx = "%s_boneprune.pmx" % core.get_clean_basename(input_filename_pmx)
	output_filename_pmx = input_filename_pmx[0:-4] + "_boneprune.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
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
	core.MY_PRINT_FUNC("Nuthouse01 - 07/09/2020 - v4.60")
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
