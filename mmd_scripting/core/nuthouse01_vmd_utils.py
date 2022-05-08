from typing import List, TypeVar, Dict, Iterable, Tuple

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_vmd_struct as vmdstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.04 - 8/19/2021"

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
		pairs.add(key)
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

	for name, framelist in allframes_dict.items():
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
		relevant_framenums = set(relevant_frames)
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
				x_ax, x_ay, x_bx, x_by = afterframe.interp_x
				y_ax, y_ay, y_bx, y_by = afterframe.interp_y
				z_ax, z_ay, z_bx, z_by = afterframe.interp_z
				r_ax, r_ay, r_bx, r_by = afterframe.interp_r
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


# Declare type variable so I can say "whatever input type is, it matches the output type"
VMD_BONEMORPHCAM_FRAME = TypeVar('VMD_BONEMORPHCAM_FRAME', vmdstruct.VmdBoneFrame, vmdstruct.VmdMorphFrame, vmdstruct.VmdCamFrame)
def fill_missing_boneframes_new(all_frame_list: List[VMD_BONEMORPHCAM_FRAME],
								desired_frames: Iterable[int],
								moreinfo=False,
								enable_append_prepend=True,
								fix_fov=True) -> List[VMD_BONEMORPHCAM_FRAME]:
	"""
	Take a list of bone/morph/camframes, then fill it out as much as I want, and return another flat list.
	This requires that you specify the frames you want keys at.
	By default it will prepend/append frames, but this can be turned off.
	After running this, any interpolation curves on the frames will/might become invalid, depending on how it is used.
	"""
	# now fill in the blanks by using interpolation, if needed
	
	initial_size = len(all_frame_list)
	num_append = 0
	num_prepend = 0
	num_interpolate = 0
	
	if isinstance(all_frame_list[0], (vmdstruct.VmdBoneFrame, vmdstruct.VmdMorphFrame)):
		# if this list is bones/morphs, then separate them via 'dictify' and also make sure they're sorted
		processed_so_far = 0
		all_frame_list = assert_no_overlapping_frames(all_frame_list)
		framedict = dictify_framelist(all_frame_list)
		all_frames_out = []
		for key, bonelist in framedict.items():  # for each bone,
			new_bonelist, (i, p, a) = _fill_missing_boneframes_new(bonelist, desired_frames,
																   enable_interp=True,
																   enable_append=enable_append_prepend,
																   enable_prepend=enable_append_prepend)
			# accumulate results for this bone/morph into a flat list
			all_frames_out.extend(new_bonelist)
			# accumulate stats
			num_append += a
			num_prepend += p
			num_interpolate += i
			# print progress thingy
			processed_so_far += len(bonelist)
			core.print_progress_oneline(processed_so_far / initial_size)
	else:
		# if this list is camframes, then make sure it's sorted
		all_frame_list.sort(key=lambda x: x.f)
		all_frames_out, (i, p, a) = _fill_missing_boneframes_new(all_frame_list, desired_frames,
															     enable_interp=True,
															     enable_append=enable_append_prepend,
															     enable_prepend=enable_append_prepend,
																 fix_fov=fix_fov)
		# accumulate stats
		num_append += a
		num_prepend += p
		num_interpolate += i
	
	# stats
	if moreinfo:
		final_size = len(all_frames_out)
		if final_size != initial_size:
			core.MY_PRINT_FUNC("Initial FrameList contained %d frames -> new size %d (added %d, increase %.2f%%)" %
							   (initial_size, final_size, final_size-initial_size, 100*final_size/initial_size))
			core.MY_PRINT_FUNC("(Prepend %d, append %d, interpolate %d)" %
							   (num_prepend, num_append, num_interpolate))
	# now it is totally filled out!
	return all_frames_out


def _fill_missing_boneframes_new(framelist: List[VMD_BONEMORPHCAM_FRAME],
								 desired_frames: Iterable[int],
								 enable_interp=True,
								 enable_append=True,
								 enable_prepend=True,
								 fix_fov=True,
								 ) -> Tuple[List[VMD_BONEMORPHCAM_FRAME], Tuple[int,int,int]]:
	"""
	Take a list of frames of one type, for one bone/morph/camera. It should already be sorted.
	Also take a list/set of the desired frame numbers.
	Return a new list of frames, plus values for number interpolated/appended/prepended.
	:param framelist:
	:param desired_frames:
	:param enable_interp:
	:param enable_append:
	:param enable_prepend:
	:param fix_fov:
	:return: list of boneframes, but filled out
	"""

	# desired_frames MUST be a superset of all the frame numbers in framelist:
	desired_frames = set(desired_frames)  # convert list to set
	desired_frames.update([foo.f for foo in framelist])  # compute union of input with frame numbers in framelist
	desired_frames = sorted(list(desired_frames))  # convert set to list, and sort
	
	# stats
	num_append = 0
	num_prepend = 0
	num_interpolate = 0
	
	# check the type of frames it contains
	BONE = 0
	MORPH = 1
	CAM = 2
	if isinstance(framelist[0], vmdstruct.VmdBoneFrame):
		frametype = BONE
	elif isinstance(framelist[0], vmdstruct.VmdMorphFrame):
		frametype = MORPH
	elif isinstance(framelist[0], vmdstruct.VmdCamFrame):
		frametype = CAM
	else:
		raise ValueError("unrecognized input type")
	
	# start a list of frames generated by interpolation
	new_framelist = []
	
	# # approach: walk the relevant_framenums list and framelist in parallel?
	# i should use an iterator for the desired frame number cuz that is strictly increasing
	# but i need to use an index for the actual frame, because i need to be able to look backward for interp
	i = 0
	# manually create an iterator over the desired frames
	framenum_iter = iter(desired_frames)
	# manually implement a for-loop
	# "for framenum in desired_frames:"
	while True:
		try:
			framenum = next(framenum_iter)
		except StopIteration:
			break  # if StopIteration is raised, break from loop. i'm done. there are no more desired frames.
		
		if framenum < framelist[0].f:           # if the desired framenum is lower than the earliest framenum,
			if enable_prepend:                  # and if i'm allowed to prepend frames on the beginning,
				newframe = framelist[0].copy()  # then the new frame is a copy of the earliest frame,
				newframe.f = framenum           # except that it has a different framenumber.
				new_framelist.append(newframe)
				num_prepend += 1
		elif framenum > framelist[-1].f:         # if the desired framenum is higher than the last framenum,
			if enable_append:                    # and if i'm allowed to append frames to the end,
				newframe = framelist[-1].copy()  # then the new frame is a copy of the last frame,
				newframe.f = framenum            # except that it has a different framenumber.
				new_framelist.append(newframe)
				num_append += 1
		elif framenum == framelist[i].f:        # if the desired framenum MATCHES the framenum of the next/current frame,
			new_framelist.append(framelist[i])  # then keep it!
			i += 1  # only increment i when i find a match in the existing frames
		else:
			# otherwise, then i need to create a new frame from interpolating...
			# this is the hard part...
			if enable_interp:
				# NOTE: remember, the interpolation in frame i is for the transition from i-1 to i
				afterframe = framelist[i]
				beforeframe = framelist[i - 1]
				#############
				# part 1: build the bezier curves
				bez_xyz = bez_rot = bez_dist = bez_fov = None
				if frametype == BONE or frametype == CAM:
					x_ax, x_ay, x_bx, x_by = afterframe.interp_x
					y_ax, y_ay, y_bx, y_by = afterframe.interp_y
					z_ax, z_ay, z_bx, z_by = afterframe.interp_z
					bez_xyz = [core.MyBezier((x_ax, x_ay), (x_bx, x_by)),
							   core.MyBezier((y_ax, y_ay), (y_bx, y_by)),
							   core.MyBezier((z_ax, z_ay), (z_bx, z_by))]
					r_ax, r_ay, r_bx, r_by = afterframe.interp_r
					bez_rot = core.MyBezier((r_ax, r_ay), (r_bx, r_by))
				if frametype == CAM:
					dist_ax, dist_ay, dist_bx, dist_by = afterframe.interp_dist
					bez_dist = core.MyBezier((dist_ax, dist_ay), (dist_bx, dist_by))
					fov_ax, fov_ay, fov_bx, fov_by = afterframe.interp_fov
					bez_fov = core.MyBezier((fov_ax, fov_ay), (fov_bx, fov_by))
					# for cam only, check and warn if there is large rotation!
					delta = [abs(b - a) for b, a in zip(beforeframe.rot, afterframe.rot)]
					if max(delta) > 160:
						core.MY_PRINT_FUNC("WARNING: f %d-%d=%d, cam-frame interpolation has massive deltas!!" % (beforeframe.f, afterframe.f, afterframe.f-beforeframe.f))
						core.MY_PRINT_FUNC("         [%.3f, %.3f, %.3f]" % (delta[0], delta[1], delta[2]))
				
				#############
				# part 2: loop over each framenum between before/after
				#		do the thing
				#		inc
				#		check & break
				while True:
					num_interpolate += 1
					#############
					# part 3: calcualte teh [0.0 - 1.0] value of where between before & after the desired framenum lands
					percentage = (framenum - beforeframe.f) / (afterframe.f - beforeframe.f)
					#############
					# part 4: evaluate the beziers
					interp_val = interp_euler = interp_pos = interp_fov = interp_dist = None
					if frametype == MORPH:
						# morph frames dont use bezier interp, only linear interp
						interp_val = core.linear_map(0, beforeframe.val, 1, afterframe.val, percentage)
					if frametype == CAM or frametype == BONE:
						# for each of the 3 position components,
						interp_pos = [0.0, 0.0, 0.0]
						for J in range(3):
							# first: shortcut check! if before = after then dont bother
							if beforeframe.pos[J] == afterframe.pos[J]:
								interp_pos[J] = beforeframe.pos[J]
							else:
								# if they are different then i do need to interpolate :(
								# push percentage into the bezier, get new percentage out
								bez_percentage = bez_xyz[J].approximate(percentage)
								# linear interpolate bezier percentage with linear map
								new_xyz = core.linear_map(0, beforeframe.pos[J], 1, afterframe.pos[J], bez_percentage)
								# save the result
								interp_pos[J] = new_xyz
					if frametype == BONE:
						# for the rotation component,
						# first, shortcut check! if before == after then dont bother
						if beforeframe.rot == afterframe.rot:
							interp_euler = beforeframe.rot.copy()
						else:
							# push percentage into bezier, get new percentage out
							bez_percentage = bez_rot.approximate(percentage)
							# convert to quats, perform slerp, and go back to euler
							quat_before = core.euler_to_quaternion(beforeframe.rot)
							quat_after = core.euler_to_quaternion(afterframe.rot)
							quat_slerp = core.my_slerp(quat_before, quat_after, bez_percentage)
							interp_euler = list(core.quaternion_to_euler(quat_slerp))
					if frametype == CAM:
						# for the rotation component,
						# first, shortcut check! if before == after then dont bother
						if beforeframe.rot == afterframe.rot:
							interp_euler = beforeframe.rot.copy()
						else:
							# # for cam only, check and warn if there is large rotation!
							# delta = [abs(b-a) for b,a in zip(beforeframe.rot, afterframe.rot)]
							# if max(delta) > 160:
							# 	core.MY_PRINT_FUNC("WARNING: cam-frame interpolation has large deltas, not sure if i'm doing this right!")
							# push percentage into bezier, get new percentage out
							bez_percentage = bez_rot.approximate(percentage)
							# TODO: verify whether cam interpolation uses piecewise linear or quaternions...?
							# convert to quats, perform slerp, and go back to euler
							quat_before = core.euler_to_quaternion(beforeframe.rot)
							quat_after = core.euler_to_quaternion(afterframe.rot)
							quat_slerp = core.my_slerp(quat_before, quat_after, bez_percentage)
							interp_euler = list(core.quaternion_to_euler(quat_slerp))
						# then, interpolate FOV and distance as well
						if beforeframe.fov == afterframe.fov:
							interp_fov = beforeframe.fov
						else:
							bez_percentage = bez_fov.approximate(percentage)
							interp_fov = core.linear_map(0, beforeframe.fov, 1, afterframe.fov, bez_percentage)
							if fix_fov:
								interp_fov = round(interp_fov)  # note: fov must be an INT before saving to vmd
						if beforeframe.dist == afterframe.dist:
							interp_dist = beforeframe.dist
						else:
							bez_percentage = bez_dist.approximate(percentage)
							interp_dist = core.linear_map(0, beforeframe.dist, 1, afterframe.dist, bez_percentage)
					################
					# part 5: build a new frame from the computed values
					newframe = None
					if frametype == MORPH:
						newframe = vmdstruct.VmdMorphFrame(name=beforeframe.name, f=framenum, val=interp_val)
					if frametype == BONE:
						# omit the interp data, it doesnt matter, use default linear
						newframe = vmdstruct.VmdBoneFrame(name=beforeframe.name, f=framenum, pos=interp_pos,
														  rot=interp_euler, phys_off=beforeframe.phys_off)
					if frametype == CAM:
						# omit the interp data, it doesnt matter, use default linear
						newframe = vmdstruct.VmdCamFrame(f=framenum, pos=interp_pos, rot=interp_euler, fov=interp_fov,
														 dist=interp_dist, perspective=beforeframe.perspective)
					new_framelist.append(newframe)
					###################
					# part 6: increment framenum
					try:
						framenum = next(framenum_iter)
					except StopIteration:
						break  # if StopIteration is raised, break from loop. i'm done. there are no more desired frames.
					###################
					# part 7: stop condition
					# when framenum reaches afterframe, then i'm done. also copy the logic from 'copy' branch above.
					if framenum == afterframe.f:  # if the desired framenum MATCHES the framenum of the next/current frame,
						new_framelist.append(afterframe)  # then keep it!
						i += 1  # only increment i when i find a match in the existing frames
						break  # then break out of the "interpolate from before to after" loop
	
	# stats
	return new_framelist, (num_interpolate, num_prepend, num_append)
