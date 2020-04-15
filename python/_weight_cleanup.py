# Nuthouse01 - 04/13/2020 - v4.00
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
except ImportError as eee:
	print(eee.__class__.__name__, eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	core = pmxlib = None


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


helptext = '''====================
weight_cleanup:
This function will fix the vertex weights that are weighted twice to the same bone, a minor issue that sometimes happens when merging bones.
This also normalizes the weights of all vertices.
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
	fix_ct = 0
	
	# for each vertex:
	for vert in pmx[1]:
		weighttype = vert[9]
		w = vert[10]
		# type0=BDEF1, one bone has 100% weight
		# type1=BDEF2, 2 bones 1 weight (other is implicit)
		# type2=BDEF4, 4 bones 4 weights
		# type3=SDEF, 2 bones 1 weight and 12 values i don't understand.
		# type4=QDEF, 4 bones 4 weights
		# TODO: if a bone has 0 weight, set that bone to index 0
		if weighttype == 0:
			# nothing to be fixed here
			continue
		elif weighttype == 1:
			# only check for and combine duplicates
			if w[0] == w[1] and w[0] != -1:
				w[1] = 0  # second bone is not used
				w[2] = 1.0  # first bone has full weight
				fix_ct += 1
		elif weighttype == 2 or weighttype == 4:
			# bdef4 and qdef handled the same way: check for dupes and also normalize
			usedbones = []
			bones = w[0:4]
			weights = w[4:8]
			is_modified = False
			for i in range(4):
				if (bones[i] != -1) and (bones[i] in usedbones):
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
				fix_ct += 1
		elif weighttype == 3:
			# dont understand, don't touch
			continue
		else:
			core.MY_PRINT_FUNC("invalid weight type for vertex")
	
	if fix_ct == 0:
		core.MY_PRINT_FUNC("No changes are required")
		return pmx, False
	
	core.MY_PRINT_FUNC("Fixed weights for {} / {} = {:.1%} of all vertices".format(fix_ct, len(pmx[1]), fix_ct/len(pmx[1])))
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
	core.MY_PRINT_FUNC("Nuthouse01 - 04/13/2020 - v4.00")
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

