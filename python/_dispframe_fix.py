# Nuthouse01 - 03/28/2020 - v3.5
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


# UTTERLY IMPOSSIBLE to get multiple frames containing morphs, they are always collapsed into one

def begin():
	# print info to explain the purpose of this file
	print("This file fixes issues with display frames. Removes morphs that would crash MMD, adds any morphs/bones that aren't already added.")
	# print info to explain what inputs it needs
	print("Inputs: PMX file 'model.pmx'")
	# print info to explain what outputs it creates
	print("Outputs: PMX file '[model]_dispframe.pmx'")
	print("")
	
	# prompt PMX name
	print("Please enter name of PMX model file:")
	input_filename_pmx = core.prompt_user_filename(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx)
	return pmx, input_filename_pmx

def dispframe_fix(pmx):
	# root group: "Root"/"Root"
	# facial group: "表情"/"Exp"
	
	# PROBLEM: if there are too many items in a group then MMD will crash????!? is it per group or total?
	# 419 crash
	# 270 crash
	# 238 pass
	# 238*2 pass
	
	fix_root = 0
	hidden_morphs_removed = 0
	duplicate_entries_removed = 0
	empty_groups_removed = 0
	
	# find the ID# for motherbone... if not found, use whatever is at 0
	motherid = 0
	for d,bone in enumerate(pmx[5]):
		if bone[0] == "全ての親":
			motherid = d
			break
	# ensure that "motherbone" and nothing else is in the root:
	for d,frame in enumerate(pmx[7]):
		# only operate on the root group
		if frame[0] == "Root" and frame[1] == "Root":
			newframelist = [[0,motherid]]
			if frame[3] != newframelist:
				frame[3] = newframelist
				fix_root += 1
			break
	if fix_root:
		print("fixing root group")
	
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
		print("!!! removed %d hidden morphs" % hidden_morphs_removed)
	if duplicate_entries_removed:
		print("removed %d duplicate bones or morphs" % duplicate_entries_removed)
		
	# have identified which bones/morphs are displayed: now identify which ones are NOT
	undisplayed_bones = []
	for d,bone in enumerate(pmx[5]):
		# if this bone is already displayed, skip
		if d in displayed_bones:
			continue
		# if this bone is visible and is enabled, add it to the set
		if bone[10] and bone[11]:
			undisplayed_bones.append(d)
	undisplayed_morphs = []
	for d,morph in enumerate(pmx[6]):
		# if this morph is already displayed, skip
		if d in displayed_morphs:
			continue
		# if this morph is not a hidden group, add it to the set
		if 1 <= morph[2] <= 4:
			undisplayed_morphs.append(d)

	if undisplayed_bones:
		print("added %d undisplayed bones to new group 'morebones'" % len(undisplayed_bones))
		# add a new frame to hold all bones
		newframelist = [[0, x] for x in undisplayed_bones]
		newframe = ["morebones","morebones",0,newframelist]
		pmx[7].append(newframe)
	if undisplayed_morphs:
		newframelist = [[1, x] for x in undisplayed_morphs]
		# if NEW_MORPH_GROUP:
		# 	print("added %d undisplayed morphs to new group 'moremorphs'" % len(undisplayed_morphs))
		# 	# TODO: add to new group, if i can make that work?
		# 	newframe = ["moremorphs","moremorphs",0,newframelist]
		# 	pmx[7].append(newframe)
		# else:
		print("added %d undisplayed morphs to Facials group" % len(undisplayed_morphs))
		# or, just add to bottom of morphs group
		# find morphs group and only operate on it
		for frame in pmx[7]:
			if frame[0] == "表情" and frame[1] == "Exp":
				# concatenate to end of list
				frame[3] += newframelist
				break
	
	# TODO: if a group has more than 240 entries, split it!
	#
	
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
		print("removed %d empty groups" % empty_groups_removed)
	
	# figure out how to add a second group for morphs that MMD will actually display????
	# add missing non-group-0 morphs to a second group (if i get it working) or to the facials group if i must
	
	overall = empty_groups_removed + len(undisplayed_bones) + len(undisplayed_morphs) + duplicate_entries_removed + hidden_morphs_removed + fix_root
	if overall == 0:
		print("No changes are required")
		return pmx, False
	
	# print("Fixed %d things related to display pane groups" % overall)
	return pmx, True

def end(pmx, input_filename_pmx):
	# write out
	output_filename_pmx = "%s_dispframe.pmx" % core.get_clean_basename(input_filename_pmx)
	# output_filename_pmx = input_filename_pmx[0:-4] + "_translate.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(pmx, output_filename_pmx)
	
	return None

def main():
	pmx, name = begin()
	pmx, is_changed = dispframe_fix(pmx)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")

if __name__ == '__main__':
	print("Nuthouse01 - 03/28/2020 - v3.5")
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
