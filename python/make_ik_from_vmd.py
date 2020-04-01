# Nuthouse01 - 03/30/2020 - v3.51
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


# NOTES:
# assumes bones are using semistandard names for feet, toes, footIK, toeIK
# assumes toeIK is a child of footIK, and footIK is a child of root (either directly or through footIKparent)

# NOTE: if you are taking positions from one model and forcing them onto another model, it's not gonna be a perfect solution
# scaling or manual adjustment will probably be required, which kinda defeats the whole point of this script...


import math

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	import nuthouse01_vmd_parser as vmd_parser
	import nuthouse01_pmx_parser as pmx_parser
	import nuthouse01_core as core
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	core = vmd_parser = pmx_parser = None

# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


# if this is true, the IK frames are stored as footIK-position + footIK-rotation
# if this is false, the IK frames are stored as footIK-position + toeIK-position
# not sure about the pros and cons of this setting, honestly
# with this true, the footIK-rotation means the arrows on the IK bones change in a sensible way, so that's nice
STORE_IK_AS_FOOT_ONLY = True

# if this is true, an IK-disp frame will be created that enables the IK-following
# if this is false, when this VMD is loaded the IK bones will be moved but the legs won't follow them
# you will need to manually turn on IK for these bones
INCLUDE_IK_ENABLE_FRAME = True



jp_lefttoe =      "左つま先"
jp_lefttoe_ik =   "左つま先ＩＫ"
jp_leftfoot =     "左足首"
jp_leftfoot_ik =  "左足ＩＫ"
jp_righttoe =     "右つま先"
jp_righttoe_ik =  "右つま先ＩＫ"
jp_rightfoot =    "右足首"
jp_rightfoot_ik = "右足ＩＫ"
jp_left_waistcancel = "腰キャンセル左"
jp_right_waistcancel = "腰キャンセル右"

class Bone:
	def __init__(self, name, xinit, yinit, zinit):
		self.name = name
		self.xinit = xinit
		self.yinit = yinit
		self.zinit = zinit
		self.xcurr = 0.0
		self.ycurr = 0.0
		self.zcurr = 0.0
		
		self.xrot = 0.0
		self.yrot = 0.0
		self.zrot = 0.0
	
	def reset(self):
		self.xcurr = self.xinit
		self.ycurr = self.yinit
		self.zcurr = self.zinit
		self.xrot = 0.0
		self.yrot = 0.0
		self.zrot = 0.0


def rotate3d(origin, angle_quat, point_in):
	# "rotate around a point in 3d space"
	
	# subtract "origin" to move the whole system to rotating around 0,0,0
	point = [p - o for p, o in zip(point_in, origin)]
	
	# might need to scale the point down to unit-length???
	# i'll do it just to be safe, it couldn't hurt
	length = core.my_euclidian_distance(point)
	if length != 0:
		point = [p / length for p in point]
		
		# set up the math as instructed by math.stackexchange
		p_vect = [0] + point
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
	point = [p + o for p, o in zip(point, origin)]
	
	return point


def build_bonechain(allbones, endbone):
	nextbone = endbone
	buildme = []
	while True:
		r = core.my_sublist_find(allbones, 0, nextbone)
		if r is None:
			core.pause_and_quit("Err: unable to find '" + nextbone + "' in input file, unable to build parentage chain")
		# 0 = bname, 5 = parent index, 234 = xyz position
		nextbone = allbones[r[5]][0]
		newrow = Bone(r[0], r[2], r[3], r[4])
		buildme.append(newrow)
		# if parent index is -1, that means there is no parent. so we reached root. so break.
		if r[5] == -1:
			break
	buildme.reverse()
	return buildme


def main():
	
	# print info to explain the purpose of this file
	core.MY_PRINT_FUNC("This script runs forward kinematics for the legs of a model, to calculate where the feet/toes will be and generates IK bone frames for those feet/toes.")
	core.MY_PRINT_FUNC("This is only useful when the input dance does NOT already use IK frames, such as Conqueror by IA.")
	core.MY_PRINT_FUNC("** Specifically, if a non-IK dance works well for model X but not for model Y (feet clipping thru floor, etc), this would let you copy the foot positions from model X onto model Y.")
	core.MY_PRINT_FUNC("** In practice, this isn't very useful... this file is kept around for historical reasons.")
	core.MY_PRINT_FUNC("The output is a VMD that should be loaded into MMD *after* the original dance VMD is loaded.")
	core.MY_PRINT_FUNC("Note: does not handle custom interpolation in the input dance VMD, assumes all interpolation is linear.")
	core.MY_PRINT_FUNC("Note: does not handle models with 'hip cancellation' bones")
	# print info to explain what inputs it needs
	core.MY_PRINT_FUNC("Inputs: dance VMD 'dancename.vmd' and model PMX 'modelname.pmx'")
	# print info to explain what outputs it creates
	core.MY_PRINT_FUNC("Outputs: VMD file '[dancename]_ik_from_[modelname].vmd' that contains only the IK frames for the dance")
	core.MY_PRINT_FUNC("")

	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.prompt_user_filename(".pmx")
	pmx = pmx_parser.read_pmx(input_filename_pmx)
	# get bones
	realbones = pmx[5]
	# then, make 2 lists: one starting from jp_righttoe, one starting from jp_lefttoe
	# start from each "toe" bone (names are known), go parent-find-parent-find until reaching no-parent
	bonechain_r = build_bonechain(realbones, jp_righttoe)
	bonechain_l = build_bonechain(realbones, jp_lefttoe)
	
	# assert that the bones were found, have correct names, and are in the correct positions
	# also verifies that they are direct parent-child with nothing in between
	try:
		assert bonechain_r[-1].name == jp_righttoe
		assert bonechain_r[-2].name == jp_rightfoot
		assert bonechain_l[-1].name == jp_lefttoe
		assert bonechain_l[-2].name == jp_leftfoot
	except AssertionError:
		core.pause_and_quit("Err: unexpected structure found for foot/toe bones, verify semistandard names and structure")
		
	# then walk down these 2 lists, add each name to a set: build union of all relevant bones
	relevant_bones = set()
	for b in bonechain_r + bonechain_l:
		relevant_bones.add(b.name)
		
	# check if waist-cancellation bones are in "relevant_bones", print a warning if they are
	if jp_left_waistcancel in relevant_bones or jp_right_waistcancel in relevant_bones:
		# TODO LOW: i probably could figure out how to support them but this whole script is useless so idgaf
		core.MY_PRINT_FUNC("Warning: waist-cancellation bones found in the model! These are not supported, tool may produce bad results! Attempting to continue...")
		
	# also need to find initial positions of ik bones (names are known)
	# build a full parentage-chain for each leg
	bonechain_ikr = build_bonechain(realbones, jp_righttoe_ik)
	bonechain_ikl = build_bonechain(realbones, jp_lefttoe_ik)
	
	# verify that the ik bones were found, have correct names, and are in the correct positions
	try:
		assert bonechain_ikr[-1].name == jp_righttoe_ik
		assert bonechain_ikr[-2].name == jp_rightfoot_ik
		assert bonechain_ikl[-1].name == jp_lefttoe_ik
		assert bonechain_ikl[-2].name == jp_leftfoot_ik
	except AssertionError:
		core.pause_and_quit("Err: unexpected structure found for foot/toe IK bones, verify semistandard names and structure")

	# verify that the bonechains are symmetric in length
	try:
		assert len(bonechain_l) == len(bonechain_r)
		assert len(bonechain_ikl) == len(bonechain_ikr)
	except AssertionError:
		core.pause_and_quit("Err: unexpected structure found, model is not left-right symmetric")

	# determine how many levels of parentage, this value "t" should hold the first level where they are no longer shared
	t = 0
	while bonechain_l[t].name == bonechain_ikl[t].name:
		t += 1
	# back off one level
	lowest_shared_parent = t - 1
	
	# now i am completely done with the bones CSV, all the relevant info has been distilled down to:
	# !!! bonechain_r, bonechain_l, bonechain_ikr, bonechain_ikl, relevant_bones
	core.MY_PRINT_FUNC("...identified " + str(len(bonechain_l)) + " bones per leg-chain, " + str(len(relevant_bones)) + " relevant bones total")
	core.MY_PRINT_FUNC("...identified " + str(len(bonechain_ikl)) + " bones per IK leg-chain")

	###################################################################################
	# prompt VMD file name
	core.MY_PRINT_FUNC("Please enter name of VMD dance input file:")
	input_filename_vmd = core.prompt_user_filename(".vmd")
	nicelist_in = vmd_parser.read_vmd(input_filename_vmd)
	
	# check if this VMD uses IK or not, print a warning if it does
	any_ik_on = False
	for ikdispframe in nicelist_in[6]:
		for ik_bone in ikdispframe[2]:
			if ik_bone[1] is True:
				any_ik_on = True
	if any_ik_on:
		core.MY_PRINT_FUNC("Warning: the input VMD already has IK enabled, there is no point in running this script. Attempting to continue...")
		
	# reduce down to only the boneframes for the relevant bones
	# also build a list of each framenumber with a frame for a bone we care about
	relevant_framenums = set()
	boneframe_list = []
	for boneframe in nicelist_in[1]:
		if boneframe[0] in relevant_bones:
			boneframe_list.append(boneframe)
			relevant_framenums.add(boneframe[1])
	# sort the boneframes by frame number
	boneframe_list.sort(key=core.get2nd)
	# make the relevant framenumbers also an ascending list
	relevant_framenums = list(relevant_framenums)
	relevant_framenums.sort()
	
	boneframe_dict = dict()
	# now restructure the data from a list to a dictionary, keyed by bone name. also discard excess data when i do
	for b in boneframe_list:
		if b[0] not in boneframe_dict:
			boneframe_dict[b[0]] = []
		# only storing the frame#(1) + position(234) + rotation values(567)
		saveme = b[1:8]
		boneframe_dict[b[0]].append(saveme)
	
	core.MY_PRINT_FUNC("...running interpolation to rectangularize the frames...")
	
	
	# now fill in the blanks by using interpolation, if needed
	for key,bone in boneframe_dict.items():								# for each bone,
		# start a list of frames generated by interpolation
		interpframe_list = []
		i=0
		j=0
		while j < len(relevant_framenums):					# for each frame it should have,
			if i == len(bone):
				# if i is beyond end of bone, then copy the values from the last frame and use as a new frame
				newframe = [relevant_framenums[j]] + bone[-1][1:7]
				interpframe_list.append(newframe)
				j += 1
			elif bone[i][0] == relevant_framenums[j]:			# does it have it?
				i += 1
				j += 1
			else:
				# TODO LOW: i could modify this to include my interpolation curve math now that I understand it, but i dont care
				core.MY_PRINT_FUNC("Warning: interpolation is needed but interpolation curves are not fully tested! Attempting to continue...")
				# if there is a mismatch then the target framenum is less than the boneframe framenum
				# build a frame that has frame# + position(123) + rotation values(456)
				newframe = [relevant_framenums[j]]
				# if target is less than the current boneframe, interp between here and prev boneframe
				for p in range(1,4):
					# interpolate for each position offset
					newframe.append(core.linear_map(bone[i][0], bone[i][p], bone[i-1][0], bone[i-1][p], relevant_framenums[j]))
				# rotation interpolation must happen in the quaternion-space
				quat1 = core.euler_to_quaternion(bone[i-1][4:7])
				quat2 = core.euler_to_quaternion(bone[i][4:7])
				# desired frame is relevant_framenums[j] = d
				# available frames are bone[i-1][0] = s and bone[i][0] = e
				# percentage = (d - s) / (e - s)
				percentage = (relevant_framenums[j] - bone[i-1][0]) / (bone[i][0] - bone[i-1][0])
				quat_slerp = core.my_slerp(quat1, quat2, percentage)
				euler_slerp = core.quaternion_to_euler(quat_slerp)
				newframe += euler_slerp
				interpframe_list.append(newframe)
				j += 1
		bone += interpframe_list
		bone.sort(key=core.get1st)
	
	# the dictionary should be fully filled out and rectangular now
	for bone in boneframe_dict:
		assert len(boneframe_dict[bone]) == len(relevant_framenums)
		
	# now i am completely done reading the VMD file and parsing its data! everything has been distilled down to:
	# relevant_framenums, boneframe_dict
	
	###################################################################################
	# begin the actual calculations
	core.MY_PRINT_FUNC("...beginning forward kinematics computation for " + str(len(relevant_framenums)) + " frames...")
	
	# output array
	ikframe_list = []
	# progress tracker
	last_progress = -1

	# # have list of bones, parentage, initial pos
	# # have list of frames
	# # now i "run the dance" and build the ik frames
	# for each relevant frame,
	for I in range(len(relevant_framenums)):
		# for each side,
		for (thisik, this_chain) in zip([bonechain_ikr, bonechain_ikl], [bonechain_r, bonechain_l]):
			# for each bone in this_chain (ordered, start with root!),
			for J in range(len(this_chain)):
				# reset the current to be the inital position again
				this_chain[J].reset()
			# for each bone in this_chain (ordered, start with toe! do children before parents!)
			# also, don't read/use root! because the IK are also children of root, they inherit the same root transformations
			# count backwards from end to lowest_shared_parent, not including lowest_shared_parent
			for J in range(len(this_chain)-1, lowest_shared_parent, -1):
				# get bone J within this_chain, translate to name
				name = this_chain[J].name
				# get bone [name] at index I: position & rotation
				try:
					xpos, ypos, zpos, xrot, yrot, zrot = boneframe_dict[name][I][1:7]
				except KeyError:
					continue
				# apply position offset to self & children
				# also resets the currposition when changing frames
				for K in range(J, len(this_chain)):
					# set this_chain[K].current456 = current456 + position
					this_chain[K].xcurr += xpos
					this_chain[K].ycurr += ypos
					this_chain[K].zcurr += zpos
				# apply rotation offset to all children, but not self
				_origin = [this_chain[J].xcurr, this_chain[J].ycurr, this_chain[J].zcurr]
				_angle = [xrot, yrot, zrot]
				_angle_quat = core.euler_to_quaternion(_angle)
				for K in range(J, len(this_chain)):
					# set this_chain[K].current456 = current rotated around this_chain[J].current456
					_point = [this_chain[K].xcurr, this_chain[K].ycurr, this_chain[K].zcurr]
					_newpoint = rotate3d(_origin, _angle_quat, _point)
					(this_chain[K].xcurr, this_chain[K].ycurr, this_chain[K].zcurr) = _newpoint
					
					# also rotate the angle of this bone
					curr_angle_euler = [this_chain[K].xrot, this_chain[K].yrot, this_chain[K].zrot]
					curr_angle_quat = core.euler_to_quaternion(curr_angle_euler)
					new_angle_quat = core.hamilton_product(_angle_quat, curr_angle_quat)
					new_angle_euler = core.quaternion_to_euler(new_angle_quat)
					(this_chain[K].xrot, this_chain[K].yrot, this_chain[K].zrot) = new_angle_euler
					pass
				pass
			# now i have cascaded this frame's pose data down the this_chain
			# grab foot/toe (-2 and -1) current position and calculate IK offset from that
			
			# first, foot:
			# footikend - footikinit = footikoffset
			xfoot = this_chain[-2].xcurr - thisik[-2].xinit
			yfoot = this_chain[-2].ycurr - thisik[-2].yinit
			zfoot = this_chain[-2].zcurr - thisik[-2].zinit
			# save as boneframe to be ultimately formatted for VMD:
			# 	need bonename = (known)
			# 	need frame# = relevantframe#s[I]
			# 	position = calculated
			# 	rotation = 0
			# 	phys = not disabled
			# 	interp = default (20/107)
			# # then, foot-angle: just copy the angle that the foot has
			if STORE_IK_AS_FOOT_ONLY:
				ikframe = [thisik[-2].name, relevant_framenums[I], xfoot, yfoot, zfoot, this_chain[-2].xrot, this_chain[-2].yrot, this_chain[-2].zrot, False]
			else:
				ikframe = [thisik[-2].name, relevant_framenums[I], xfoot, yfoot, zfoot, 0.0, 0.0, 0.0, False]
			ikframe += [20] * 8
			ikframe += [107] * 8
			# append the freshly-built frame
			ikframe_list.append(ikframe)
			if not STORE_IK_AS_FOOT_ONLY:
				# then, toe:
				# toeikend - toeikinit - footikoffset = toeikoffset
				xtoe = this_chain[-1].xcurr - thisik[-1].xinit - xfoot
				ytoe = this_chain[-1].ycurr - thisik[-1].yinit - yfoot
				ztoe = this_chain[-1].zcurr - thisik[-1].zinit - zfoot
				ikframe = [thisik[-1].name, relevant_framenums[I], xtoe, ytoe, ztoe, 0.0, 0.0, 0.0, False]
				ikframe += [20] * 8
				ikframe += [107] * 8
				# append the freshly-built frame
				ikframe_list.append(ikframe)
		# now done with a timeframe for all bones on both sides
		# print progress updates
		if I > last_progress:
			last_progress += 200
			core.print_progress_oneline(I, len(relevant_framenums))
	
	core.MY_PRINT_FUNC("...done with forward kinematics computation, now writing output...")

	if INCLUDE_IK_ENABLE_FRAME:
		# create a single ikdispframe that enables the ik bones at frame 0
		ikdispframe_list = [[0, True, [[jp_rightfoot_ik, True], [jp_righttoe_ik, True], [jp_leftfoot_ik, True], [jp_lefttoe_ik, True]]]]
	else:
		ikdispframe_list = []
		core.MY_PRINT_FUNC("Warning: IK following will NOT be enabled when this VMD is loaded, you will need enable it manually!")


	nicelist_out = [[2,"SEMISTANDARD-IK-BONES--------"],
					ikframe_list,	# bone
					[],				# morph
					[],				# cam
					[],				# light
					[],				# shadow
					ikdispframe_list	# ikdisp
					]
	
	
	# write out
	output_filename_vmd = "%s_ik_from_%s.vmd" % \
						  (core.get_clean_basename(input_filename_vmd), core.get_clean_basename(input_filename_pmx))
	output_filename_vmd = output_filename_vmd.replace(" ", "_")
	output_filename_vmd = core.get_unused_file_name(output_filename_vmd)
	vmd_parser.write_vmd(output_filename_vmd, nicelist_out)

	core.pause_and_quit("Done with everything! Goodbye!")
	return None

if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 03/30/2020 - v3.51")
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
