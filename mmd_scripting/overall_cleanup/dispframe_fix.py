import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.00 - 6/10/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


# "全ての親": "motherbone",
# "操作中心": "view cnt",
# "センター": "center",
# "グルーブ": "groove",
# "腰": "waist",

CENTER_FRAME_BONES = ["操作中心",
					  "センター",
					  "グルーブ",
					  "腰"]


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
	input_filename_pmx = core.prompt_user_filename("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=True)
	return pmx, input_filename_pmx

def dispframe_fix(pmx: pmxstruct.Pmx, moreinfo=False):
	# root group: "Root"/"Root"
	# facial group: "表情"/"Exp"
	
	fix_root = 0
	fix_center = 0
	hidden_morphs_removed = 0
	duplicate_entries_removed = 0
	empty_groups_removed = 0
	
	# find the ID# for motherbone... if not found, use whatever is at 0
	motherid = core.my_list_search(pmx.bones, lambda x: x.name_jp == "全ての親")
	if motherid is None:
		motherid = 0
	
	# ensure that "motherbone" and nothing else is in the root:
	for d,frame in enumerate(pmx.frames):
		# only operate on the root group
		if frame.name_jp == "Root" and frame.name_en == "Root" and frame.is_special:
			newframelist = [pmxstruct.PmxFrameItem(is_morph=False,idx=motherid)]
			if frame.items != newframelist:
				# if the itemslist is not exactly only motherbone, make it exactly only motherbone
				frame.items = newframelist
				fix_root += 1
			break
	if fix_root and moreinfo:
		core.MY_PRINT_FUNC("fixing root group")
	
	# fix the contents of the "center"/"センター" group
	# first, find it, or if it does not exist, make it
	centerid = core.my_list_search(pmx.frames, lambda x: x.name_jp == "センター")
	if centerid is None:
		centerid = 2
		newframe = pmxstruct.PmxFrame(name_jp="センター", name_en="Center", is_special=False, items=[])
		pmx.frames.insert(2, newframe)
		fix_center += 1
	# if i set "motherbone" to be root, then remove it from center
	if fix_root:
		removeme = core.my_list_search(pmx.frames[centerid].items, lambda x: x.idx == motherid)
		if removeme is not None:
			pmx.frames[centerid].items.pop(removeme)
	# ensure center contains the proper semistandard contents: view/center/groove/waist
	# find bone IDs for each of these desired bones
	centerframeboneids = [core.my_list_search(pmx.bones, lambda x: x.name_jp == name) for name in CENTER_FRAME_BONES]
	for boneid in centerframeboneids:
		# if this bone does not exist, skip
		if boneid is None: continue
		# if this bone already in center, skip
		if any(item.idx==boneid for item in pmx.frames[centerid].items): continue
		# add an item for this bone to the group
		newitem = pmxstruct.PmxFrameItem(is_morph=False,idx=boneid)
		pmx.frames[centerid].items.append(newitem)
		# do not count moving a bone from root to center
		fix_center += 1
	if fix_center and moreinfo:
		core.MY_PRINT_FUNC("fixing center group")
	
	displayed_morphs = set()
	displayed_bones = set()
	# build sets of all bones/morphs that are in the panels
	# delete bones that are in the panels more than once
	# remove all morphs that are group 0
	for d,frame in enumerate(pmx.frames):  # for each display group,
		i = 0
		while i < len(frame.items):  # for each item in that display group,
			item = frame.items[i]
			if item.is_morph:  # if it is a morph
				# look up the morph
				morph = pmx.morphs[item.idx]
				# figure out what panel of this morph is
				# if it has an invalid panel #, discard it
				if morph.panel == pmxstruct.MorphPanel.HIDDEN:
					frame.items.pop(i)
					hidden_morphs_removed += 1
				# if this is valid but already in the set of used morphs, discard it
				elif item.idx in displayed_morphs:
					frame.items.pop(i)
					duplicate_entries_removed += 1
				# otherwise, add it to set of used morphs
				else:
					displayed_morphs.add(item.idx)
					i += 1
			else:  # if it is a bone
				# if this is already in the set of used bones, delete it
				if item.idx in displayed_bones:
					frame.items.pop(i)
					duplicate_entries_removed += 1
				# otherwise, add it to set of used bones
				else:
					displayed_bones.add(item.idx)
					i += 1
	
	if hidden_morphs_removed:
		core.MY_PRINT_FUNC("removed %d hidden morphs (cause of crashes)" % hidden_morphs_removed)
		# core.MY_PRINT_FUNC("!!! Warning: do not add 'hidden' morphs to the display group! MMD will crash!")
	if duplicate_entries_removed and moreinfo:
		core.MY_PRINT_FUNC("removed %d duplicate bones or morphs" % duplicate_entries_removed)
		
	# have identified which bones/morphs are displayed: now identify which ones are NOT
	# want all bones not already in 'displayed_bones' that are also visible and enabled
	undisplayed_bones = [d for d,bone in enumerate(pmx.bones) if
						(d not in displayed_bones) and bone.has_visible and bone.has_enabled]
	if undisplayed_bones:
		if moreinfo:
			core.MY_PRINT_FUNC("added %d undisplayed bones to new group 'morebones'" % len(undisplayed_bones))
		# add a new frame to hold all bones
		newframelist = [pmxstruct.PmxFrameItem(is_morph=False, idx=x) for x in undisplayed_bones]
		newframe = pmxstruct.PmxFrame(name_jp="morebones", name_en="morebones", is_special=False, items=newframelist)
		pmx.frames.append(newframe)
	
	# build list of which morphs are NOT shown
	# want all morphs not already in 'displayed_morphs' that are not hidden
	undisplayed_morphs = [d for d,morph in enumerate(pmx.morphs) if
						(d not in displayed_morphs) and (morph.panel != pmxstruct.MorphPanel.HIDDEN)]
	if undisplayed_morphs:
		if moreinfo:
			core.MY_PRINT_FUNC("added %d undisplayed morphs to Facials group" % len(undisplayed_morphs))
		newframelist = [pmxstruct.PmxFrameItem(is_morph=True, idx=x) for x in undisplayed_morphs]
		# find morphs group and only add to it
		# should ALWAYS be at index 1 but whatever might as well be extra safe
		idx = core.my_list_search(pmx.frames, lambda x: (x.name_jp == "表情" and x.is_special))
		if idx is not None:
			# concatenate to end of item list
			pmx.frames[idx].items += newframelist
		else:
			core.MY_PRINT_FUNC("ERROR: unable to find semistandard 'expressions' display frame")
	
	# check if there are too many morphs among all frames... if so, trim and remake "displayed morphs"
	# morphs can theoretically be in any frame, they SHOULD only be in the "expressions" frame but people mess things up
	total_num_morphs = 0
	for frame in pmx.frames:
		i = 0
		while i < len(frame.items):
			# if this is a bone, skip it
			if not frame.items[i].is_morph:
				i += 1
			else:
				# if it is a morph, count it
				total_num_morphs += 1
				# if i have already counted too many morphs, pop it
				if total_num_morphs > MAX_MORPHS_IN_DISPLAY:
					frame.items.pop(i)
				else:
					i += 1
	num_morphs_over_limit = max(total_num_morphs - MAX_MORPHS_IN_DISPLAY, 0)
	if num_morphs_over_limit:
		core.MY_PRINT_FUNC("removed %d morphs to stay under the %d morph limit (cause of crashes)" % (num_morphs_over_limit, MAX_MORPHS_IN_DISPLAY))
		core.MY_PRINT_FUNC("!!! Warning: do not add the remaining morphs to the display group! MMD will crash!")
		
	# delete any groups that are empty
	i = 0
	while i < len(pmx.frames):
		frame = pmx.frames[i]
		# if it is empty AND it is not "special" then delete it
		if len(frame.items) == 0 and not frame.is_special:
			pmx.frames.pop(i)
			empty_groups_removed += 1
		else:
			i += 1
	if empty_groups_removed and moreinfo:
		core.MY_PRINT_FUNC("removed %d empty groups" % empty_groups_removed)
		
	overall = num_morphs_over_limit + \
			  fix_center + \
			  empty_groups_removed + \
			  len(undisplayed_bones) + \
			  len(undisplayed_morphs) + \
			  duplicate_entries_removed + \
			  hidden_morphs_removed + \
			  fix_root
	if overall == 0:
		core.MY_PRINT_FUNC("No changes are required")
		return pmx, False
	
	core.MY_PRINT_FUNC("Fixed %d things related to display pane groups" % overall)
	return pmx, True

def end(pmx, input_filename_pmx):
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_dispframe")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
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
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
