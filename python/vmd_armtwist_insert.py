# Nuthouse01 - 04/02/2020 - v3.60
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


# assumes bones are using semistandard names for arm/elbow/armtwist/elbowtwist

# read a VMD, convert rotation on arm/wrist bones around axis of "armtwist" into rotation around "armtwist"


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
	length = core.my_euclidian_distance(twist)
	twist = [t / length for t in twist]
	
	# swing = quat_in * twist.conjugated();
	twist_conjugate = core.my_quat_conjugate(twist)
	swing = core.hamilton_product(quat_in, twist_conjugate)
	
	return swing, twist



def main():
	
	# the goal: extract rotation around the "arm" bone local X? axis and transfer it to rotation around the "armtwist" bone local axis
	# print info to explain the purpose of this file
	core.MY_PRINT_FUNC("This script will modify a VMD for a specific model so that the 'arm twist bones' are actually used for twisting the arms.")
	core.MY_PRINT_FUNC("This will fix pinching/tearing at the shoulder/elbow of the model.")
	core.MY_PRINT_FUNC("This is done via a 'swing twist decomposition' to isolate the 'local X axis rotation' from the arm bone frames.")
	core.MY_PRINT_FUNC("This local X-axis rotation is transferred to the arm twist bones where it is supposed to be.")
	core.MY_PRINT_FUNC("The local Y-axis and local Z-axis rotation of the bone stay on the original arm bone.")
	core.MY_PRINT_FUNC("The output file contains the entire improved dance, including modified arm/elbow frames and added armtwist/elbowtwist frames.")
	# print info to explain what inputs it needs
	core.MY_PRINT_FUNC("Inputs: dance VMD 'dancename.vmd' and model PMX 'modelname.pmx'")
	# print info to explain what outputs it creates
	core.MY_PRINT_FUNC("Outputs: VMD file '[dancename]_twistbones_for_[modelname].vmd'")
	core.MY_PRINT_FUNC("")
	
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.prompt_user_filename(".pmx")
	pmx = pmx_parser.read_pmx(input_filename_pmx)
	# get bones
	realbones = pmx[5]

	twistbone_axes = []
	# then, grab the "twist" bones & save their fixed-rotate axes, if they have them
	# fallback plan: find the arm-to-elbow and elbow-to-wrist unit vectors and use those
	for i in range(len(jp_twistbones)):
		# jp bone name is at index 0
		r = core.my_sublist_find(realbones, 0, jp_twistbones[i])
		if r is None:
			core.MY_PRINT_FUNC("Err: twist bone '{}'({}) cannot be found model, unable to continue. Ensure they use the correct semistandard names, or edit the script to change the JP names it is looking for.".format(jp_twistbones[i], eng_twistbones[i]))
			raise RuntimeError()
		if r[17] != 0:
			# this bone DOES have fixed-axis enabled! use the unit vector in r[18]
			twistbone_axes.append(r[18])
		else:
			# i can infer local axis by angle from arm-to-elbow or elbow-to-wrist
			start = core.my_sublist_find(realbones, 0, jp_sourcebones[i])
			if start is None:
				core.MY_PRINT_FUNC("Err: semistandard bone '%s' is missing from the model, unable to infer axis of rotation" % jp_sourcebones[i])
				raise RuntimeError()
			end = core.my_sublist_find(realbones, 0, jp_pointat_bones[i])
			if end is None:
				core.MY_PRINT_FUNC("Err: semistandard bone '%s' is missing from the model, unable to infer axis of rotation" % jp_pointat_bones[i])
				raise RuntimeError()
			start_pos = start[2:5]
			end_pos = end[2:5]
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
	input_filename_vmd = core.prompt_user_filename(".vmd")
	
	# next, read/use/prune the dance vmd
	nicelist_in = vmd_parser.read_vmd(input_filename_vmd)
	
	# sort boneframes into individual lists: [Larm + Lelbow + Rarm + Relbow] + everything else
	# copy from nicelist to dedicated lists:
	all_sourcebone_frames = [[x for x in nicelist_in[1] if x[0] == sourcebone] for sourcebone in jp_sourcebones]
	# remove these frames from the nicelist
	nicelist_in[1] = [x for x in nicelist_in[1] if x[0] not in jp_sourcebones]
	
	sourcenumframes = sum([len(x) for x in all_sourcebone_frames])
	if sourcenumframes == 0:
		core.MY_PRINT_FUNC("Err: no arm/elbow bone frames are found in the VMD, nothing for me to do!")
		return None, False
	else:
		core.MY_PRINT_FUNC("...source contains " + str(sourcenumframes) + " arm/elbow bone frames to decompose...")

	if USE_OVERKEY_BANDAID:
		# to fix the path that the arms take during interpolation we need to overkey the frames
		# i.e. create intermediate frames that they should have been passing through already, to FORCE it to take the right path
		# i'm replacing the interpolation curves with actual frames
		for sublist in all_sourcebone_frames:
			newframelist = []
			sublist.sort(key=core.get2nd) # ensure they are sorted by frame number
			# for each frame
			for i in range(1, len(sublist)):
				this = sublist[i]
				prev = sublist[i-1]
				# use interpolation curve i to interpolate from i-1 to i
				# first: do i need to do anything or are they already close?
				thisframenum = this[1]
				prevframenum = prev[1]
				if (thisframenum - prevframenum) <= OVERKEY_FRAME_SPACING:
					continue
				# if they are far enough apart that i need to do something,
				thisframequat = core.euler_to_quaternion(this[5:8])
				prevframequat = core.euler_to_quaternion(prev[5:8])
				# 12, 16, 20, 24 = ax, ay, bx, by
				curve = core.my_bezier_characterize((this[12], this[16]), (this[20], this[24]))
				# create new frames at these frame numbers, spacing is OVERKEY_FRAME_SPACING
				for interp_framenum in range(prevframenum + OVERKEY_FRAME_SPACING, thisframenum, OVERKEY_FRAME_SPACING):
					# calculate the x time percentage from prev frame to this frame
					x = (interp_framenum - prevframenum) / (thisframenum - prevframenum)
					# apply the interpolation curve to translate X to Y
					y = core.my_bezier_approximation(x, curve)
					# interpolate from prev to this by amount Y
					interp_quat = core.my_slerp(prevframequat, thisframequat, y)
					# begin building the new frame
					newframe = list(this)
					newframe[1] = interp_framenum # overwrite frame num
					newframe[5:8] = core.quaternion_to_euler(interp_quat) # overwrite euler angles
					newframe[9:25] = core.bone_interpolation_default_linear # overwrite custom interpolation
					newframelist.append(newframe)
				# overwrite thisframe interp curve with default too
				this[9:25] = core.bone_interpolation_default_linear # overwrite custom interpolation
			# concat the new frames onto the existing frames for this sublist
			sublist += newframelist
			
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
	last_progress = -1
	curr_progress = 0
	
	# for each sourcebone & corresponding twistbone,
	for (twistbone, axis_orig, sourcebone_frames) in zip(jp_twistbones, twistbone_axes, all_sourcebone_frames):
		new_twistbone_frames.append([])
		# for each frame of the sourcebone,
		for frame in sourcebone_frames:
			# XYZrot = 567 euler
			quat_in = core.euler_to_quaternion(frame[5:8])
			axis = list(axis_orig)	# make a copy to be safe
			
			# "swing twist decomposition"
			# swing = "local" x rotation and nothing else
			# swing = sourcebone, twist = twistbone
			(swing, twist) = swing_twist_decompose(quat_in, axis)
			
			# modify "frame" in-place
			# only modify the XYZrot to use new values
			new_sourcebone_euler = core.quaternion_to_euler(swing)
			frame[5:8] = new_sourcebone_euler
			
			# create & store new twistbone frame
			# name=twistbone, framenum=copy, XYZpos=copy, XYZrot=new, phys=copy, interp16=copy
			newframe = list(frame)
			newframe[0] = twistbone
			new_twistbone_euler = core.quaternion_to_euler(twist)
			newframe[5:8] = new_twistbone_euler
			new_twistbone_frames[-1].append(newframe)
			# print progress updates
			curr_progress += 1
			if curr_progress > last_progress:
				last_progress += 200
				core.print_progress_oneline(curr_progress, totalnumframes)
	
	
	######################################################################
	# done with calculations!
	core.MY_PRINT_FUNC("...done with decomposition, now reassembling output...")
	# attach the list of newly created boneframes, modify the original input
	for sublist in all_sourcebone_frames:
		nicelist_in[1] += sublist
	for sublist in new_twistbone_frames:
		nicelist_in[1] += sublist
	
	# write out the VMD
	output_filename_vmd = "%s_twistbones_for_%s.vmd" % \
						   (core.get_clean_basename(input_filename_vmd), core.get_clean_basename(input_filename_pmx))
	output_filename_vmd = output_filename_vmd.replace(" ", "_")
	output_filename_vmd = core.get_unused_file_name(output_filename_vmd)
	vmd_parser.write_vmd(output_filename_vmd, nicelist_in)
	
	core.pause_and_quit("Done with everything! Goodbye!")
	return None

if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 04/02/2020 - v3.60")
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
			core.MY_PRINT_FUNC(ee.__class__.__name__, ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
