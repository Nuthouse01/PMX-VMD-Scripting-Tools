import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.core.nuthouse01_pmx_utils import delme_list_to_rangemap, morph_delete_and_remap

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.05 - 8/22/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################



# just take a wild guess what this field controls
PRINT_AFFECTED_MORPHS = False


# also try to guess what this does
DELETE_NEWLY_EMPTIED_MORPHS = True


# a vertex is removed from a morph if its total deformation is below this value
# after testing several models, on models which have a grouping near 0, the grouping stops around 0.0003
WINNOW_THRESHOLD = 0.0003


# these are morphs used for controlling AutoLuminous stuff, they generally are vertex morphs that contain 1-3
# vertices with offsets of 0,0,0, but they shouldn't be deleted like normal morphs
IGNORE_THESE_MORPHS = [
	"LightUp",
	"LightOff",
	"LightBlink",
	"LightBS",
	"LightUpE",
	"LightDuty",
	"LightMin",
	"LClockUp",
	"LClockDown",
]


helptext = '''====================
morph_winnow:
To reduce overall file size, this will delete vertices from vertex morphs that move imperceptibly small distances.
This will also delete any vertex morphs that have all of their controlled vertices deleted this way.
The default threshold is 0.0003 units. Trust me it really is imperceptible.
'''

iotext = '''Inputs:  PMX file "[model].pmx"\nOutputs: PMX file "[model]_winnow.pmx"
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

def morph_winnow(pmx: pmxstruct.Pmx, moreinfo=False):
	total_num_verts = 0
	total_vert_dropped = 0
	total_morphs_affected = 0

	morphs_now_empty = []
	
	# for each morph:
	for d,morph in enumerate(pmx.morphs):
		# if not a vertex morph, skip it
		if morph.morphtype != pmxstruct.MorphType.VERTEX: continue
		# if it has one of the special AutoLuminous morph names, then skip it
		if morph.name_jp in IGNORE_THESE_MORPHS: continue
		# for each vert in this vertex morph:
		i = 0
		this_vert_dropped = 0  # lines dropped from this morph
		total_num_verts += len(morph.items)
		while i < len(morph.items):
			vert = morph.items[i]
			vert:pmxstruct.PmxMorphItemVertex
			# determine if it is worth keeping or deleting
			# first, calculate euclidian distance
			length = core.my_euclidian_distance(vert.move)
			if length < WINNOW_THRESHOLD:
				morph.items.pop(i)
				this_vert_dropped += 1
			else:
				i += 1
		if len(morph.items) == 0:
			# mark newly-emptied vertex morphs for later removal
			morphs_now_empty.append(d)
		# increment tracking variables
		if this_vert_dropped != 0:
			if moreinfo:
				core.MY_PRINT_FUNC("morph #{:<3} JP='{}' / EN='{}', removed {} vertices".format(
					d, morph.name_jp, morph.name_en, this_vert_dropped))
			total_morphs_affected += 1
			total_vert_dropped += this_vert_dropped
	
	if total_vert_dropped == 0:
		core.MY_PRINT_FUNC("No changes are required")
		return pmx, False
	
	core.MY_PRINT_FUNC("Dropped {} / {} = {:.1%} vertices from among {} affected morphs".format(
		total_vert_dropped, total_num_verts, total_vert_dropped/total_num_verts, total_morphs_affected))
	
	if morphs_now_empty and DELETE_NEWLY_EMPTIED_MORPHS:
		core.MY_PRINT_FUNC("Deleted %d morphs that had all of their vertices below the threshold" % len(morphs_now_empty))
		rangemap = delme_list_to_rangemap(morphs_now_empty)
		
		morph_delete_and_remap(pmx, morphs_now_empty, rangemap)
		
	return pmx, True
	
def end(pmx, input_filename_pmx):
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_winnow")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=True)
	return None

def main():
	showhelp()
	pmx, name = showprompt()
	pmx, is_changed = morph_winnow(pmx, PRINT_AFFECTED_MORPHS)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
