import math
from typing import List, Tuple, Set

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_vmd_parser as vmdlib
import mmd_scripting.core.nuthouse01_vmd_struct as vmdstruct
import mmd_scripting.core.nuthouse01_vmd_utils as vmdutil
from mmd_scripting.vectorpaths_chrisarridge import vectorpaths


_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.05 - 9/7/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################
# https://github.com/chrisarridge/vectorpaths

DEBUG = True
DEBUG_PLOTS = True

import logging
if DEBUG:
	# this prints a bunch of useful stuff in the bezier regression, and a bunch of useless stuff from matplotlib
	logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

if DEBUG_PLOTS:
	import matplotlib.pyplot as plt

helptext = '''=================================================
vmd_uninterpolate:
Modify a VMD and remove excess keyframes caused by deliberate over-keying.
This will make the VMD much smaller (filesize) and make it easier to load or tweak for different models.
WARNING: THIS TAKES AN EXTREMELY LONG TIME TO RUN!

Output: dunno
'''

'''
data: how for bone センター in Marionette, how many frames are kept based on position for varying bezier error targets
errors 0.5 - 3.0
total=6212

0.5, keep%=59%
0.6, keep%=54%
0.7, keep%=50%
0.79, keep%=46%
0.89, keep%=42%
0.99, keep%=38%
1.09, keep%=36%
1.2, keep%=34%
1.3, keep%=33%
1.4, keep%=32%
1.5, keep%=30%
1.6, keep%=30%
1.7, keep%=29%
1.8, keep%=28%
1.9, keep%=27%
2.0, keep%=26%
2.1, keep%=25%
2.2, keep%=25%
2.3, keep%=24%
2.4, keep%=23%
2.5, keep%=22%
2.6, keep%=22%
2.7, keep%=21%
2.8, keep%=21%
2.9, keep%=21%
'''

SIMPLIFY_BONE_POSITION = False
SIMPLIFY_BONE_ROTATION = True

MORPH_ERROR_THRESHOLD = 0.00001

BEZIER_ERROR_THRESHOLD_BONE_POSITION_RMS = 1.2
BEZIER_ERROR_THRESHOLD_BONE_POSITION_MAX = 1.2

BONE_ROTATION_STRAIGHTNESS_VALUE = 0.85

# TODO: overall cleanup, once everything is acceptably working. variable names, comments, function names, etc.

# TODO: change morph-simplify to use a structure more similar to the bone-simplify structure? i.e. store frame
#  indices in a set and then get the frames back at the very end. it would be less efficient but its just for
#  more consistency between sections.

# TODO: optimize the position section of bone-simplify, add another loop layer so i don't need to keep re-finding z.

# TODO: do something to ensure that bezier control points are guaranteed within the box...
#  clamp it afterward? somehow change the regression algorithm to restrict them at each step?
#  ALSO want to compute exactly how often the points are outside the box.
#  **BEST**: if control points are outside the box, then it doesn't represent a curve that's possible in MMD! discard it!

# TODO: modify the bezier regression to return the error values? i think it would just be for logging, not sure if its
#  worth changing the structure.
#  it would be useful for, "keep walking backward until you find a curve that's good, and the NEXT curve is worse"...?
#  except that no, if region M can be well fit then any subset of the region can be fit as well or better...

# TODO: even more testing to figure out what good values are for bezier error targets

# TODO: how the fuck can i effectively visualize quaternions? i need to see them plotted on a globe or something
#  so i can have confidence that my "how straight should be considered a straight line" threshold is working right

# TODO: re-research how to measure quaternion angle and angular distance (is there a difference?)

# TODO: should quaternion straightness be judged by "AB vs CD" or "AB vs AC" ?

def sign(U):
	# return -1/0/+1 if input is negative/zero/positive
	if U == 0:  return 0
	elif U > 0: return 1
	else:       return -1


def get_corner_sharpness_factor(deltaquat_AB: Tuple[float, float, float, float],
								deltaquat_BC: Tuple[float, float, float, float],) -> float:
	"""
	Calculate a [0.0-1.0] factor indicating how "sharp" the corner is at B.
	By "corner" I mean the directional change when A->B stops and B->C begins.
	If they are going the same angular "direction", then return 1.0. If they
	are going perfectly opposite directions, return 0.0. Otherwise return something
	in between.

	:param deltaquat_AB: "delta quaterinon" WXYZ from frame A to B
	:param deltaquat_BC: "delta quaternion" WXYZ from frame B to C
	:return: float [0.0-1.0]
	"""
	
	# "how sharp a corner is" = the "angular distance" between AtoB delta and BtoC delta
	
	# first, find the deltas between the quaternions
	# deltaquat_AB = core.hamilton_product(core.my_quat_conjugate(quatA), quatB)
	# deltaquat_BC = core.hamilton_product(core.my_quat_conjugate(quatB), quatC)
	# to get sensible results below, ignore the "W" component and only use the XYZ components, treat as 3d vector
	deltavect_AB = deltaquat_AB[1:4]
	deltavect_BC = deltaquat_BC[1:4]
	# second, find the angle between these two deltas
	# use the plain old "find the angle between two vectors" formula
	len1 = core.my_euclidian_distance(deltavect_AB)
	len2 = core.my_euclidian_distance(deltavect_BC)
	if (len1 == 0) and (len2 == 0):
		# zero equals zero, so return 1!
		return 1.0
	t = len1 * len2
	if t == 0:
		# if exactly one vector has a length of 0 (but not both, otherwise it would be caught above) then they are DIFFERENT
		return 0.0
	# technically the clamp shouldn't be necessary but floating point inaccuracy caused it to do math.acos(1.000000002) which crashed lol
	shut_up = core.my_dot(deltavect_AB, deltavect_BC) / t
	shut_up = core.clamp(shut_up, -1.0, 1.0)
	ang_d = math.acos(shut_up)
	# print(math.degrees(ang_d))
	# if ang = 0, perfectly colinear, factor = 1
	# if ang = 180, perfeclty opposite, factor = 0
	factor = 1 - (ang_d / math.pi)
	return factor


def simplify_morphframes(allmorphlist: List[vmdstruct.VmdMorphFrame]) -> List[vmdstruct.VmdMorphFrame]:
	"""
	morphs have only one dimension to worry about, and cannot have interpolation "curves"
	everything is perfectly linear!
	i'm not entirely sure that the facials are over-keyed like the bones are... but it's a good warmup
	turns out that there are a few spots with excessive keys, but it's mostly sparse like i expected

	:param allmorphlist:
	:return:
	"""
	output = []  # this is the list of frames to preserve, the startpoints and endpoints
	
	# verify there is no overlapping frames, just in case
	allmorphlist = vmdutil.assert_no_overlapping_frames(allmorphlist)
	# sort into dict form to process each morph independently
	morphdict = vmdutil.dictify_framelist(allmorphlist)
	
	# analyze each morph one at a time
	for morphname, morphlist in morphdict.items():
		# make a list of the deltas, for simplicity
		thisoutput = []
		# the first frame is always kept. and the last frame is also always kept.
		# if there is only one frame, or two, then don't even bother walking i guess?
		if len(morphlist) <= 2:
			output.extend(morphlist)
			continue
		
		# the first frame is always kept.
		thisoutput.append(morphlist[0])
		i = 0
		while i < (len(morphlist)-1):
			# start walking down this list
			# assume that i is the start point of a potentially over-keyed section
			m_this = morphlist[i]
			m_next = morphlist[i+1]
			delta_rate = (m_next.val - m_this.val) / (m_next.f - m_this.f)
			# now, walk forward from here until i "return" a frame that has a different delta
			z = 0  # to make pycharm shut up
			for z in range(i+1, len(morphlist)):
				# if i reach the end of the morphlist, then "return" the final valid index
				if z == len(morphlist)-1:
					break
				z_this = morphlist[z]
				z_next = morphlist[z + 1]
				delta_z = (z_next.val - z_this.val) / (z_next.f - z_this.f)
				if (delta_rate - MORPH_ERROR_THRESHOLD) < delta_z < (delta_rate + MORPH_ERROR_THRESHOLD):
					# if this is within the tolerance, then this is continuing the slide and should be skipped over
					pass
				else:
					# if this delta is not within some %tolerance of matching, then this is a break!
					break
			# now, z is the index for the end of the sequence
			# it starts at i and ends at z
			# i know that i have found a segment endpoint and i can discard everything in between!
			# no need to preserve 'i', it has already been added
			thisoutput.append(morphlist[z])
			# now skip ahead and start walking from z
			i = z
		if DEBUG:
			# when i am done with this morph, how many have i lost?
			tossed = len(morphlist) - len(thisoutput)
			if tossed:
				print(morphname)
				print("tossed %d frames" % tossed)
				for i in range(len(morphlist)):
					m = morphlist[i]
					if i == len(morphlist)-1:
						delta = 999
					else:
						m2 = morphlist[i+1]
						delta = (m2.val - m.val) / (m2.f - m.f)
					print("%s n:%s f:%d v:%f d:%f" % ("*" if m in thisoutput else " ", morphname, m.f, m.val, delta))
		
		output.extend(thisoutput)
	# FIN
	print("TOTAL: tossed %d frames" % (len(allmorphlist) - len(output)))
	
	return output

def _simplify_boneframes_position(bonename: str, bonelist: List[vmdstruct.VmdBoneFrame]) -> Set[int]:
	"""
	
	:param bonename:
	:param bonelist:
	:return:
	"""
	keepset = set()
	# i'll do the x independent from the y independent from the z
	for C in range(3):  # for X, then Y, then Z:
		axis_keep_list = []
		i = 0
		while i < (len(bonelist) - 1):
			# start walking down this list
			# assume that i is the start point of a potentially over-keyed section
			b_this = bonelist[i]
			b_next = bonelist[i + 1]
			# find the delta for this channel
			b_delta = (b_next.pos[C] - b_this.pos[C]) / (b_next.f - b_this.f)
			b_sign = sign(b_delta)
			
			#+++++++++++++++++++++++++++++++++++++
			# now, walk forward from here until i "return" the frame "z" that has a different delta
			# "z" is the farthest plausible endpoint of the section (the real endpoint might be between i and z, tho)
			# "different" means only different state, i.e. rising/falling/zero
			z = 0  # to make pycharm shut up
			for z in range(i + 1, len(bonelist)):
				# if i reach the end of the bonelist, then "return" the final valid index
				if z == len(bonelist) - 1:
					break
				z_this = bonelist[z]
				z_next = bonelist[z + 1]
				z_delta = (z_next.pos[C] - z_this.pos[C]) / (z_next.f - z_this.f)
				# TODO: also break if the delta is way significantly different than the previous delta?
				#  pretty sure that idea is needed for the camera jumpcuts to be guaranteed detected?
				if sign(z_delta) == b_sign:
					pass  # if this is potentially part of the same sequence, keep iterating
				else:
					break  # if this is definitely no longer part of the sequence, THEN i can break
			# anything past z is DEFINITELY NOT the endpoint for this sequence
			# everything from i to z is monotonic: always increasing OR always decreasing OR flat zero
			# if it's flat zero, then i already know it's linear and i don't need to try to fit a curve to it lol
			if b_sign == 0:
				axis_keep_list.append(z)  # then save this proposed endpoint as a valid endpoint,
				i = z  # and move the startpoint to here and keep walking from here
				continue
			# if it hits past here, then i've got something interesting to work with!

			# OPTIMIZE: if i find z, then walk backward a bit, i can reuse the same z! no need to re-walk the same section
			while i < z:
				# +++++++++++++++++++++++++++++++++++++
				# from z, walk backward and test endpoint quality at each frame
				x_points = []
				y_points = []
				b_this = bonelist[i]
				y_start = b_this.pos[C]
				x_start = b_this.f
				# i think i want to run backwards from z until i find "an acceptably good match"
				# gonna need to do a bunch of testing to quantify what "acceptably good" looks like tho
				for w in range(z, i, -1):
					# calculate the x,y (scale of 0 to 1) for all points between i and "test"
					y_range = bonelist[w].pos[C] - y_start
					x_range = bonelist[w].f - x_start
					x_points.clear()
					y_points.clear()
					for P in range(i, w + 1):
						point = bonelist[P]
						x_rel = 127 * (point.f - x_start) / x_range
						y_rel = 127 * (point.pos[C] - y_start) / y_range
						x_points.append(x_rel)
						y_points.append(y_rel)
					# then run regression to find a reasonable interpolation curve for this stretch
					# TODO what are good error parameters to use for targets?
					#  RMSerr=2.3 and MAXerr=4.5 are pretty darn close, but could maybe be better
					#  RMSerr=9.2 and MAXerr=15.5 is TOO LARGE
					# TODO: modify to return the error values, for easier logging?
					bezier_list = vectorpaths.fit_cubic_bezier(x_points, y_points,
															   rms_err_tol=BEZIER_ERROR_THRESHOLD_BONE_POSITION_RMS,
															   max_err_tol=BEZIER_ERROR_THRESHOLD_BONE_POSITION_MAX)
					# this innately measures both the RMS error and the max error, and i can specify thresholds
					# if it cannot satisfy those thresholds it will split and try again
					# if it has split, then it's not good for my purposes
					# TODO: do something to ensure that control points are guaranteed within the box
					
					if len(bezier_list) == 1:
						# once i find a good interp curve match (if a match is found),
						if DEBUG:
							print("MATCH! bone='%s' : chan=%d : len = %d : i,w,z=%d, %d, %d : sign=%d" % (
								bonename, C, len(bonelist), i, w, z, b_sign))
						if DEBUG_PLOTS:
							bezier_list[0].plotcontrol()
							bezier_list[0].plot()
							plt.plot(x_points, y_points, 'r+')
							plt.show(block=True)
						
						axis_keep_list.append(w)  # then save this proposed endpoint as a valid endpoint,
						i = w  # and move the startpoint to here and keep walking from here
						break
					# TODO: what do i do to handle if i cannot find a good match?
					#  if i let it iterate all the way down to 2 points then it is guaranteed to find a match (cuz linear)
					#  actually it's probably also guaranteed to pass at 3 points. do i want that? hm... probably not?
					pass  # end walking backwards from z to i
				pass  # end "while i < z"
			pass  # end "while i < len(bonelist)"
		# now i have found every frame# that is important for this axis
		if DEBUG and len(axis_keep_list) > 1:
			# ignore everything that found only 1, cuz that would mean just startpoint and endpoint
			# add 1 to the length cuz frame 0 is implicitly important to all axes
			print("bone='%s' : pos : chan=%d   : keep %d/%d" % (bonename, C, len(axis_keep_list) + 1, len(bonelist)))
		# everything that this axis says needs to be kept, is stored
		keepset.update(axis_keep_list)
		pass  # end for x, then y, then z
	# now i have found every frame# that is important due to position changes
	if DEBUG and len(keepset) > 1:
		# if it found only 1, ignore it, cuz that would mean just startpoint and endpoint
		# add 1 to the length cuz frame 0 is implicitly important to all axes
		print("bone='%s' : pos : chan=ALL : keep %d/%d" % (bonename, len(keepset) + 1, len(bonelist)))
	return keepset


def simplify_boneframes(allbonelist: List[vmdstruct.VmdBoneFrame]) -> List[vmdstruct.VmdBoneFrame]:
	"""
	dont yet care about phys on/off... but, eventually i should.
	only care about x/y/z/rotation
	
	:param allbonelist:
	:return:
	"""
	
	output = []
	
	# verify there is no overlapping frames, just in case
	allbonelist = vmdutil.assert_no_overlapping_frames(allbonelist)
	# sort into dict form to process each morph independently
	bonedict = vmdutil.dictify_framelist(allbonelist)
	
	# analyze each morph one at a time
	for bonename, bonelist in bonedict.items():
		# print(bonename, len(bonelist))
		# if bonename != "センター": # or bonename == "左足ＩＫ":
		# 	continue
		# if bonename != "上半身": # or bonename == "左足ＩＫ":
		# 	continue
		
		if len(bonelist) <= 2:
			output.extend(bonelist)
			continue
		
		# since i need to analyze what's "important" along 4 different channels,
		# i think it's best to store a set of the indices of the frames that i think are important?
		keepset = set()
		
		# the first frame is always kept.
		keepset.add(0)
		
		#######################################################################################
		if SIMPLIFY_BONE_POSITION:
			keepset.update(_simplify_boneframes_position(bonename, bonelist))
			
		#######################################################################################
		# now, i walk along the frames analyzing the ROTATION channel. this is the hard part.
		if SIMPLIFY_BONE_ROTATION:
			i = 0
			while i < (len(bonelist) - 1):
				# start walking down this list
				# assume that i is the start point of a potentially over-keyed section
				b_this = bonelist[i]
				b_next = bonelist[i + 1]
				# find the delta for this channel
				deltaquat_AB = core.hamilton_product(core.my_quat_conjugate(core.euler_to_quaternion(b_this.rot)),
													 core.euler_to_quaternion(b_next.rot))
				
				# now, walk FORWARD from here until i identify a frame z that has a significantly different angle delta
				# everything between i and z might be in a over-key section!
				def foober(start):
					ret = ""
					for zz in range(start, start+10):
						# if i reach the end of the bonelist, then "return" the final valid index
						if zz == len(bonelist) - 1:
							break
						zz_this = bonelist[zz]
						zz_next = bonelist[zz + 1]
						deltaquatt_CD = core.hamilton_product(core.my_quat_conjugate(core.euler_to_quaternion(zz_this.rot)),
															 core.euler_to_quaternion(zz_next.rot))
						# what is the angle between these two deltas? are the rotations moving the same direction?
						factorr = get_corner_sharpness_factor(deltaquat_AB, deltaquatt_CD)
						ret += "%.3f, " % factorr
						
					return ret
				
				z = 0  # to make pycharm shut up
				# FACTORS = []
				# for z in range(i+1, 1000):
				for z in range(i + 1, len(bonelist)):
					# if i reach the end of the bonelist, then "return" the final valid index
					if z == len(bonelist) - 1:
						break
					z_this = bonelist[z]
					z_next = bonelist[z + 1]
					# TODO: compare AB to CD or compare AB to AD ?
					deltaquat_CD = core.hamilton_product(core.my_quat_conjugate(core.euler_to_quaternion(z_this.rot)),
														 core.euler_to_quaternion(z_next.rot))
					# what is the angle between these two deltas? are the rotations moving the same direction?
					factor = get_corner_sharpness_factor(deltaquat_AB, deltaquat_CD)
					# FACTORS.append(factor)
					# TODO: for debug graphing, i want to do this same thing 10 units farther...
					if factor >= BONE_ROTATION_STRAIGHTNESS_VALUE:
						# if this is potentially part of the same sequence, keep iterating
						pass
					else:
						# if this is definitely no longer part of the sequence, THEN i can break
						print(foober(z))
						
						break
				# plt.plot(FACTORS)
				# plt.show(block=True)
				
				# now i have z, and anything past z is DEFINITELY NOT the endpoint for this sequence
				# if AB has zero rotation, then the whole sequence has zero rotation, so i already know it's linear and i don't need to try to fit a curve to it
				# if math.fabs(deltaquat_AB[0] - 1.0) < 0.000001:
				if core.my_euclidian_distance(deltaquat_AB[1:4]) < 1e-8:
					keepset.add(z)  # then save this proposed endpoint as a valid endpoint,
					i = z  # and move the startpoint to here and keep walking from here
					continue
				
				# now i know i've got something interesting to work with!
				# from z, walk backward and test endpoint quality at each frame
				x_points = []
				y_points = []
				x_start = b_this.f
				y_start = core.euler_to_quaternion(b_this.rot)
				# gonna need to do a bunch of testing to quantify what "acceptably good" looks like tho
				for w in range(z, i, -1):
					# calculate the x,y (scale of 0 to 1) for all points between i and "test"
					# calculate the "angular distance" from the start rotation to the end rotation... right?
					y_range = (1 - get_corner_sharpness_factor(y_start, core.euler_to_quaternion(bonelist[w].rot)))
					if y_range == 0:
						# TODO HOW SI THIS STILL HAPPENING?!
						print("what")
					x_range = bonelist[w].f - x_start
					x_points.clear()
					y_points.clear()
					for P in range(i, w + 1):
						point = bonelist[P]
						x_rel = 128 * (point.f - x_start) / x_range
						y_rel = 128 * (1 - get_corner_sharpness_factor(y_start, core.euler_to_quaternion(point.rot))) / y_range
						x_points.append(x_rel)
						y_points.append(y_rel)
					# then run regression to find a reasonable interpolation curve for this stretch
					# TODO what are good error parameters to use for targets?
					#  RMSerr=2.3 and MAXerr=4.5 are pretty darn close, but could maybe be better
					#  RMSerr=9.2 and MAXerr=15.5 is TOO LARGE
					# TODO: modify to return the error values, for easier logging?
					bezier_list = vectorpaths.fit_cubic_bezier(x_points, y_points,
															   rms_err_tol=BEZIER_ERROR_THRESHOLD_BONE_POSITION_RMS,
															   max_err_tol=BEZIER_ERROR_THRESHOLD_BONE_POSITION_MAX)
					# this innately measures both the RMS error and the max error, and i can specify thresholds
					# if it cannot satisfy those thresholds it will split and try again
					# if it has split, then it's not good for my purposes
					# TODO: do something to ensure that control points are guaranteed within the box
					
					if len(bezier_list) == 1:
						# once i find a good interp curve match (if a match is found),
						if DEBUG:
							print("MATCH! bone='%s' : len = %d : i,w,z=%d,%d,%d" % (
								bonename, len(bonelist), i, w, z))
						if DEBUG_PLOTS:
							bezier_list[0].plotcontrol()
							bezier_list[0].plot()
							plt.plot(x_points, y_points, 'r+')
							plt.show(block=True)
						
						keepset.add(w)  # then save this proposed endpoint as a valid endpoint,
						i = w  # and move the startpoint to here and keep walking from here
						break
					# TODO: what do i do to handle if i cannot find a good match?
					#  if i let it iterate all the way down to 2 points then it is guaranteed to find a match (cuz linear)
					#  actually it's probably also guaranteed to pass at 3 points. do i want that? hm... probably not?
					pass
		
		#######################################################################################
		# now done searching for the "important" points, filled "keepset"
		print("RESULT: bone='%s', keep=%d, total=%d, keep%%=%f%%" % (
			bonename, len(keepset), len(bonelist), 100*len(keepset)/len(bonelist)
		))
		# now that i have filled the "keepidx" set, turn those into frames
		keepframe_indices = sorted(list(keepset))
		# TODO: for each of them, re-calculate the best interpolation curve for each channel based on the frames between the keepframes
		pass  # end "for each bonename, bonelist"
	return output

def main(moreinfo=True):
	###################################################################################
	# prompt for inputs
	# vmd = vmdlib.read_vmd("../../../Apple Pie_Cam-interpolated.vmd")
	vmd = vmdlib.read_vmd("../../../marionette motion 1person.vmd")
	# simplify_morphframes(vmd.morphframes)
	
	simplify_boneframes(vmd.boneframes)
	
	
	# framenums = [cam.f for cam in vmd.camframes]
	# rotx = [cam.rot[0] for cam in vmd.camframes]
	# roty = [cam.rot[1] for cam in vmd.camframes]
	# rotz = [cam.rot[2] for cam in vmd.camframes]
	# plt.plot(framenums, rotx, label="x")
	# plt.plot(framenums, roty, label="y")
	# plt.plot(framenums, rotz, label="z")
	# plt.legend()
	# plt.show()
	
	for i in range(len(vmd.camframes) - 1):
		cam = vmd.camframes[i]
		nextcam = vmd.camframes[i+1]
		rot_delta = [f - i for f,i in zip(nextcam.rot, cam.rot)]
		framedelta = nextcam.f - cam.f
		rot_delta = [r/framedelta for r in rot_delta]
		# print(cam.rot)
		try:
			r1 = rot_delta[0] / rot_delta[1]
		except ZeroDivisionError:
			r1 = 0
		try:
			r2 = rot_delta[1] / rot_delta[2]
		except ZeroDivisionError:
			r2 = 0
		try:
			r3 = rot_delta[0] / rot_delta[2]
		except ZeroDivisionError:
			r3 = 0
		if cam.f in (460, 2100, 2149):
			print('hi')
		print(cam.f, round(r1, 3), round(r2, 3), round(r3, 3))
	
	###################################################################################
	# write outputs
	#
	#
	#
	core.MY_PRINT_FUNC("")
	# output_filename_vmd = core.filepath_insert_suffix(input_filename_vmd, "_renamed")
	# output_filename_vmd = core.filepath_get_unused_name(output_filename_vmd)
	# vmdlib.write_vmd(output_filename_vmd, vmd, moreinfo=moreinfo)
	
	core.MY_PRINT_FUNC("Done!")
	return None

if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
