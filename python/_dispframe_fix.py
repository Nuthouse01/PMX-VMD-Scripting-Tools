# Nuthouse01 - 04/17/2020 - v4.04
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
DEBUG = True


# if MMD has 256+ morphs among all display groups, it will crash
MAX_MORPHS_IN_DISPLAY = 250

# UTTERLY IMPOSSIBLE to get multiple frames containing morphs, they are always collapsed into one

helptext = '''====================
dispframe_fix:
This function fixes issues with display frames.
Remove "hidden" morphs that would crash MMD (because they are not in either eye/brow/lip/other).
Ensure there are <250 morphs among all display frames, because that will crash MMD as well.
This will also ensure that "motherbone" is only bone in "root" frame, add any morphs/bones that aren't already in frames, delete duplicate entries, and delete empty frames.
'''

iotext = '''Inputs:  PMX file "[model].pmx"\nOutputs: PMX file "[model]_dispframe.pmx"
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

def dispframe_fix(pmx, moreinfo=False):
	# root group: "Root"/"Root"
	# facial group: "表情"/"Exp"
	
	fix_root = 0
	hidden_morphs_removed = 0
	duplicate_entries_removed = 0
	empty_groups_removed = 0
	
	# find the ID# for motherbone... if not found, use whatever is at 0
	motherid = core.my_sublist_find(pmx[5], 0, "全ての親", getindex=True)
	if motherid is None:
		motherid = 0
	
	# ensure that "motherbone" and nothing else is in the root:
	for d,frame in enumerate(pmx[7]):
		# only operate on the root group
		if frame[0] == "Root" and frame[1] == "Root" and frame[2]:
			newframelist = [[0,motherid]]
			if frame[3] != newframelist:
				frame[3] = newframelist
				fix_root += 1
			break
	if fix_root:
		core.MY_PRINT_FUNC("fixing root group")
	
	displayed_morphs = set()
	displayed_bones = set()
	# build sets of all bones/morphs that are in the panels
	# delete bones that are in the panels more than once
	# remove all morphs that are group 0
	for d,frame in enumerate(pmx[7]):
		i = 0
		while i < len(frame[3]):
			item = frame[3][i]
			if item[0]:  # if it is a morph
				# figure out what panel of this morph is
				panel = pmx[6][item[1]][2]
				# if this is an invalid panel #, delete it here
				if not 1 <= panel <= 4:
					frame[3].pop(i)
					hidden_morphs_removed += 1
				# if this is already in the set of used morphs, delete it
				elif item[1] in displayed_morphs:
					frame[3].pop(i)
					duplicate_entries_removed += 1
				# otherwise, add it to set of used morphs
				else:
					displayed_morphs.add(item[1])
					i += 1
			else:  # if it is a bone
				# if this is already in the set of used bones, delete it
				if item[1] in displayed_bones:
					frame[3].pop(i)
					duplicate_entries_removed += 1
				# otherwise, add it to set of used bones
				else:
					displayed_bones.add(item[1])
					i += 1
	
	if hidden_morphs_removed:
		core.MY_PRINT_FUNC("removed %d hidden morphs (cause of crashes)" % hidden_morphs_removed)
		core.MY_PRINT_FUNC("!!! Warning: do not add 'hidden' morphs to the display group! MMD will crash!")
	if duplicate_entries_removed:
		core.MY_PRINT_FUNC("removed %d duplicate bones or morphs" % duplicate_entries_removed)
		
	# have identified which bones/morphs are displayed: now identify which ones are NOT
	undisplayed_bones = []
	for d,bone in enumerate(pmx[5]):
		# if this bone is already displayed, skip
		if d in displayed_bones:
			continue
		# if this bone is visible and is enabled, add it to the set
		if bone[10] and bone[11]:
			undisplayed_bones.append(d)
	if undisplayed_bones:
		core.MY_PRINT_FUNC("added %d undisplayed bones to new group 'morebones'" % len(undisplayed_bones))
		# add a new frame to hold all bones
		newframelist = [[0, x] for x in undisplayed_bones]
		newframe = ["morebones","morebones",0,newframelist]
		pmx[7].append(newframe)
	
	# build list of which morphs are NOT shown
	undisplayed_morphs = []
	for d,morph in enumerate(pmx[6]):
		# if this morph is already displayed, skip
		if d in displayed_morphs:
			continue
		# if this morph is not a hidden group, add it to the set
		if 1 <= morph[2] <= 4:
			undisplayed_morphs.append(d)
	if undisplayed_morphs:
		newframelist = [[1, x] for x in undisplayed_morphs]
		core.MY_PRINT_FUNC("added %d undisplayed morphs to Facials group" % len(undisplayed_morphs))
		# find morphs group and only add to it
		for frame in pmx[7]:
			if frame[0] == "表情" and frame[1] == "Exp" and frame[2]:
				# concatenate to end of list
				frame[3] += newframelist
				break
	
	# check if there are too many morphs... if so, trim and remake "displayed morphs"
	total_num_morphs = 0
	for frame in pmx[7]:
		# find the facials group
		i = 0
		while i < len(frame[3]):
			item = frame[3][i]
			# if this is a bone, skip it
			if not item[0]:
				i += 1
			else:
				# if it is a morph, count it
				total_num_morphs += 1
				# if i have already counted too many morphs, pop it
				if total_num_morphs > MAX_MORPHS_IN_DISPLAY:
					frame[3].pop(i)
				else:
					i += 1
	num_morphs_over_limit = max(total_num_morphs - MAX_MORPHS_IN_DISPLAY, 0)
	if num_morphs_over_limit:
		core.MY_PRINT_FUNC("removed %d morphs to stay under the %d morph limit (cause of crashes)" % (num_morphs_over_limit, MAX_MORPHS_IN_DISPLAY))
		core.MY_PRINT_FUNC("!!! Warning: do not add the remaining morphs to the display group! MMD will crash!")
		
	# delete any groups that are empty
	i = 0
	while i < len(pmx[7]):
		frame = pmx[7][i]
		# if it is empty AND it is not "special" then delete it
		if frame[2] == 0 and len(frame[3]) == 0:
			pmx[7].pop(i)
			empty_groups_removed += 1
		else:
			i += 1
	if empty_groups_removed:
		core.MY_PRINT_FUNC("removed %d empty groups" % empty_groups_removed)
		
	overall = num_morphs_over_limit + empty_groups_removed + len(undisplayed_bones) + len(undisplayed_morphs) + duplicate_entries_removed + hidden_morphs_removed + fix_root
	if overall == 0:
		core.MY_PRINT_FUNC("No changes are required")
		return pmx, False
		
	# print("Fixed %d things related to display pane groups" % overall)
	return pmx, True

def end(pmx, input_filename_pmx):
	# write out
	# output_filename_pmx = "%s_dispframe.pmx" % core.get_clean_basename(input_filename_pmx)
	output_filename_pmx = input_filename_pmx[0:-4] + "_dispframe.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=True)
	return None

def main():
	showhelp()
	pmx, name = showprompt()
	pmx, is_changed = dispframe_fix(pmx)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")

if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 04/17/2020 - v4.04")
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
