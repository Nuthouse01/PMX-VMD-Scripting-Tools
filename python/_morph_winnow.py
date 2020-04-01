# Nuthouse01 - 03/30/2020 - v3.51
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

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
DEBUG = False


# just take a wild guess what this field controls
PRINT_AFFECTED_MORPHS = False


# also try to guess what this does
DELETE_NEWLY_EMPTIED_MORPHS = True


# a vertex is removed from a morph if its total deformation is below this value
WINNOW_THRESHOLD = 0.0003

USE_EUCLIDIAN_DISTANCE = True


helptext = '''morph_winnow:
To reduce overall file size, this will delete vertices from vertex morphs that move imperceptibly small distances.
This will also delete any vertex morphs that have all of their controlled vertices deleted this way.
The default threshold is 0.0003 units. Trust me it really is imperceptible.
'''

iotext = '''Inputs:  PMX file "[model].pmx"\nOutputs: PMX file "[model]_winnow.pmx"
'''

# TODO: run some heuristics with matplotlib, make a distribution graph of deformation distance so i can pick a good threshold!

def begin():
	# print info to explain the purpose of this file
	core.MY_PRINT_FUNC("To reduce overall file size, this will delete vertices from vertex morphs that move imperceptibly small amounts.")
	core.MY_PRINT_FUNC("This will also delete any vertex morphs that have all of their controlled vertices deleted this way.")
	# print info to explain what inputs it needs
	core.MY_PRINT_FUNC("Inputs: PMX file 'model.pmx'")
	# print info to explain what outputs it creates
	core.MY_PRINT_FUNC("Outputs: PMX file '[model]_winnow.pmx'")
	core.MY_PRINT_FUNC("")
	
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX model file:")
	input_filename_pmx = core.prompt_user_filename(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx)
	return pmx, input_filename_pmx

def morph_winnow(pmx, moreinfo=False):
	# core.MY_PRINT_FUNC("Please enter the positive threshold for values that will be reduced to 0:")
	# core.MY_PRINT_FUNC("Threshold of 0 means no change")
	# core.MY_PRINT_FUNC("Recommended threshold is 0.0001 - 0.0005. Do you really think you can see deformation smaller than this?")
	# while True:
	# 	# continue prompting until the user gives valid input
	# 	value_str = input(" Enter scale: ")
	# 	try:
	# 		value = float(value_str)
	# 		break
	# 	except ValueError:
	# 		# if given invalid input, prompt and loop again
	# 		core.MY_PRINT_FUNC("invalid number")
	
	total_num_verts = 0
	total_vert_dropped = 0
	total_morphs_affected = 0

	morphs_now_empty = []
	
	# for each morph:
	for d,morph in enumerate(pmx[6]):
		# if not a vertex morph, skip it
		if morph[3] != 1:
			continue
		# for each vert in this vertex morph:
		i = 0
		this_vert_dropped = 0  # lines dropped from this morph
		total_num_verts += len(morph[4])
		while i < len(morph[4]):
			vert = morph[4][i]
			# determine if it is worth keeping or deleting
			if USE_EUCLIDIAN_DISTANCE:
				# first, calculate euclidian distance
				length = core.my_euclidian_distance(vert[1:4])
				delete_me = (length < WINNOW_THRESHOLD)
			else:
				vert_modify_ct = 0  # indicates how many values can be zeroed out for this vertex
				for v in (1, 2, 3):
					# count if below threshold
					if -WINNOW_THRESHOLD < vert[v] < WINNOW_THRESHOLD:
						vert_modify_ct += 1
				# if all 3 are close to zero, then remove this vertex from this vertex morph
				delete_me = (vert_modify_ct == 3)
			if delete_me:
				morph[4].pop(i)
				this_vert_dropped += 1
			else:
				i += 1
		if len(morph[4]) == 0:
			# mark newly-emptied vertex morphs for later removal
			morphs_now_empty.append(d)
		# increment tracking variables
		if this_vert_dropped != 0:
			if moreinfo:
				core.MY_PRINT_FUNC("JP: '%s'     EN: '%s'" % (morph[0], morph[1]))
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
		
		# actually delete the morphs from the list
		for f in reversed(morphs_now_empty):
			pmx[6].pop(f)

		# frames:
		for d, frame in enumerate(pmx[7]):
			i = 0
			while i < len(frame[3]):
				item = frame[3][i]
				# if this item is a bone, skip it
				if not item[0]:
					i += 1
				else:
					# if this is one of the morphs being deleted, delete it here too. otherwise remap.
					if binary_search_isin(item[1], morphs_now_empty):
						frame[3].pop(i)
					else:
						item[1] = newval_from_range_map(item[1], rangemap)
						i += 1
		
		# group/flip morphs:
		for d, morph in enumerate(pmx[6]):
			# group/flip = 0/9
			if morph[3] not in (0,9):
				continue
			i = 0
			while i < len(morph[4]):
				# if this is one of the morphs being deleted, delete it here too. otherwise remap.
				if binary_search_isin(morph[4][i][0], morphs_now_empty):
					morph[4].pop(i)
				else:
					morph[4][i][0] = newval_from_range_map(morph[4][i][0], rangemap)
					i += 1
		
	return pmx, True
	
def end(pmx, input_filename_pmx):
	# write out
	output_filename_pmx = "%s_winnow.pmx" % core.get_clean_basename(input_filename_pmx)
	# output_filename_pmx = input_filename_pmx[0:-4] + "_translate.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx)
	
	return None

def main():
	pmx, name = begin()
	pmx, is_changed = morph_winnow(pmx, PRINT_AFFECTED_MORPHS)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")


if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 03/30/2020 - v3.51")
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
