# Nuthouse01 - 03/14/2020 - v3.01
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


def main():
	# print info to explain the purpose of this file
	print("This script will fix the vertex weights that are weighted twice to the same bone, a minor issue that sometimes happens when merging bones.")
	print("This also normalizes the weights of all vertices.")
	# print info to explain what inputs it needs
	print("Inputs: PMX file 'model.pmx'")
	# print info to explain what outputs it creates
	print("Outputs: PMX file '[model]_weightfix.pmx'")
	print("")
	
	# prompt PMX name
	print("Please enter name of PMX model file:")
	input_filename_pmx = core.prompt_user_filename(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx)

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
			print("invalid weight type for vertex")
	
	print("Fixed weights for {} / {} = {:.1%} of all vertices".format(fix_ct, len(pmx[1]), fix_ct/len(pmx[1])))
	if fix_ct == 0:
		print("No changes are required")
		core.pause_and_quit("Done with everything! Goodbye!")
		return None
	
	# write out
	output_filename_pmx = "%s_weightfix.pmx" % core.get_clean_basename(input_filename_pmx)
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(pmx, output_filename_pmx)
	
	core.pause_and_quit("Done with everything! Goodbye!")
	return None
	

if __name__ == '__main__':
	print("Nuthouse01 - 03/14/2020 - v3.01")
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

