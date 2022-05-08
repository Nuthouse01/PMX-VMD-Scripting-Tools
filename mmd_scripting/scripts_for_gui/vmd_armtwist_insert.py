import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_vmd_parser as vmdlib
import mmd_scripting.core.nuthouse01_vmd_struct as vmdstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.04 - 8/19/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# NOTE: DON'T BOTHER USING THIS SCRIPT! Just use "bone_add_semistandard_auto_armtwist" or "bone_make_sdef_auto_armtwist" instead.
# This script still works, but... why bother customizing every motion you want to use with a model, when you can just modify the model only once?
# The bonerig scripts also fix the wrist pinching problem, which this script does not.

# assumes bones are using semistandard names for arm/elbow/armtwist/elbowtwist

# read a VMD, convert rotation on arm/wrist bones around axis of "armtwist" into rotation around "armtwist"





###############
# PROBLEM!!!!
# I'm breaking up each arm-bone frame A into an arm-bone frame B and an armtwist-bone frame C
# and I've got it set up so that B + C = A, always and perfectly
# but A1 interpolates to A2 along a certain path,
# and B1+C1 interpolates to B2+C2 along a DIFFERENT path!?
# even tho A1=B1+C1 and A2=B2+C2
# ugly solution: over-key the motion data so that it doesn't get the chance to interpolate wrong
# because I'm overkeying i use the interpolation curve info to *create* the intermediate frames, but i discard the
# interpolation curve data when saving because it's now overkeyed and should use a linear-segment approximation instead
USE_OVERKEY_BANDAID = True
# recommended values: 1-4, creates 1 intermediate frame every X frames
# more spacing = less frames = less file size, but more deviation from the original VMD interpolation path
OVERKEY_FRAME_SPACING = 2



jp_left_arm =         "左腕"
jp_left_elbow =       "左ひじ"
jp_left_wrist =       "左手首"
jp_right_arm =        "右腕"
jp_right_elbow =      "右ひじ"
jp_right_wrist =      "右手首"
jp_left_armtwist =    "左腕捩"
jp_left_elbowtwist =  "左手捩" # technically this translates to "wrist twist" but armtwist is twisting the arm bone and wrist twist is twisting the elbow bone...
jp_right_armtwist =   "右腕捩"
jp_right_elbowtwist = "右手捩"

# useful for iterating
jp_sourcebones =   [jp_left_arm, jp_left_elbow, jp_right_arm, jp_right_elbow]
jp_pointat_bones = [jp_left_elbow, jp_left_wrist, jp_right_elbow, jp_right_wrist]
jp_twistbones =    [jp_left_armtwist, jp_left_elbowtwist, jp_right_armtwist, jp_right_elbowtwist]
eng_twistbones =   ["left_armtwist", "left_elbowtwist", "right_armtwist", "right_elbowtwist"]


def swing_twist_decompose(quat_in, axis):
	"""
	Decompose the rotation on to 2 parts.
	1. Twist - rotation around the "direction" vector
	2. Swing - rotation around axis that is perpendicular to "direction" vector
	The rotation can be composed back by
	quat_in = swing * twist
	
	has singularity in case of swing_rotation close to 180 degrees rotation.
	if the input quaternion is of non-unit length, the outputs are non-unit as well
	otherwise, outputs are both unit
	output = (swing, twist)
	"""

	# vector3 quat_rotation_axis( quat_in.x, quat_in.y, quat_in.z ); // rotation axis
	# quat rotation axis
	quat_rotation_axis = quat_in[1:4]
	
	# vector3 p = projection( quat_rotation_axis, axis ); // return projection x on to y  (parallel component)
	p = core.my_projection(quat_rotation_axis, axis)
	
	# twist.set( p.x, p.y, p.z, quat_in.w ); // but i use them as W X Y Z
	twist = [quat_in[0], p[0], p[1], p[2]]
	
	# twist.normalize();
	twist = core.normalize_distance(twist)
	
	# swing = quat_in * twist.conjugated();
	twist_conjugate = core.my_quat_conjugate(twist)
	swing = core.hamilton_product(quat_in, twist_conjugate)
	
	return swing, twist


helptext = '''=================================================
vmd_armtwist_insert:
NOTE: DON'T BOTHER USING THIS SCRIPT! Just use "bone_add_semistandard_auto_armtwist" or "bone_make_sdef_auto_armtwist" instead.
This script still works, but... why bother customizing every motion you want to use with a model, when you can just modify the model only once?
The bonerig scripts also fix the wrist pinching problem, which this script does not.

This script will modify a VMD for a specific model so that the 'arm twist bones' are actually used for twisting the arms.
This will fix pinching/tearing at the shoulder/elbow of the model, if the armtwist bones are present and properly rigged.
This is done via a 'swing twist decomposition' to isolate the 'local X-axis rotation' from the arm bone frames.
(The local X-axis extends down the center of the arm)
This local X-axis rotation is transferred to the arm twist bones where it is supposed to be.
The local Y-axis and local Z-axis rotation of the bone stay on the original arm bone.
The output file contains the entire improved dance, including modified arm/elbow frames and added armtwist/elbowtwist frames.

This requires both a PMX model and a VMD motion to run.
Output: dance VMD file '[dancename]_twistbones_for_[modelname].vmd'
'''

def main(moreinfo=True):
	# the goal: extract rotation around the "arm" bone local X? axis and transfer it to rotation around the "armtwist" bone local axis
	
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("")
	# get bones
	realbones = pmx.bones
	
	twistbone_axes = []
	# then, grab the "twist" bones & save their fixed-rotate axes, if they have them
	# fallback plan: find the arm-to-elbow and elbow-to-wrist unit vectors and use those
	for i in range(len(jp_twistbones)):
		r = core.my_list_search(realbones, lambda x: x.name_jp == jp_twistbones[i], getitem=True)
		if r is None:
			core.MY_PRINT_FUNC("ERROR1: twist bone '{}'({}) cannot be found model, unable to continue. Ensure they use the correct semistandard names, or edit the script to change the JP names it is looking for.".format(jp_twistbones[i], eng_twistbones[i]))
			raise RuntimeError()
		if r.has_fixedaxis:
			# this bone DOES have fixed-axis enabled! use the unit vector in r[18]
			twistbone_axes.append(r.fixedaxis)
		else:
			# i can infer local axis by angle from arm-to-elbow or elbow-to-wrist
			start = core.my_list_search(realbones, lambda x: x.name_jp == jp_sourcebones[i], getitem=True)
			if start is None:
				core.MY_PRINT_FUNC("ERROR2: semistandard bone '%s' is missing from the model, unable to infer axis of rotation" % jp_sourcebones[i])
				raise RuntimeError()
			end = core.my_list_search(realbones, lambda x: x.name_jp == jp_pointat_bones[i], getitem=True)
			if end is None:
				core.MY_PRINT_FUNC("ERROR3: semistandard bone '%s' is missing from the model, unable to infer axis of rotation" % jp_pointat_bones[i])
				raise RuntimeError()
			start_pos = start.pos
			end_pos = end.pos
			# now have both startpoint and endpoint! find the delta!
			delta = [b - a for a,b in zip(start_pos, end_pos)]
			# normalize to length of 1
			length = core.my_euclidian_distance(delta)
			unit = [t / length for t in delta]
			twistbone_axes.append(unit)
	
	# done extracting axes limits from bone CSV, in list "twistbone_axes"
	core.MY_PRINT_FUNC("...done extracting axis limits from PMX...")
	
	
	###################################################################################
	# prompt VMD file name
	core.MY_PRINT_FUNC("Please enter name of VMD dance input file:")
	input_filename_vmd = core.MY_FILEPROMPT_FUNC("VMD file", ".vmd")
	
	# next, read/use/prune the dance vmd
	nicelist_in = vmdlib.read_vmd(input_filename_vmd, moreinfo=moreinfo)
	
	# sort boneframes into individual lists: one for each [Larm + Lelbow + Rarm + Relbow] and remove them from the master boneframelist
	# frames for all other bones stay in the master boneframelist
	all_sourcebone_frames = []
	for sourcebone in jp_sourcebones:
		# partition & writeback
		temp, nicelist_in.boneframes = core.my_list_partition(nicelist_in.boneframes, lambda x: x.name == sourcebone)
		# all frames for "sourcebone" get their own sublist here
		all_sourcebone_frames.append(temp)
	
	# verify that there is actually arm/elbow frames to process
	sourcenumframes = sum([len(x) for x in all_sourcebone_frames])
	if sourcenumframes == 0:
		core.MY_PRINT_FUNC("No arm/elbow bone frames are found in the VMD, nothing for me to do!")
		core.MY_PRINT_FUNC("Aborting: no files were changed")
		return None
	else:
		core.MY_PRINT_FUNC("...source contains " + str(sourcenumframes) + " arm/elbow bone frames to decompose...")
	
	if USE_OVERKEY_BANDAID:
		# to fix the path that the arms take during interpolation we need to overkey the frames
		# i.e. create intermediate frames that they should have been passing through already, to FORCE it to take the right path
		# i'm replacing the interpolation curves with actual frames
		for sublist in all_sourcebone_frames:
			newframelist = []
			sublist.sort(key=lambda x: x.f) # ensure they are sorted by frame number
			# for each frame
			for i in range(1, len(sublist)):
				this = sublist[i]
				prev = sublist[i-1]
				# use interpolation curve i to interpolate from i-1 to i
				# first: do i need to do anything or are they already close on the timeline?
				thisframenum = this.f
				prevframenum = prev.f
				if (thisframenum - prevframenum) <= OVERKEY_FRAME_SPACING:
					continue
				# if they are far enough apart that i need to do something,
				thisframequat = core.euler_to_quaternion(this.rot)
				prevframequat = core.euler_to_quaternion(prev.rot)
				# create a bezier object from the rotation interpolation parameters, for creating intermediate frames
				r_ax, r_ay, r_bx, r_by = this.interp_r
				bez = core.MyBezier((r_ax, r_ay), (r_bx, r_by))
				# create new frames at these frame numbers, spacing is OVERKEY_FRAME_SPACING
				for interp_framenum in range(prevframenum + OVERKEY_FRAME_SPACING, thisframenum, OVERKEY_FRAME_SPACING):
					# calculate the x time percentage from prev frame to this frame
					x = (interp_framenum - prevframenum) / (thisframenum - prevframenum)
					# apply the interpolation curve to translate X to Y
					y = bez.approximate(x)
					# interpolate from prev to this by amount Y
					interp_quat = core.my_slerp(prevframequat, thisframequat, y)
					# begin building the new frame
					newframe = vmdstruct.VmdBoneFrame(
						name=this.name,  # same name
						f=interp_framenum,  # overwrite frame num
						pos=list(this.pos),  # same pos (but make a copy)
						rot=list(core.quaternion_to_euler(interp_quat)),  # overwrite euler angles
						phys_off=this.phys_off,  # same phys_off
						# default linear interpolation
					)
					newframelist.append(newframe)
				# overwrite thisframe interp curve with default too
				this.interp_x = core.interpolation_default_linear.copy()
				this.interp_y = core.interpolation_default_linear.copy()
				this.interp_z = core.interpolation_default_linear.copy()
				this.interp_r = core.interpolation_default_linear.copy()
			# concat the new frames onto the existing frames for this sublist
			sublist += newframelist
			
	# re-count the number of frames for printing purposes
	totalnumframes = sum([len(x) for x in all_sourcebone_frames])
	overkeyframes = totalnumframes - sourcenumframes
	if overkeyframes != 0:
		core.MY_PRINT_FUNC("...overkeying added " + str(overkeyframes) + " arm/elbow bone frames...")
	core.MY_PRINT_FUNC("...beginning decomposition of " + str(totalnumframes) + " arm/elbow bone frames...")
	
	# now i am completely done reading the VMD file and parsing its data! everything has been distilled down to:
	# all_sourcebone_frames = [Larm, Lelbow, Rarm, Relbow] plus nicelist_in[1]
	
	###################################################################################
	# begin the actual calculations
	
	# output array
	new_twistbone_frames = []
	# progress tracker
	curr_progress = 0
	
	# for each sourcebone & corresponding twistbone,
	for (twistbone, axis_orig, sourcebone_frames) in zip(jp_twistbones, twistbone_axes, all_sourcebone_frames):
		# for each frame of the sourcebone,
		for frame in sourcebone_frames:
			# XYZrot = 567 euler
			quat_in = core.euler_to_quaternion(frame.rot)
			axis = list(axis_orig)	# make a copy to be safe
			
			# "swing twist decomposition"
			# swing = "local" x rotation and nothing else
			# swing = sourcebone, twist = twistbone
			(swing, twist) = swing_twist_decompose(quat_in, axis)
			
			# modify "frame" in-place
			# only modify the XYZrot to use new values
			new_sourcebone_euler = list(core.quaternion_to_euler(swing))
			frame.rot = new_sourcebone_euler
			
			# create & store new twistbone frame
			# it's a copy of the sourcebone frame, except for name and rotation amount
			new_twistbone_euler = list(core.quaternion_to_euler(twist))
			newframe = frame.copy()
			newframe.name = twistbone
			newframe.rot = new_twistbone_euler
			
			new_twistbone_frames.append(newframe)
			# print progress updates
			curr_progress += 1
			core.print_progress_oneline(curr_progress / totalnumframes)
	
	
	######################################################################
	# done with calculations!
	core.MY_PRINT_FUNC("...done with decomposition, now reassembling output...")
	# attach the list of newly created boneframes, modify the original input
	for sublist in all_sourcebone_frames:
		nicelist_in.boneframes += sublist
	nicelist_in.boneframes += new_twistbone_frames
	
	core.MY_PRINT_FUNC("")
	# write out the VMD
	basename_pmx = core.filepath_splitext(core.filepath_splitdir(input_filename_pmx)[1])[0]
	output_filename_vmd = core.filepath_insert_suffix(input_filename_vmd, ("_twistbones_for_%s" % basename_pmx))
	output_filename_vmd = core.filepath_get_unused_name(output_filename_vmd)
	vmdlib.write_vmd(output_filename_vmd, nicelist_in, moreinfo=moreinfo)
	
	core.MY_PRINT_FUNC("Done!")
	return None

if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
