# Nuthouse01 - 04/17/2020 - v4.04
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
	from . import _prune_unused_vertices as prune_unused_vertices
except ImportError as eee:
	try:
		import nuthouse01_core as core
		import nuthouse01_pmx_parser as pmxlib
		import _prune_unused_vertices as prune_unused_vertices
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = pmxlib = prune_unused_vertices = None


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


helptext = '''====================
weight_cleanup:
This function will fix the vertex weights that are weighted twice to the same bone, a minor issue that sometimes happens when merging bones.
This also normalizes the weights of all vertices, and normalizes the normal vectors for all vertices.
'''

iotext = '''Inputs:  PMX file "[model].pmx"\nOutputs: PMX file "[model]_weightfix.pmx"
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

def weight_cleanup(pmx, moreinfo=False):
	#############################
	# ready for logic

	# number of vertices fixed
	weight_fix = 0
	norm_fix = 0
	
	normbad = []
	normbad_err = 0
	
	# for each vertex:
	for d,vert in enumerate(pmx[1]):
		# clean/normalize the weights
		weighttype = vert[9]
		w = vert[10]
		# type0=BDEF1, one bone has 100% weight
		# type1=BDEF2, 2 bones 1 weight (other is implicit)
		# type2=BDEF4, 4 bones 4 weights
		# type3=SDEF, 2 bones 1 weight and 12 values i don't understand.
		# type4=QDEF, 4 bones 4 weights
		if weighttype == 0:
			# nothing to be fixed here
			# continue
			pass
		elif weighttype == 1:
			# only check for and combine duplicates
			# no need to normalize because the 2nd weight is implicit, not explicit
			if w[0] == w[1] and w[0] != -1:
				w[1] = 0  # second bone is not used
				w[2] = 1.0  # first bone has full weight
				weight_fix += 1
		elif weighttype == 2 or weighttype == 4:
			# bdef4 and qdef handled the same way: check for dupes and also normalize
			usedbones = []
			bones = w[0:4]
			weights = w[4:8]
			is_modified = False
			for i in range(4):
				if not (bones[i] == 0 and weights[i] == 0.0) and (bones[i] in usedbones):
					is_modified = True  # then this is a duplicate bone!
					where = usedbones.index(bones[i])  # find index where it was first used
					weights[where] += weights[i]  # combine this bone's weight with the first place it was used
					bones[i] = 0  # set this bone to null
					weights[i] = 0.0  # set this weight to 0
				# add to list of usedbones regardless of whether first or dupe
				usedbones.append(bones[i])
			if is_modified:
				# if it was modified, re-sort by greatest weight
				together = list(zip(bones, weights))
				together.sort(reverse=True,key=lambda x: x[1])
				a,b = zip(*together)
				bones = list(a)
				weights = list(b)
			# do the weights need normalized?
			s = sum(weights)
			if round(s, 6) != 1.0:
				# it needs it, so do it
				weights = [t / s for t in weights]
				# print(round(s, 6), round(sum(weights), 6))
				is_modified = True
			# if I have combined dupes OR normalized weights, count this vertex and write bones+weights back into w
			if is_modified:
				w[0:4] = bones
				w[4:8] = weights
				weight_fix += 1
		elif weighttype == 3:
			# dont understand, don't touch
			# continue
			pass
		else:
			core.MY_PRINT_FUNC("invalid weight type for vertex")
	
		# normalize the normal, vert[3:6]
		if vert[3:6] == [0, 0, 0]:
			# invalid normals will be taken care of below
			normbad.append(d)
		else:
			norm_L = core.my_euclidian_distance(vert[3:6])
			if round(norm_L, 6) != 1.0:
				norm_fix += 1
				vert[3:6] = [n / norm_L for n in vert[3:6]]
	
	if weight_fix:
		core.MY_PRINT_FUNC("Fixed weights for {} / {} = {:.1%} of all vertices".format(weight_fix, len(pmx[1]), weight_fix/len(pmx[1])))
	if norm_fix:
		core.MY_PRINT_FUNC("Normalized ordinary normals for {} / {} = {:.1%} of all vertices".format(norm_fix, len(pmx[1]), norm_fix/len(pmx[1])))
	
	# previously identify all verts w/ 0,0,0 normals so I can get a progress %
	if normbad:
		# create a list in parallel with the faces list for holding the perpendicular normal to each face
		facenorm_list = [None] * len(pmx[2])
		# create a list in paralle with normbad for holding the set of connected faces
		normbad_linked_faces = [list() for i in normbad]
		
		# goal: build the sets of faces that are associated with each bad vertex
		
		# first, flatten the list of face-vertices, probably faster to search that way
		flatlist = [item for sublist in pmx[2] for item in sublist]
		
		# second, for each face-vertex, check if it is a bad vertex
		for d, facevert in enumerate(flatlist):
			core.print_progress_oneline(d / len(flatlist))
			# bad vertices are unique and in sorted order, can use binary search to further optimize
			whereinlist = prune_unused_vertices.binary_search_wherein(facevert, normbad)
			if whereinlist != -1:
				# if it is a bad vertex, int div by 3 to get face ID
				(normbad_linked_faces[whereinlist]).append(d // 3)
		
		# for each bad vert:
		for d, (badvert_idx, badvert_faces) in enumerate(zip(normbad, normbad_linked_faces)):
			newnorm = [0,0,0] # default value in case something goes wrong
			core.print_progress_oneline(d / len(normbad))
			# iterate over the faces it is connected to
			for face_id in badvert_faces:
				# for each face, does the perpendicular normal already exist in the parallel list? if not, calculate and save it for reuse
				facenorm = facenorm_list[face_id]
				if facenorm is None:
					# need to calculate it! use cross product or whatever
					# order of vertices is important! not sure what's right
					q = pmx[1][ pmx[2][face_id][0] ][0:3]
					r = pmx[1][ pmx[2][face_id][1] ][0:3]
					s = pmx[1][ pmx[2][face_id][2] ][0:3]
					qr = [0,0,0]
					qs = [0,0,0]
					for i in range(3):
						qr[i] = r[i] - q[i]
						qs[i] = s[i] - q[i]
					facenorm = core.my_cross_product(qr, qs)
					# then normalize the fresh normal
					norm_L = core.my_euclidian_distance(facenorm)
					try:
						facenorm = [n / norm_L for n in facenorm]
					except ZeroDivisionError:
						# this should never happen in normal cases
						facenorm = [0,1,0]
					# then save the result so I don't have to do this again
					facenorm_list[face_id] = facenorm
				# once I have the perpendicular normal, then accumulate it
				for i in range(3):
					newnorm[i] += facenorm[i]
			# error case check, theoretically possible for this to happen if there are no connected faces or their normals exactly cancel out
			if newnorm == [0,0,0]:
				if len(badvert_faces) == 0:
					# if there are no connected faces, set the normal to 0,1,0 (same handling as PMXE)
					pmx[1][badvert_idx][3:6] = [0,1,0]
				else:
					# if there are faces that just so happened to perfectly cancel, choose the first face and use its normal
					pmx[1][badvert_idx][3:6] = facenorm_list[badvert_faces[0]]
				normbad_err += 1
				continue
			# when done accumulating, divide by # to make an average
			newnorm = [n / len(badvert_faces) for n in newnorm]
			# then normalize this, again
			norm_L = core.my_euclidian_distance(newnorm)
			newnorm = [n / norm_L for n in newnorm]
			# finally, apply this new normal
			pmx[1][badvert_idx][3:6] = newnorm
	
	normbad_fix = len(normbad)
	if len(normbad):
		core.MY_PRINT_FUNC(
			"Repaired invalid normals for {} / {} = {:.1%} of all vertices".format(len(normbad), len(pmx[1]),len(normbad) / len(pmx[1])))
		if normbad_err and moreinfo:
			core.MY_PRINT_FUNC("WARNING: used fallback vertex repair method for %d vertices" % normbad_err)
	
	if weight_fix == 0 and norm_fix == 0 and normbad_fix == 0:
		core.MY_PRINT_FUNC("No changes are required")
		return pmx, False
	
	return pmx, True
	
def end(pmx, input_filename_pmx):
	# write out
	# output_filename_pmx = "%s_weightfix.pmx" % core.get_clean_basename(input_filename_pmx)
	output_filename_pmx = input_filename_pmx[0:-4] + "_weightfix.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
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
	core.MY_PRINT_FUNC("Nuthouse01 - 04/17/2020 - v4.04")
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
			core.MY_PRINT_FUNC(ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")

