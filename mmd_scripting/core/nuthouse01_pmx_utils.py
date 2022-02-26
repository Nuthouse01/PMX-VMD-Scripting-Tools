from typing import List, TypeVar, Set, Tuple

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.05 - 8/22/2021"

################################################################################
# this file defines some handy functions that help when manipulating PMXs


def delme_list_to_rangemap(delme: List[int]) -> Tuple[List[int], List[int]]:
	"""
	Given an ascending sorted list of ints, build a pair of lists that let me know what indices OTHER things will map
	to when THESE indices are deleted. list1 is the index each cluster starts at, list2 is how much to offset indices
	by if greater than that cluster-start.
	Exclusively used with newval_from_rangemap().

	:param delme: ascending sorted list of ints
	:return: tuple(list-of-starts, list-of-cumulativelength)
	"""
	# if given an empty list, return an empty list
	if len(delme) == 0: return [],[]
	
	# assert that the input is ascending sorted
	if not all(delme[i] < delme[i + 1] for i in range(len(delme) - 1)):
		raise ValueError("BUG DETECTED: delme_list_to_rangemap() received argument not in sorted order!!")
	
	# from stackoverflow: create pairs of (startitem, enditem)
	delme_start_end = []
	start = delme[0]
	prev = delme[0]
	for N in delme[1:]:
		if prev + 1 != N:  # if they are not contiguous,
			delme_start_end.append((start, prev))  # then the previous value is the end of a cluster,
			start = N  # and the current value is the beginning of a new cluster
		prev = N
	delme_start_end.append((start, prev))  # also need to add the final cluster
	
	# convert to (startitem, length)
	delme_length = []
	for start,end in delme_start_end:
		delme_length.append((start, end-start+1))
	
	# convert to (startitem, cumulative offset)
	delme_offset = []
	cumlen = 0
	for start, length in delme_length:
		cumlen += length
		delme_offset.append((start, -cumlen))
	
	# convert from [[start,len],[start,len],[start,len]] to [[start,start,start],[len,len,len]]
	a, b = zip(*delme_offset)
	return a, b


INT_OR_INTLIST = TypeVar("INT_OR_INTLIST", int, List[int])
def newval_from_rangemap(v: INT_OR_INTLIST, range_map: Tuple[List[int], List[int]]) -> INT_OR_INTLIST:
	"""
	Given a rangemap from delme_list_to_rangemap(), determine the resulting index for an input or set of inputs.
	If v is a list, it must be in ascending sorted order. Returns same type as v type.

	:param v: int or list of ints in ascending sorted order
	:param range_map: result from delme_list_to_rangemap()
	:return: int if v is int, list[int] if v is list[int]
	"""
	list_of_starts, list_of_offsets = range_map
	# support both int and list-of-int inputs... do basically the same thing, just looped
	# if input is list, IT MUST BE IN ASCENDING SORTED ORDER
	if isinstance(v, int):
		# bisect_right: binary search for appropriate insert location, if exact match is found return exact index + 1
		pos = core.bisect_right(list_of_starts, v)
		if pos == 0:
			# if it doesnt find a block starting below v, then the offset is 0
			return v
		else:
			# return the input value plus the applicable offset (offset will be negative)
			return v + list_of_offsets[pos - 1]
	elif isinstance(v, (list,tuple)):
		# if given an empty list, return an empty list
		if len(v) == 0: return []
		# if given a list, the list is ordered so take advantage of that to pick up where the previous item left off
		# core idea: walk BACKWARDS along the range_map until i find the start that is CLOSEST BELOW the input v
		# go backwards so I can use the tail end unchanged in some circumstances
		retme = []
		input_idx = len(v) - 1
		# start_idx = len(list_of_starts) - 1
		start_idx = core.bisect_right(list_of_starts, v[-1]) - 1
		while start_idx >= 0 and input_idx >= 0:
			if list_of_starts[start_idx] <= v[input_idx]:
				# if this start idx is below the value idx, then it is applicable! so, apply the corresponding offset
				retme.append(v[input_idx] + list_of_offsets[start_idx])
				input_idx -= 1
			else:
				start_idx -= 1
		retme.reverse()
		if input_idx != -1:
			# if it finished walking down the range-list before it finished the input-list, all remaining inputs are unchanged
			retme = v[0:input_idx + 1] + retme
		return retme
	else:
		raise ValueError("error: newval_from_rangemap() called with '%s' arg, must be int or list/tuple" % v.__class__.__name__)


def bone_get_ancestors(bones: List[pmxstruct.PmxBone], idx: int) -> Set[int]:
	"""
	Walk parent to parent to parent, return the set of all ancestors of the initial bone.
	Does not care about "partial inherit" stuff.
	:param bones: list of PmxBone objects, taken from Pmx.bones.
	:param idx: index within "bones" to start from. NOT INCLUDED within return value.
	:return: set of int indicies of all ancestors.
	"""
	retme = set()
	# if the parent index is not already marked, and not invalid,
	while (bones[idx].parent_idx not in retme) and (bones[idx].parent_idx >= 0):
		# then add the parent index,
		retme.add(bones[idx].parent_idx)
		# and repeat from the parent index
		idx = bones[idx].parent_idx
	return retme


def insert_single_bone(pmx: pmxstruct.Pmx, newbone: pmxstruct.PmxBone, newindex: int):
	"""
	Wrapper function to make inserting bones simpler.
	(!) No existing bones should refer to this bone before it is inserted. (!) When constructing newbone, it should
	refer to already-existing bones by using their indices BEFORE this insert happens. (!) If you want to refer to
	bones that haven't yet been created, too bad, come back and modify it after all insertions are done.
	
	:param pmx: PMX object
	:param newbone: PMX Bone object to be inserted
	:param newindex: position to insert it
	"""
	if newindex > len(pmx.bones) or newindex < 0:
		raise ValueError("invalid index %d for inserting bone, current bonelist len= %d" % (newindex, len(pmx.bones)))
	elif newindex == len(pmx.bones):
		pmx.bones.append(newbone)
	else:
		# insert the bone at the new location
		pmx.bones.insert(newindex, newbone)
		# create the shiftmap for inserting things
		bone_shiftmap = ([newindex], [1])
		# apply the shiftmap
		# this also changes any references inside newbone to refer to the correct indices after the insertion
		bone_delete_and_remap(pmx, [], bone_shiftmap)
	return


def delete_multiple_bones(pmx: pmxstruct.Pmx, bone_dellist: List[int]):
	"""
	Wrapper function to make deleting bones simpler.
	
	:param pmx: PMX object
	:param bone_dellist: list of bone indices to delete
	"""
	# force it to be sorted, just to be safe
	bone_dellist2 = sorted(bone_dellist)
	# build the rangemap to determine how index references will be modified from this deletion
	bone_shiftmap = delme_list_to_rangemap(bone_dellist2)
	# apply remapping scheme to all remaining bones
	bone_delete_and_remap(pmx, bone_dellist2, bone_shiftmap)
	return

def bone_delete_and_remap(pmx: pmxstruct.Pmx, bone_dellist: List[int], bone_shiftmap: Tuple[List[int], List[int]]):
	"""
	Given a list of bones to delete, delete them, and update the indices for all references to all remaining bones.
	PMX is modified in-place. Behavior is undefined if the dellist bones are still in use somewhere!
	References include: vertex weight, bone morph, display frame, rigidbody anchor, bone tail, bone partial inherit,
	bone IK target, bone IK link.
	
	:param pmx: PMX object
	:param bone_dellist: list of ints to delete, MUST be in sorted order!
	:param bone_shiftmap: created by delme_list_to_rangemap() before calling
	"""
	
	core.print_progress_oneline(0 / 5)
	# VERTICES:
	# just remap the bones that have weight
	# any references to bones being deleted will definitely have 0 weight, and therefore it doesn't matter what they reference afterwards
	for d, vert in enumerate(pmx.verts):
		for pair in vert.weight:
			pair[0] = newval_from_rangemap(int(pair[0]), bone_shiftmap)
	# done with verts
	
	core.print_progress_oneline(1 / 5)
	# MORPHS:
	for d, morph in enumerate(pmx.morphs):
		# only operate on bone morphs
		if morph.morphtype != pmxstruct.MorphType.BONE: continue
		# first, it is plausible that bone morphs could reference otherwise unused bones, so I should check for and delete those
		i = 0
		while i < len(morph.items):
			it = morph.items[i]
			it: pmxstruct.PmxMorphItemBone
			# if the bone being manipulated is in the list of bones being deleted, delete it here too. otherwise remap.
			if core.binary_search_isin(it.bone_idx, bone_dellist):
				morph.items.pop(i)
			else:
				it.bone_idx = newval_from_rangemap(it.bone_idx, bone_shiftmap)
				i += 1
	# done with morphs
	
	core.print_progress_oneline(2 / 5)
	# DISPLAY FRAMES
	for d, frame in enumerate(pmx.frames):
		i = 0
		while i < len(frame.items):
			item = frame.items[i]
			# if this item is a morph, skip it
			if item.is_morph:
				i += 1
			else:
				# if this is one of the bones being deleted, delete it here too. otherwise remap.
				if core.binary_search_isin(item.idx, bone_dellist):
					frame.items.pop(i)
				else:
					item.idx = newval_from_rangemap(item.idx, bone_shiftmap)
					i += 1
	# done with frames
	
	core.print_progress_oneline(3 / 5)
	# RIGIDBODY
	for d, body in enumerate(pmx.rigidbodies):
		# if bone is being used by a rigidbody, set that reference to -1. otherwise, remap.
		if core.binary_search_isin(body.bone_idx, bone_dellist):
			body.bone_idx = -1
		else:
			body.bone_idx = newval_from_rangemap(body.bone_idx, bone_shiftmap)
	# done with bodies
	
	core.print_progress_oneline(4 / 5)
	# BONES: point-at target, true parent, external parent, partial append, ik stuff
	for d, bone in enumerate(pmx.bones):
		# point-at link:
		if bone.tail_usebonelink:
			if core.binary_search_isin(bone.tail, bone_dellist):
				# if pointing at a bone that will be deleted, instead change to offset with offset 0,0,0
				bone.tail_usebonelink = False
				bone.tail = [0, 0, 0]
			else:
				# otherwise, remap
				bone.tail = newval_from_rangemap(bone.tail, bone_shiftmap)
		# other 4 categories only need remapping
		# true parent:
		bone.parent_idx = newval_from_rangemap(bone.parent_idx, bone_shiftmap)
		# partial append:
		if (bone.inherit_rot or bone.inherit_trans) and bone.inherit_parent_idx != -1:
			if core.binary_search_isin(bone.inherit_parent_idx, bone_dellist):
				# if a bone is getting partial append from a bone getting deleted, break that relationship
				# shouldn't be possible but whatever i'll support the case
				bone.inherit_rot = False
				bone.inherit_trans = False
				bone.inherit_parent_idx = -1
			else:
				bone.inherit_parent_idx = newval_from_rangemap(bone.inherit_parent_idx, bone_shiftmap)
		# ik stuff:
		if bone.has_ik:
			bone.ik_target_idx = newval_from_rangemap(bone.ik_target_idx, bone_shiftmap)
			for link in bone.ik_links:
				link.idx = newval_from_rangemap(link.idx, bone_shiftmap)
	# done with bones
	
	# acutally delete the bones
	for f in reversed(bone_dellist):
		pmx.bones.pop(f)

	return

def morph_delete_and_remap(pmx: pmxstruct.Pmx, morph_dellist: List[int], morph_shiftmap: Tuple[List[int], List[int]]) -> None:
	"""
	Delete morphs from the model, and correspondingly update dispframes and group-morphs.
	No return, updates the PMX in-place.

	:param pmx: PMX object
	:param morph_dellist: list of ints to delete, MUST be in sorted order!
	:param morph_shiftmap: created by delme_list_to_rangemap() before calling
	"""
	# actually delete the morphs from the list
	for f in reversed(morph_dellist):
		pmx.morphs.pop(f)
	
	# frames:
	for d, frame in enumerate(pmx.frames):
		i = 0
		while i < len(frame.items):
			item = frame.items[i]
			# if this item is a bone, skip it
			if not item.is_morph:
				i += 1
			else:
				# if this is one of the morphs being deleted, delete it here too. otherwise remap.
				if core.binary_search_isin(item.idx, morph_dellist):
					frame.items.pop(i)
				else:
					item.idx = newval_from_rangemap(item.idx, morph_shiftmap)
					i += 1
	
	# group/flip morphs:
	for d, morph in enumerate(pmx.morphs):
		# group/flip = 0/9
		if morph.morphtype not in (pmxstruct.MorphType.GROUP, pmxstruct.MorphType.FLIP): continue
		i = 0
		while i < len(morph.items):
			it = morph.items[i]
			it : pmxstruct.PmxMorphItemGroup
			# if this is one of the morphs being deleted, delete it here too. otherwise remap.
			if core.binary_search_isin(it.morph_idx, morph_dellist):
				morph.items.pop(i)
			else:
				it.morph_idx = newval_from_rangemap(it.morph_idx, morph_shiftmap)
				i += 1
	return

def delete_faces(pmx: pmxstruct.Pmx, faces_to_remove: List[int]) -> None:
	"""
	Delete faces from the model, and correspondingly update the material objects.
	This does not check if it would cause a material to have 0 faces afterward.
	No return, updates the PMX in-place.
	
	:param pmx: PMX object
	:param faces_to_remove: list of ints to delete, MUST be in sorted order!
	"""
	# the question simply becomes, "how many faces within range [start, end] are being deleted"
	delface_idx = 0
	prev_delface_idx = 0
	mat_end_idx = 0
	for mat in pmx.materials:
		mat_end_idx += mat.faces_ct  # this tracks the id of the final face in this material
		try:
			# inc until delface_idx points at a face that doesn't fall into this material's range
			while faces_to_remove[delface_idx] < mat_end_idx:
				delface_idx += 1
		except IndexError:
			# indexerror means i hit the end of the list, no biggie
			pass
		# within the list of faces to be deleted,
		# prev_delface_idx is the idx of the first face that falls within this material's scope,
		# delface_idx is the idx of the first face that falls within THE NEXT material's scope
		# therefore their difference is the number of faces to remove from the current material
		num_remove_from_this_material = delface_idx - prev_delface_idx
		mat.faces_ct -= num_remove_from_this_material
		# update the start idx for next material
		prev_delface_idx = delface_idx
	
	# now, delete the acutal faces
	for f in reversed(faces_to_remove):
		pmx.faces.pop(f)
	return


def vert_delete_and_remap(pmx: pmxstruct.Pmx, vert_dellist: List[int], vert_shiftmap: Tuple[List[int], List[int]]) -> None:
	"""
	Delete vertices from the model, and correspondingly update everything that references them.
	No return, updates the PMX in-place.
	Faces, morphs, softbodies need updating.

	:param pmx: PMX object
	:param vert_dellist: list of ints to delete, MUST be in sorted order!
	:param vert_shiftmap: created by delme_list_to_rangemap() before calling
	"""

	# need to update places that reference vertices: faces, morphs, softbody
	# first get the total # of iterations I need to do, for progress purposes: #faces + sum of len of all UV and vert morphs
	totalwork = len(pmx.faces) + sum([len(m.items) for m in pmx.morphs if (m.morphtype in (pmxstruct.MorphType.VERTEX,
																						   pmxstruct.MorphType.UV,
																						   pmxstruct.MorphType.UV_EXT1,
																						   pmxstruct.MorphType.UV_EXT2,
																						   pmxstruct.MorphType.UV_EXT3,
																						   pmxstruct.MorphType.UV_EXT4))])
	
	# faces:
	d = 0
	for d, face in enumerate(pmx.faces):
		# vertices in a face are not guaranteed sorted, and sorting them is a Very Bad Idea
		# therefore they must be remapped individually
		face[0] = newval_from_rangemap(face[0], vert_shiftmap)
		face[1] = newval_from_rangemap(face[1], vert_shiftmap)
		face[2] = newval_from_rangemap(face[2], vert_shiftmap)
		# display progress printouts
		core.print_progress_oneline(d / totalwork)
	
	# core.MY_PRINT_FUNC("Done updating vertex references in faces")
	
	# morphs:
	orphan_vertex_references = 0
	for morph in pmx.morphs:
		# if not a vertex morph or UV morph, skip it
		if not morph.morphtype in (pmxstruct.MorphType.VERTEX,
								   pmxstruct.MorphType.UV,
								   pmxstruct.MorphType.UV_EXT1,
								   pmxstruct.MorphType.UV_EXT2,
								   pmxstruct.MorphType.UV_EXT3,
								   pmxstruct.MorphType.UV_EXT4): continue
		lenbefore = len(morph.items)
		# it is plausible that vertex/uv morphs could reference orphan vertices, so I should check for and delete those
		i = 0
		while i < len(morph.items):
			# if the vertex being manipulated is in the list of verts being deleted,
			if core.binary_search_isin(morph.items[i].vert_idx, vert_dellist):
				# delete it here too
				morph.items.pop(i)
				orphan_vertex_references += 1
			else:
				# otherwise, remap it
				# but don't remap it here, wait until I'm done deleting vertices and then tackle them all at once
				i += 1
		
		# morphs usually contain vertexes in sorted order, but not guaranteed!!! MAKE it sorted, nobody will mind
		morph.items.sort(key=lambda x: x.vert_idx)
		
		# separate the vertices from the morph entries into a list of their own, for more efficient remapping
		vertlist = [x.vert_idx for x in morph.items]
		# remap
		remappedlist = newval_from_rangemap(vertlist, vert_shiftmap)
		# write the remapped values back into where they came from
		for x, newval in zip(morph.items, remappedlist):
			x.vert_idx = newval
		# display progress printouts
		d += lenbefore
		core.print_progress_oneline(d / totalwork)
	
	# core.MY_PRINT_FUNC("Done updating vertex references in morphs")
	
	# softbody: probably not relevant but eh
	for soft in pmx.softbodies:
		# anchors
		# first, delete any references to delme verts in the anchors
		i = 0
		while i < len(soft.anchors_list):
			# if the vertex referenced is in the list of verts being deleted,
			if core.binary_search_isin(soft.anchors_list[i][1], vert_dellist):
				# delete it here too
				soft.anchors_list.pop(i)
			else:
				# otherwise, remap it
				# but don't remap it here, wait until I'm done deleting vertices and then tackle them all at once
				i += 1
		
		#  MAKE it sorted, nobody will mind
		soft.anchors_list.sort(key=lambda x: x[1])
		# extract the vert indices into a list of their town
		anchorlist = [x[1] for x in soft.anchors_list]
		# remap
		newanchorlist = newval_from_rangemap(anchorlist, vert_shiftmap)
		# write the remapped values back into where they came from
		for x, newval in zip(soft.anchors_list, newanchorlist):
			x[1] = newval
		
		# vertex pins
		# first, delete any references to delme verts
		i = 0
		while i < len(soft.vertex_pin_list):
			# if the vertex referenced is in the list of verts being deleted,
			if core.binary_search_isin(soft.vertex_pin_list[i], vert_dellist):
				# delete it here too
				soft.vertex_pin_list.pop(i)
			else:
				# otherwise, remap it
				# but don't remap it here, wait until I'm done deleting vertices and then tackle them all at once
				i += 1
		#  MAKE it sorted, nobody will mind
		soft.anchors_list.sort()
		# remap
		soft.vertex_pin_list = newval_from_rangemap(soft.vertex_pin_list, vert_shiftmap)
	# done with softbodies!
	
	# now, finally, actually delete the vertices from the vertex list
	vert_dellist.reverse()
	for f in vert_dellist:
		pmx.verts.pop(f)
		
	return