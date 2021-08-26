import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.core.nuthouse01_pmx_utils import newval_from_rangemap, delme_list_to_rangemap

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.00 - 6/10/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################



helptext = '''====================
prune_unused_vertices:
This script will delete any unused vertices from the model, sometimes causing massive file size improvements.
An unused vertex is one which is not used to define any faces.
'''

iotext = '''Inputs:  PMX file "[model].pmx"\nOutputs: PMX file "[model]_vertprune.pmx"
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

def prune_unused_vertices(pmx: pmxstruct.Pmx, moreinfo=False):
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
	for face in pmx.faces:
		used_verts.add(face[0])
		used_verts.add(face[1])
		used_verts.add(face[2])
	# build set of ALL vertices
	all_verts = set(list(range(len(pmx.verts))))
	# derive set of UNUSED vertices
	unused_verts = all_verts.difference(used_verts)
	# convert to ordered list
	delme_verts = sorted(list(unused_verts))
	
	numdeleted = len(delme_verts)
	prevtotal = len(pmx.verts)
	if numdeleted == 0:
		core.MY_PRINT_FUNC("No changes are required")
		return pmx, False
	
	delme_range = delme_list_to_rangemap(delme_verts)
	
	if moreinfo:
		core.MY_PRINT_FUNC("Detected %d orphan vertices arranged in %d contiguous blocks" % (len(delme_verts), len(delme_range[0])))
	
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
	for d,face in enumerate(pmx.faces):
		# vertices in a face are not guaranteed sorted, and sorting them is a Very Bad Idea
		# therefore they must be remapped individually
		face[0] = newval_from_rangemap(face[0], delme_range)
		face[1] = newval_from_rangemap(face[1], delme_range)
		face[2] = newval_from_rangemap(face[2], delme_range)
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
			if core.binary_search_isin(morph.items[i].vert_idx, delme_verts):
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
		remappedlist = newval_from_rangemap(vertlist, delme_range)
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
			if core.binary_search_isin(soft.anchors_list[i][1], delme_verts):
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
		newanchorlist = newval_from_rangemap(anchorlist, delme_range)
		# write the remapped values back into where they came from
		for x, newval in zip(soft.anchors_list, newanchorlist):
			x[1] = newval
		
		# vertex pins
		# first, delete any references to delme verts
		i = 0
		while i < len(soft.vertex_pin_list):
			# if the vertex referenced is in the list of verts being deleted,
			if core.binary_search_isin(soft.vertex_pin_list[i], delme_verts):
				# delete it here too
				soft.vertex_pin_list.pop(i)
			else:
				# otherwise, remap it
				# but don't remap it here, wait until I'm done deleting vertices and then tackle them all at once
				i += 1
		#  MAKE it sorted, nobody will mind
		soft.anchors_list.sort()
		# remap
		soft.vertex_pin_list = newval_from_rangemap(soft.vertex_pin_list, delme_range)
		# done with softbodies!
		
	# now, finally, actually delete the vertices from the vertex list
	delme_verts.reverse()
	for f in delme_verts:
		pmx.verts.pop(f)
	
	core.MY_PRINT_FUNC("Identified and deleted {} / {} = {:.1%} vertices for being unused".format(
		numdeleted, prevtotal, numdeleted/prevtotal))
	
	return pmx, True

def end(pmx, input_filename_pmx):
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_vertprune")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=True)
	return None
	
def main():
	showhelp()
	pmx, name = showprompt()
	pmx, is_changed = prune_unused_vertices(pmx)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
