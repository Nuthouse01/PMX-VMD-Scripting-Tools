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
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	core = pmxlib = None


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False

# bisect_left and bisect_right literally just copied from the "bisect" library
def bisect_left(a, x):
	"""Return the index where to insert item x in list a, assuming a is sorted.

	The return value i is such that all e in a[:i] have e < x, and all e in
	a[i:] have e >= x.  So if x already appears in the list, a.insert(x) will
	insert just before the leftmost x already there.
	"""
	lo = 0
	hi = len(a)
	while lo < hi:
		mid = (lo+hi)//2
		if a[mid] < x: lo = mid+1
		else: hi = mid
	return lo

def bisect_right(a, x):
	"""Return the index where to insert item x in list a, assuming a is sorted.

	The return value i is such that all e in a[:i] have e <= x, and all e in
	a[i:] have e > x.  So if x already appears in the list, a.insert(x) will
	insert just after the rightmost x already there.
	"""
	lo = 0
	hi = len(a)
	while lo < hi:
		mid = (lo+hi)//2
		if x < a[mid]: hi = mid
		else: lo = mid+1
	return lo

def binary_search_isin(x, a):
	# if x is in a, return its index. otherwise return -1
	pos = bisect_left(a, x)  # find insertion position
	return True if pos != len(a) and a[pos] == x else False  # don't walk off the end


def newval_from_range_map(v, range_map):
	# support both int and list inputs... do basically the same thing, just looped
	# core idea: walk BACKWARDS along the range_map until i find the start that is CLOSEST BELOW the input v
	if isinstance(v, int):
		# # bisect_right: same as bisect_left but when matching something already in it it goes one to the right
		pos = bisect_right(range_map[0], v)
		if pos == 0:
			# if it doesnt find a block starting below v, then the offset is 0
			return v
		else:
			# return the input value minus the applicable offset
			return v - range_map[1][pos-1]
	else:
		# if given a list, the list is ordered so take advantage of that to pick up where the previous item left off
		# walk backwards along both lists side-by-side
		retme = []
		input_idx = len(v) - 1
		idx = len(range_map[0]) - 1
		while idx >= 0 and input_idx >= 0:
			if range_map[0][idx] <= v[input_idx]:
				# return the input value minus the applicable offset
				retme.append(v[input_idx] - range_map[1][idx])
				input_idx -= 1
			else:
				idx -= 1
		if input_idx != -1:
			# if it finished walking down the range-list before it finished the input-list, all remaining inputs are unchanged
			retme += reversed(v[0:input_idx+1])
		retme.reverse()
		return retme
	
def delme_list_to_rangemap(delme_verts: list):
	# convert from individual vertices to list of ranges, [start-length]
	# start begins 0, end begins 1
	delme_range = []
	start_idx = 0
	for end_idx in range(1, len(delme_verts)+1):
		if (end_idx == len(delme_verts)) or (delme_verts[end_idx] != (delme_verts[end_idx-1] + 1)):
			# if the next vert ID is non-contiguous, or is the end of the list, that defines a breakpoint between ranges
			# that means that everything from start to end IS contiguous
			# so save the VALUE of the start, and the LENGTH of the range (which equals the length of the block)
			delme_range.append([delme_verts[start_idx], end_idx - start_idx])
			start_idx = end_idx
	# convert from [start-length] to [start-cumulativelength]
	for i in range(1, len(delme_range)):
		delme_range[i][1] += delme_range[i-1][1]
	# convert from [[start,len],[start,len],[start,len]] to [[start,start,start],[len,len,len]]
	a,b = zip(*delme_range)
	return a,b


def begin():
	# print info to explain the purpose of this file
	print("This script will delete any unused vertices from the model, sometimes causing massive file size improvements.")
	# print info to explain what inputs it needs
	print("Inputs: PMX file 'model.pmx'")
	# print info to explain what outputs it creates
	print("Outputs: PMX file '[model]_vertprune.pmx'")
	print("")
	
	# prompt PMX name
	print("Please enter name of PMX model file:")
	input_filename_pmx = core.prompt_user_filename(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx)
	return pmx, input_filename_pmx

def prune_unused_vertices(pmx):
	#############################
	# ready for logic

	# vertices are referenced in faces, morphs (uv and vertex morphs), and soft bodies (should be handled just for completeness' sake)
	
	# find individual vertices to delete
	#		build set of vertices used in faces
	#		build set of all vertices (just a range)
	#		subtract
	#		convert to sorted list
	# convert to list of [begin, length]
	#		iterate over delvertlist, identify contiguous blocks
	# convert to list of [begin, cumulative size]
	
	# build set of USED vertices
	used_verts = set()
	for face in pmx[2]:
		used_verts.add(face[0])
		used_verts.add(face[1])
		used_verts.add(face[2])
	# build set of ALL vertices
	all_verts = []
	all_verts.extend(range(len(pmx[1])))
	all_verts = set(all_verts)
	# derive set of UNUSED vertices
	unused_verts = all_verts.difference(used_verts)
	# convert to ordered list
	delme_verts = sorted(list(unused_verts))
	
	numdeleted = len(delme_verts)
	prevtotal = len(pmx[1])
	if numdeleted == 0:
		print("Nothing to be done")
		return pmx, False
	
	delme_range = delme_list_to_rangemap(delme_verts)
	
	print("Detected %d orphan vertices arranged in %d contiguous blocks" % (len(delme_verts), len(delme_range)))
	
	# need to update places that reference vertices: faces, morphs, softbody
	# faces:
	last_progress = -1
	for d,face in enumerate(pmx[2]):
		# display progress printouts
		if d > last_progress:
			last_progress += 2000
			core.print_progress_oneline(d, len(pmx[2]))
		
		# vertices in a face are not guaranteed sorted, and changing their order is a Very Bad Idea
		# therefore they must be handled individually
		face[0] = newval_from_range_map(face[0], delme_range)
		face[1] = newval_from_range_map(face[1], delme_range)
		face[2] = newval_from_range_map(face[2], delme_range)
	print("Done updating vertex references in faces")
	
	# morphs:
	orphan_vertex_references = 0
	for d,morph in enumerate(pmx[6]):
		core.print_progress_oneline(d, len(pmx[6]))
		# if not a vertex morph or UV morph, skip it
		if not (3 <= morph[3] <= 7) and morph[3] != 1:
			continue
		# first, it is plausible that vertex/uv morphs could reference orphan vertices, so I should check for and delete those
		i = 0
		while i < len(morph[4]):
			# if the vertex being manipulated is in the list of verts being deleted,
			if binary_search_isin(morph[4][i][0], delme_verts):
				# delete it here too
				morph[4].pop(i)
				orphan_vertex_references += 1
			else:
				# otherwise, remap it
				# but don't remap it here, wait until I'm done deleting vertices and then tackle them all at once
				i += 1
		
		# morphs usually contain vertexes in sorted order, but not guaranteed!!! MAKE it sorted, nobody will mind
		morph[4].sort(key=lambda x: x[0])
		
		# assemble the vertices from the morph entries into a list of their own, for more efficient remapping
		vertlist = [x[0] for x in morph[4]]
		# remap
		remappedlist = newval_from_range_map(vertlist, delme_range)
		# write the remapped values back into where they came from
		for x, newval in zip(morph[4], remappedlist):
			x[0] = newval
	print("Done updating vertex references in morphs")
	
	# if orphan_vertex_references != 0:
	# 	print("debug: orphan vertex references removed = ", orphan_vertex_references)
	
	# softbody: probably not relevant but eh
	for soft in pmx[10]:
		# assemble the vertices from the morph entries into a list of their own, for more efficient remapping
		# todo: delete anchors and pins in the "delme" list, as well as remapping
		anchorlist = [x[1] for x in soft[37]]
		newanchorlist = newval_from_range_map(anchorlist, delme_range)
		# write the remapped values back into where they came from
		for x, newval in zip(soft[37], newanchorlist):
			x[1] = newval
		soft[38] = newval_from_range_map(soft[38], delme_range)
		
	# now, finally, actually delete the vertices from the vertex list
	delme_verts.reverse()
	for f in delme_verts:
		pmx[1].pop(f)
	
	print("Identified and deleted {} / {} = {:.1%} vertices for being unused".format(
		numdeleted, prevtotal, numdeleted/prevtotal))
	
	return pmx, True

def end(pmx, input_filename_pmx):
	# write out
	output_filename_pmx = "%s_vertprune.pmx" % core.get_clean_basename(input_filename_pmx)
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(pmx, output_filename_pmx)
	
	return None
	
def main():
	pmx, name = begin()
	pmx, is_changed = prune_unused_vertices(pmx)
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
