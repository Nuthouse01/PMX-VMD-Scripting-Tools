# Nuthouse01 - 03/30/2020 - v3.51
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
	from _prune_unused_vertices import newval_from_range_map, delme_list_to_rangemap, binary_search_isin
except ImportError as eee:
	print(eee)
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



def begin():
	# print info to explain the purpose of this file
	print("This script identifies all bones in a PMX model that are not currently being used.")
	print("A bone is USED if any of the following are true:\n    other used bones use it as parent, AKA it has children\n    other used bones use it as link point\n    other used bones use it for 'append' (partial parent)\n    it is an IK type bone\n    rigid bodies use it as an anchor\n    any vertex has nonzero weight with that bone")
	print("A bone is UNUSED if none of these conditions are met.")
	print("All unused bones can be safely removed without affecting the current function of the model.")
	print("")
	
	# print info to explain what inputs it needs
	print("Inputs: PMX file 'model.pmx'")
	# print info to explain what outputs it creates
	print("Outputs: PMX file '[model]_boneprune.pmx'")
	print("")
	
	# prompt PMX name
	print("Please enter name of PMX model file:")
	input_filename_pmx = core.prompt_user_filename(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx)
	return pmx, input_filename_pmx
	

def identify_unused_bones(pmx):
	#############################
	# ready for logic

	# python set: no duplicates! .add(newbone), "in", .discard(delbone)
	used_bones = set()
	unused_bones = set()
	# python dict: [newbone], "in"
	vertex_ct = {}

	# # first, build the ordered list of bones for name-to-index lookup later
	# bone_list = []
	# for row in rawlist_bone:
	# 	# ignore all IK links
	# 	if row[0] != core.pmxe_bone_csv_tag:
	# 		continue
	# 	# add JP name to bone-list for lookup
	# 	bone_list.append(row[1])

	# print('Identified {} bones in total.'.format(len(pmx[5])))


	# used_bones is set of BONE INDEXES
	
	# first: bones used by a rigidbody
	for body in pmx[8]:
		used_bones.add(body[2])

	# second: bones used by a vertex i.e. has nonzero weight
	for vert in pmx[1]:
		# 	any vertex that has nonzero weight for that bone
		weighttype = vert[9]
		weights = vert[10]
		if weighttype==0:
			used_bones.add(weights[0])
			core.increment_occurance_dict(vertex_ct,weights[0])
		elif weighttype==1 or weighttype==3:
			# b1, b2, b1w
			# if b1w = 0, then skip b1
			if weights[2] != 0:
				used_bones.add(weights[0])
				core.increment_occurance_dict(vertex_ct,weights[0])
			# if b1w = 1, then skip b2
			if weights[2] != 1:
				used_bones.add(weights[1])
				core.increment_occurance_dict(vertex_ct,weights[1])
		elif weighttype==2 or weighttype==4:
			for i in range(4):
				if weights[i+4] != 0:
					used_bones.add(weights[i])
					core.increment_occurance_dict(vertex_ct, weights[i])
		
	# NOTE: must remove null string from set of "used bones"
	used_bones.discard(-1)

	# third: IK bones and IK links, make this a separate stage just for compartmentalization
	for d,bone in enumerate(pmx[5]):
		if bone[23]:  # if ik enabled for this bone,
			used_bones.add(d)  # mark this bone as used
			used_bones.add(bone[24][0])  # mark this bone's target as used
			for iklink in bone[24][3]:
				used_bones.add(iklink[0])  # mark all this bone's IK links as used
	
	# set of all bones, for inverting purposes
	all_bones_list = []
	all_bones_list.extend(range(len(pmx[5])))
	all_bones_set = set(all_bones_list)

	
	# fourth: bone-list check
	# on first pass unused_bones is empty, it will only grow
	# iterate over bones, growing the list of unused bones each pass
	# it propagates through the parent-child relationships at this stage
	# completely ignore bone point-at links, for now. do that as the final stage.
	used_bones_from_bones_prev = set()
	while True:
		used_bones_from_bones = set()
		for d, bone in enumerate(pmx[5]):
			### if i am useless, then skip all the checks below
			if d in unused_bones:
				continue
			# a bone is used if...
			
			# other bones use as parent, AKA has !useful! children [13]
			### if i am not useless, add my parent to used bones
			used_bones_from_bones.add(bone[5])
			
			# has append and append value is not 0
			### if i am not useless, add my "append" source to used bones
			if (bone[14] or bone[15]) and bone[16][1] != 0:
				used_bones_from_bones.add(bone[16][0])
				
		unused_bones = all_bones_set.difference(used_bones.union(used_bones_from_bones))
		# print("boneloop used from bones:", len(used_bones_from_bones))
		
		# repeat until "used from bones" used list no longer changes
		if used_bones_from_bones == used_bones_from_bones_prev:
			break
		else:
			used_bones_from_bones_prev = used_bones_from_bones
	
	
	# fifth: point-at links
	# after establishing what is actually used, THEN we care about point-at links
	# anything used as a link for something used is, itself, used
	# only make 1 pass of this, that way the "used" doesn't propagate downward along the chain
	used_bones_from_links = set(())
	for d, bone in enumerate(pmx[5]):
		
		### if i am useless, then skip all the checks below
		if d in unused_bones:
			continue
		
		# a bone is used if other !useful! bones use as link point
		### if i am useful, and i am using a point-at link, add my link target to used bones
		if bone[12] and bone[13]:
			used_bones_from_links.add(bone[13][0])
	
	# assemble the final "used" and "unused" sets
	used_bones = (used_bones.union(used_bones_from_bones)).union(used_bones_from_links)
	unused_bones = all_bones_set.difference(used_bones)
	
	# remove the "exception" bones from the unused set
	t = set(unused_bones)
	for idx in t:
		# look up the jp name of this bone
		if pmx[5][idx][0] in BONES_TO_PROTECT:
			unused_bones.remove(idx)
	
	unused_bones_list = sorted(list(unused_bones))

	# debug aid
	if PRINT_VERTICES_CONTROLLED_BY_EACH_BONE:
		print("Number of vertices controlled by each bone:")
		for b in all_bones_list:
			if b in vertex_ct:
				print("#: %d    ct: %d" % (b, vertex_ct[b]))
			
	# another debug aid:
	if PRINT_FOUND_UNUSED_BONES:
		print("The following bones are unused:")
		for b in unused_bones_list:
			print("#: %d    EN: %s    JP: %s" % (b, pmx[5][b][1], pmx[5][b][0]))
	
	return unused_bones_list
	
	
	
def prune_unused_bones(pmx):
	
	unused_list = identify_unused_bones(pmx)
	
	if not unused_list:
		print("Nothing to be done")
		return pmx, False
	
	# convert the list of individual bones to remove into a list of ranges
	delme_rangemap = delme_list_to_rangemap(unused_list)
	# print("blocks", len(delme_rangemap))
	
	num_bones_before = len(pmx[5])
	# acutally delete the bones
	for f in reversed(unused_list):
		pmx[5].pop(f)

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
	
	core.print_progress_oneline(0, 5)
	# VERTICES:
	# just remap the bones that have weight
	# any references to bones being deleted will definitely have 0 weight
	for d,vert in enumerate(pmx[1]):
		# core.print_progress_oneline(d, len(pmx[1]))
		weighttype = vert[9]
		weights = vert[10]
		if weighttype==0:
			# just remap, this cannot have 0 weight
			weights[0] = newval_from_range_map(weights[0], delme_rangemap)
		elif weighttype==1 or weighttype==3:
			# b1, b2, b1w
			# if b1w == 0, zero out b1
			if weights[2] == 0:
				weights[0] = 0
			else:
				weights[0] = newval_from_range_map(weights[0], delme_rangemap)
			# if b1w == 1, then b2w == 0 so zero out b2
			if weights[2] == 1:
				weights[1] = 0
			else:
				weights[1] = newval_from_range_map(weights[1], delme_rangemap)
		elif weighttype==2 or weighttype==4:
			for i in range(4):
				# if weight == 0, then change its bone to 0. otherwise, remap
				if weights[i+4] == 0:
					weights[i] = 0
				else:
					weights[i] = newval_from_range_map(weights[i], delme_rangemap)
	# done with verts
	
	core.print_progress_oneline(1, 5)
	# MORPHS:
	for d,morph in enumerate(pmx[6]):
		# core.print_progress_oneline(d, len(pmx[6]))
		# only operate on bone morphs
		if morph[3] != 2:
			continue
		# first, it is plausible that bone morphs could reference otherwise unused bones, so I should check for and delete those
		i = 0
		while i < len(morph[4]):
			# if the bone being manipulated is in the list of bones being deleted, delete it here too. otherwise remap.
			if binary_search_isin(morph[4][i][0], unused_list):
				morph[4].pop(i)
			else:
				morph[4][i][0] = newval_from_range_map(morph[4][i][0], delme_rangemap)
				i += 1
	# done with morphs
	
	core.print_progress_oneline(2, 5)
	# DISPLAY FRAMES
	for d,frame in enumerate(pmx[7]):
		# core.print_progress_oneline(d, len(pmx[7]))
		i = 0
		while i < len(frame[3]):
			item = frame[3][i]
			# if this item is a morph, skip it
			if item[0]:
				i += 1
			else:
				# if this is one of the bones being deleted, delete it here too. otherwise remap.
				if binary_search_isin(item[1], unused_list):
					frame[3].pop(i)
				else:
					item[1] = newval_from_range_map(item[1], delme_rangemap)
					i += 1
	# done with frames
	
	core.print_progress_oneline(3, 5)
	#RIGIDBODY
	for d,body in enumerate(pmx[8]):
		# core.print_progress_oneline(d, len(pmx[8]))
		# only remap, no possibility of one of these bones being deleted
		body[2] = newval_from_range_map(body[2], delme_rangemap)
	# done with bodies
	
	core.print_progress_oneline(4, 5)
	# BONES: point-at target, true parent, external parent, partial append, ik stuff
	for d,bone in enumerate(pmx[5]):
		core.print_progress_oneline(d, len(pmx[5]))
		# point-at link:
		if bone[12]:
			if binary_search_isin(bone[13][0], unused_list):
				# if pointing at a bone that will be deleted, instead change to offset with offset 0,0,0
				bone[12] = 0
				bone[13] = [0,0,0]
			else:
				# otherwise, remap
				bone[13][0] = newval_from_range_map(bone[13][0], delme_rangemap)
		# other 4 categories only need remapping
		# true parent:
		bone[5] = newval_from_range_map(bone[5], delme_rangemap)
		# partial append:
		if (bone[14] or bone[15]) and bone[16][1] != 0:
			bone[16][0] = newval_from_range_map(bone[16][0], delme_rangemap)
		# external parent:
		if bone[21]:
			bone[22] = newval_from_range_map(bone[22], delme_rangemap)
		# ik stuff:
		if bone[23]:
			bone[24][0] = newval_from_range_map(bone[24][0], delme_rangemap)
			for iklink in bone[24][3]:
				iklink[0] = newval_from_range_map(iklink[0], delme_rangemap)
	# done with bones
	
	# print("Done deleting unused bones")
	print("Found and deleted {} / {} = {:.1%} unused bones".format(
		len(unused_list), num_bones_before, len(unused_list) / num_bones_before))
	
	return pmx, True


def end(pmx, input_filename_pmx):
	# write out
	output_filename_pmx = "%s_boneprune.pmx" % core.get_clean_basename(input_filename_pmx)
	# output_filename_pmx = input_filename_pmx[0:-4] + "_translate.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(pmx, output_filename_pmx)
	
	return None


def main():
	pmx, name = begin()
	pmx, is_changed = prune_unused_bones(pmx)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")


if __name__ == '__main__':
	print("Nuthouse01 - 03/30/2020 - v3.51")
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
