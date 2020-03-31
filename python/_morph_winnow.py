# Nuthouse01 - 03/30/2020 - v3.51
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


def begin():
	# print info to explain the purpose of this file
	print("To reduce overall file size, this will delete vertices from vertex morphs that move imperceptibly small amounts.")
	print("This will also delete any vertex morphs that have all of their controlled vertices deleted this way.")
	# print info to explain what inputs it needs
	print("Inputs: PMX file 'model.pmx'")
	# print info to explain what outputs it creates
	print("Outputs: PMX file '[model]_winnow.pmx'")
	print("")
	
	# prompt PMX name
	print("Please enter name of PMX model file:")
	input_filename_pmx = core.prompt_user_filename(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx)
	return pmx, input_filename_pmx

def morph_winnow(pmx):
	print("Please enter the positive threshold for values that will be reduced to 0:")
	print("Threshold of 0 means no change")
	print("Recommended threshold is 0.0001 - 0.0005. Do you really think you can see deformation smaller than this?")
	while True:
		# continue prompting until the user gives valid input
		value_str = input(" Enter scale: ")
		try:
			value = float(value_str)
			break
		except ValueError:
			# if given invalid input, prompt and loop again
			print("invalid number")
	
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
			vert_modify_ct = 0  # indicates how many values can be zeroed out for this vertex
			for v in (1, 2, 3):
				# reduce values to 0 if below threshold
				if -value < vert[v] < value:
					vert_modify_ct += 1
			# if all 3 can be zeroed, then remove this vertex from this vertex morph
			if vert_modify_ct == 3:
				morph[4].pop(i)
				this_vert_dropped += 1
			else:
				i += 1
		if len(morph[4]) == 0:
			# mark newly-emptied vertex morphs for later removal
			morphs_now_empty.append(d)
		# increment tracking variables
		if this_vert_dropped != 0:
			if PRINT_AFFECTED_MORPHS:
				print("JP: '%s'     EN: '%s'" % (morph[0], morph[1]))
			total_morphs_affected += 1
			total_vert_dropped += this_vert_dropped
	
	if total_vert_dropped == 0:
		print("No changes are required")
		return pmx, False
	
	print("Dropped {} / {} = {:.1%} vertices from among {} affected morphs".format(
		total_vert_dropped, total_num_verts, total_vert_dropped/total_num_verts, total_morphs_affected))
	
	if morphs_now_empty and DELETE_NEWLY_EMPTIED_MORPHS:
		print("Deleted %d morphs that had all of their vertices below the threshold" % len(morphs_now_empty))
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
	pmxlib.write_pmx(pmx, output_filename_pmx)
	
	return None

def main():
	pmx, name = begin()
	pmx, is_changed = morph_winnow(pmx)
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
