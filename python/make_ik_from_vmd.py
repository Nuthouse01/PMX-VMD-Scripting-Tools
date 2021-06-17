_SCRIPT_VERSION = "Script version:  Nuthouse01 - 10/10/2020 - v5.03"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# STATUS: it runs! it's fully written!
#	but its a pain to use
#	and i need to verify it actually works correctly

# NOTE: this won't work for normal arm IK the way you think it will, i think? because arm IK is normally an append-thing

# NOTE: if you are taking positions from one model and forcing them onto another model, it's not gonna be a perfect solution
# scaling or manual adjustment will probably be required, which kinda defeats the whole point of this script...

# first system imports
from typing import List, Sequence, Dict, Set


# second, wrap custom imports with a try-except to catch it if files are missing
try:
	# these imports work if running from GUI
	from . import nuthouse01_core as core
	from . import nuthouse01_vmd_parser as vmdlib
	from . import nuthouse01_vmd_struct as vmdstruct
	from . import nuthouse01_pmx_parser as pmxlib
	from . import nuthouse01_pmx_struct as pmxstruct
	from . import WIP_vmd_animation_smoothing
	from . import morph_scale
except ImportError as eee:
	try:
		# these imports work if running from double-click on THIS script
		import nuthouse01_core as core
		import nuthouse01_vmd_parser as vmdlib
		import nuthouse01_vmd_struct as vmdstruct
		import nuthouse01_pmx_parser as pmxlib
		import nuthouse01_pmx_struct as pmxstruct
		import WIP_vmd_animation_smoothing
		import morph_scale
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = vmdlib = vmdstruct = pmxlib = pmxstruct = WIP_vmd_animation_smoothing = morph_scale = None

# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


# # if this is true, the IK frames are stored as footIK-position + footIK-rotation
# # if this is false, the IK frames are stored as footIK-position + toeIK-position
# # not sure about the pros and cons of this setting, honestly?
# # with this true, the footIK-rotation means the arrows on the IK bones change in a sensible way, so that's nice
# STORE_IK_AS_FOOT_ONLY = True

# if this is true, an IK-disp frame will be created that enables the IK-following
# if this is false, when this VMD is loaded the IK bones will be moved but the legs won't follow them
# you will need to manually turn on IK for these bones
INCLUDE_IK_ENABLE_FRAME = True


'''
how do i arrange this?
inputs:
PMX (duh)
VMD (duh)
the desired IK bone
the normal bone used as the target for the IK bone

what bones do we execute forward kinematics on? is it harmful to just simulate teh whole model?
if the ik bone exists i can know which to execute.
i can calculate where the IK bone ends up objectively, but i also need to know its parent and where
its parent is, so i can know where the base position for the bone ends up, so i can know what offset to put in the
vmd bone frame.
lets say that the target IK bone might not be in the reference model...?
we can assume that the starting position of the ik bone is the same as its target
we need to ask what the parent of that ik bone is
	absolute position of target
	absolute position of IK parent


functions:
rotate 3d
rectangularize
"run fwd ik and get position of all bones when given frames"

'''


# jp_lefttoe =      "左つま先"
# jp_lefttoe_ik =   "左つま先ＩＫ"
# jp_leftfoot =     "左足首"
# jp_leftfoot_ik =  "左足ＩＫ"
# jp_righttoe =     "右つま先"
# jp_righttoe_ik =  "右つま先ＩＫ"
# jp_rightfoot =    "右足首"
# jp_rightfoot_ik = "右足ＩＫ"
# jp_left_waistcancel = "腰キャンセル左"
# jp_right_waistcancel = "腰キャンセル右"

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
		
# class Bone:
# 	def __init__(self, name, xinit, yinit, zinit):
# 		self.name = name
# 		self.xinit = xinit
# 		self.yinit = yinit
# 		self.zinit = zinit
# 		self.xcurr = 0.0
# 		self.ycurr = 0.0
# 		self.zcurr = 0.0
#
# 		self.xrot = 0.0
# 		self.yrot = 0.0
# 		self.zrot = 0.0
#
# 	def reset(self):
# 		self.xcurr = self.xinit
# 		self.ycurr = self.yinit
# 		self.zcurr = self.zinit
# 		self.xrot = 0.0
# 		self.yrot = 0.0
# 		self.zrot = 0.0


def rotate3d(rotate_around: Sequence[float],
			 angle_quat: Sequence[float],
			 initial_position: Sequence[float]) -> List[float]:
	"""
	Rotate a point within 3d space around another specified point by a specific quaternion angle.
	:param rotate_around: X Y Z usually a bone location
	:param angle_quat: W X Y Z quaternion rotation to apply
	:param initial_position: X Y Z starting location of the point to be rotated
	:return: X Y Z position after rotating
	"""
	# "rotate around a point in 3d space"
	
	# subtract "origin" to move the whole system to rotating around 0,0,0
	point = [p - o for p, o in zip(initial_position, rotate_around)]
	
	# might need to scale the point down to unit-length???
	# i'll do it just to be safe, it couldn't hurt
	length = core.my_euclidian_distance(point)
	if length != 0:
		point = [p / length for p in point]
		
		# set up the math as instructed by math.stackexchange
		p_vect = [0.0] + point
		r_prime_vect = core.my_quat_conjugate(angle_quat)
		# r_prime_vect = [angle_quat[0], -angle_quat[1], -angle_quat[2], -angle_quat[3]]
		
		# P' = R * P * R'
		# P' = H( H(R,P), R')
		temp = core.hamilton_product(angle_quat, p_vect)
		p_prime_vect = core.hamilton_product(temp, r_prime_vect)
		# note that the first element of P' will always be 0
		point = p_prime_vect[1:4]
		
		# might need to undo scaling the point down to unit-length???
		point = [p * length for p in point]
	
	# re-add "origin" to move the system to where it should have been
	point = [p + o for p, o in zip(point, rotate_around)]
	
	return point

def fill_missing_boneframes(boneframe_dict: Dict[str, List[vmdstruct.VmdBoneFrame]]) -> Dict[str, List[vmdstruct.VmdBoneFrame]]:
	"""
	Run interpolation so that all bones in boneframe_dict have keyframes at all framenumbers in relevant_framenums.
	Newly-created keyframes have basic linear interpolation.
	Currently only works with boneframes, could plausibly be changed to work with morphframes tho.
	:param boneframe_dict: returned from dictify_framelist()
	:return: another boneframe_dict, but filled out
	"""
	# boneframe_dict: keys are bonenames, values are sorted lists of frames for that bone
	# now fill in the blanks by using interpolation, if needed
	
	initial_size = sum(len(bonelist) for bonelist in boneframe_dict.values())
	
	# relevant_framenums: sorted list of all framenums that any relevent bone is keyed on
	relevant_framenums = set()
	for listofboneframes in boneframe_dict.values():
		framenums_for_this_bone = [b.f for b in listofboneframes]
		relevant_framenums.update(framenums_for_this_bone)
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
				newframe = bonelist[0].copy()
				newframe.f = framenum
				new_bonelist.append(newframe)
			elif framenum > bonelist[-1].f:  # if the desired framenum is higher than the last framenum,
				# then the new frame is a copy of the last frame
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
	final_size = sum(len(bonelist) for bonelist in new_boneframe_dict.values())
	core.MY_PRINT_FUNC("initial=%d, final=%d, added %d" % (initial_size, final_size, final_size-initial_size))  # todo
	# now it is totally filled out!
	return new_boneframe_dict
	
# def build_bonechain(allbones: List[pmxstruct.PmxBone], endbone: str) -> List[Bone]:
# 	nextbone = endbone
# 	buildme = []
# 	while True:
# 		r = core.my_list_search(allbones, lambda x: x.name_jp == nextbone, getitem=True)
# 		if r is None:
# 			core.MY_PRINT_FUNC("ERROR: unable to find '" + nextbone + "' in input file, unable to build parentage chain")
# 			raise RuntimeError()
# 		# 0 = bname, 5 = parent index, 234 = xyz position
# 		nextbone = allbones[r.parent_idx].name_jp
# 		newrow = Bone(r.name_jp, r.pos[0], r.pos[1], r.pos[2])
# 		buildme.append(newrow)
# 		# if parent index is -1, that means there is no parent. so we reached root. so break.
# 		if r.parent_idx == -1:
# 			break
# 	buildme.reverse()
# 	return buildme

helptext = '''=================================================
make_ik_from_vmd:
This script runs forward kinematics for the legs of a model, to calculate where the feet/toes will be and generates IK bone frames for those feet/toes.
This is only useful when the input dance does NOT already use IK frames, such as the dance Conqueror by IA.
** Specifically, if a non-IK dance works well for model X but not for model Y (feet clipping thru floor, etc), this would let you copy the foot positions from model X onto model Y.
** In practice, this isn't very useful... this file is kept around for historical reasons.
The output is a VMD that should be loaded into MMD *after* the original dance VMD is loaded.

Note: does not handle custom interpolation in the input dance VMD, assumes all interpolation is linear.
Note: does not handle models with 'hip cancellation' bones

This requires both a PMX model and a VMD motion to run.
Outputs: VMD file '[dancename]_ik_from_[modelname].vmd' that contains only the IK frames for the dance
'''


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
					# i.e. slerp from nothing to the full thing
					# TODO: does slerp support negative values? very large values? verify!
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
				thing.pos = rotate3d(currbone.pos, frame_rot, thing.pos)
				# rotate the angle of this bone as well
				thing.rot = core.hamilton_product(frame_rot, thing.rot)
	# once i'm done, then return the same list that was passed in as an argument,
	# but the pos/rot members have been changed
	return boneorder
	
def recursive_find_all_parents(bones: List[pmxstruct.PmxBone], idx: int) -> Set[int]:
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
		this_bone_parents = recursive_find_all_parents(bones, B)
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
	sortme.sort(key=lambda x: (x.deform, x.idx))
	return sortme

def main(moreinfo=True):
	# # prompt PMX name
	# core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	# input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")
	# pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	# # get bones
	# realbones = pmx.bones
	# then, make 2 lists: one starting from jp_righttoe, one starting from jp_lefttoe
	# start from each "toe" bone (names are known), go parent-find-parent-find until reaching no-parent
	# bonechain_r = build_bonechain(realbones, jp_righttoe)
	# bonechain_l = build_bonechain(realbones, jp_lefttoe)
	#
	# # assert that the bones were found, have correct names, and are in the correct positions
	# # also verifies that they are direct parent-child with nothing in between
	# try:
	# 	assert bonechain_r[-1].name == jp_righttoe
	# 	assert bonechain_r[-2].name == jp_rightfoot
	# 	assert bonechain_l[-1].name == jp_lefttoe
	# 	assert bonechain_l[-2].name == jp_leftfoot
	# except AssertionError:
	# 	core.MY_PRINT_FUNC("ERROR: unexpected structure found for foot/toe bones, verify semistandard names and structure")
	# 	raise RuntimeError()
	#
	# # then walk down these 2 lists, add each name to a set: build union of all relevant bones
	# relevant_bones = set()
	# for b in bonechain_r + bonechain_l:
	# 	relevant_bones.add(b.name)
	#
	# # check if waist-cancellation bones are in "relevant_bones", print a warning if they are
	# if jp_left_waistcancel in relevant_bones or jp_right_waistcancel in relevant_bones:
	# 	core.MY_PRINT_FUNC("Warning: waist-cancellation bones found in the model! These are not supported, tool may produce bad results! Attempting to continue...")
	#
	# # also need to find initial positions of ik bones (names are known)
	# # build a full parentage-chain for each leg
	# bonechain_ikr = build_bonechain(realbones, jp_righttoe_ik)
	# bonechain_ikl = build_bonechain(realbones, jp_lefttoe_ik)
	#
	# # verify that the ik bones were found, have correct names, and are in the correct positions
	# try:
	# 	assert bonechain_ikr[-1].name == jp_righttoe_ik
	# 	assert bonechain_ikr[-2].name == jp_rightfoot_ik
	# 	assert bonechain_ikl[-1].name == jp_lefttoe_ik
	# 	assert bonechain_ikl[-2].name == jp_leftfoot_ik
	# except AssertionError:
	# 	core.MY_PRINT_FUNC("ERROR: unexpected structure found for foot/toe IK bones, verify semistandard names and structure")
	# 	raise RuntimeError()
	#
	# # verify that the bonechains are symmetric in length
	# try:
	# 	assert len(bonechain_l) == len(bonechain_r)
	# 	assert len(bonechain_ikl) == len(bonechain_ikr)
	# except AssertionError:
	# 	core.MY_PRINT_FUNC("ERROR: unexpected structure found, model is not left-right symmetric")
	# 	raise RuntimeError()
	#
	# # determine how many levels of parentage, this value "t" should hold the first level where they are no longer shared
	# t = 0
	# while bonechain_l[t].name == bonechain_ikl[t].name:
	# 	t += 1
	# # back off one level
	# lowest_shared_parent = t - 1
	#
	# # now i am completely done with the bones CSV, all the relevant info has been distilled down to:
	# # !!! bonechain_r, bonechain_l, bonechain_ikr, bonechain_ikl, relevant_bones
	# core.MY_PRINT_FUNC("...identified " + str(len(bonechain_l)) + " bones per leg-chain, " + str(len(relevant_bones)) + " relevant bones total")
	# core.MY_PRINT_FUNC("...identified " + str(len(bonechain_ikl)) + " bones per IK leg-chain")
	
	###################################################################################
	###################################################################################
	###################################################################################
	# # prompt VMD file name
	# core.MY_PRINT_FUNC("Please enter name of VMD dance input file:")
	# input_filename_vmd = core.MY_FILEPROMPT_FUNC(".vmd")
	# nicelist_in = vmdlib.read_vmd(input_filename_vmd, moreinfo=moreinfo)
	
	############################################
	############################################
	############################################
	############################################
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	ikbone_name_list = []
	targetbone_name_list = []
	
	core.MY_PRINT_FUNC("")
	core.MY_PRINT_FUNC("Common IK/target pairs: (listed for convenient copying)")
	core.MY_PRINT_FUNC("    Right foot:    右足ＩＫ/右足首")
	core.MY_PRINT_FUNC("    Right toe:     右つま先ＩＫ/右つま先")
	core.MY_PRINT_FUNC("    Left foot:     左足ＩＫ/左足首")
	core.MY_PRINT_FUNC("    Left toe:      左つま先ＩＫ/左つま先")
	core.MY_PRINT_FUNC("    Right hand:    右腕IK/右手首")
	core.MY_PRINT_FUNC("    Left hand:     左腕IK/左手首")
	core.MY_PRINT_FUNC("    Right hand2:   右腕ＩＫ/右手首")
	core.MY_PRINT_FUNC("    Left hand2:    左腕ＩＫ/左手首")
	core.MY_PRINT_FUNC("")
	core.MY_PRINT_FUNC("Please specify all IK/target pairs to create frames for:")
	core.MY_PRINT_FUNC("")
	while True:
		# ask for both ik and target at same time
		# valid input is any string that contains a forwardslash
		def ik_target_valid_input_check(x:str)->bool:
			# if input is empty that counts as valid cuz that's the "ok now go do it" signal
			if x == "": return True
			# valid input must contain a forwardslash
			sp = x.split('/')
			if len(sp) != 2:
				core.MY_PRINT_FUNC("invalid input: must contain exactly 2 terms separated by a forwardslash")
				return False
			ikbone = core.my_list_search(pmx.bones, lambda b: b.name_jp == sp[0], getitem=True)
			targbone = core.my_list_search(pmx.bones, lambda b: b.name_jp == sp[1])
			if ikbone is None:
				core.MY_PRINT_FUNC("invalid input: first bone '%s' does not exist in model" % sp[0])
				return False
			if ikbone.has_ik is False:
				core.MY_PRINT_FUNC("invalid input: first bone '%s' exists but is not IK-type" % sp[0])
				return False
			if targbone is None:
				core.MY_PRINT_FUNC("invalid input: second bone '%s' does not exist in model" % sp[1])
				return False
			return True

		s = core.MY_GENERAL_INPUT_FUNC(ik_target_valid_input_check,
									   ["What IK bone do you want to make frames for, and what bone should it follow?",
										"Please give the JP names of both bones separated by a forwardslash: ikname/followname",
										"Empty input will begin forward kinematics simulation."])
		# if the input is empty string, then we break and begin executing with current args
		if s == "" or s is None:
			break
			
		# because of ik_target_valid_input_check() it should be guaranteed safe to call split here
		ikbone_name, targetbone_name = s.split('/')
		
		# core.MY_PRINT_FUNC("argument accepted: creating frames for IK bone '%s' to follow non-IK bone '%s'" % (ikbone_name, targetbone_name))
		ikbone_name_list.append(ikbone_name)
		targetbone_name_list.append(targetbone_name)
		core.MY_PRINT_FUNC("")
		pass
	
	for i,t in zip(ikbone_name_list, targetbone_name_list):
		core.MY_PRINT_FUNC("creating frames for IK bone '%s' to follow non-IK bone '%s'" % (i, t))
	core.MY_PRINT_FUNC("")

	# now create the set "relevant_bones" from these ik/target pairs
	# remember to ignore any bones that are parents of both ikbone and targetbone... right?
	
	# set of INT INDICES that reference bones that will be simulated by forward kinematics
	relevant_bones_idxs = set()
	
	for ikbone_name, targetbone_name in zip(ikbone_name_list, targetbone_name_list):
		# turn ik bone NAME into INDEX
		ikbone_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == ikbone_name, getitem=False)
		# perform recursion & fill the set with INDEXES
		ikbone_relevant_bones = recursive_find_all_parents(pmx.bones, ikbone_idx)
		# turn target bone NAME into INDEX
		targetbone_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == targetbone_name, getitem=False)
		# perform recursion & fill the set with INDEXES
		targetbone_relevant_bones = recursive_find_all_parents(pmx.bones, targetbone_idx)
		
		# discard any bones that are in both sets
		unique = ikbone_relevant_bones.symmetric_difference(targetbone_relevant_bones)
		# combine this result with everything i had already gotten
		relevant_bones_idxs.update(unique)
		relevant_bones_idxs.add(targetbone_idx)
		
		# add all the partial-inherit parents for each of these bones (most won't have any tho)
		for idx in list(relevant_bones_idxs):
			bone = pmx.bones[idx]
			if (bone.inherit_rot or bone.inherit_trans) and (bone.inherit_ratio != 0):
				relevant_bones_idxs.add(bone.inherit_parent_idx)
		
	# turn set of ints into set of strings, bone names that will be simulated by forward kinematics
	relevant_bones = set(pmx.bones[a].name_jp for a in relevant_bones_idxs)
	
	core.MY_PRINT_FUNC("Found %d important bones to simulate" % len(relevant_bones))
	# print(relevant_bones)

	# determine the deform order of all bones in the model
	# result is a list of ForwardKinematicsBone objects with all the info i'm gonna need
	order = predetermine_bone_deform_order(pmx.bones)

	############################################
	############################################
	############################################
	############################################
	core.MY_PRINT_FUNC("")
	# prompt VMD file name
	core.MY_PRINT_FUNC("Please enter name of VMD dance input file:")
	input_filename_vmd = core.MY_FILEPROMPT_FUNC(".vmd")
	vmd = vmdlib.read_vmd(input_filename_vmd, moreinfo=moreinfo)
	
	# # check if this VMD uses IK or not, print a warning if it does
	# if any(any(ik_bone.enable for ik_bone in ikdispframe.ikbones) for ikdispframe in vmd.ikdispframes):
	# 	core.MY_PRINT_FUNC(
	# 		"Warning: the input VMD already has IK enabled, there is no point in running this script? Continuing anyway...")
	
	# arrange the boneframes into a dict, key=name and value=sorted list of frames on that bone
	boneframe_dict = WIP_vmd_animation_smoothing.dictify_framelist(vmd.boneframes)
	
	# remove all irrelevant bones from the boneframe_dict
	for key,value in list(boneframe_dict.items()):
		if key not in relevant_bones:
			boneframe_dict.pop(key)
	# pop any frames for the IK bone itself, just to be safe (since i'm making new frames for it)
	for ikbone_name in ikbone_name_list:
		if ikbone_name in boneframe_dict:
			boneframe_dict.pop(ikbone_name)
	
	# print("aaa")
	# """rectangularize""" these boneframes by adding interpolated frames, so that every relevant bone
	# has a frame at every relevant timestep
	full_boneframe_dict = fill_missing_boneframes(boneframe_dict)
	# print("zzz")
	
	# "forward kinematics" function shouldn't need any knowledge of what timestep it is computing at
	# i want to ultimately give the forward-k function a list of boneframes and bonepositions, nothing more
	# therefore lets invert this dict, so that the primary key is framenum!!
	# each value is a dict, where the keys are the bone names and the values are the actual frames
	invert_boneframe_dict = {}
	for bonelist in full_boneframe_dict.values():  # for each bone,
		for frame in bonelist:
			# insert each frame into the dict that exists under that frame number
			try:
				# get the dict for that frame number
				subdict = invert_boneframe_dict[frame.f]
			except KeyError:
				# if the dict does not exist, make/set it
				subdict = dict()
				invert_boneframe_dict[frame.f] = subdict
			subdict[frame.name] = frame
			
	# sanity check
	# from this reduced dict, determine what framenumbers have frames for any relevant bone
	relevant_framenums = set()
	for listofboneframes in boneframe_dict.values():
		framenums_for_this_bone = [b.f for b in listofboneframes]
		relevant_framenums.update(framenums_for_this_bone)
	# turn the relevant_framenums set into a sorted list
	relevant_framenums = sorted(list(relevant_framenums))
	
	assert len(invert_boneframe_dict.keys()) == len(relevant_framenums)
	for foo in invert_boneframe_dict.values():
		assert len(foo) == len(full_boneframe_dict.keys())
		
	core.MY_PRINT_FUNC("...beginning forward kinematics computation for %d frames..." % len(invert_boneframe_dict.keys()))
	
	output_vmd_frames = []
	# for each relevant framenum,
	for d,(framenum, frames) in enumerate(invert_boneframe_dict.items()):
		core.print_progress_oneline(d/len(invert_boneframe_dict.keys()))
		# run forward kinematics!
		results = run_forward_kinematics_for_one_timestep(frames, order)
		for ikbone_name, targetbone_name in zip(ikbone_name_list, targetbone_name_list):
			# where is the absolute position of the IK bone?
			ikbone_result = core.my_list_search(results, lambda x: x.name == ikbone_name, getitem=True)
			# where is the absolute position of the target for the ik bone?
			targetbone_result = core.my_list_search(results, lambda x: x.name == targetbone_name, getitem=True)
			# determine the XYZ change needed to make get teh ik bone from its origin to the target bone (remember to account
			# for any rotation on the ik bone!)
			# what i need to do is rotate by the opposite of the current rotation amount.
			opposite = core.my_quat_conjugate(ikbone_result.rot)
			# what point do i rotate around? i don't think it really matters, so just rotate around the ik bone
			new_target_pos = rotate3d(ikbone_result.pos, opposite, targetbone_result.pos)
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
		pass
	
	############################################
	############################################
	############################################
	############################################

	# # reduce down to only the boneframes for the relevant bones
	# # also build a list of each framenumber with a frame for a bone we care about
	# relevant_framenums = set()
	# boneframe_list = []
	# for boneframe in nicelist_in.boneframes:
	# 	if boneframe.name in relevant_bones:
	# 		boneframe_list.append(boneframe)
	# 		relevant_framenums.add(boneframe.f)
	# # sort the boneframes by frame number
	# boneframe_list.sort(key=lambda x: x.f)
	# # make the relevant framenumbers also an ascending list
	# relevant_framenums = sorted(list(relevant_framenums))
	#
	# boneframe_dict = dict()
	# # now restructure the data from a list to a dictionary, keyed by bone name. also discard excess data when i do
	# for b in boneframe_list:
	# 	if b.name not in boneframe_dict:
	# 		boneframe_dict[b.name] = []
	# 	# only storing the frame#(1) + position(234) + rotation values(567)
	# 	saveme = [b.f, *b.pos, *b.rot]
	# 	boneframe_dict[b.name].append(saveme)
	#
	# core.MY_PRINT_FUNC("...running interpolation to rectangularize the frames...")
	#
	# has_warned = False
	# # now fill in the blanks by using interpolation, if needed
	# for key,bone in boneframe_dict.items():								# for each bone,
	# 	# start a list of frames generated by interpolation
	# 	interpframe_list = []
	# 	i=0
	# 	j=0
	# 	while j < len(relevant_framenums):					# for each frame it should have,
	# 		if i == len(bone):
	# 			# if i is beyond end of bone, then copy the values from the last frame and use as a new frame
	# 			newframe = [relevant_framenums[j]] + bone[-1][1:7]
	# 			interpframe_list.append(newframe)
	# 			j += 1
	# 		elif bone[i][0] == relevant_framenums[j]:			# does it have it?
	# 			i += 1
	# 			j += 1
	# 		else:
	# 			if not has_warned:
	# 				core.MY_PRINT_FUNC("Warning: interpolation is needed but interpolation curves are not fully tested! Assuming linear interpolation...")
	# 				has_warned = True
	# 			# if there is a mismatch then the target framenum is less than the boneframe framenum
	# 			# build a frame that has frame# + position(123) + rotation values(456)
	# 			newframe = [relevant_framenums[j]]
	# 			# if target is less than the current boneframe, interp between here and prev boneframe
	# 			for p in range(1,4):
	# 				# interpolate for each position offset
	# 				newframe.append(core.linear_map(bone[i][0], bone[i][p], bone[i-1][0], bone[i-1][p], relevant_framenums[j]))
	# 			# rotation interpolation must happen in the quaternion-space
	# 			quat1 = core.euler_to_quaternion(bone[i-1][4:7])
	# 			quat2 = core.euler_to_quaternion(bone[i][4:7])
	# 			# desired frame is relevant_framenums[j] = d
	# 			# available frames are bone[i-1][0] = s and bone[i][0] = e
	# 			# percentage = (d - s) / (e - s)
	# 			percentage = (relevant_framenums[j] - bone[i-1][0]) / (bone[i][0] - bone[i-1][0])
	# 			quat_slerp = core.my_slerp(quat1, quat2, percentage)
	# 			euler_slerp = core.quaternion_to_euler(quat_slerp)
	# 			newframe += euler_slerp
	# 			interpframe_list.append(newframe)
	# 			j += 1
	# 	bone += interpframe_list
	# 	bone.sort(key=core.get1st)
	#
	# # the dictionary should be fully filled out and rectangular now
	# for bone in boneframe_dict:
	# 	assert len(boneframe_dict[bone]) == len(relevant_framenums)
	#
	# # now i am completely done reading the VMD file and parsing its data! everything has been distilled down to:
	# # relevant_framenums, boneframe_dict
	
	###################################################################################
	# begin the actual calculations
	
	# output array
	
	
	
	# # have list of bones, parentage, initial pos
	# # have list of frames
	# # now i "run the dance" and build the ik frames
	# # for each relevant frame,
	# for I in range(len(relevant_framenums)):
	# 	# for each side,
	# 	for (thisik, this_chain) in zip([bonechain_ikr, bonechain_ikl], [bonechain_r, bonechain_l]):
	# 		# for each bone in this_chain (ordered, start with root!),
	# 		for J in range(len(this_chain)):
	# 			# reset the current to be the inital position again
	# 			this_chain[J].reset()
	# 		# for each bone in this_chain (ordered, start with toe! do children before parents!)
	# 		# also, don't read/use root! because the IK are also children of root, they inherit the same root transformations
	# 		# count backwards from end to lowest_shared_parent, not including lowest_shared_parent
	# 		for J in range(len(this_chain)-1, lowest_shared_parent, -1):
	# 			# get bone J within this_chain, translate to name
	# 			name = this_chain[J].name
	# 			# get bone [name] at index I: position & rotation
	# 			try:
	# 				xpos, ypos, zpos, xrot, yrot, zrot = boneframe_dict[name][I][1:7]
	# 			except KeyError:
	# 				continue
	# 			# apply position offset to self & children
	# 			# also resets the currposition when changing frames
	# 			for K in range(J, len(this_chain)):
	# 				# set this_chain[K].current456 = current456 + position
	# 				this_chain[K].xcurr += xpos
	# 				this_chain[K].ycurr += ypos
	# 				this_chain[K].zcurr += zpos
	# 			# apply rotation offset to all children, but not self
	# 			_origin = [this_chain[J].xcurr, this_chain[J].ycurr, this_chain[J].zcurr]
	# 			_angle = [xrot, yrot, zrot]
	# 			_angle_quat = core.euler_to_quaternion(_angle)
	# 			for K in range(J, len(this_chain)):
	# 				# set this_chain[K].current456 = current rotated around this_chain[J].current456
	# 				_point = [this_chain[K].xcurr, this_chain[K].ycurr, this_chain[K].zcurr]
	# 				_newpoint = rotate3d(_origin, _angle_quat, _point)
	# 				(this_chain[K].xcurr, this_chain[K].ycurr, this_chain[K].zcurr) = _newpoint
	#
	# 				# also rotate the angle of this bone
	# 				curr_angle_euler = [this_chain[K].xrot, this_chain[K].yrot, this_chain[K].zrot]
	# 				curr_angle_quat = core.euler_to_quaternion(curr_angle_euler)
	# 				new_angle_quat = core.hamilton_product(_angle_quat, curr_angle_quat)
	# 				new_angle_euler = core.quaternion_to_euler(new_angle_quat)
	# 				(this_chain[K].xrot, this_chain[K].yrot, this_chain[K].zrot) = new_angle_euler
	# 				pass
	# 			pass
	# 		# now i have cascaded this frame's pose data down the this_chain
	# 		# grab foot/toe (-2 and -1) current position and calculate IK offset from that
	#
	# 		# first, foot:
	# 		# footikend - footikinit = footikoffset
	# 		xfoot = this_chain[-2].xcurr - thisik[-2].xinit
	# 		yfoot = this_chain[-2].ycurr - thisik[-2].yinit
	# 		zfoot = this_chain[-2].zcurr - thisik[-2].zinit
	# 		# save as boneframe to be ultimately formatted for VMD:
	# 		# 	need bonename = (known)
	# 		# 	need frame# = relevantframe#s[I]
	# 		# 	position = calculated
	# 		# 	rotation = 0
	# 		# 	phys = not disabled
	# 		# 	interp = default (20/107)
	# 		# # then, foot-angle: just copy the angle that the foot has
	# 		if STORE_IK_AS_FOOT_ONLY:
	# 			ikframe = [thisik[-2].name, relevant_framenums[I], xfoot, yfoot, zfoot, this_chain[-2].xrot, this_chain[-2].yrot, this_chain[-2].zrot, False]
	# 		else:
	# 			ikframe = [thisik[-2].name, relevant_framenums[I], xfoot, yfoot, zfoot, 0.0, 0.0, 0.0, False]
	# 		ikframe += [20] * 8
	# 		ikframe += [107] * 8
	# 		# append the freshly-built frame
	# 		ikframe_list.append(ikframe)
	# 		if not STORE_IK_AS_FOOT_ONLY:
	# 			# then, toe:
	# 			# toeikend - toeikinit - footikoffset = toeikoffset
	# 			xtoe = this_chain[-1].xcurr - thisik[-1].xinit - xfoot
	# 			ytoe = this_chain[-1].ycurr - thisik[-1].yinit - yfoot
	# 			ztoe = this_chain[-1].zcurr - thisik[-1].zinit - zfoot
	# 			ikframe = [thisik[-1].name, relevant_framenums[I], xtoe, ytoe, ztoe, 0.0, 0.0, 0.0, False]
	# 			ikframe += [20] * 8
	# 			ikframe += [107] * 8
	# 			# append the freshly-built frame
	# 			ikframe_list.append(ikframe)
	# 	# now done with a timeframe for all bones on both sides
	# 	# print progress updates
	# 	core.print_progress_oneline(I / len(relevant_framenums))
	
	
	# if INCLUDE_IK_ENABLE_FRAME:
	# 	# create a single ikdispframe that enables the ik bones at frame 0
	# 	ikbones = [vmdstruct.VmdIkbone(name=jp_rightfoot_ik, enable=True),
	# 			   vmdstruct.VmdIkbone(name=jp_righttoe_ik, enable=True),
	# 			   vmdstruct.VmdIkbone(name=jp_leftfoot_ik, enable=True),
	# 			   vmdstruct.VmdIkbone(name=jp_lefttoe_ik, enable=True)]
	# 	ikdispframe_list = [vmdstruct.VmdIkdispFrame(f=0, disp=True, ikbones=ikbones)]
	# else:
	# 	ikdispframe_list = []
	# 	core.MY_PRINT_FUNC("Warning: IK following will NOT be enabled when this VMD is loaded, you will need enable it manually!")
	#
	# # convert old-style bonelist ikframe_list to new object format
	# ikframe_list = [vmdstruct.VmdBoneFrame(name=r[0], f=r[1], pos=r[2:5], rot=r[5:8], phys_off=r[8], interp=r[9:]) for r in ikframe_list]
	# # build actual VMD object
	# nicelist_out = vmdstruct.Vmd(
	# 	,
	# 	ikframe_list,  # bone
	# 	[],  # morph
	# 	[],  # cam
	# 	[],  # light
	# 	[],  # shadow
	# 	ikdispframe_list  # ikdisp
	# 	)
	
	core.MY_PRINT_FUNC("...done with forward kinematics computation, now writing output...")
	
	# todo should i include an ik-enable frame?
	
	nicelist_out = vmdstruct.Vmd(
		header=vmdstruct.VmdHeader(2, "IK-BONES"),
		boneframes=output_vmd_frames,
		morphframes=[], camframes=[], lightframes=[], shadowframes=[], ikdispframes=[]
	)
	
	# write out
	output_filename_vmd = "%s_ik_from_%s.vmd" % \
						  (input_filename_vmd[0:-4], core.get_clean_basename(input_filename_pmx))
	output_filename_vmd = core.get_unused_file_name(output_filename_vmd)
	vmdlib.write_vmd(output_filename_vmd, nicelist_out, moreinfo=moreinfo)

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
