from typing import List, Dict, Set

from mmd_scripting import WIP_vmd_animation_smoothing
from mmd_scripting import nuthouse01_core as core
from mmd_scripting import nuthouse01_pmx_parser as pmxlib
from mmd_scripting import nuthouse01_pmx_struct as pmxstruct
from mmd_scripting import nuthouse01_vmd_parser as vmdlib
from mmd_scripting import nuthouse01_vmd_struct as vmdstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - 7/12/2021 - v6.01"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
# Special thanks to "tERBO" for making me overhaul & breathe new life into this old, forgotten code!
#####################

# NOTE: this won't work for normal arm IK the way you think it will, i think? because arm IK is normally an append-thing

# NOTE: if you are taking positions from one model and forcing them onto another model, it's not gonna be a perfect solution
# scaling or manual adjustment will probably be required, which kinda defeats the whole point of this script...

# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = True


# if this is true, an IK-disp frame will be created that enables the IK-following
# if this is false, when this VMD is loaded the IK bones will be moved but the legs won't follow them
# you will need to manually turn on IK for these bones
INCLUDE_IK_ENABLE_FRAME = True


helptext = '''=================================================
make_ik_from_vmd:
This script runs forward kinematics for the bones in model X to calculate how they will move during a dance, and find the resulting absolute world-positions of some specified bones.
This will then run that same dance on model Y, and calculate VMD frames to move specified IK bones to those absolute world-positions.
Model X and model Y can be the same model, but is that really useful?
This was originally designed for dances that do not use leg-IK frames, and instead control the legs by controlling the actual leg-knee-foot angles (like Conqueror by IA). If a non-IK dance works well for model X but not for model Y (feet clipping thru floor, etc), this would let you copy the foot positions from model X onto model Y.
However, this can also work to generate arm-IK frames when you have a motion that controls the shoulder-arm-elbow bones. If a dance for model X has the model holding their hand on a stationary object, but model Y has different proportions and their hand is no longer stationary, this script will fix that problem.
** In practice, this highly specific and not generally very useful... this file is kept around for historical reasons. And because I think the forward kinematics math is pretty cool.
The output is a VMD that should be loaded into MMD *after* the original dance VMD is loaded.

This requires at least 1 PMX model and a VMD motion to run.
Outputs: VMD file '[dancename]_ik_from_[modelname].vmd' that contains only the IK frames for the dance
'''


class ForwardKinematicsBone:
	def __init__(self, name, idx, deform, pos, descendents, ancestors,
				 has_inherit_rot, has_inherit_trans, inherit_parent_name, inherit_ratio):
		self.name = name
		self.idx = idx
		self.deform = deform
		self._pos_original = pos.copy()
		self.pos = pos.copy()  # X Y Z position vector!
		self.rot = [1.0, 0.0, 0.0, 0.0]  # W X Y Z quaternion!
		self.descendents = descendents  # children & children's children & etc, indices!
		self.ancestors = ancestors
		self.has_inherit_rot = has_inherit_rot
		self.has_inherit_trans = has_inherit_trans
		self.inherit_parent_name = inherit_parent_name
		self.inherit_ratio = inherit_ratio
	def reset(self):
		self.pos = self._pos_original.copy()
		self.rot = [1.0, 0.0, 0.0, 0.0]
		

# todo: move this to the same place as 'dictify_framelist'
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
		d = WIP_vmd_animation_smoothing.dictify_framelist(framelist)
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
	
# todo: move this to the same place as 'dictify_framelist'
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


def run_forward_kinematics_for_one_timestep(frames: Dict[str, vmdstruct.VmdBoneFrame],
											boneorder: List[ForwardKinematicsBone]) -> List[ForwardKinematicsBone]:
	"""
	Run forward kinematics to simulate the resulting positions of all bones in the model! Only operates on one
	timestep at a time, i.e. all frames at t=173. Returns a copy of "boneorder" list but filled with rotation/position
	data.
	:param frames: dict of {bonename: vmdboneframe} for each boneframe at a specific timestep
	:param boneorder: list created by predetermine_bone_deform_order()
	:return: same list passed in but .pos and .rot members have been modified
	"""
	# reset each item
	# NOTE: it is WAY faster to re-use the structure and just call 'reset' on each pass than it is to create a pure
	# copy of the list to return each time
	for b in boneorder:
		b.reset()
	# NOTE: according to previous implementation, i NEED to do this backwards, start from leaves & work inward.
	# not entirely sure why but i trust my past self.
	for currbone in reversed(boneorder):
		# first, get the frame for this bone, if it exists
		if currbone.name in frames:
			frame_pos = frames[currbone.name].pos
			frame_rot = core.euler_to_quaternion(frames[currbone.name].rot)
		else:
			# if this bone is not keyed in this timestep, then skip it entirely
			continue
		
		# if this bone has partial-inherit-rotate or partial-inherit-translate, then look up the name of the bone
		# it comes from, & get the frame for that bone, & multiply by the ratio to get how much it gets from that
		# source, & add that amount into the amount i got from the frame dict!
		if (currbone.has_inherit_rot or currbone.has_inherit_trans) and currbone.inherit_ratio != 0:
			if currbone.inherit_parent_name in frames:
				partialframe = frames[currbone.inherit_parent_name]
				# first, modify frame_pos
				if currbone.has_inherit_trans:
					for i in range(3):
						frame_pos[i] += partialframe.pos[i] * currbone.inherit_ratio
				if currbone.has_inherit_rot:
					# second, modify frame_rot
					partial_rot = core.euler_to_quaternion(partialframe.rot)
					# """multiply""" the rotation by the ratio
					# i.e. slerp from nothing (euler 0,0,0 === quat 1,0,0,0) to the full thing
					# negative ratio or ratio greater than 1 will still work
					partial_rot_after_ratio = core.my_slerp([1.0, 0.0, 0.0, 0.0], partial_rot, currbone.inherit_ratio)
					# """add""" the partial-inherit rotation to the full frame rotation
					frame_rot = core.hamilton_product(partial_rot_after_ratio, frame_rot)
			# if the bone to inherit from doesnt exist in the VMD, just do nothing
		
		all_children = []
		if frame_pos != [0.0, 0.0, 0.0] or frame_rot != [1.0, 0.0, 0.0, 0.0]:
			# if i am going to do a real change, turn the list of child indices into the actual child objects
			for child_idx in currbone.descendents:
				# find the ForwardKinematicsBone that corresponds to this index
				child = core.my_list_search(boneorder, lambda x: x.idx == child_idx, getitem=True)
				all_children.append(child)

		# if there is any amount of position offset,
		if frame_pos != [0.0, 0.0, 0.0]:
			# apply the position offset to this & all the children of this
			for thing in [currbone] + all_children:
				for i in range(3):
					thing.pos[i] += frame_pos[i]
		# if there is any amount of rotation offset,
		if frame_rot != [1.0, 0.0, 0.0, 0.0]:
			# apply the rotation offset to this & all children of this
			for thing in [currbone] + all_children:
				# rotate in 3d space around the current position of currbone
				thing.pos = core.rotate3d(currbone.pos, frame_rot, thing.pos)
				# rotate the angle of this bone as well
				thing.rot = core.hamilton_product(frame_rot, thing.rot)
	# once i'm done, then return the same list that was passed in as an argument,
	# but the pos/rot members have been changed
	return boneorder

# todo: move this... somewhere... idk
def recursive_find_all_ancestors(bones: List[pmxstruct.PmxBone], idx: int) -> Set[int]:
	"""
	Walk parent to parent to parent, return the set of all ancestors of the initial bone.
	It's actually iterative, not recursive, but whatever.
	:param bones: list of PmxBone objects, taken from Pmx.bones.
	:param idx: index within "bones" to start from. NOT INCLUDED within return value.
	:return: set of int indicies of all ancestors.
	"""
	retme = set()
	# if the parent index is not already marked, and not invalid,
	while (bones[idx].parent_idx not in retme) and (bones[idx].parent_idx >= 0):
		# then add the parent index,
		retme.add(bones[idx].parent_idx)
		# and repeat from the parent index
		idx = bones[idx].parent_idx
	return retme

def predetermine_bone_deform_order(bones: List[pmxstruct.PmxBone]) -> List[ForwardKinematicsBone]:
	"""
	Predetermine the order that bones should be deformed when doing forward kinematics. Exclusively determined by
	order within the pmx.bones list, deform layer, and deform_after_phys flag.
	:param bones: list of bones from pmx object
	:return: sorted list of names/indices/deform levels
	"""
	# all_parents_list: for each bone, walk up parent to parent to parent & find all ancestors of this bone (list of indices)
	all_parents_list = []
	for B in range(len(bones)):
		# start with the index of the current bone, "B", then recurse upward & fill the set
		this_bone_parents = recursive_find_all_ancestors(bones, B)
		# convert set to list & append
		all_parents_list.append(list(this_bone_parents))
	# all_descendent_list: for each bone, if any other bone sees this bone as it's parent, then that bone is
	# a child of this one!
	all_descendent_list = []
	for B in range(len(bones)):
		this_bone_descendents = []
		for D,parents in enumerate(all_parents_list):
			# bone d sees all "parents" as it's parents/ancestors
			if B in parents:
				# if "D" considers "B" to be a parent, then B will consider D to be a child
				this_bone_descendents.append(D)
		all_descendent_list.append(this_bone_descendents)
	
	sortme = []
	for d,bone in enumerate(bones):
		effective_deform = bone.deform_layer
		if bone.deform_after_phys:
			effective_deform += 2000
		parname = bones[bone.inherit_parent_idx].name_jp if bone.inherit_parent_idx is not None else ""
		thing = ForwardKinematicsBone(name=bone.name_jp,
									  idx=d,
									  deform=effective_deform,
									  pos=bone.pos,
									  descendents=all_descendent_list[d],
									  ancestors=all_parents_list[d],
									  has_inherit_rot=bone.inherit_rot,
									  has_inherit_trans=bone.inherit_trans,
									  inherit_parent_name=parname,
									  inherit_ratio=bone.inherit_ratio)
		sortme.append(thing)
	# sort by effective_deform with current index as a tiebreaker
	# therefore the bones that should deform first (motherbone, etc) will be at the top and leaf bones (fingers, etc)
	# will be at the bottom
	sortme.sort(key=lambda x: (x.deform, x.idx))
	return sortme


# function that takes a string & returns INDEX if it can match one, or None otherwise
def get_item_from_string(s: str, pmxlist: List):
	# search JP names first
	t = core.my_list_search(pmxlist, lambda x: x.name_jp.lower() == s.lower(), getitem=True)
	if t is not None: return t
	# search EN names next
	t = core.my_list_search(pmxlist, lambda x: x.name_en.lower() == s.lower(), getitem=True)
	if t is not None: return t
	# try to cast to int next
	try:
		t = int(s)
		if 0 <= t < len(pmxlist):
			return pmxlist[t]
		else:
			core.MY_PRINT_FUNC("valid indexes are [0-'%d']" % (len(pmxlist) - 1))
			return None
	except ValueError:
		core.MY_PRINT_FUNC("unable to find matching item for input '%s'" % s)
		return None


def main(moreinfo=True):
	############################################
	############################################
	############################################
	############################################
	# NEW USAGE TEMPLATE:
	# 1. ask for dance that works as intended with model X
	core.MY_PRINT_FUNC("Please specify the VMD dance input file:")
	input_filename_vmd = core.MY_FILEPROMPT_FUNC(".vmd")
	vmd = vmdlib.read_vmd(input_filename_vmd, moreinfo=moreinfo)

	# 2. ask for model X
	core.MY_PRINT_FUNC("")
	core.MY_PRINT_FUNC("Please specify (X) the PMX model file that the VMD works correctly with:")
	input_filename_pmx_source = core.MY_FILEPROMPT_FUNC(".pmx")
	pmx_source = pmxlib.read_pmx(input_filename_pmx_source, moreinfo=moreinfo)

	# 3. ask for model Y
	core.MY_PRINT_FUNC("")
	core.MY_PRINT_FUNC("Please specify (Y) the PMX model file that you want to create VMD IK frames for:")
	input_filename_pmx_dest = core.MY_FILEPROMPT_FUNC(".pmx")
	if input_filename_pmx_dest == input_filename_pmx_source:
		# if it's the same model, i can cheat!
		pmx_dest = pmx_source
	else:
		pmx_dest = pmxlib.read_pmx(input_filename_pmx_dest, moreinfo=moreinfo)

	# 4. ask for the bones... how?
	# ask for both ik and target at same time
	# valid input is any string that contains a forwardslash? then afterwards I can check that the Lside and Rside exist?
	# allow for any number of pairs...
	
	core.MY_PRINT_FUNC("")
	core.MY_PRINT_FUNC("Please specify all IK/target pairs to create frames for, one pair at a time.")
	core.MY_PRINT_FUNC("The IK is a bone in model Y, and the 'target' is a bone in model X.")
	core.MY_PRINT_FUNC("The script will move on and begin simulation when you give empty input.")
	core.MY_PRINT_FUNC("")
	
	ikbone_name_list = []
	targetbone_name_list = []
	
	while True:
		# ask for both ik and target at same time
		# valid input is any string that contains a forwardslash, and both halves can be matched to a bone
		
		def ik_target_valid_input_check(x:str)->bool:
			# if input is empty that counts as valid cuz that's the "ok now go do it" signal
			if x == "": return True
			# valid input must contain a forwardslash, both sides of the split but not be empty
			sp = x.split('/')
			if not (len(sp) == 2 and sp[0] and sp[1]):
				core.MY_PRINT_FUNC("invalid input: must contain exactly 2 terms separated by a forwardslash")
				return False
			ik_arg = sp[0]
			targ_arg = sp[1]
			# first: is ik_arg a valid identifier?
			ik = get_item_from_string(ik_arg, pmx_dest.bones)
			if ik is None:
				return False
			# second: is targ_arg a valid identifier?
			targ = get_item_from_string(targ_arg, pmx_source.bones)
			if targ is None:
				return False
			# third: is ik really an ik-type bone?
			if ik.has_ik is False:
				core.MY_PRINT_FUNC("invalid input: first bone '%s' exists but is not IK-type" % sp[0])
				return False
			return True

		s = core.MY_GENERAL_INPUT_FUNC(ik_target_valid_input_check,
									   ["What IK bone do you want to make frames for, and what bone should it follow?",
										"Please specify the two bones separated by a forwardslash: ik/follow",
										"A bone can be specified by JP name, EN name, or index #.",
										"The IK bone must exist in model Y and the follow bone must exist in model X.",
										"Empty input means you are done inputting bones."])
		# if the input is empty string, then we break and begin executing with current args
		if s == "" or s is None:
			break
			
		# because of ik_target_valid_input_check() it should be guaranteed safe to call split here & resolve them to bones
		ik_foo, target_foo = s.split('/')
		ik_bar = get_item_from_string(ik_foo, pmx_dest.bones)
		targ_bar = get_item_from_string(target_foo, pmx_source.bones)
		core.MY_PRINT_FUNC("ACCEPTED: ik bone = {}/'{}'/'{}', target bone = {}/'{}'/'{}'".format(
			ik_bar.idx_within(pmx_dest.bones), ik_bar.name_jp, ik_bar.name_en,
			targ_bar.idx_within(pmx_source.bones), targ_bar.name_jp, targ_bar.name_en,
		))
		core.MY_PRINT_FUNC("")
		
		ikbone_name_list.append(ik_bar.name_jp)
		targetbone_name_list.append(targ_bar.name_jp)
		pass
	
	if len(ikbone_name_list) == 0:
		core.MY_PRINT_FUNC("No bones to simulate, aborting")
		return
	
	# for i,t in zip(ikbone_name_list, targetbone_name_list):
	# 	core.MY_PRINT_FUNC("creating frames for IK bone '%s' to follow non-IK bone '%s'" % (i, t))
	# core.MY_PRINT_FUNC("")

	############################################
	############################################
	############################################
	############################################
	# DONE ASKING FOR INPUTS, NOW JUST DO PRE-PROCESSING
	# FIRST, do the "predetermine_bone_deform_order" stage for both models
	# determine the deform order of all bones in the model
	# result is a list of ForwardKinematicsBone objects with all the info i'm gonna need
	order_source = predetermine_bone_deform_order(pmx_source.bones)
	order_dest = predetermine_bone_deform_order(pmx_dest.bones)
	
	# SECOND, begin massaging the VMD
	# remove redundant frames just cuz i can, it might help reduce processing time
	boneframe_list = remove_redundant_frames(vmd.boneframes, moreinfo)
	# arrange the boneframes into a dict, key=name and value=sorted list of frames on that bone
	# make a copy of the dict so i can modify the sourcedict separate from the targetdict
	boneframe_source_dict = WIP_vmd_animation_smoothing.dictify_framelist(boneframe_list)
	boneframe_dest_dict = WIP_vmd_animation_smoothing.dictify_framelist(boneframe_list)
	
	# # check if this VMD uses IK or not, print a warning if it does
	# if any(any(ik_bone.enable for ik_bone in ikdispframe.ikbones) for ikdispframe in vmd.ikdispframes):
	# 	core.MY_PRINT_FUNC(
	# 		"Warning: the input VMD already has IK enabled, there is no point in running this script? Continuing anyway...")
	
	# THIRD, create the set "relevant_bones" from these ik/target pairs
	# (really this is just an optimization thing, not strictly necessary)
	# gotta create a separate set for the separate models :/
	# these are the ancestors of all the specified bones, everything needed to simulate their forward K
	# so i can discard the VMD frames of anything not in this ancestor set
	# does include the actual ik and actual target
	
	# set of INT INDICES that reference bones that will be simulated by forward kinematics
	relevant_bone_dest_idxs = set()
	for ikbone_name in ikbone_name_list:
		# turn ik bone NAME into INDEX
		ikbone_idx = core.my_list_search(pmx_dest.bones, lambda x: x.name_jp == ikbone_name, getitem=False)
		# perform recursion & fill the set with INDEXES
		relevant_bone_dest_idxs.update(recursive_find_all_ancestors(pmx_dest.bones, ikbone_idx))
		relevant_bone_dest_idxs.add(ikbone_idx)
	# add all the partial-inherit parents for each of these bones, if they exist
	for idx in list(relevant_bone_dest_idxs):
		# turn index into object
		bone = pmx_dest.bones[idx]
		if (bone.inherit_rot or bone.inherit_trans) and (bone.inherit_ratio != 0):
			relevant_bone_dest_idxs.add(bone.inherit_parent_idx)
		
	relevant_bone_source_idxs = set()
	for targetbone_name in targetbone_name_list:
		# turn target bone NAME into INDEX
		targetbone_idx = core.my_list_search(pmx_source.bones, lambda x: x.name_jp == targetbone_name, getitem=False)
		# perform recursion & fill the set with INDEXES
		relevant_bone_source_idxs.update(recursive_find_all_ancestors(pmx_source.bones, targetbone_idx))
		relevant_bone_source_idxs.add(targetbone_idx)
	# add all the partial-inherit parents for each of these bones, if they exist
	for idx in list(relevant_bone_source_idxs):
		# turn index into object
		bone = pmx_source.bones[idx]
		if (bone.inherit_rot or bone.inherit_trans) and (bone.inherit_ratio != 0):
			relevant_bone_source_idxs.add(bone.inherit_parent_idx)
	
	# turn set of ints into set of strings, bone names that will be simulated by forward kinematics
	relevant_bones_dest = set(pmx_dest.bones[a].name_jp for a in relevant_bone_dest_idxs)
	relevant_bones_source = set(pmx_source.bones[a].name_jp for a in relevant_bone_source_idxs)
	
	# remove all irrelevant bones from the boneframe_dicts
	for key in list(boneframe_source_dict.keys()):
		if key not in relevant_bones_source:
			boneframe_source_dict.pop(key)
	for key in list(boneframe_dest_dict.keys()):
		if key not in relevant_bones_dest:
			boneframe_dest_dict.pop(key)
	# print(relevant_bones)

	# FOURTH, continue massaging the VMD
	# (this is necessary unlike step 3)
	# pop any frames for the IK bone itself, just to be safe (since i'm making new frames for it, the old data will be overwritten)
	for key in list(boneframe_dest_dict.keys()):
		if key in ikbone_name_list:
			boneframe_dest_dict.pop(key)

	core.MY_PRINT_FUNC("Simulating %d bones in source model and %d bones in dest model" % (len(boneframe_source_dict), len(boneframe_dest_dict)))

	# """rectangularize""" these boneframes by adding interpolated frames, so that every relevant bone
	# has a frame at every relevant timestep
	framenums = set()
	for listofboneframes in boneframe_source_dict.values():
		for oneframe in listofboneframes:
			framenums.add(oneframe.f)
	for listofboneframes in boneframe_dest_dict.values():
		for oneframe in listofboneframes:
			framenums.add(oneframe.f)
	full_boneframe_source_dict = fill_missing_boneframes(boneframe_source_dict, moreinfo, framenums)
	full_boneframe_dest_dict = fill_missing_boneframes(boneframe_dest_dict, moreinfo, framenums)
	
	# "forward kinematics" function shouldn't need any knowledge of what timestep it is computing at
	# i want to ultimately give the forward-k function a list of boneframes and bonepositions, nothing more
	# therefore lets invert this dict, so that the primary key is framenum!!
	# each value is a dict, where the keys are the bone names and the values are the actual frames
	# invert_boneframe_dict[5][motherbone_name] = VmdBoneFrame object
	def invert_boneframe_dict(fulldict):
		invertdict = {}
		for bonelist in fulldict.values():  # for each key=bonename, get a list of frames
			for frame in bonelist:  # for each frame,
				# use its framenum to get the subdict in the inverted dict (so i can insert into the subdict)
				try:
					subdict = invertdict[frame.f]
				except KeyError:
					# if the dict does not exist, make/set it
					subdict = dict()
					invertdict[frame.f] = subdict
				# write into that dict with the key of bonename
				subdict[frame.name] = frame
		return invertdict
	invert_boneframe_source_dict = invert_boneframe_dict(full_boneframe_source_dict)
	invert_boneframe_dest_dict = invert_boneframe_dict(full_boneframe_dest_dict)
			
	# # sanity check
	# # from this reduced dict, determine what framenumbers have frames for any relevant bone
	# relevant_framenums = set()
	# for listofboneframes in boneframe_dict.values():
	# 	framenums_for_this_bone = [b.f for b in listofboneframes]
	# 	relevant_framenums.update(framenums_for_this_bone)
	# # turn the relevant_framenums set into a sorted list
	# relevant_framenums = sorted(list(relevant_framenums))
	# # verify that it is "rectangular"
	# assert len(invert_boneframe_dict.keys()) == len(relevant_framenums)
	# for foo in invert_boneframe_dict.values():
	# 	assert len(foo) == len(full_boneframe_dict.keys())
		
	############################################
	############################################
	############################################
	############################################
	
	# before running forward-K, SORT the targetbone_name_list and ikbone_name_list into the same order in which the ikbones deform
	ikbonename_targetbonename_sorted = []
	for name in [x.name for x in order_dest]:
		# fill "ikbonename_targetbonename_sorted" in the order in which the ikbones appear in order_dest
		try:
			i = ikbone_name_list.index(name)
			newthing = (ikbone_name_list[i], # ikbone_name
						core.my_list_search(pmx_dest.bones, lambda x: x.name_jp == name), # ikbone_idx_in_pmx_dest
						core.my_list_search(order_dest, lambda x: x.name == name), # ikbone_idx_in_order_dest
						targetbone_name_list[i], # targetbone_name
						core.my_list_search(order_source, lambda x: x.name == targetbone_name_list[i]) # targetbone_idx_in_order_source
						)
			ikbonename_targetbonename_sorted.append(newthing)
		except ValueError:
			# if name not in ikbone_name_list, do nothing
			pass
	
	# now actually run forward-K
	# first, simulate the source model and find the resulting location of the target bone for every frame
	core.MY_PRINT_FUNC("...running forward kinematics computation for %d frames on SOURCE model..." % len(invert_boneframe_source_dict))
	target_bone_positions = []
	# for each relevant framenum,
	for d,(framenum, frames) in enumerate(invert_boneframe_source_dict.items()):
		core.print_progress_oneline(d/len(invert_boneframe_source_dict))
		# run forward kinematics!
		results = run_forward_kinematics_for_one_timestep(frames, order_source)
		newlist = []
		# for each targetbone,
		for _, _, _, targetbone_name, targetbone_idx_in_order_source in ikbonename_targetbonename_sorted:
			# where is the absolute position of the target bone?
			targetbone_result = results[targetbone_idx_in_order_source]
			newlist.append(targetbone_result.pos.copy())
		target_bone_positions.append(newlist)
		pass
	# now i have the absolute positions for each target bone at each frame
	
	core.MY_PRINT_FUNC("...running forward kinematics computation for %d frames on DESTINATION model..." % len(invert_boneframe_dest_dict))

	# second, simulate the destination model and find the "resting position" of each IK bone
	# then i can figure out how much i need to move that bone to move it from rest to the desired position
	output_vmd_frames = []
	for d,(framenum, frames) in enumerate(invert_boneframe_dest_dict.items()):
		target_bone_positions_for_this_frame = target_bone_positions[d]
		core.print_progress_oneline(d/len(invert_boneframe_dest_dict))
		# run forward kinematics!
		results = run_forward_kinematics_for_one_timestep(frames, order_dest)
		# for each ikbone,
		for (ikbone_name, ikbone_idx_in_pmx_dest, ikbone_idx_in_order_dest, _, _), targetbone_position in \
				zip(ikbonename_targetbonename_sorted, target_bone_positions_for_this_frame):
			# where is the absolute position of the IK bone?
			ikbone_result = results[ikbone_idx_in_order_dest]
			# determine the XYZ change needed to make get teh ik bone from its origin to the target bone (remember to account
			# for any rotation on the ik bone!)
			# what i need to do is rotate by the opposite of the current rotation amount.
			opposite = core.my_quat_conjugate(ikbone_result.rot)
			# what point do i rotate around? i don't think it really matters, so just rotate around the ik bone
			new_target_pos = core.rotate3d(ikbone_result.pos, opposite, targetbone_position)
			# now ikbone_result.pos and new_target_pos should be alinged with the primary X Y Z axes, so just find the difference
			# final minus initial
			position_delta = [f - i for f,i in zip(new_target_pos, ikbone_result.pos)]
			# create a new VmdBoneFrame, use default linear interpolation
			new_frame = vmdstruct.VmdBoneFrame(name=ikbone_name, f=framenum,
											   pos=position_delta,
											   rot=[0.0, 0.0, 0.0],
											   phys_off=False,
											   # omit the interpolation
											   )
			# append it
			output_vmd_frames.append(new_frame)
			# now apply the offset (in origin frame, not in rotated frame) to the "ikbone_result" and any of its descendents
			# first, modify self:
			norotate_position_delta = [f - i for f,i in zip(targetbone_position, ikbone_result.pos)]
			ikbone_result.pos = [p + d for p,d in zip(ikbone_result.pos, norotate_position_delta)]
			# then, modify any other ik bones that are listed as a child of this
			for child_idx_in_pmx_dest in ikbone_result.descendents:
				for (ikbone_name2, ikbone_idx_in_pmx_dest2, ikbone_idx_in_order_dest2, _, _) in ikbonename_targetbonename_sorted:
					if child_idx_in_pmx_dest == ikbone_idx_in_pmx_dest2:
						# this is a child!
						ikbone_result2 = results[ikbone_idx_in_order_dest2]
						# apply the norotate delta
						ikbone_result2.pos = [p + d for p, d in zip(ikbone_result2.pos, norotate_position_delta)]
		
		pass

	############################################
	############################################
	############################################
	############################################
	
	core.MY_PRINT_FUNC("...done with forward kinematics computation, now writing output...")
	
	if INCLUDE_IK_ENABLE_FRAME:
		# create a single ikdispframe that enables the ik bones at frame 0
		ikbones_enable = []
		for ikbone_name in ikbone_name_list:
			ikbones_enable.append(vmdstruct.VmdIkbone(name=ikbone_name, enable=True))
		earliest_timestep = min(invert_boneframe_dest_dict.keys())
		ikdispframe_list = [vmdstruct.VmdIkdispFrame(f=earliest_timestep, disp=True, ikbones=ikbones_enable)]
	else:
		ikdispframe_list = []
		core.MY_PRINT_FUNC("Warning: IK following will NOT be enabled when this VMD is loaded, you will need enable it manually!")
		
	vmd_out = vmdstruct.Vmd(
		header=vmdstruct.VmdHeader(version=2, modelname=pmx_dest.header.name_jp),
		boneframes=output_vmd_frames,
		morphframes=[], camframes=[], lightframes=[], shadowframes=[],
		ikdispframes=ikdispframe_list
	)
	
	# write out
	output_filename_vmd = "%s_ik_for_%s.vmd" % \
						  (input_filename_vmd[0:-4], core.get_clean_basename(input_filename_pmx_source))
	output_filename_vmd = core.get_unused_file_name(output_filename_vmd)
	vmdlib.write_vmd(output_filename_vmd, vmd_out, moreinfo=moreinfo)

	core.MY_PRINT_FUNC("Done!")
	return None

if __name__ == '__main__':
	print(_SCRIPT_VERSION)
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
