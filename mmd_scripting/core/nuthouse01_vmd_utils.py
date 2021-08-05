from typing import List, TypeVar, Dict

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_vmd_struct as vmdstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.03 - 7/30/2021"

################################################################################
# this file defines some handy functions that help when manipulating VMDs

BONEFRAME_OR_MORPHFRAME = TypeVar("BONEFRAME_OR_MORPHFRAME", vmdstruct.VmdBoneFrame, vmdstruct.VmdMorphFrame)
def assert_no_overlapping_frames(frames: List[BONEFRAME_OR_MORPHFRAME]) -> List[BONEFRAME_OR_MORPHFRAME]:
	"""
	Remove any overlapping frames from the list: anything with the same name at the same timestep.
	When an overlap is detected, which one is removed is arbitrary!
	How do I want to report this? Not sure.
	
	:param frames: list of VmdBoneFrame obj or VmdMorphFrame obj
	:return: new list of VmdBoneFrame obj or VmdMorphFrame obj with any overlapping frames removed.
	"""
	pairs = set()
	ret = []
	num_collisions = 0
	for frame in frames:
		# generate unique keys from the name+timestep
		key = hash((frame.name, frame.f))
		# has this unique key been used before?
		if key in pairs:
			# if yes, count it but don't keep it
			num_collisions += 1
		else:
			# if no, keep this frame and make it part of the list that is returned
			ret.append(frame)
	if num_collisions:
		core.MY_PRINT_FUNC("WARNING: removed %d overlapping frames (same name, same timestep)" % num_collisions)
	return ret

def parse_vmd_used_dict(frames: List[BONEFRAME_OR_MORPHFRAME], moreinfo=False) -> Dict[str,int]:
	"""
	Generate a dictionary where keys are bones/morphs that are "actually used" and values are # of times they are used.
	"Actually used" means the first frame with a nonzero value and each frame after that. (ignore leading repeated zeros)
	
	:param frames: list of VmdBoneFrame obj or VmdMorphFrame obj
	:param moreinfo: print extra info and stuff
	:return: dict of {name: used_ct} that only includes names of "actually used" bones/morphs
	"""
	if len(frames) == 0:
		return {}
	
	# functions used to judge if a frame is different from the base state
	def is_zero_boneframe(F: vmdstruct.VmdBoneFrame) -> bool:
		return list(F.pos) == [0.0,0.0,0.0] and list(F.rot) == [0.0,0.0,0.0]
	def is_zero_morphframe(F: vmdstruct.VmdMorphFrame) -> bool:
		return F.val == 0.0
	
	if isinstance(frames[0], vmdstruct.VmdBoneFrame):
		is_zero = is_zero_boneframe
	elif isinstance(frames[0], vmdstruct.VmdMorphFrame):
		is_zero = is_zero_morphframe
	else:
		msg = "err: unsupported type to parse_vmd_used_dict(), accepts list of (VmdBoneFrame,VmdMorphFrame) but input is type '%s'" % frames[0].__class__.__name__
		raise ValueError(msg)

	# 1. break the flat list into sublists for each bone or morph. each sublist is sorted by frame number.
	allframes_dict = dictify_framelist(frames)
	# use this dict to count the times things are used
	usedframes_count_dict = {}

	for name, framelist in allframes_dict:
		# 2. for each frame target, count all the leading zeros!
		num_leading_zeros = 0
		for frame in framelist:
			if is_zero(frame): num_leading_zeros += 1
			else:              break
		# all frames after the leading zeros are used!
		num_useful_frames = len(framelist) - num_leading_zeros
		if num_useful_frames:
			usedframes_count_dict[name] = num_useful_frames
	
	# 3, if there are any "used" items then print a statement saying so
	if usedframes_count_dict and moreinfo:
		if isinstance(frames[0], vmdstruct.VmdBoneFrame):
			core.MY_PRINT_FUNC("...unique bones, used/total = %d / %d" % (len(usedframes_count_dict), len(allframes_dict)))
		else:
			core.MY_PRINT_FUNC("...unique morphs, used/total= %d / %d" % (len(usedframes_count_dict), len(allframes_dict)))

	return usedframes_count_dict


def dictify_framelist(frames: List[BONEFRAME_OR_MORPHFRAME]) -> Dict[str, List[BONEFRAME_OR_MORPHFRAME]]:
	"""
	Split a list of boneframes into sublists where they are grouped by bone name. The sublists are
	sorted by frame number. Also supports morph frames.
	
	:param frames: list of all boneframes in the vmd
	:return: dict with keys being bonenames and values being list of frames for that bone in sorted order
	"""
	# first, split into sublists
	retdict = {}
	for t in frames:
		try:
			retdict[t.name].append(t)
		except KeyError:
			retdict[t.name] = [t]
	# then, guarantee each sublist is in sorted order, sorted by frame number
	for sublist in retdict.values():
		sublist.sort(key=lambda x: x.f)
	# return it
	return retdict


def remove_redundant_frames(framelist: List[vmdstruct.VmdBoneFrame], moreinfo=False) -> List[vmdstruct.VmdBoneFrame]:
	"""
	Remove any redundant/excessive frames that don't add anything to the motion. This should be the same as the
	function "Edit > Delete Unused Frame" within MikuMikuDance.
	TODO: change the type hints to allow inputs of any kind of frame type, just for completeness
	:param framelist: input list of frames
	:param moreinfo: if true, then print stuff
	:return: new list of frames, same or fewer than input
	"""
	# if the list has 1 or is empty, nothing to do
	if len(framelist) <= 1:
		return framelist.copy()
	FIRST = framelist[0]
	if isinstance(FIRST, (vmdstruct.VmdBoneFrame, vmdstruct.VmdMorphFrame)):
		# guarantee that they're split by morphname/bonename (if already split this is harmless)
		d = dictify_framelist(framelist)
		list_of_framelists = list(d.values())
	else:
		# guarantee sorted by ascending framenumber cuz why not
		# this DOES modify the input object but it should have already been in sorted order so boo hoo
		framelist.sort(key=lambda x: x.f)
		list_of_framelists = [framelist]
	
	size_before = len(framelist)
	
	# return true if they are the SAME! (except for framenum and interp values)
	def compare_boneframe(x,y):
		return (x.pos == y.pos) and (x.rot == y.rot) and (x.phys_off == y.phys_off)
	def compare_morphframe(x,y):
		return x.val == y.val
	def compare_camframe(x,y):
		return (x.pos == y.pos) and (x.rot == y.rot) and (x.dist == y.dist) and (x.fov == y.fov) and (x.perspective == y.perspective)

	# select which equalfunc to use based on the type of the objects in the list
	if isinstance(FIRST, vmdstruct.VmdBoneFrame):
		equalfunc = compare_boneframe
	elif isinstance(FIRST, vmdstruct.VmdMorphFrame):
		equalfunc = compare_morphframe
	elif isinstance(FIRST, vmdstruct.VmdCamFrame):
		equalfunc = compare_camframe
	else:
		raise ValueError("err: unsupported type '%s' given to remove_redundant_frames()" % str(FIRST.__class__.__name__))
	
	# return as a flattened list
	ultimate_outlist = []
	for this_framelist in list_of_framelists:
		# if there is only 1 frame in this list then i can't possibly remove anything
		if len(this_framelist) <= 1:
			ultimate_outlist.extend(this_framelist)
			continue
			
		outlist = []
		# if either neighbor has a different value, keep it. is it that simple?
		# first, check the first frame:
		if not equalfunc(this_framelist[0], this_framelist[1]):
			# then keep it
			outlist.append(this_framelist[0])
		# second, check all middle frames
		for i in range(1, len(this_framelist)-1):
			this = this_framelist[i]
			prev = this_framelist[i-1]
			after = this_framelist[i+1]
			# if the previous frame has a different value than the current,
			# or if the following frame has a different value than the current,
			if (not equalfunc(this,prev)) or (not equalfunc(this,after)):
				# then keep it
				outlist.append(this)
		# third, check the final frame:
		if not equalfunc(this_framelist[-1], this_framelist[-2]):
			# then keep it
			outlist.append(this_framelist[-1])
		# all of "outlist" is used to extend the flat "ultimate_outlist" which is really returned
		ultimate_outlist.extend(outlist)
	size_after = len(ultimate_outlist)
	diff = size_before - size_after
	if moreinfo:
		core.MY_PRINT_FUNC("Removed {:d} frames ({:.1%}) for being redundant".format(diff, diff/size_before))
	return ultimate_outlist


def fill_missing_boneframes(boneframe_dict: Dict[str, List[vmdstruct.VmdBoneFrame]],
							moreinfo: bool,
							relevant_frames=None,
							) -> Dict[str, List[vmdstruct.VmdBoneFrame]]:
	"""
	Run interpolation so that all bones in boneframe_dict have keyframes at all framenumbers in relevant_framenums.
	Newly-created keyframes have basic linear interpolation.
	Currently only works with boneframes, could plausibly be changed to work with morphframes tho.
	Returns a separate dict, input is unmodified.
	:param boneframe_dict: returned from dictify_framelist()
	:param moreinfo: if true then print some stats
	:param relevant_frames: optional, the set of frame numbers to ensure there are keys at.
	:return: another boneframe_dict, but filled out
	"""
	# boneframe_dict: keys are bonenames, values are sorted lists of frames for that bone
	# now fill in the blanks by using interpolation, if needed
	
	initial_size = sum(len(bonelist) for bonelist in boneframe_dict.values())
	num_append_prepend = 0
	num_interpolate = 0
	
	# relevant_framenums: set of all framenums that any relevent bone is keyed on
	if relevant_frames is None:
		relevant_framenums = set()
	else:
		relevant_framenums = relevant_frames.copy()
	for listofboneframes in boneframe_dict.values():
		for oneframe in listofboneframes:
			relevant_framenums.add(oneframe.f)
	# turn the relevant_framenums set into a sorted list
	relevant_framenums = sorted(list(relevant_framenums))

	new_boneframe_dict = {}
	for key, bonelist in boneframe_dict.items():  # for each bone,
		# start a list of frames generated by interpolation
		new_bonelist = []
		i = 0
		# approach: walk the relevant_framenums list and bonelist in parallel?
		for framenum in relevant_framenums:
			if framenum < bonelist[0].f:  # if the desired framenum is lower than the earliest framenum,
				# then the new frame is a copy of the earliest frame
				num_append_prepend += 1
				newframe = bonelist[0].copy()
				newframe.f = framenum
				new_bonelist.append(newframe)
			elif framenum > bonelist[-1].f:  # if the desired framenum is higher than the last framenum,
				# then the new frame is a copy of the last frame
				num_append_prepend += 1
				newframe = bonelist[-1].copy()
				newframe.f = framenum
				new_bonelist.append(newframe)
			elif framenum == bonelist[i].f:  # if the desired framenum matches the framenum of the next/current frame,
				# then keep it!
				new_bonelist.append(bonelist[i])
				# only increment i when i find a match in the existing frames
				i += 1
			else:
				# otherwise, then i need to create a new frame from interpolating...
				num_interpolate += 1
				# NOTE: remember, the interpolation in frame i is for the transition from i-1 to i
				afterframe = bonelist[i]
				beforeframe = bonelist[i-1]
				# calcualte teh [0.0 - 1.0] value of where between before & after the desired framenum lands
				percentage = (framenum - beforeframe.f) / (afterframe.f - beforeframe.f)
				# extract the bezier interpolation params
				[x_ax, y_ax, z_ax, r_ax, x_ay, y_ay, z_ay, r_ay, x_bx, y_bx, z_bx, r_bx, x_by, y_by, z_by, r_by] = afterframe.interp
				# build bezier curves from them
				xyz_bez = [core.MyBezier((x_ax, x_ay), (x_bx, x_by)),
						   core.MyBezier((y_ax, y_ay), (y_bx, y_by)),
						   core.MyBezier((z_ax, z_ay), (z_bx, z_by)),]
				rot_bez = core.MyBezier((r_ax, r_ay), (r_bx, r_by))
				# for each of the 3 position components,
				output_pos = [0.0, 0.0, 0.0]
				for J in range(3):
					# first: shortcut check! if before = after then dont bother
					if beforeframe.pos[J] == afterframe.pos[J]:
						output_pos[J] = beforeframe.pos[J]
					else:
						# if they are different then i do need to interpolate :(
						# push percentage into the bezier, get new percentage out
						bez_percentage = xyz_bez[J].approximate(percentage)
						# linear interpolate bezier percentage with linear map
						new_xyz = core.linear_map(0, beforeframe.pos[J], 1, afterframe.pos[J], bez_percentage)
						# save the result
						output_pos[J] = new_xyz
				# for the rotation component,
				# first, shortcut check! if before == after then dont bother
				if beforeframe.rot == afterframe.rot:
					euler_slerp = beforeframe.rot.copy()
				else:
					# push percentage into bezier, get new percentage out
					bez_percentage = rot_bez.approximate(percentage)
					# convert to quats, perform slerp, and go back to euler
					quat_before = core.euler_to_quaternion(beforeframe.rot)
					quat_after = core.euler_to_quaternion(afterframe.rot)
					quat_slerp = core.my_slerp(quat_before, quat_after, bez_percentage)
					euler_slerp = core.quaternion_to_euler(quat_slerp)
					euler_slerp = list(euler_slerp)
				
				# build a new boneframe from the available info
				new_boneframe = vmdstruct.VmdBoneFrame(
					name=key,
					f=framenum,
					pos=output_pos,
					rot=euler_slerp,
					phys_off=beforeframe.phys_off,
					# omit the interp data, it doesnt matter
				)
				new_bonelist.append(new_boneframe)
		# now that i am done building a new complete bonelist, replace the old one with the new one
		# boneframe_dict[key] = new_bonelist
		new_boneframe_dict[key] = new_bonelist
		
	# stats
	if moreinfo:
		final_size = sum(len(bonelist) for bonelist in new_boneframe_dict.values())
		if final_size != initial_size:
			core.MY_PRINT_FUNC("Initial FrameDict contained %d frames, added %d" % (initial_size, final_size-initial_size))
			core.MY_PRINT_FUNC("Appended/prepended %d, interpolated %d" % (num_append_prepend, num_interpolate))
	# now it is totally filled out!
	return new_boneframe_dict