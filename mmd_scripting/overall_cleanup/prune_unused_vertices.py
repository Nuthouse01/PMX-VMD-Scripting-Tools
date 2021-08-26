import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.core.nuthouse01_pmx_utils import delme_list_to_rangemap, vert_delete_and_remap

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.05 - 6/10/2021"
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
		used_verts.update(face)
	# build set of ALL vertices
	all_verts = set(list(range(len(pmx.verts))))
	# derive set of UNUSED vertices by subtracting
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
	
	vert_delete_and_remap(pmx, delme_verts, delme_range)
	
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
