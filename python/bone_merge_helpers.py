# Nuthouse01 - 07/24/2020 - v4.63
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
	from ._weight_cleanup import normalize_weights
except ImportError as eee:
	try:
		import nuthouse01_core as core
		import nuthouse01_pmx_parser as pmxlib
		from _weight_cleanup import normalize_weights
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = pmxlib = normalize_weights = None




# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = True

helptext = '''=================================================
bone_merge_helpers:
This is used for transferring the weights of bone X to bone Y, to effectively merge the bones.
Specifically this is intended for merging "helper" bones that inherit only a portion of the rotatation from their parent.
But you can use it to merge any 2 bones if you wish.

Output: model PMX file '[modelname]_weightmerge.pmx'
'''


# stage 1: script(function) to flatten/merge helper bones
def transfer_bone_weights(pmx, to_bone, from_bone, scalefactor=1.0):
	# TODO: test this! ensure that this math is logically correct! not 100% convinced
	if to_bone == from_bone: return
	# !!! WARNING: result is not normal, need to normalize afterward !!!
	# clamp just cuz
	scalefactor = core.clamp(scalefactor, 0.0, 1.0)
	# for each vertex, determine if that vert is controlled by from_bone
	for d,vert in enumerate(pmx[1]):
		weighttype = vert[9]
		w = vert[10]
		if weighttype == 0:
			# BDEF1
			if w[0] == from_bone: # match!
				if scalefactor == 1:
					w[0] = to_bone
				else:
					# TODO: rethink this? test this? not 100% convinced this is correct
					# if the from_bone had 100% weight but only a .5 factor, then this should only move half as much as the to_bone
					# the other half of the weight would come from the parent of the to_bone, i suppose?
					to_bone_parent = pmx[5][to_bone][5]
					if to_bone_parent == -1: # if to_bone is root and has no parent,
						w[0] = to_bone
					else: # if to_parent is valid, convert to BDEF2
						vert[9] = 1
						vert[10] = [to_bone, to_bone_parent, scalefactor]
		elif weighttype in (1, 3):
			# BDEF2, SDEF
			# (b1, b2, b1w)
			# replace the from_bone ref with to_bone, but also need to modify the value
			# a = b1w out, z = b1w in, f = scalefactor
			# a = z*f / (z*f + (1-z))
			if w[0] == from_bone:
				w[0] = to_bone
				z = w[2]
				w[2] = (z*scalefactor) / (z*scalefactor + (1-z))
			elif w[1] == from_bone:
				w[1] = to_bone
				z = 1 - w[2]
				w[2] = 1 - ((z*scalefactor) / (z*scalefactor + (1-z)))
		elif weighttype in (2, 4):
			# BDEF4, QDEF
			# (b1, b2, b3, b4, b1w, b2w, b3w, b4w)
			for i in range(4):
				if w[i] == from_bone and w[i+4] != 0:
					w[i] = to_bone
					w[i+4] = w[i+4] * scalefactor
	# done! no return, modifies PMX list directly
	return None


def is_float(x):
	try:
		v = float(x)
		return True
	except ValueError:
		core.MY_PRINT_FUNC("Please enter a decimal number")
		return False


def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	##################################
	# user flow:
	# ask for the helper bone (to be merged)
	# ask for the destination bone (merged onto)
	# try to infer proper merge factor, if it cannot infer then prompt user
	# then write out to file
	##################################
		
	dest_idx = 0
	while True:
		# any input is considered valid
		s = core.MY_GENERAL_INPUT_FUNC(lambda x: True,
									   ["Please specify the DESTINATION bone that weights will be transferred to.",
										"Enter bone #, JP name, or EN name (names are case sensitive).",
										"Empty input will quit the script."])
		# if empty, leave & do nothing
		if s == "":
			dest_idx = -1
			break
		# then get the morph index from this
		# search JP names first
		dest_idx = core.my_sublist_find(pmx[5], 0, s, getindex=True)
		if dest_idx is not None: break  # did i find a match?
		# search EN names next
		dest_idx = core.my_sublist_find(pmx[5], 1, s, getindex=True)
		if dest_idx is not None: break  # did i find a match?
		# try to cast to int next
		try:
			dest_idx = int(s)
			if 0 <= dest_idx < len(pmx[5]):
				break  # is this within the proper bounds?
			else:
				core.MY_PRINT_FUNC("valid bone indexes are 0-%d" % (len(pmx[5]) - 1))
		except ValueError:
			pass
		core.MY_PRINT_FUNC("unable to find matching bone for name '%s'" % s)
	
	if dest_idx == -1:
		core.MY_PRINT_FUNC("quitting")
		return None
	
	dest_tag = "bone #{} JP='{}' / EN='{}'".format(dest_idx, pmx[5][dest_idx][0], pmx[5][dest_idx][1])
	source_idx = 0
	while True:
		# any input is considered valid
		s = core.MY_GENERAL_INPUT_FUNC(lambda x: True,
									   ["Please specify the SOURCE bone that will be merged onto %s." % dest_tag,
										"Enter bone #, JP name, or EN name (names are case sensitive).",
										"Empty input will quit the script."])
		# if empty, leave & do nothing
		if s == "":
			source_idx = -1
			break
		# then get the morph index from this
		# search JP names first
		source_idx = core.my_sublist_find(pmx[5], 0, s, getindex=True)
		if source_idx is not None: break  # did i find a match?
		# search EN names next
		source_idx = core.my_sublist_find(pmx[5], 1, s, getindex=True)
		if source_idx is not None: break  # did i find a match?
		# try to cast to int next
		try:
			source_idx = int(s)
			if 0 <= source_idx < len(pmx[5]):
				break  # is this within the proper bounds?
			else:
				core.MY_PRINT_FUNC("valid bone indexes are 0-%d" % (len(pmx[5]) - 1))
		except ValueError:
			pass
		core.MY_PRINT_FUNC("unable to find matching bone for name '%s'" % s)
	
	if source_idx == -1:
		core.MY_PRINT_FUNC("quitting")
		return None
	
	# print to confirm
	core.MY_PRINT_FUNC("Merging bone #{} JP='{}' / EN='{}' ===> bone #{} JP='{}' / EN='{}'".format(
		source_idx, pmx[5][source_idx][0], pmx[5][source_idx][1], dest_idx, pmx[5][dest_idx][0], pmx[5][dest_idx][1]
	))
	# now try to infer the merge factor
	
	f = 0.0
	if pmx[5][source_idx][14] and pmx[5][source_idx][16][0] == dest_idx and pmx[5][source_idx][16][1] != 0:
		# if using partial rot inherit AND inheriting from dest_idx AND ratio != 0, use that
		# think this is good, if twistbones exist they should be children of preferred
		f = pmx[5][source_idx][16][1]
	elif pmx[5][source_idx][5] == dest_idx:
		# if they have a direct parent-child relationship, then factor is 1
		f = 1
	else:
		# otherwise, prompt for the factor
		factor_str = core.MY_GENERAL_INPUT_FUNC(is_float, "Unable to infer relationship, please specify a merge factor:")
		if factor_str == "":
			core.MY_PRINT_FUNC("quitting")
			return None
		f = float(factor_str)
		
	# do the actual transfer
	transfer_bone_weights(pmx, dest_idx, source_idx, f)
	
	# run the weight-cleanup function
	dummy = normalize_weights(pmx)
	
	# write out
	output_filename_pmx = input_filename_pmx[0:-4] + "_weightmerge.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 07/24/2020 - v4.63")
	if DEBUG:
		# print info to explain the purpose of this file
		core.MY_PRINT_FUNC(helptext)
		core.MY_PRINT_FUNC("")
		
		main()
		core.pause_and_quit("Done with everything! Goodbye!")
	else:
		try:
			# print info to explain the purpose of this file
			core.MY_PRINT_FUNC(helptext)
			core.MY_PRINT_FUNC("")
			
			main()
			core.pause_and_quit("Done with everything! Goodbye!")
		except (KeyboardInterrupt, SystemExit):
			# this is normal and expected, do nothing and die normally
			pass
		except Exception as ee:
			# if an unexpected error occurs, catch it and print it and call pause_and_quit so the window stays open for a bit
			core.MY_PRINT_FUNC(ee.__class__.__name__, ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
