import math
from typing import Tuple, Optional, Sequence

# import numpy as np
# import matplotlib.pyplot as plt
import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_vmd_parser as vmdlib
from mmd_scripting.core.nuthouse01_vmd_utils import dictify_framelist

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.04 - 8/19/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

ANGLE_SHARPNESS_FACTORS = []




# if 1, slope outside a cut will be set to 0. AKA after a cut, accelerate from a stop.
# if 2, slope outside a cut will be calculated to "point at" the control point for the opposite side.
# this should produce a smooth, pleasant motion curve.
HOW_TO_HANDLE_SINGLE_SIDE_CUTPOINT = 2 ###

# a double cutpoint means a segment with cuts on either end. like 9 to 34 if given frames 8,9,34,35
# if 1, the segment will begin/end with slope 0, AKA begin by accelerating from rest and stop by decelerating to rest.
# if 2, the segment will have linear slope.
HOW_TO_HANDLE_DOUBLE_CUTPOINT = 1 ###


# 1.0 = totally average them (perfectly smooth transition), 0.0 = no change from linear path
AVERAGE_SLOPES_BY_HOW_MUCH = 1.0 ###


# at a turnaround point, one side will "want" to have a negative slope. but, that's impossible.
# if 1, set both sides of the turnaround to slope of 0.
# if 2, set the negative side to slope 0, the other side is unmodified.
HOW_TO_HANDLE_TURNAROUND_POINTS = 1 ###


# option: angle-bisector averaging or total-slope averaging
# if 1, use angle-bisector averaging
# if 2, use the total-slope smoothing idea
HOW_TO_FIND_DESIRED_SLOPE_FOR_SCALAR = 1 ###
HOW_TO_FIND_DESIRED_SLOPE_FOR_ROTATION = 1 ###


# option: do you want to treat adjacent frames of bones within a model as though
# they represent a cut? they probably dont. models don't generally cut between
# discrete poses, that would make the physics freak out.
TREAT_ADJACENT_BONEFRAMES_AS_JUMPCUT = False ###


# TODO
# option: how do I turn the 0-180 degree "how sharp is the corner when transitioning
# between these two rotations" value into a factor to multiply the slopes by?
# if 1, disabled (no slowdown, even when perfectly reversing the direction)
# if 2, linear (half-speed at 90deg, full stop at 180deg)
# if 3, suqare-root (more than half speed at 90deg, full stop at 180deg)
# if 4, floored piecewise (full speed from 0-90deg, then 0.75speed at 135deg and 0.5speed at 180deg)
ROTATION_CORNER_SHARPNESS_FACTOR_MODE = 2 ###


# if 1, control points are placed on a circle centered around the corners
# if 2, control points are placed on a diagonal line
CONTROL_POINT_PLACING_METHOD = 1 ###

# range [0.0-1.0], control distance from corner to control point.
# higher number makes the bezier curve S-bends more pronounced.
CONTROL_POINT_ECCENTRICITY = 0.8 ###




# my tester guy is useless. i'll have to do it myself.


# TODO helptext
helptext = '''=================================================
vmd_animation_smoothing:
This script will modify a VMD and change the interpolation curve values to attempt to "smooth" all the motions.
This will work on both model motions and camera motions.
It does not change any of the actual keyframe poses.
It ignores any existing interpolation curves and creates new ones.
Results will not be perfect, but it should be a good starting point.
!!! THIS IS STILL A WORK IN PROGRESS !!!
There are many tuneable parameters near the top of the file, please experiment and find out what looks best to you.

Output: VMD file '[vmdname]_smoothed.vmd'
'''



# don't touch these
MAX_CIRCLE_RADIUS = 1.4142135623730951 / 2
CURRENT_BONENAME = ""
NAME_FOR_CAMFRAMES = "..."
CLOSE_TO_ZERO = 0.001

'''
def calculate_approach_depart_slope(A: Optional[Tuple[int,float]],
									B: Tuple[int,float],
									C: Optional[Tuple[int,float]]) -> Tuple[float,float]:
	"""
	Calculate the approach-slope and depart-slope of the bezier interpolation curve for point B, when
	given the points before it and after it. These are not the "true" slope, they have been scaled to
	the 1/1 reference frame of the interpolation curve.
	
	The inside edges of a cutpoint segment are assigned a slope of 1.
	The borders of a cutpoint segment are assigned a slope of -1 and are handled later once all
	cutpoints are detected and all non-cutpoint slopes are calculated.
	
	:param A: tuple(X,Y) or None
	:param B: tuple(X,Y)
	:param C: tuple(X,Y) or None
	:return: tuple(B-approach, B-depart)
	"""
	
	# first, check if either AB or BC are cut transitions, and handle appropriately
	if A is None or B[0] - A[0] == 1:
		# AB is a cutpoint!
		# mark B-approach as a cutpoint (1) and B-depart as a cutpoint border (-1)
		return 1, -1
	if C is None or C[0] - B[0] == 1:
		# BC is a cutpoint!
		# mark B-approach as a cutpoint border (-1) and B-depart as a cutpoint (1)
		return -1, 1
	
	# second, calculate the true slope of AC, AB, and BC
	# true_slope is the total amount the metric changes over the total time between the frames
	true_slope = (C[1] - A[1]) / (C[0] / A[0])
	ab_slope = (B[1] - A[1]) / (B[0] / A[0])
	bc_slope = (C[1] - B[1]) / (C[0] / B[0])
	
	# third, normalize the true slope by the frame-to-frame slope to get the normalized reference frame used by the bezier curve
	# if a slope is 0, then the metric value isn't changing so the slope doesn't matter, so leave it at linear(1)
	b_slope_approach = 1
	b_slope_depart = 1
	if ab_slope != 0:
		b_slope_approach = true_slope / ab_slope
	if bc_slope != 0:
		b_slope_depart = true_slope / bc_slope
	
	# fourth, negative slopes are impossible. if either slope is negative, set both to 0.
	# negative slopes will happen if B is a "turnaround frame", a local min or local max compared to A and C
	if b_slope_approach < 0 or b_slope_depart < 0:
		b_slope_approach = 0
		b_slope_depart = 0
	
	return b_slope_approach, b_slope_depart
'''



# angle-friendly tangent solving:
# 3 convert this real-space slope to an angle, average them, and then convert back to slope again
# 4 use the frame-gap and the total angle delta to normalize this to the bezier reference scope

'''
# this is garbage now.
def detect_quaternion_slerp_wraparound(Arot: List[float],
									   Brot: List[float]) -> Tuple[int,int,int]:
	"""
	This will count the number of times the SLERP path will wrap around in angle-space for X/Y/Z.
	Returns 3 ints where +1 means it wraps while increasing (pos to neg) and -1 means it wraps while
	decreasing (neg to pos).
	
	:param Arot: euler angles, startpoint
	:param Brot: euler angles, endpoint
	:return: tuple of ints (x,y,z)
	"""
	Aquat = core.euler_to_quaternion(Arot)
	Bquat = core.euler_to_quaternion(Brot)
	retme = [0,0,0]
	prev_angle = Arot
	# run slerp at 50 different points along the length of the path,
	for i in range(1,WRAPAROUND_CHECK_RESOLUTION+1):
		this_quat = core.my_slerp(Aquat, Bquat, (i/WRAPAROUND_CHECK_RESOLUTION))
		# find the angle it is at,
		this_angle = core.quaternion_to_euler(this_quat)
		for j in range(3):
			# check each axis independently for wraps
			if prev_angle[j] > 100 and this_angle[j] < -100:
				# this has wrapped from very positive to very negative
				retme[j] += 1
			if prev_angle[j] < -100 and this_angle[j] > 100:
				# this has wrapped from very negative to very positive
				retme[j] += -1
		# save this into prev to compare the next segment
		prev_angle = this_angle
	# return the list as a tuple
	return retme[0], retme[1], retme[2]
'''
'''
# TODO this is garbage now?
def calculate_rotation_truespace_slope(A: Optional[vmdstruct.VmdBoneFrame],
									   B: vmdstruct.VmdBoneFrame,
									   C: Optional[vmdstruct.VmdBoneFrame]) -> Tuple[List[float],List[float]]:
	# because it requires slerp, x/y/z need to be done all at the same time
	# returns approach[x,y,z],depart[x,y,z]
	angle_b = B.rot
	
	if A is not None:
		# 1 slerp by 1% and 99% to find the approach and depart deltas
		# NOTE: it is unlikely but possible that a wraparound may happen in the first or last 1% of a slerp
		# thats just a risk i'll have to take
		qe_approach = core.my_slerp(core.euler_to_quaternion(B.rot), core.euler_to_quaternion(A.rot), 0.01)
		# 2 convert to euler space
		angle_approach = core.quaternion_to_euler(qe_approach)
		# 3 calculate the angle-delta and time-delta
		delta_approach = [e - s for e, s in zip(angle_b, angle_approach)]
		timedelta_approach = B.f - A.f
		# 4 find anglular delta per frame, "true slope"
		# if it were perfectly linear then this delta would be 1/100th of the total angle change over the total time duration
		# therefore to make things right it must be multiplied by 100 before dividing by the time delta
		slopes_approach = [100 * ad / timedelta_approach for ad in delta_approach]
	else:
		slopes_approach = [1,1,1]
		
	if C is not None:
		qe_depart = core.my_slerp(core.euler_to_quaternion(B.rot), core.euler_to_quaternion(C.rot), 0.01)
		angle_depart = core.quaternion_to_euler(qe_depart)
		delta_depart = [e - s for e, s in zip(angle_depart, angle_b)]
		timedelta_depart = C.f - B.f
		slopes_depart = [100 * ad / timedelta_depart for ad in delta_depart]
	else:
		slopes_depart = [1,1,1]
		
	# this is the real-space angular delta per frame
	return slopes_approach, slopes_depart
'''


def scalar_calculate_ideal_bezier_slope(A: Optional[Tuple[int, float]],
										B: Tuple[int, float],
										C: Optional[Tuple[int, float]]) -> Tuple[float, float]:
	"""
	Calculate the ideal bezier slope for any scalar interpolation curve.
	Works for positional x/y/z, or field-of-view, or camera distance.

	:param A: tuple(frame, value) or None
	:param B: tuple(frame, value)
	:param C: tuple(frame, value) or None
	:return: ideal bezier slopes, 2 floats, tuple(approach,depart)
	"""
	if A is None and C is None:  # both sides are cutpoints
		return 1, 1
	if A is None:  # AB is an endpoint!
		# mark B-approach as a cutpoint (1) and B-depart as a cutpoint border (-1)
		return 1, -1
	if C is None:  # BC is an endpoint!
		# mark B-approach as a cutpoint border (-1) and B-depart as a cutpoint (1)
		return -1, 1
	# now i can proceed knowing that A and C are guaranteed to not be None
	
	# first, determine the current truespace slope for each side
	valuedelta_AB = B[1] - A[1]
	valuedelta_BC = C[1] - B[1]
	# do some rounding to make extremely small numbers become zero
	if valuedelta_AB < CLOSE_TO_ZERO: valuedelta_AB = 0
	if valuedelta_BC < CLOSE_TO_ZERO: valuedelta_BC = 0
	# slope = rise(valuedelta) over run(timedelta)
	slope_AB = valuedelta_AB / (B[0] - A[0])
	slope_BC = valuedelta_BC / (C[0] - B[0])
	
	# second, combine/average them to get the desired truespace slope
	if HOW_TO_FIND_DESIRED_SLOPE_FOR_SCALAR == 1:
		# desired = angle bisector method
		desired_approach, desired_depart = calculate_slope_bisectors(slope_AB, slope_BC, AVERAGE_SLOPES_BY_HOW_MUCH)
	else:  # elif HOW_TO_FIND_DESIRED_SLOPE_FOR_POSITION == 2:
		# desired = total rise over total run
		total_slope = (C[1] - A[1]) / (C[0] - A[0])
		blend = AVERAGE_SLOPES_BY_HOW_MUCH
		desired_approach = (blend * total_slope) + ((blend - 1) * slope_AB)
		desired_depart = (blend * total_slope) + ((blend - 1) * slope_BC)
		
	# third, convert the desired truespace slope to the bezier reference frame
	# also handle any corner cases
	out1, out2 = desired_truespace_slope_to_bezier_slope((B[0] - A[0], valuedelta_AB),
														 desired_approach,
														 (C[0] - B[0], valuedelta_BC),
														 desired_depart)
	# return exactly 1 approach slope and one depart slope
	return out1, out2


def rotation_calculate_ideal_bezier_slope(A: Optional[Tuple[int, Sequence[float]]],
										  B: Tuple[int, Sequence[float]],
										  C: Optional[Tuple[int, Sequence[float]]]) -> Tuple[float,float]:
	"""
	Calculate the ideal bezier slope for rotation interpolation curve. There is
	only one Bezier curve for the entire 3d rotation, meaning it can vary the speed
	along the path between keyframes but cannot deviate from that path.
	Part 1 is speeding/slowing to match angular speed when approaching/leaving a keyframe.
	Part 2 is detecting the "sharpness" of the corners and slowing down when approaching/leaving
	a sharp corner.
	
	:param A: tuple(frame, euler xyz) or None
	:param B: tuple(frame, euler xyz)
	:param C: tuple(frame, euler xyz) or None
	:return: ideal bezier slopes, 2 floats, tuple(approach,depart)
	"""
	if A is None and C is None: # both sides are cutpoints
		return 1,1
	if A is None: # AB is an endpoint!
		# mark B-approach as a cutpoint (1) and B-depart as a cutpoint border (-1)
		return 1, -1
	if C is None: # BC is an endpoint!
		# mark B-approach as a cutpoint border (-1) and B-depart as a cutpoint (1)
		return -1, 1
	# now i can proceed knowing that A and C are guaranteed to not be None
	
	quatA = core.euler_to_quaternion(A[1])
	quatB = core.euler_to_quaternion(B[1])
	quatC = core.euler_to_quaternion(C[1])
	
	# first, calc angle between each quat to get slerp "length"
	# technically the clamp shouldn't be necessary but floating point inaccuracy caused it to die
	asdf = abs(core.my_dot(quatA, quatB))
	asdf = core.clamp(asdf, -1.0, 1.0)
	angdist_AB = math.acos(asdf)
	asdf = abs(core.my_dot(quatB, quatC))
	asdf = core.clamp(asdf, -1.0, 1.0)
	angdist_BC = math.acos(asdf)
	# do some rounding to make extremely small numbers become zero
	if angdist_AB < CLOSE_TO_ZERO: angdist_AB = 0
	if angdist_BC < CLOSE_TO_ZERO: angdist_BC = 0
	# print(math.degrees(angdist_AB), math.degrees(angdist_BC))
	# use framedelta to turn the "length" into "speed"
	# this is also the "truespace slope" of the approach/depart
	# cannot be negative, can be zero
	angslope_AB = angdist_AB / (B[0] - A[0])
	angslope_BC = angdist_BC / (C[0] - B[0])
	# second, average/compromise them to get the "desired truespace slope"
	if HOW_TO_FIND_DESIRED_SLOPE_FOR_ROTATION == 1:
		# desired = angle bisector method
		angslope_AB, angslope_BC = calculate_slope_bisectors(angslope_AB, angslope_BC, AVERAGE_SLOPES_BY_HOW_MUCH)
	else:  # elif HOW_TO_FIND_DESIRED_SLOPE_FOR_POSITION == 2:
		# desired = total angular distance over total time
		total_slope = (angdist_AB + angdist_BC) / (C[0] - A[0])
		blend = AVERAGE_SLOPES_BY_HOW_MUCH
		angslope_AB = (blend * total_slope) + ((blend - 1) * angslope_AB)
		angslope_BC = (blend * total_slope) + ((blend - 1) * angslope_BC)
	
	# third, determine how sharp the corner is [0-1]. 3d rotations are wierd.
	# reduce the slopes by this factor.
	factor = get_corner_sharpness_factor(quatA, quatB, quatC)
	angslope_AB *= factor
	angslope_BC *= factor
	if angdist_AB != 0 and angdist_BC != 0 and B[0] - A[0] != 0 and C[0] - B[0] != 0:
		# print(factor)
		ANGLE_SHARPNESS_FACTORS.append(factor)
	
	# fourth, scale the desired truespace slope to the bezier scale
	# also handle any corner cases
	out1, out2 = desired_truespace_slope_to_bezier_slope((B[0] - A[0], angdist_AB),
														 angslope_AB,
														 (C[0] - B[0], angdist_BC),
														 angslope_BC)
	# return exactly 1 approach slope and one depart slope
	return out1, out2


def get_corner_sharpness_factor(quatA: Tuple[float,float,float,float],
								quatB: Tuple[float,float,float,float],
								quatC: Tuple[float,float,float,float]) -> float:
	"""
	Calculate a [0.0-1.0] factor indicating how "sharp" the corner is at B.
	By "corner" I mean the directional change when A->B stops and B->C begins.
	If they are going the same angular "direction", then return 1.0. If they
	are going perfectly opposite directions, return 0.0. Otherwise return something
	in between.
	The option ROTATION_CORNER_SHARPNESS_FACTOR_MODE controls what the transfer
	curve looks like from angle to factor.
	
	:param quatA: quaterinon WXYZ for frame A
	:param quatB: quaterinon WXYZ for frame B
	:param quatC: quaterinon WXYZ for frame C
	:return: float [0.0-1.0]
	"""
	# to compensate for the angle difference, both will be slowed by some amount
	# IDENTICAL IMPACT
	
	# first, find the deltas between the quaternions
	deltaquat_AB = core.hamilton_product(core.my_quat_conjugate(quatA), quatB)
	deltaquat_BC = core.hamilton_product(core.my_quat_conjugate(quatB), quatC)
	# to get sensible results below, ignore the "W" component and only use the XYZ components, treat as 3d vector
	deltavect_AB = deltaquat_AB[1:4]
	deltavect_BC = deltaquat_BC[1:4]
	# second, find the angle between these two deltas
	# use the plain old "find the angle between two vectors" formula
	t = core.my_euclidian_distance(deltavect_AB) * core.my_euclidian_distance(deltavect_BC)
	if t == 0:
		# this happens when one vector has a length of 0
		ang_d = 0
	else:
		# technically the clamp shouldn't be necessary but floating point inaccuracy caused it to do math.acos(1.000000002) which crashed lol
		shut_up = core.my_dot(deltavect_AB, deltavect_BC) / t
		shut_up = core.clamp(shut_up, -1.0, 1.0)
		ang_d = math.acos(shut_up)
	# print(math.degrees(ang_d))
	# if ang = 0, perfectly colinear, factor = 1
	# if ang = 180, perfeclty opposite, factor = 0
	factor = 1 - (math.degrees(ang_d) / 180)
	# print(factor)
	# ANGLE_SHARPNESS_FACTORS.append(factor)
	if ROTATION_CORNER_SHARPNESS_FACTOR_MODE == 1:
		# disabled
		out_factor = 1
	elif ROTATION_CORNER_SHARPNESS_FACTOR_MODE == 2:
		# linear
		out_factor = factor
	elif ROTATION_CORNER_SHARPNESS_FACTOR_MODE == 3:
		# square root
		out_factor = math.sqrt(factor)
	elif ROTATION_CORNER_SHARPNESS_FACTOR_MODE == 4:
		# piecewise floored, (0,.5) to (.5,1)
		out_factor = 0.5 + factor
		out_factor = core.clamp(out_factor, 0.0, 1.0)
	else:
		out_factor = 1
	out_factor = core.clamp(out_factor, 0.0, 1.0)
	return out_factor
	



def calculate_slope_bisectors(approach_slope: float, depart_slope: float, blend:float) -> Tuple[float, float]:
	"""
	"Average" two slopes by treating them as angles and finding the angle that bisects them.
	Is this better or worse than my original idea? No clue!
	By changing the value of AVERAGE_SLOPES_BY_HOW_MUCH you can control how much it moves towards
	this perfect bisector.
	
	:param approach_slope: float real-space slope when approaching a point
	:param depart_slope: float real-space slope when departing a point
	:param blend: float [0-1] how much to move toward perfect average
	:return: tuple(new_approach_slope, new_depart_slope)
	"""
	# this only needs to operate on one pair of slopes at a time
	# 3 convert this real-space slope to an angle, average them, and then convert back to slope again
	approach_angle = math.atan2(approach_slope, 1)
	depart_angle = math.atan2(depart_slope, 1)
	# one more knob to fiddle with: don't need to average these values all the way!
	center = (approach_angle + depart_angle) / 2
	new_approach_angle = (blend * center) + ((blend-1) * approach_angle)
	new_depart_angle = (blend * center) + ((blend-1) * depart_angle)
	
	# convert from angle back to real-space slope
	new_approach_slope = math.tan(new_approach_angle)
	new_depart_slope = math.tan(new_depart_angle)

	return new_approach_slope, new_depart_slope


def desired_truespace_slope_to_bezier_slope(AB: Tuple[int,float],
											slope_approach: float,
											BC: Tuple[int,float],
											slope_depart: float) -> Tuple[float,float]:
	"""
	Scale the truespace approach-slope and depart-slope to the 1/1 reference frame of
	the interpolation curve. Also handles all the edge cases like cutpoints or slope
	of zero. Works for both angle-space and scalar-space.
	
	If a segment has a "true" slope of 0 (metric does not change) then its inside edges are set to 1.
	If a segment is a cutpoint, its inside edges are assigned a slope of 1. Its *outside* edges
	are assigned a slope of -1 and are handled later once all cutpoints are detected and all
	non-cutpoint slopes are calculated.
	If B is a local min/max (a turnaround point) then its edges will be assigned a slope of 0.
	
	:param AB: tuple(frame-delta,value-delta)
	:param slope_approach: float real-space slope when approaching a point
	:param BC: tuple(frame-delta,value-delta)
	:param slope_depart: float real-space slope when departing a point
	:return: tuple(B-approach, B-depart)
	"""
	# in MMD, when two frames are on sequential timesteps, interpolation does not happen between them.
	# it directly jumps from one position to the next, even when rendering at 60fps or higher.
	
	if TREAT_ADJACENT_BONEFRAMES_AS_JUMPCUT or CURRENT_BONENAME == NAME_FOR_CAMFRAMES:
		# first, check if either AB or BC are cut transitions (adjacent frames), and handle appropriately
		if AB[0] == 1 and BC[0] == 1:  # both sides are cutpoints, so it's only on pose B for a single frame
			return 1, 1
		if AB[0] == 1:  # AB is a cutpoint!
			# mark B-approach as a cutpoint (1) and B-depart as a cutpoint border (-1)
			return 1, -1
		if BC[0] == 1:  # BC is a cutpoint!
			# mark B-approach as a cutpoint border (-1) and B-depart as a cutpoint (1)
			return -1, 1
	
	# second, calculate the total slope of AB and BC
	ab_slope = AB[1] / AB[0]
	bc_slope = BC[1] / BC[0]

	# third, handle edge cases:
	if ab_slope == 0:
		# if this segment has a slope of 0, then the metric value isn't changing so the slope doesn't matter, so leave it at linear(1)
		b_slope_approach = 1
	elif bc_slope == 0:
		# if the opposite segment has a slope of 0, then this segment should slow to/accelerate from a stop
		b_slope_approach = 0
	else:
		# normal case: normalize the desired slope by the total slope to get the 1/1 reference frame used by the bezier curve
		b_slope_approach = slope_approach / ab_slope
		
	if bc_slope == 0:
		b_slope_depart = 1
	elif ab_slope == 0:
		b_slope_depart = 0
	else:
		b_slope_depart = slope_depart / bc_slope
		
	# fourth, negative slopes cannot be done in the bezier. if either slope is negative, set both to 0??
	# negative slopes will happen if B is a "turnaround frame", a local min or local max compared to A and C.
	# negative slopes will not happen in angle-space however
	if HOW_TO_HANDLE_TURNAROUND_POINTS == 1:
		if b_slope_approach < 0 or b_slope_depart < 0:
			b_slope_approach = 0
			b_slope_depart = 0
	elif HOW_TO_HANDLE_TURNAROUND_POINTS == 2:
		if b_slope_approach < 0:
			b_slope_approach = 0
		if b_slope_depart < 0:
			b_slope_depart = 0

	return b_slope_approach, b_slope_depart


def make_point_from_slope(slope: float) -> Tuple[int,int]:
	"""
	Create a depart-point (around 0,0) when given a desired slope.
	The distance to the point is based on global options.
	
	:param slope: float slope, from 0-inf
	:return: tuple(x,y) ints from 0-127
	"""
	
	assert slope >= 0
	
	if CONTROL_POINT_PLACING_METHOD == 1:
		# max distance is half of sqrt2, then the circles centered at each corner touch in the middle
		dist = CONTROL_POINT_ECCENTRICITY * MAX_CIRCLE_RADIUS
		# the point is on the circle with radius "dist" centered at 0,0
		# and where that circle intercepts the desired slope line
		# circle: use pythagoras + algebra!
		# dist^2 = x^2 + y^2
		# y = x * slope
		# dist^2 = x^2 + (x*slope)^2
		# dist^2 = xx + xxss
		# dist^2 = xx(1 + ss)
		# dist^2 / (1+ss) = xx
		# sqrt[dist^2 / (1+ss)] = x
		x = math.sqrt((dist**2) / (1 + (slope**2)))
		y = x * slope
	else: #elif CONTROL_POINT_PLACING_METHOD == 2:
		# the point is on the downward-slanting diagonal line with y-intercept "dist"
		# y = x * slope
		# y = -x + dist
		# x * s = -x + dist
		# x * s = x(-1 + dist)
		# ?????
		# x = d / (s + 1), thank you wolframalpha
		dist = CONTROL_POINT_ECCENTRICITY
		x = dist / (slope + 1)
		y = x * slope

	# clamp just to be extra safe
	x = core.clamp(x, 0.0, 1.0)
	y = core.clamp(y, 0.0, 1.0)
	# convert [0-1] to nearest int in [0-127] range
	x = round(x * 127)
	y = round(y * 127)
	return x, y


def main(moreinfo=True):
	# TODO: actually load it in MMD and verify that the curves look how they should
	#  not 100% certain that the order of interpolation values is correct for bone/cam frames
	
	# TODO: some sort of additional stats somehow?
	
	# TODO: progress % trackers?
	
	# prompt VMD file name
	core.MY_PRINT_FUNC("Please enter name of VMD motion input file:")
	input_filename_vmd = core.MY_FILEPROMPT_FUNC("VMD file", ".vmd")
	
	# next, read/use/prune the dance vmd
	vmd = vmdlib.read_vmd(input_filename_vmd, moreinfo=moreinfo)
	
	core.MY_PRINT_FUNC("")
	
	# dictify the boneframes so i can deal with one bone at a time
	boneframe_dict = dictify_framelist(vmd.boneframes)
	
	# add the camframes to the dict so I can process them at the same time
	# this makes the typechecker angry
	if len(vmd.camframes) != 0:
		boneframe_dict[NAME_FOR_CAMFRAMES] = vmd.camframes
	
	# >>>>>> part 0: verify that there are no "multiple frames on the same timestep" situations
	# the MMD GUI shouldn't let this happen, but apparently it has happened... how???
	# the only explanation I can think of is that it's due to physics bones with names that are too long and
	# get truncated, and the uniquifying numbers are in the part that got lost. they originally had one frame
	# per bone but because the names were truncated they look like they're all the same name so it looks like
	# there are many frames for that non-real bone at the same timestep.
	for bonename, boneframe_list in boneframe_dict.items():
		# if a bone has only 1 (or 0?) frames associated with it then there's definitely no overlap probelm
		if len(boneframe_list) < 2:
			continue
		i = 0
		while i < len(boneframe_list)-1:
			# look at all pairs of adjacent frames along a bone
			A = boneframe_list[i]
			B = boneframe_list[i+1]
			# are they on the same timestep? if so, problem!
			if A.f == B.f:
				# are they setting the same pose?
				if A == B:
					# if they are setting the same values at the same frame, just fix the problem silently
					pass
				else:
					# if they are trying to set different values at the same frame, this is a problem!
					# gotta fix it to continue, but also gotta print some kind of warning
					if bonename == NAME_FOR_CAMFRAMES:
						core.MY_PRINT_FUNC("WARNING: at timestep t=%d, there are multiple cam frames trying to set different poses. How does this even happen???" % A.f)
					else:
						core.MY_PRINT_FUNC("WARNING: at timestep t=%d, there are multiple frames trying to set bone '%s' to different poses. How does this even happen???" % (A.f, bonename))
					core.MY_PRINT_FUNC("I will delete one of them and continue.")
				# remove the 2nd one so that there is only one frame at each timestep
				boneframe_list.pop(i+1)
				continue
			# otherwise, no problem at all
			i += 1
	
	# >>>>>> part 1: identify the desired slope for each metric of each frame
	core.MY_PRINT_FUNC("Finding smooth approach/depart slopes...")
	global CURRENT_BONENAME
	allbone_bezier_slopes = {}
	for bonename in sorted(boneframe_dict.keys()):
		CURRENT_BONENAME = bonename  # you're not supposed to pass info via global like this, but idgaf sue me
		boneframe_list = boneframe_dict[bonename]
		# this will hold all the resulting bezier slopes
		# each item corresponds to one frame and is stored as:
		# [approach posx,y,z,rot],[depart posx,y,z,rot]
		thisbone_bezier_slopes = []
		
		# for each sequence of frames on a single bone,
		for i in range(len(boneframe_list)):
			
			thisframe_bezier_approach = []
			thisframe_bezier_depart = []
			
			A = boneframe_list[i-1] if i != 0 else None
			B = boneframe_list[i]
			C = boneframe_list[i+1] if i != len(boneframe_list)-1 else None
			# now i have the 3 frames I want to analyze
			# need to do the analysis for rotations & for positions
			
			# POSITION
			for j in range(3):
				A_point = (A.f, A.pos[j]) if (A is not None) else None
				B_point = (B.f, B.pos[j])
				C_point = (C.f, C.pos[j]) if (C is not None) else None
				# stuffed all operations into one function for encapsulation
				bez_a, bez_d = scalar_calculate_ideal_bezier_slope(A_point, B_point, C_point)
				# store it
				thisframe_bezier_approach.append(bez_a)
				thisframe_bezier_depart.append(bez_d)
			
			# ROTATION
			A_point = (A.f, A.rot) if (A is not None) else None
			B_point = (B.f, B.rot)
			C_point = (C.f, C.rot) if (C is not None) else None
			# stuffed all operations into one function for encapsulation
			bez_a, bez_d = rotation_calculate_ideal_bezier_slope(A_point, B_point, C_point)
			# store it
			thisframe_bezier_approach.append(bez_a)
			thisframe_bezier_depart.append(bez_d)
			
			# CAMFRAME ONLY STUFF
			if bonename == NAME_FOR_CAMFRAMES:
				# the typechecker expects boneframes so it gets angry here
				# distance from camera to position
				A_point = (A.f, A.dist) if (A is not None) else None
				B_point = (B.f, B.dist)
				C_point = (C.f, C.dist) if (C is not None) else None
				# stuffed all operations into one function for encapsulation
				bez_a, bez_d = scalar_calculate_ideal_bezier_slope(A_point, B_point, C_point)
				# store it
				thisframe_bezier_approach.append(bez_a)
				thisframe_bezier_depart.append(bez_d)
				# field of view
				A_point = (A.f, A.fov) if (A is not None) else None
				B_point = (B.f, B.fov)
				C_point = (C.f, C.fov) if (C is not None) else None
				# stuffed all operations into one function for encapsulation
				bez_a, bez_d = scalar_calculate_ideal_bezier_slope(A_point, B_point, C_point)
				# store it
				thisframe_bezier_approach.append(bez_a)
				thisframe_bezier_depart.append(bez_d)
			
			# next i need to store them in some sensible manner
			# ..., [approach posx,y,z,rot], [depart posx,y,z,rot], ...
			thisbone_bezier_slopes.append(thisframe_bezier_approach)
			thisbone_bezier_slopes.append(thisframe_bezier_depart)
			pass  # end "for each frame in this bone"
		# now i have calculated all the desired bezier approach/depart slopes for both rotation and position
		# next i need to rearrange things slightly
		
		# currently the slopes are stored in "approach,depart" pairs associated with a single frame.
		# but the interpolation curves are stored as "depart, approach" associated with the segment leading up to a frame.
		# AKA, interpolation info stored with frame i is to interpolate from i-1 to i
		# therefore there is no place for the slope when interpolating away from the last frame, pop it
		thisbone_bezier_slopes.pop(-1)
		# the new list needs to start with 1,1,1,1 to interpolate up to the first frame, insert it
		if bonename == NAME_FOR_CAMFRAMES:
			thisbone_bezier_slopes.insert(0, [1]*6)
		else:
			thisbone_bezier_slopes.insert(0, [1]*4)
		# now every pair is a "depart,approach" associated with a single frame
		final = []
		for i in range(0, len(thisbone_bezier_slopes), 2):
			# now store as pairs
			final.append([thisbone_bezier_slopes[i], thisbone_bezier_slopes[i+1]])
		
		assert len(final) == len(boneframe_list)
		
		# save it!
		allbone_bezier_slopes[bonename] = final
		pass  # end of "for each bone
		
	# >>>>>> part 2: calculate the x/y position of the control points for the curve, based on the slope
	core.MY_PRINT_FUNC("Calculating control points...")
	allbone_bezier_points = {}
	for bonename in sorted(allbone_bezier_slopes.keys()):
		bezier_for_one_frame = allbone_bezier_slopes[bonename]
		thisbone_bezier_points = []
		for depart_slopes, approach_slopes in bezier_for_one_frame:
			slopes_per_channel = list(zip(depart_slopes, approach_slopes))
			# print(slopes_per_channel)
			depart_points = []
			approach_points = []
			for depart_slope, approach_slope in slopes_per_channel:
				# now i have the approach & depart for one channel of one frame of one bone
				# 1. handle double-sided cutpoint
				if approach_slope == -1 and depart_slope == -1:
					# this is a double-sided cutpoint!
					# see where the global is declared to understand the modes
					if HOW_TO_HANDLE_DOUBLE_CUTPOINT == 1:
						approach_slope, depart_slope = 0,0
					else: #elif HOW_TO_HANDLE_DOUBLE_CUTPOINT == 2:
						approach_slope, depart_slope = 1,1
						
				# 3a. in this mode the cutpoint is handled BEFORE normal calculation
				if HOW_TO_HANDLE_SINGLE_SIDE_CUTPOINT == 1:
					if approach_slope == -1:
						approach_slope = 0
					if depart_slope == -1:
						depart_slope = 0
				
				# 2. base case: calculate the point position based on the slope
				depart_point = (10,10)
				approach_point = (117,117)
				if approach_slope != -1:
					# note: the approach point is based on 127,127
					approach_point = tuple(127 - p for p in make_point_from_slope(approach_slope))
				if depart_slope != -1:
					depart_point = make_point_from_slope(depart_slope)
					
				# 3b. handle the one-sided cutpoint
				if HOW_TO_HANDLE_SINGLE_SIDE_CUTPOINT == 2:
					# fancy "point at the control point of the other side" idea
					# define the slope via the opposing control point and re-run step 2
					if approach_slope == -1:
						# note: depart_point[0] can be 127, if so then this is divide by 0
						if depart_point[0] == 127:
							approach_slope = 1000
						else:
							approach_slope = (depart_point[1] - 127) / (depart_point[0] - 127)
						# note: the approach point is based on 127,127
						approach_point = tuple(127 - p for p in make_point_from_slope(approach_slope))
					if depart_slope == -1:
						# note: approach_point[0] CAN BE 0, in theory.
						if approach_point[0] == 0:
							depart_slope = 1000
						else:
							depart_slope = approach_point[1] / approach_point[0]
						depart_point = make_point_from_slope(depart_slope)
				
				# 4. accumulate teh channels
				depart_points.append(depart_point)
				approach_points.append(approach_point)
				pass  # end "for one channel of one frame of one bone"
			# 5. accumulate all the frames
			thisbone_bezier_points.append([depart_points, approach_points])
			pass  # end "for one frame of one bone"
		# 6. accumulate teh bones
		allbone_bezier_points[bonename] = thisbone_bezier_points
		pass  # end "for one bone"
	
	# >>>>>> part 3: store this into the boneframe & un-dictify the frames to put it back into the VMD
	for bonename in sorted(boneframe_dict.keys()):
		boneframe_list = boneframe_dict[bonename]
		bezier_points_list = allbone_bezier_points[bonename]
		if bonename == NAME_FOR_CAMFRAMES:
			# this is a list of camframes!
			# for each frame & associated points,
			for camframe, b in zip(boneframe_list, bezier_points_list):
				# unpack this "b" thing into named values
				# top level: [a,b]
				# next level: [x,y,z,r,dist,fov]
				# innermost level: [x,y]
				((x_ax, x_ay), (y_ax,y_ay),(z_ax,z_ay),(r_ax,r_ay),(dist_ax,dist_ay),(fov_ax,fov_ay)), \
				((x_bx, x_by), (y_bx,y_by),(z_bx,z_by),(r_bx,r_by),(dist_bx,dist_by),(fov_bx,fov_by)) = b
				
				# overwrite the interp_? members of this camframe with the newly-calculated control points
				camframe.interp_x = [x_ax, x_ay, x_bx, x_by]
				camframe.interp_y = [y_ax, y_ay, y_bx, y_by]
				camframe.interp_z = [z_ax, z_ay, z_bx, z_by]
				camframe.interp_r = [r_ax, r_ay, r_bx, r_by]
				camframe.interp_dist = [dist_ax, dist_ay, dist_bx, dist_by]
				camframe.interp_fov = [fov_ax, fov_ay, fov_bx, fov_by]
				
		else:
			# for each frame & associated points,
			for boneframe, b in zip(boneframe_list, bezier_points_list):
				# unpack this "b" thing into named values
				((x_ax, x_ay), (y_ax,y_ay),(z_ax,z_ay),(r_ax,r_ay)), \
				((x_bx, x_by), (y_bx,y_by),(z_bx,z_by),(r_bx,r_by)) = b
				# overwrite the interp_? members of this camframe with the newly-calculated control points
				# this goes into the actual boneframe object still in the lists in boneframe_dict
				boneframe.interp_x = [x_ax, x_ay, x_bx, x_by]
				boneframe.interp_y = [y_ax, y_ay, y_bx, y_by]
				boneframe.interp_z = [z_ax, z_ay, z_bx, z_by]
				boneframe.interp_r = [r_ax, r_ay, r_bx, r_by]
	
	# un-dictify it!
	# first, extract the camframes
	if NAME_FOR_CAMFRAMES in boneframe_dict:
		vmd.camframes = boneframe_dict.pop(NAME_FOR_CAMFRAMES)
	# then do the boneframes
	# the names dont matter, make a list of all the lists in the dict
	asdf = list(boneframe_dict.values())
	# flatten it
	flat_boneframe_list = [item for sublist in asdf for item in sublist]
	vmd.boneframes = flat_boneframe_list
	
	core.MY_PRINT_FUNC("")
	# write out the VMD
	output_filename_vmd = core.filepath_insert_suffix(input_filename_vmd, "_smoothed")
	output_filename_vmd = core.filepath_get_unused_name(output_filename_vmd)
	vmdlib.write_vmd(output_filename_vmd, vmd, moreinfo=moreinfo)
	
	# H = plt.hist([j for j in ANGLE_SHARPNESS_FACTORS if j!=0 and j!=1], bins=40, density=True)
	# print("factors=", len(ANGLE_SHARPNESS_FACTORS))
	# H = plt.hist(ANGLE_SHARPNESS_FACTORS, bins=16, density=True)
	# plt.show()
	
	core.MY_PRINT_FUNC("Done!")
	return None

if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
