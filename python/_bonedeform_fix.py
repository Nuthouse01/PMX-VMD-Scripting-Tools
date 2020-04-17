# Nuthouse01 - 04/16/2020 - v4.03
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
except ImportError as eee:
	try:
		import nuthouse01_core as core
		import nuthouse01_pmx_parser as pmxlib
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
bonedeform_fix:
This function fixes bone deform order issues. This frequently occurs with "finger curl"-type bones.
Ensure that each bone will have its position/rotation calculated after all bones it inherits from.
This can usually be fixed by reordering bones but this script fixes it by modifying the bone deform layers instead.
Specifically this looks at parents, parial-inherit, and IK target/chains, and ensures that either the downstream bone is lower in the list or has a higher deform layer than its parents.
'''

iotext = '''Inputs:  PMX file "[model].pmx"\nOutputs: PMX file "[model]_bonedeform.pmx"
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

def bonedeform_fix(pmx, moreinfo=False):
	# make a parallel list of the deform layers for each bone so I can work there
	# if I encounter a recursive relationship I will have not touched the acutal PMX and can err and return it unchanged
	deforms = [p[6] for p in pmx[5]]
	modified_bones = set()
	
	def good_deform_relationship(me_idx, parent_idx):
		# "after" means idx>source and layer >= source or idx<source and layer > source
		# note: if somehow me_idx == parent_idx this returns true to prevent infinite looping
		if me_idx < parent_idx:
			if deforms[me_idx] > deforms[parent_idx]:
				return True
		else: # if me_idx >= parent_idx
			if deforms[me_idx] >= deforms[parent_idx]:
				return True
		return False
	
	# loop until nothing changes, or until 1000 iterations (indicates recursive relationship)
	loops = 0
	while loops < 1000:
		loops += 1
		has_changed = False
		for d,bone in enumerate(pmx[5]):
			# decide if this bone has a good deform layer!
			# each bone must deform after its parent
			is_good = True
			is_good &= good_deform_relationship(d, bone[5])
			# each bone must deform after its partial inherit source, if it uses it
			if (bone[14] or bone[15]) and bone[16][1] != 0:
				is_good &= good_deform_relationship(d, bone[16][0])
			# each ik bone must deform after its target and IK chain
			if bone[23]:
				# target
				is_good &= good_deform_relationship(d, bone[24][0])
				for link in bone[24][3]:
					# links
					is_good &= good_deform_relationship(d, link[0])
			# if the relationship is NOT good, then raise the deform layer of this bone
			if not is_good:
				has_changed = True
				modified_bones.add(d)
				deforms[d] += 1
			pass  # end for-loop
		
		# this is the while-loop exit condition
		if not has_changed:
			break
		pass  # end while-loop
	
	# did it break because of recursion error?
	if loops == 1000:
		# if yes, warn & return without changes
		core.MY_PRINT_FUNC("ERROR: recursive inheritance relationship among bones!! You must manually investigate and resolve this issue.")
		core.MY_PRINT_FUNC("Bone deform order not changed")
		return pmx, False
	
	if not modified_bones:
		core.MY_PRINT_FUNC("No changes are required")
		return pmx, False
	
	core.MY_PRINT_FUNC("Modified deform order for %d bones" % len(modified_bones))
	
	if moreinfo:
		deforms_orig = [p[6] for p in pmx[5]]
		for d, (o, n) in enumerate(zip(deforms_orig, deforms)):
			if o != n:
				core.MY_PRINT_FUNC("#: %d    deform: %d --> %d" % (d, o, n))
	
	# now actually apply the changes stored in deforms
	for d,v in enumerate(deforms):
		pmx[5][d][6] = v
	
	return pmx, True

def end(pmx, input_filename_pmx):
	# write out
	# output_filename_pmx = "%s_dispframe.pmx" % core.get_clean_basename(input_filename_pmx)
	output_filename_pmx = input_filename_pmx[0:-4] + "_bonedeform.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=True)
	return None

def main():
	showhelp()
	pmx, name = showprompt()
	pmx, is_changed = bonedeform_fix(pmx)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")

if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 04/16/2020 - v4.03")
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
