from mmd_scripting.core import nuthouse01_core as core
from mmd_scripting.core import nuthouse01_pmx_parser as pmxlib
from mmd_scripting.core import nuthouse01_pmx_struct as pmxstruct
from .prune_unused_vertices import newval_from_range_map, delme_list_to_rangemap

_SCRIPT_VERSION = "Script version:  Nuthouse01 - 6/10/2021 - v6.00"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


# just take a wild guess what this field controls
PRINT_AFFECTED_MORPHS = False


# also try to guess what this does
DELETE_NEWLY_EMPTIED_MORPHS = True


# a vertex is removed from a morph if its total deformation is below this value
# after testing several models, on models which have a grouping near 0, the grouping stops around 0.0003
WINNOW_THRESHOLD = 0.0003


helptext = '''====================
morph_winnow:
To reduce overall file size, this will delete vertices from vertex morphs that move imperceptibly small distances.
This will also delete any vertex morphs that have all of their controlled vertices deleted this way.
The default threshold is 0.0003 units. Trust me it really is imperceptible.
'''

iotext = '''Inputs:  PMX file "[model].pmx"\nOutputs: PMX file "[model]_winnow.pmx"
'''

def apply_morph_remapping(pmx: pmxstruct.Pmx, morph_dellist, morph_shiftmap):
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
					item.idx = newval_from_range_map(item.idx, morph_shiftmap)
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
				it.morph_idx = newval_from_range_map(it.morph_idx, morph_shiftmap)
				i += 1
	return pmx


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

def morph_winnow(pmx: pmxstruct.Pmx, moreinfo=False):
	total_num_verts = 0
	total_vert_dropped = 0
	total_morphs_affected = 0

	morphs_now_empty = []
	
	# for each morph:
	for d,morph in enumerate(pmx.morphs):
		# if not a vertex morph, skip it
		if morph.morphtype != pmxstruct.MorphType.VERTEX: continue
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
		
		pmx = apply_morph_remapping(pmx, morphs_now_empty, rangemap)
		
	return pmx, True
	
def end(pmx, input_filename_pmx):
	# write out
	# output_filename_pmx = "%s_winnow.pmx" % core.get_clean_basename(input_filename_pmx)
	output_filename_pmx = input_filename_pmx[0:-4] + "_winnow.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
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
	print(_SCRIPT_VERSION)
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
