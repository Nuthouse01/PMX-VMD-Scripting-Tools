from typing import List, Tuple

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.00 - 6/10/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################



helptext = '''====================
weight_cleanup:
This function will fix the vertex weights that are weighted twice to the same bone, a minor issue that sometimes happens when merging bones.
This also normalizes the weights of all vertices, and normalizes the normal vectors for all vertices.
Finally, it removes weight for any bones that have <0.001% weight, because it's imperceptible anyways.
'''

iotext = '''Inputs:  PMX file "[model].pmx"\nOutputs: PMX file "[model]_weightfix.pmx"
'''

# epsilon: a number very close to zero. weights below this value become zero.
EPSILON = 0.00001  # = 1e-5 = 0.001%

WEIGHTTYPE_TO_LEN = {pmxstruct.WeightMode.BDEF1:1,
					 pmxstruct.WeightMode.BDEF2:2,
					 pmxstruct.WeightMode.BDEF4:4,
					 pmxstruct.WeightMode.SDEF: 2,
					 pmxstruct.WeightMode.QDEF: 4}

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


def normalize_weights(pmx: pmxstruct.Pmx) -> int:
	"""
	Normalize weights for verts in the PMX object. Also "clean" the weights by removing bones with 0 weight, reducing
	weight type to lowest possible, and sorting them by greatest weight.
	Finally, it removes weight for any bones that have <0.001% weight, because it's imperceptible anyways.
	Return the # of vertices that were modified.
	
	:param pmx: PMX object
	:return: int, # of vertices that were modified
	"""
	# number of vertices fixed
	weight_fix = 0
	
	num_winnow = 0
	num_useless = 0
	num_invalid = 0
	num_merge = 0
	num_normalize = 0
	num_sort = 0
	num_reduce = 0
	
	# for each vertex:
	for d, vert in enumerate(pmx.verts):
		# clean/normalize the weights
		is_modified = False
		
		invalid = False
		winnow = False
		useless = False
		merge = False
		normalize = False
		sort = False
		reduce = False
		
		# vert.weight is a list of "boneidx,weight" pairs
		# FIRST, winnow: every weight below EPSILON is discarded
		# SECOND, remove useless: everything with 0 weight is discarded
		# THIRD, remove invalid: everything on bone -1 is discarded
		# also toss all the [0,0] entries
		# this applies to all weighttypes
		# count backward so i can safely pop by index
		for i in reversed(range(len(vert.weight))):
			boneidx, val = vert.weight[i]
			# 1) if it has weight 0 on bone 0, then pop it but don't count it as a modification of any kind
			if boneidx == 0 and val == 0:
				vert.weight.pop(i)
			# 2) if the weight is attributed to an invalid bone index, then pop it
			elif not (0 <= boneidx < len(pmx.bones)):
				vert.weight.pop(i)
				is_modified = True
				invalid = True
			# 3) if the weight is extremely small but not zero (because i wanna count zeros separately) then pop it
			elif 0 < val < EPSILON:
				vert.weight.pop(i)
				is_modified = True
				winnow = True
			# 4) if it has weight 0 on a REAL bone, then pop it & count it as useless
			elif boneidx != 0 and val == 0:
				vert.weight.pop(i)
				is_modified = True
				useless = True
		
		# THIRD, merge duplicate entries!
		# count backward so i can safely pop by index
		for i in reversed(range(len(vert.weight))):  # COUNTING BACKWARDS 3 2 1
			# compare item i with each item BEFORE it
			# if there is a match, accumulate into the earlier index and delete i
			# don't worry about ignoring the [0,0] they are already gone
			for k in range(i):  # COUNTING FORWARDS 0 1 2
				# if both i and k attribute their weight to the same bone,
				if vert.weight[i][0] == vert.weight[k][0]:
					# then this is a duplicate bone! first used at idx k
					is_modified = True
					merge = True
					vert.weight[k][1] += vert.weight[i][1]  # add i into k
					vert.weight.pop(i)  # delete this second use of the bone
					break  # stop looking for any other match
		# worst case example, all 4 are the same bone: 0 1 2 3
		# i=3, k=0, match, add 3 into 0 then delete 3
		# i=2, k=0, match, add 2 into 0 then delete 2
		# i=1, k=0, match, add 1 into 0 then delete 1

		# FOURTH, normalize if needed
		# this is only really needed for BDEF4 but can be applied to all types so i'm gonna
		# actually, it would be needed for BDEF2 if the epsilon trimming above cuts something out
		weightidx = [foo for foo, _ in vert.weight]
		weightvals = [bar for _, bar in vert.weight]
		if round(sum(weightvals), 6) != 1.0:
			try:
				# normalize to a sum of 1
				weightvals = core.normalize_sum(weightvals)
				# re-write it back into the pattern
				vert.weight = [list(a) for a in zip(weightidx, weightvals)]
			except ZeroDivisionError:
				core.MY_PRINT_FUNC("Warning: vert %d has BDEF4 weights that sum to 0, repairing" % d)
				# force the leading bone to have full weight i guess? better than zero-sum
				vert.weight[0][1] = 1
			is_modified = True
			normalize = True
			
		# FIFTH, sort! descending by strength
		# if SDEF, do not sort! the order is significant, somehow
		if vert.weighttype != pmxstruct.WeightMode.SDEF:
			# save the order of items for comparison
			# weightidx = [foo for foo,_ in vert.weight]
			vert.weight.sort(reverse=True, key=lambda x: x[1])
			# get the new order of items, if it is different then flag it as so
			weightidx_new = [foo for foo,_ in vert.weight]
			if weightidx_new != weightidx:
				is_modified = True
				sort = True
		
		# SIXTH, pick new weighttype based on how many pairs are left!
		# all the [0,0] placeholder should be gone so just use the raw length
		if vert.weighttype == pmxstruct.WeightMode.QDEF:  # QDEF
			# if vert is QDEF type, it stays qdef type. no matter what. I don't understand it so i'm not taking chances.
			pass
		elif len(vert.weight) == 1:
			# BDEF1/BDEF2/BDEF4/SDEF modes go to BDEF1 if there is only 1 thing left
			if vert.weighttype != pmxstruct.WeightMode.BDEF1:
				vert.weighttype = pmxstruct.WeightMode.BDEF1
				is_modified = True
				reduce = True
		elif len(vert.weight) == 2:
			# BDEF2/SDEF stay the same
			# BDEF4 changes to bdef2
			# QDEF doesn't hit here
			if vert.weighttype == pmxstruct.WeightMode.BDEF4:  # BDEF4
				vert.weighttype = pmxstruct.WeightMode.BDEF2
				is_modified = True
				reduce = True
		
		# SEVENTH, pad with 0,0 till appropriate size
		# doesn't count as a change, its just a housekeeping thing
		while len(vert.weight) < WEIGHTTYPE_TO_LEN[vert.weighttype]:
			vert.weight.append([0,0])
		
		weight_fix += is_modified
		
		num_winnow += winnow
		num_useless += useless
		num_invalid += invalid
		num_merge += merge
		num_normalize += normalize
		num_sort += sort
		num_reduce += reduce
		
		pass  # close the for-each-vert loop
	# debug printing, not visible in GUI
	print("invalid %d, winnow %d, useless %d, merge %d, normalize %d, sort %d, reduce %d" %
		  (num_invalid, num_winnow, num_useless, num_merge, num_normalize, num_sort, num_reduce))
	# how many did I change? printing is handled outside
	return weight_fix

def normalize_normals(pmx: pmxstruct.Pmx) -> Tuple[int,List[int]]:
	"""
	Normalize normal vectors for each vertex in the PMX object. Return # of verts that were modified, and also a list
	of all vert indexes that have 0,0,0 normals and need special handling.
	
	:param pmx: PMX list-of-lists object
	:return: # verts modified + list of all vert idxs that have 0,0,0 normals
	"""
	norm_fix = 0
	
	normbad = []
	for d,vert in enumerate(pmx.verts):
		# normalize the normal
		if vert.norm == [0, 0, 0]:
			# invalid normals will be taken care of below
			normbad.append(d)
		else:
			norm_L = core.my_euclidian_distance(vert.norm)
			if round(norm_L, 6) != 1.0:
				norm_fix += 1
				vert.norm = [n / norm_L for n in vert.norm]
	# printing is handled outside
	return norm_fix, normbad

def repair_invalid_normals(pmx: pmxstruct.Pmx, normbad: List[int]) -> int:
	"""
	Repair all 0,0,0 normals in the model by averaging the normal vector for each face that vertex is a member of.
	It is theoretically possible for a vertex to be a member in two faces with exactly opposite normals, and therefore
	the average would be zero; in this case one of the faces is arbitrarily chosen and its normal is used. Therefore,
	after this function all invalid normals are guaranteed to be fixed.
	Returns the number of times this fallback method was used.
	
	:param pmx: PMX list-of-lists object
	:param normbad: list of vertex indices so I don't need to walk all vertices again
	:return: # times fallback method was used
	"""
	normbad_err = 0
	# create a list in parallel with the faces list for holding the perpendicular normal to each face
	facenorm_list = [list() for _ in pmx.faces]
	# create a list in paralle with normbad for holding the set of faces connected to each bad-norm vert
	normbad_linked_faces = [list() for _ in normbad]
	
	# goal: build the sets of faces that are associated with each bad vertex
	
	# first, flatten the list of face-vertices, probably faster to search that way
	flatlist = [item for sublist in pmx.faces for item in sublist]
	
	# second, for each face-vertex, check if it is a bad vertex
	# (this takes 70% of time)
	for d, facevert in enumerate(flatlist):
		core.print_progress_oneline(.7 * d / len(flatlist))
		# bad vertices are unique and in sorted order, can use binary search to further optimize
		whereinlist = core.binary_search_wherein(facevert, normbad)
		if whereinlist != -1:
			# if it is a bad vertex, int div by 3 to get face ID
			(normbad_linked_faces[whereinlist]).append(d // 3)
	
	# for each bad vert:
	# (this takes 30% of time)
	for d, (badvert_idx, badvert_faces) in enumerate(zip(normbad, normbad_linked_faces)):
		newnorm = [0, 0, 0]  # default value in case something goes wrong
		core.print_progress_oneline(.7 + (.3 * d / len(normbad)))
		# iterate over the faces it is connected to
		for face_id in badvert_faces:
			# for each face, does the perpendicular normal already exist in the parallel list? if not, calculate and save it for reuse
			facenorm = facenorm_list[face_id]
			if not facenorm:
				# need to calculate it! use cross product or whatever
				# q,r,s order of vertices is important!
				q = pmx.verts[ pmx.faces[face_id][0] ].pos
				r = pmx.verts[ pmx.faces[face_id][1] ].pos
				s = pmx.verts[ pmx.faces[face_id][2] ].pos
				# qr, qs order of vertices is critically important!
				qr = [r[i] - q[i] for i in range(3)]
				qs = [s[i] - q[i] for i in range(3)]
				facenorm = core.my_cross_product(qr, qs)
				# then normalize the fresh normal
				try:
					facenorm = core.normalize_distance(facenorm)
				except ZeroDivisionError:
					# this should never happen in normal cases
					# however it can happen when the verts are at the same position and therefore their face has zero surface area
					facenorm = [0, 1, 0]
				# then save the result so I don't have to do this again
				facenorm_list[face_id] = facenorm
			# once I have the perpendicular normal for this face, then accumulate it (will divide later to get avg)
			for i in range(3):
				newnorm[i] += facenorm[i]
		# error case check, theoretically possible for this to happen if there are no connected faces or their normals exactly cancel out
		if newnorm == [0, 0, 0]:
			if len(badvert_faces) == 0:
				# if there are no connected faces, set the normal to 0,1,0 (same handling as PMXE)
				pmx.verts[badvert_idx].norm = [0, 1, 0]
			else:
				# if there are faces that just so happened to perfectly cancel, choose the first face and use its normal
				pmx.verts[badvert_idx].norm = facenorm_list[badvert_faces[0]]
			normbad_err += 1
			continue
		# when done accumulating, divide by # to make an average
		# zerodiv err not possible: if there are no connected faces then it will hit [0,0,0] branch above
		newnorm = [n / len(badvert_faces) for n in newnorm]
		# then normalize this, again
		newnorm = core.normalize_distance(newnorm)
		# finally, apply this new normal
		pmx.verts[badvert_idx].norm = newnorm
	return normbad_err



# TODO: rename this script & this function
def weight_cleanup(pmx: pmxstruct.Pmx, moreinfo=False):
	
	#############################
	# part 1: fix all the weights, get an answer for how many i changed
	weight_fix = normalize_weights(pmx)
	
	if weight_fix:
		core.MY_PRINT_FUNC("Fixed weights for {} / {} = {:.1%} of all vertices".format(
			weight_fix, len(pmx.verts), weight_fix/len(pmx.verts)))
	
	#############################
	# part 2: normalize all normals that aren't invalid, also count how many are invalid
	# also build 'normbad' to identify all verts w/ 0,0,0 normals so I can get a progress % in following step
	norm_fix, normbad = normalize_normals(pmx)
	
	if norm_fix:
		core.MY_PRINT_FUNC("Normalized normals for {} / {} = {:.1%} of all vertices".format(
			norm_fix, len(pmx.verts), norm_fix / len(pmx.verts)))
	
	#############################
	# part 3: normalize all the normals that were invalid
	if normbad:
		normbad_err = repair_invalid_normals(pmx, normbad)
		core.MY_PRINT_FUNC("Repaired invalid normals for {} / {} = {:.1%} of all vertices".format(
			len(normbad), len(pmx.verts), len(normbad) / len(pmx.verts)))
		if normbad_err and moreinfo:
			core.MY_PRINT_FUNC("WARNING: used fallback vertex repair method for %d vertices" % normbad_err)
	
	if weight_fix == 0 and norm_fix == 0 and len(normbad) == 0:
		core.MY_PRINT_FUNC("No changes are required")
		return pmx, False
	
	return pmx, True
	
def end(pmx, input_filename_pmx):
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_weightfix")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=True)
	return None
	
def main():
	showhelp()
	pmx, name = showprompt()
	pmx, is_changed = weight_cleanup(pmx)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
