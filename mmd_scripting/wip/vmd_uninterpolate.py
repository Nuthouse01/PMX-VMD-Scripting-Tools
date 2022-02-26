import math
from typing import List, Tuple, Set, Sequence, Callable, Any, Generator
import time

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_vmd_parser as vmdlib
import mmd_scripting.core.nuthouse01_vmd_struct as vmdstruct
import mmd_scripting.core.nuthouse01_vmd_utils as vmdutil
from mmd_scripting.vectorpaths_chrisarridge import vectorpaths

import cProfile
import pstats
import logging

"""
There are too many problems with this task, and the benefit for if I get
it working is too small. This script is indefinitely shelved.

1. The major problem with trying to "uninterpolate" a VMD file is the fact that
the bezier-fitting algorithm has too much difficulty finding the correct
solution, even when an exact solution exists. Its threshold for "good enough"
is too easy to reach with an imperfect solution, which means that the algorithm
will insert more endpoints than necessary.
The current vectorpaths algorithm is "iterate until total error is below a threshold",
but in order to get a proper match I need to change the algorithm to "iterate
until error stops improving", and when I do that it jumps from ~50 iterations to ~800
iterations for evaluating one potential endpoint.
It simply is not suited to matching control points when they are in the extreme
corners.
Also, it doesn't leverage the fact that the control points must be within
a specific box; that should reduce the possibility space immensely but I don't
know how the algorithm could be changed to leverage this.

2. Second, I don't know how to handle everything that the camera VMDs can
throw at me. I don't know how to detect or handle jump-cuts. Also, camera VMDs
are stored as raw degrees, not quats... meaning the difference between two
frames can exceed 180deg or 360deg if the camera is orbiting the focus.
I simply don't know how to SLERP between two "points" that are greater than 180deg
apart! The current alg requires converting to quaternions, which has no concept
of great-rotations.
"""

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.05 - 9/7/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################
# https://github.com/chrisarridge/vectorpaths

DEBUG = 1
# debug 1: per-channel results
# debug 2: overrotate/longseg/monotonic prints
# debug 3: each match segment
# debug 4: reverse slerp info
# debug 5: bez logging always on
DEBUG_PLOTS = False

# if DEBUG >= 4:
# 	# this prints a bunch of useful stuff in the bezier regression, and a bunch of useless stuff from matplotlib
# 	logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

# if DEBUG_PLOTS:
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

'''
bone='アホ毛１' : rot : keep 18/197
bone='アホ毛１' : RESULT : keep 18/197 : keep%=9.137056%
bone='アホ毛２' : rot : keep 28/6404
bone='アホ毛２' : RESULT : keep 28/6404 : keep%=0.437227%
bone='センター' : pos : chan=0   : keep 1366/6212
bone='センター' : pos : chan=1   : keep 1469/6212
bone='センター' : pos : chan=2   : keep 1384/6212
bone='センター' : pos : chan=ALL : keep 3200/6212
bone='センター' : RESULT : keep 3200/6212 : keep%=51.513200%
bone='上半身' : rot : keep 4203/6034
bone='上半身' : RESULT : keep 4203/6034 : keep%=69.655287%
bone='上半身2' : rot : keep 4060/5660
bone='上半身2' : RESULT : keep 4060/5660 : keep%=71.731449%
bone='下半身' : rot : keep 4387/6237
bone='下半身' : RESULT : keep 4387/6237 : keep%=70.338304%
bone='前髪１' : rot : keep 4/197
bone='前髪１' : RESULT : keep 4/197 : keep%=2.030457%
bone='前髪１_２' : rot : keep 47/6406
bone='前髪１_２' : RESULT : keep 47/6406 : keep%=0.733687%
bone='前髪２' : rot : keep 4/197
bone='前髪２' : RESULT : keep 4/197 : keep%=2.030457%
bone='前髪２_２' : rot : keep 4/197
bone='前髪２_２' : RESULT : keep 4/197 : keep%=2.030457%
bone='前髪３' : rot : keep 4/197
bone='前髪３' : RESULT : keep 4/197 : keep%=2.030457%
bone='前髪３_２' : rot : keep 4/197
bone='前髪３_２' : RESULT : keep 4/197 : keep%=2.030457%
bone='右ひじ' : rot : keep 3982/5448
bone='右ひじ' : RESULT : keep 3982/5448 : keep%=73.091043%
bone='右もみあげ１' : rot : keep 4/197
bone='右もみあげ１' : RESULT : keep 4/197 : keep%=2.030457%
bone='右もみあげ２' : rot : keep 4/197
bone='右もみあげ２' : RESULT : keep 4/197 : keep%=2.030457%
bone='右中指１' : rot : keep 2209/4263
bone='右中指１' : RESULT : keep 2209/4263 : keep%=51.817969%
bone='右中指２' : rot : keep 1585/3963
bone='右中指２' : RESULT : keep 1585/3963 : keep%=39.994953%
bone='右中指３' : rot : keep 1541/4290
bone='右中指３' : RESULT : keep 1541/4290 : keep%=35.920746%
bone='右人指１' : rot : keep 2448/4602
bone='右人指１' : RESULT : keep 2448/4602 : keep%=53.194263%
bone='右人指２' : rot : keep 1644/5017
bone='右人指２' : RESULT : keep 1644/5017 : keep%=32.768587%
bone='右人指３' : rot : keep 1609/4506
bone='右人指３' : RESULT : keep 1609/4506 : keep%=35.707945%
bone='右小指１' : rot : keep 2884/5256
bone='右小指１' : RESULT : keep 2884/5256 : keep%=54.870624%
bone='右小指２' : rot : keep 2246/5570
bone='右小指２' : RESULT : keep 2246/5570 : keep%=40.323160%
bone='右小指３' : rot : keep 1569/4619
bone='右小指３' : RESULT : keep 1569/4619 : keep%=33.968391%
'''

'''
9/22/2021: program is almost totally complete
running on marionette 1person dance:
TOTAL TOTAL RESULT: keep 141052/292580 = 48.21%
TIME FOR ALL BONES: 5067.36 = 84 minutes = 1.5 hr
jesus christ that's so slow, for such a poor result... and this is just the "find the keyframes" part
i still dont have the "assemble into final keyframe list" part yet

10/10/2021: optimizations and bugfixes
marionette-motion-1person-log-2.txt
includes the "assemble into final keyframe list" portion
running on marionette 1persond dance,
TOTAL TOTAL RESULT: keep 143284/292580 = 48.97%
TIME FOR ALL BONES: 3762.887979030609
down to 62 minutes! much faster!
I think most of the time comes from the armtwist/wristtwist bones

log3:
add the "find the entire linear section and operate on all monotonic segments within it" idea
from 62 minutes to 14 minutes :D
there are a sparse handful of places where one method or the other used different numbers of frames
for a section but it's a very minor difference.
'''

# enable/disable switches
SIMPLIFY_BONE_POSITION = True
SIMPLIFY_BONE_ROTATION = True

SIMPLIFY_CAM_POSITION = True
SIMPLIFY_CAM_FOV = True
SIMPLIFY_CAM_DIST = True
SIMPLIFY_CAM_ROTATION = True

# this controls how "straight" a line has to be (in 1d morph-space) to get collapsed
# higher values = more likely to collapse = fewer frames in result, but greater deviation from original movements
MORPH_ERROR_THRESHOLD = 0.00001

BEZIER_ERROR_THRESHOLD_BONE_POSITION_RMS = 0.3
BEZIER_ERROR_THRESHOLD_BONE_POSITION_MAX = 0.3

# BONE_ROTATION_STRAIGHTNESS_VALUE = 0.15

# this controls how "straight" a line has to be (in rotation-space) to get collapsed
# higher values = more likely to collapse = fewer frames in result, but greater deviation from original movements
REVERSE_SLERP_TOLERANCE = 0.05

CONTROL_POINT_BOX_THRESHOLD = 1

# # this reduces quality-of-results slightly (by not stripping out every single theoretically collapsable frame)
# # but, it's needed to prevent O(n^2) compute time from getting out of hand :(
# BONE_ROTATION_MAX_Z_LOOKAHEAD = 500

BONE_ROTATION_MAX_SAMPLES = 200

# to prevent accidentally wrapping around "the wrong way" i need to put a cap on the max length a rotiation segment can be
GREATEST_LENGTH_OF_ROTATION_SEGMENT_IN_DEGREES = 160


# these values are the average/expected rate of change (units per frame) for the respective channels.
# this was calculated by analyzing a few dance motions and looking at histograms or whatever.
# the exact value doesn't hugely matter (i hope?) it's just about getting the """weight""" of the value-change
# to be roughly the same as the """weight""" of the time change.
# todo should this data be derived from full-keyed motions? or partially-keyed motions? or both?
# todo re-evaluate motion heuristics with larger dataset
EXPECTED_DELTA_BONE_XPOS = 0.15
EXPECTED_DELTA_BONE_YPOS = 0.18
EXPECTED_DELTA_BONE_ZPOS = 0.16
EXPECTED_DELTA_BONE_ROTATION_RADIANS = 0.10

EXPECTED_DELTA_CAM_XPOS = 0.1149
EXPECTED_DELTA_CAM_YPOS = 0.0796
EXPECTED_DELTA_CAM_ZPOS = 0.1319
EXPECTED_DELTA_CAM_FOV = 0.4926
EXPECTED_DELTA_CAM_DIST = 0.3184
EXPECTED_DELTA_CAM_ROTATION_RADIANS = 0.0525

ONE_DEGREE_IN_RADIANS = 0.017453292519943295

standard_skeleton_bones = [
	"全ての親","センター","グルーブ","腰","上半身","上半身２","下半身","首","頭","両目",
	"右足ＩＫ","右つま先ＩＫ","右肩P","右肩","右腕","右腕捩","右ひじ","右手捩","右手首",
	"右親指０","右親指１","右親指２","右小指１","右小指２","右小指３","右薬指１","右薬指２",
	"右薬指３","右中指１","右中指２","右中指３","右人指１","右人指２","右人指３","右目",
	"右足","右ひざ","右足首","右つま先","右足D","右ひざD","右足首D","右足先EX","左足ＩＫ",
	"左つま先ＩＫ","左肩P","左肩","左腕","左腕捩","左ひじ","左手捩","左手首","左親指０",
	"左親指１","左親指２","左小指１","左小指２","左小指３","左薬指１","左薬指２","左薬指３",
	"左中指１","左中指２","左中指３","左人指１","左人指２","左人指３","左目","左足","左ひざ",
	"左足首","左つま先","左足D","左ひざD","左足首D","左足先EX",
]

# TODO: use looser bezier parameters for rotation section?

# TODO: find some better way to keep the bez error constraints "realistic" for curves at all scales


# TODO: overall cleanup, once everything is acceptably working. variable names, comments, function names, etc.

# TODO: change morph-simplify to use a structure more similar to the bone-simplify structure? i.e. store frame
#  indices in a set and then get the frames back at the very end. it would be less efficient but its just for
#  more consistency between sections.

# TODO: optimize the position section of bone-simplify, add another loop layer so i don't need to keep re-finding z.

# TODO: modify the bezier regression to return the error values? i think it would just be for logging, not sure if its
#  worth changing the structure.
#  it would be useful for, "keep walking backward until you find a curve that's good, and the NEXT curve is worse"...?
#  except that no, if region M can be well fit then any subset of the region can be fit as well or better...

# TODO: even more testing to figure out what good values are for bezier error targets

# TODO: how the fuck can i effectively visualize quaternions? i need to see them plotted on a globe or something
#  so i can have confidence that my "how straight should be considered a straight line" threshold is working right


# TODO investigate 'local breakup' when length = 2(3) but it breaks into 2 segments? are there really so many Vs?

# TODO: ARMTWIST BONES are probably exclusively along one axis, whole thing is slerpable, MASSIVE efficiency loss to
#  recompute that with every pass, really should reuse past results

def get_some_interp_testpoints(start:int, end:int, maxnum:int) ->  Generator[int, None, None]:
	# basically replaces the "range" operator, but lets me cap the number of intermediate points
	# should this return as a list? or as a generator with yield? idk
	# let's set it up as a generator, sure
	R = end-start
	if R <= maxnum:
		for i in range(start,end):
			yield i
	else:
		for i in range(maxnum):
			yield start + round(i * R / maxnum)
	pass

def rotation_close(_a, _b, tol=1e-6) -> bool:
	return all(math.isclose(_aa, _bb, abs_tol=tol) for _aa, _bb in zip(_a, _b))

def break_due_to_monotonic_sections(L:List[float]) -> List[int]:
	# return the list of all local minimums or maximums in the input list
	assert len(L) >= 2
	
	if len(L) == 2: return [0,1]
	# i know that the length is 3 or greater
	retme = []
	# finding discrete peaks is easy... what do i do about plateaus?
	# i guess i only want to add the earliest edge of a plateau?
	# but i also want to ignore plateaus at the start or end...?
	# if i see a plateau, and then i see rising or falling (such that it creates a local minmax), then add the leading edge of the plateau
	# if it starts with a flat, which flat-state doesn't matter because 0 will be added to the set, which is fine
	# if it ends with a flat, it will never see the state stop being flat and will never add it to the set
	flat_start_idx = 0
	last_state = 3  # rising=1, falling=2, flat-last-rising=3, flat-last-falling=4
	for i in range(0, len(L)-1):
		a = L[i]    # this
		b = L[i+1]  # next
		# first, determine state of this-to-next
		if a > b:
			state = 2  # falling
		elif a < b:
			state = 1  # rising
		elif last_state == 2:
			state = 4  # flat-last-falling
			flat_start_idx = i  # if it was falling, and now flat, then save idx of beginning of flat
		elif last_state == 1:
			state = 3  # flat-last-rising
			flat_start_idx = i  # if it was rising, and now flat, then save idx of beginning of flat
		else:
			# if currently flat and was flat, then retain state
			state = last_state
		
		# second, compare with state of prev-to-this
		# in most cases, state will not change
		if last_state == state:
			pass
		# if was rising, now falling OR was falling, now rising
		elif (last_state == 1 and state == 2) or (last_state == 2 and state == 1):
			# then store idx of THIS
			retme.append(i)
		# if was flat-last-rising, now falling, then store the flat-start-idx
		# if was flat-last-falling, now rising, then store the flat-start-idx
		elif (last_state == 3 and state == 2) or (last_state == 4 and state == 1):
			retme.append(flat_start_idx)
		
		# third, move state to last-state
		last_state = state
		
	if (not retme) or retme[0] != 0:
		retme.insert(0, 0)  # return list always begins with 0
	retme.append(len(L)-1)  # return list always ends with ultimate endpoint
	return retme

'''
def sign(U):
	# return -1/0/+1 if input is negative/zero/positive
	if U == 0:  return 0
	elif U > 0: return 1
	else:       return -1

def scale_list(L:List[float], R: float) -> List[float]:
	"""
	Take a list of floats, shift/scale it so it starts at 0 and ends at R.
	:param L: list of floats
	:param R: range endpoint
	:return: list of floats, same length
	"""
	assert len(L) >= 2
	# one mult and one shift
	ra = L[-1] - L[0]  # current range of list
	if math.isclose(ra, 0, abs_tol=1e-6):
		# if the range is basically 0, then add 0 to the first, add R to the last, and interpolate in between
		offset = [R * s / (len(L)-1) for s in range(len(L))]
		L = [v + o for v,o in zip(L,offset)]
	else:
		# if the range is "real",
		L = [v * R / ra for v in L]  # scale the list to be the desired range
	L = [v - L[0] for v in L]  # shift it so the 0th item equals 0
	return L

def get_difference_quat(quatA: Tuple[float, float, float, float],
						quatB: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
	# get the "difference quaternion" that represents how to get from A to B...
	# or is this how to get from B to A?
	# as long as I'm consistent I don't think it matters?
	deltaquat_AB = core.hamilton_product(core.my_quat_conjugate(quatA), quatB)
	return deltaquat_AB

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
'''


def scale_two_lists(x:List[float], y:List[float], R: float) -> Tuple[List[float], List[float]]:
	"""
	Take a list of floats, shift/scale it so it starts at 0 and ends at R.
	:param x: list of floats for x
	:param y: list of floats for y
	:param R: range endpoint
	:return: list of floats, same length
	"""
	assert len(x) == len(y)
	assert len(x) >= 2
	# one mult and one shift
	# first do x
	xR = x[-1] - x[0]  # current range of list
	assert not math.isclose(xR, 0, abs_tol=1e-6)  # x must have real-valued range
	x = [v * R / xR for v in x]  # scale the list to be the desired range
	x = [v - x[0] for v in x]  # shift it so the 0th item equals 0
	# now, do y
	yR = y[-1] - y[0]
	
	if math.isclose(yR, 0, abs_tol=1e-6):
		# if the range is basically 0, then add 0 to the first, add R to the last, and interpolate in between
		# offset = [R * s / (len(x) - 1) for s in range(len(x))]  # wrong
		# offset = [core.linear_map(0, 0, x[-1], R, xx) for xx in x]  # inefficient
		offset = [R*xx/x[-1] for xx in x]
		y = [v + o for v, o in zip(y, offset)]
	else:
		# if the range is "real",
		y = [v * R / yR for v in y]  # scale the list to be the desired range
	y = [v - y[0] for v in y]  # shift it so the 0th item equals 0
	return x, y

def get_quat_angular_distance(quatA: Tuple[float, float, float, float],
							  quatB: Tuple[float, float, float, float]) -> float:
	"""
	Calculate the "angular distance" between two quaternions, in radians. Opposite direction = pi.
	:param quatA: WXYZ quaternion A
	:param quatB: WXYZ quaternion B
	:return: float [0-pi]
	"""
	# https://math.stackexchange.com/questions/90081/quaternion-distance
	# theta = arccos{2 * dot(qA, qB)^2 - 1}
	# unlike previous "get_corner_sharpness_factor", this doesn't discard the W component
	# so i have a bit more confidence in this approach, i think?
	quatA = core.normalize_distance(quatA)
	quatB = core.normalize_distance(quatB)
	
	a = core.my_dot(quatA, quatB)
	b = (2 * (a ** 2)) - 1
	c = core.clamp(b, -1.0, 1.0)  # this may not be necessary? better to be safe tho
	d = math.acos(c)
	# d: radians, 0 = same, pi = opposite
	# return d / math.pi
	return d

def reverse_slerp(q, q0, q1) -> Tuple[float,float]:
	"""
	If given a start-quat and an end-quat, assume that the intermediate-quat lies on the SLERP-path between start/end
	and try to calculate its percentage for where it lies between them. This uses math from:
	https://math.stackexchange.com/questions/2346982/slerp-inverse-given-3-quaternions-find-t
	[t = log(q0not * q) / log(q0not * q1)], elementwise division, except skip the w component.
	If the x/y/z channels will return similar values, then the intermediate truly does lie on the "linear" path.
	If the values greatly diverge, then the intermediate quat does not lie on the path.
	
	Return the average of the 3 channels, and the greatest divergence among the 3 channels.
	If start == end, divergence is zero and I can't return a percentage so instead calculate the angular distance
	from start to intermediate.
	
	:param q: quaternion W X Y Z intermediate
	:param q0: quaternion W X Y Z start
	:param q1: quaternion W X Y Z end
	:return: tuple(percentage, divergence)
	"""
	
	if not rotation_close(q0, q1, tol=1e-6):
		# check for and correct quaternion "handedness" to fix slerp going along wrong path
		# todo problem: the slerp is doing something strange at certain points... how is it possible for what1, what2, what3
		#  to be printed? it's a triangle, there should not be only one inequalty here????
		dot01 = core.my_dot(q0,q1)
		dot0q = core.my_dot(q0, q)
		dotq1 = core.my_dot(q, q1)
		if dot01 < 0:
			if dot0q < 0:
				# if 0!=1 and 0!=q then 0 is bad
				q0 = [-z for z in q0]
			elif dotq1 < 0:
				# if 0!=1 and q!=1 then 1 is bad
				q1 = [-z for z in q1]
			# else:
			# 	print("what1")
		elif dot0q < 0 and dotq1 < 0:
			# if 0!=q and q!=1 then q is bad
			q = [-z for z in q]
		# elif dot0q < 0:
		# 	print("what2")
		# elif dotq1 < 0:
		# 	print("what3")
		q0not = core.my_quat_conjugate(q0)
		num = core.quat_ln(core.hamilton_product(q0not, q))
		dom = core.quat_ln(core.hamilton_product(q0not, q1))
		
		# compute the result for each channel that doesn't div-by-zero-error
		# if b==0, then a SHOULD also be zero... if it's not, that's divergence! i'm not sure the scale matches, but oh well...
		# if they all get zero (should never happen i hope?) then fall thru and do the ang dist thing
		channel_results = []
		channel_zerror = []
		for a,b in zip(num[1:4],dom[1:4]):
			if b == 0:
				channel_zerror.append(2*abs(a))
			else:
				channel_results.append(a/b)
			
		if len(channel_results) != 0:
			# compute the average t-value
			avg = sum(channel_results) / len(channel_results)
			# compute the deviation between the channels
			channel_results.sort()  # sort the channels to be ascending
			diff = channel_results[-1] - channel_results[0]  # the diff is the biggest minus smallest
			if channel_zerror:
				# if max(channel_zerror) > diff:
				# 	print("new error thing, %.5f %.5f" % (diff, max(channel_zerror)))
				diff = max(diff, max(channel_zerror))
			return avg, diff
		else:
			print("ERR OH COME ON")

	
	# fall thru case
	# this also happens if b is ALL zeros
	# this happens when q0 EXACTLY EQUALS q1... so, if interpolating between Z and Z, you're not moving at all, right?
	# actually, what if something starts at A, goes to B, then returns to A? it's all perfectly linear with
	# start/end exactly the same! but it's definitely 2 segments. so I cant just return a static value.
	# i'll return the angular distance between q and q0 instead, its on a different scale but w/e, it gets
	# normalized to 127 anyways
	x = 100 * get_quat_angular_distance(q0, q)
	return x, 0



def break_due_to_overrotation(bonelist: List[vmdstruct.VmdBoneFrame],
							  original_i: int,
							  original_z: int) -> int:
	"""
	Turn a "linear slerpable section" into a same-or-smaller sub-section that contains rotation of 160 degrees or less.

	:param bonelist: list of all boneframes
	:param original_i: idx of beginning of linear slerpable section
	:param original_z: idx of end of linear slerpable section
	:return: new (or same) idx of end of section
	"""
	
	def recursive_something(y_points_all2: List[float],
							i: int, z: int, level=0) -> int:
		last_max = 0
		last_min = 0
		# walk along the "radians from start" list
		for e, val in enumerate(y_points_all2):
			# track min and max
			if val < last_min: last_min = val
			if val > last_max: last_max = val
			# if the range (max-min) exceeds 160 degrees, then this found segment is NOT OKAY!
			range_in_degrees = math.degrees(last_max - last_min)
			if range_in_degrees >= GREATEST_LENGTH_OF_ROTATION_SEGMENT_IN_DEGREES:
				z = i + e - 1  # redefine z as the point before this one
				if z == i: z += 1  # but, z must always be at least 1 greater than i. even if that puts me back where i started.
				# recalculate the y_points_all from this new z value
				_, y_points_new = make_xy_from_segment_rotation(bonelist, i, z, 1.0, check=False)
				# moving the endpoint will sometimes cause radian measurements to flip!!
				# compare the new y-list with the previous y-list... if all remaining elements match, then this is good!
				# "zip" lets me iterate over pairs up to the length of the shorter list
				if all(old == new for old, new in zip(y_points_all2, y_points_new)):
					# if all radian measurements are unchanged, i'm done! the new value is just good!
					return z
				else:
					# if any radian measurements flipped, check it again!!
					# might return the same answer, might return something different, might recurse even deeper
					# return whatever result it comes up with
					return recursive_something(y_points_new, i, z, level=level+1)
		# if i walked over the whole list and the range never exceeded 160, then this z is good.
		return z
	
	# calculate the y-data from this proposed z value
	_, y_points_all = make_xy_from_segment_rotation(bonelist, original_i, original_z, 1.0, check=False)
	# test (and recurse/repeat if necessary) and find a new, closer z point that doesn't include overrotation
	new_z = recursive_something(y_points_all, original_i, original_z)
	return new_z


def make_xy_from_segment_rotation(bonelist: List[vmdstruct.VmdBoneFrame],
								  idx_this: int,
								  idx_next: int,
								  expected_delta_rate: float,
								  check=True) -> Tuple[List[float], List[float]]:
	# look at all the points in between (including endpoints),
	assert idx_this < idx_next
	# x-points are dead easy
	x_points = [frame.f for frame in bonelist[idx_this: idx_next + 1]]
	# for y-points.... knowing the direction/polarity is kind of a problem. first, check whether start==end:
	quat_start = core.euler_to_quaternion(bonelist[idx_this].rot)
	quat_end = core.euler_to_quaternion(bonelist[idx_next].rot)
	max_idx = idx_next - idx_this
	if rotation_close(quat_start, quat_end):
		# if start==end, then there is NO RIGHT ANSWER for polarity, so i just need to pick any direction
		# and declare it positive! there is no objective truth. I will pick the greatest SQ distance as positive point.
		max_quat = quat_start
		max_val = 0
		max_idx = 0
		for i, frame in enumerate(bonelist[idx_this: idx_next + 1]):
			q = core.euler_to_quaternion(frame.rot)
			dist_SQ = get_quat_angular_distance(quat_start, q)  # SQ = start to Q
			if dist_SQ > max_val:
				max_val = dist_SQ
				max_quat = q
				max_idx = i
		# possible shortcut: if all distances are super small, then return list of zeros
		if max_val < 1e-6:
			y_points = [0] * len(x_points)
			return x_points, y_points
		# if not all distances are small, then use this "greatest SQ" as the end quat
		quat_end = max_quat
	
	# okay, now i have ensured that quat_start != quat_end, so i have a sense of direction!
	dist_SE = get_quat_angular_distance(quat_start, quat_end)  # SE = start to end
	y_points = []
	divergence_list = []
	revslerp_list = []
	
	# now, compute the actual results y_points
	for i, frame in enumerate(bonelist[idx_this: idx_next + 1]):
		q = core.euler_to_quaternion(frame.rot)
		if check:
			revslerp, diff = reverse_slerp(q, quat_start, quat_end)
			divergence_list.append(diff)
			revslerp_list.append(revslerp)
		# ^^ this is just for... stats? bookkeeping? curiosity? idk
		# now i really calculate the answer
		dist_SQ = get_quat_angular_distance(quat_start, q)  # SQ = start to Q
		dist_EQ = get_quat_angular_distance(quat_end, q)  # EQ = end to Q
		# how to determine "polarity": make it a triangle and compare distances
		if dist_SE < dist_EQ and dist_SQ < dist_EQ:
			y_points.append(-dist_SQ)
		else:
			y_points.append(dist_SQ)
	
	if check:
		# assert that all of the values I calculated are close to the linear slerp path
		# exactly how far off am i?
		# radians -> slerp% -> quat -> compare with full-key input
		max_ang = y_points[max_idx]
		if max_ang != 0 and not rotation_close(quat_start, quat_end):
			revslerp_list_from_rads = [v / max_ang for v in y_points]
			wrongness = []
			for i in range(idx_this, idx_next + 1):
				j = i - idx_this  # j is idx within "revslerp_list"
				fwd_slerp = core.my_slerp(quat_start, quat_end, revslerp_list_from_rads[j])
				# fwd_slerp_eul = core.quaternion_to_euler(fwd_slerp)
				point = bonelist[i]
				point_quat = core.euler_to_quaternion(point.rot)
				ang = get_quat_angular_distance(fwd_slerp, point_quat)
				wrongness.append(math.degrees(ang))
			max_wrongness = max(wrongness)
			if max_wrongness > 2:
				print("max wrongness = %7.2fdeg" % max_wrongness)
			if max_wrongness > 20:
				print("oh no")
	
	# the expected rate of change for time is 1frame/frame
	# the expected rate of change for value is EXPECTED_DELTA_BONE_ROTATION_RADIANS/frame
	# i need to get these to be square so that value-error has the same weight as time-error
	# so, i... divide by the expected? yeah? yeah.
	y_points = [v / expected_delta_rate for v in y_points]
	
	return x_points, y_points


def make_xy_from_segment_scalar(bonelist: List[vmdstruct.VmdBoneFrame],
								idx_this: int,
								idx_next: int,
								getter: Callable[[vmdstruct.VmdBoneFrame], float],
								expected_delta_rate) -> Tuple[List[float], List[float]]:
	# look at all the points in between (including endpoints),
	assert idx_this < idx_next
	x_points = [bonelist[i].f for i in range(idx_this, idx_next + 1)]
	y_points = [getter(bonelist[i]) for i in range(idx_this, idx_next + 1)]
	# the expected rate of change for time is 1frame/frame
	# the expected rate of change for value is ??/frame
	# i need to get these to be square so that value-error has the same weight as time-error
	# so, i... divide by the expected? yeah? yeah.
	
	y_points = [v / expected_delta_rate for v in y_points]
	
	return x_points, y_points


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
	
	num_skipped = 0
	
	# print("number of morphs %d" % len(morphdict))
	# analyze each morph one at a time
	for morphname, morphlist in morphdict.items():
		# print("MORPH '%s' LEN %d" % (morphname, len(morphlist)))
		# make a list of the deltas, for simplicity
		thisoutput = []
		# the first frame is always kept. and the last frame is also always kept.
		# if there is only one frame, or two, then don't even bother walking i guess?
		if len(morphlist) <= 2:
			output.extend(morphlist)
			num_skipped += 1
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
				if math.isclose(delta_z, delta_rate, abs_tol=MORPH_ERROR_THRESHOLD):
				# if (delta_rate - MORPH_ERROR_THRESHOLD) < delta_z < (delta_rate + MORPH_ERROR_THRESHOLD):
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
			if len(thisoutput) != len(morphlist):
				print("'%s' : RESULT : keep %d/%d = %.2f%%" % (morphname, len(thisoutput), len(morphlist), 100 * len(thisoutput) / len(morphlist)))
		
		output.extend(thisoutput)
	# FIN
	print("MORPH RESULTS (inner):")
	print("    identified %d unique morphs, processed %d" % (len(morphdict), len(morphdict) - num_skipped))
	print("    keep frames %d/%d = %.2f%%" % (len(output), len(allmorphlist), 100 * len(output) / len(allmorphlist)))
	
	return output

def _simplify_boneframes_scalar(bonename: str,
								bonelist: List[vmdstruct.VmdBoneFrame],
								chan: str,
								getter: Callable[[vmdstruct.VmdBoneFrame], float],
								expected_delta_rate: float,
								) -> Set[int]:
	"""
	Wrapper function for the sake of organization.
	
	:param bonename: str name of the bone being analyzed, for debug print
	:param bonelist: list of all boneframes that correspond to this bone
	:param chan: str label for channel being analyzed, for debug print
	:param getter: lambda func for accessing the scalar channel being analyzed
	:param expected_delta_rate: float average/expected rate-of-change, radians per frame
	:return: set of ints, referring to indices within bonelist that are "important frames"
	"""
	keepset = set()
	i = 0
	while i < (len(bonelist) - 1):
		# start walking down this list
		# assume that i is the start point of a potentially over-keyed section
		i_sign = getter(bonelist[i+1]) > getter(bonelist[i])
		
		# +++++++++++++++++++++++++++++++++++++
		# zero-change shortcut
		z = i+1  # to make pycharm shut up
		# while (z < len(bonelist)) and math.isclose(bonelist[i].pos[C], bonelist[z].pos[C], abs_tol=1e-4):
		while (z < len(bonelist)) and getter(bonelist[i]) == getter(bonelist[z]):
			z += 1
		if z != i+1:  # if the while-loop went thru at least 1 loop,
			z -= 1  # back off one value, since z is the value that no longer matches,
			if DEBUG >= 3:
				print(f"MATCH! bone='{bonename}' {chan} : i-z= {i}-{z} : pts={z-i+1} (ZERO CHANGE)")
			keepset.add(z)  # add this endpoint
			i = z  # and move the startpoint to here and keep walking from here
			continue
		
		# +++++++++++++++++++++++++++++++++++++
		# now, walk forward from here until i "return" the frame "z" that has a different delta
		# "z" is the farthest plausible endpoint of the section (the real endpoint might be between i and z, tho)
		# "different" means only different state, i.e. rising/falling/zero
		
		for z in range(i + 1, len(bonelist)):
			# if i reach the end of the bonelist, then "return" the final valid index
			if z == len(bonelist) - 1:
				break
			z_this = bonelist[z]
			z_next = bonelist[z + 1]
			z_sign = getter(z_next) > getter(z_this)
			# TODO: also break if the delta is way significantly different than the previous delta?
			#  pretty sure this concept is needed for the camera jumpcuts to be guaranteed detected?
			if z_sign == i_sign:
				pass  # if this is potentially part of the same sequence, keep iterating
			else:
				break  # if this is definitely no longer part of the sequence, THEN i can break
		# anything past z is DEFINITELY NOT the endpoint for this sequence
		# everything from i to z is monotonic: always increasing OR always decreasing
		
		# +++++++++++++++++++++++++++++++++++++
		# generate all the x-values and y-values
		x_points_all, y_points_all = make_xy_from_segment_scalar(bonelist, i, z, getter, expected_delta_rate)
		
		assert len(x_points_all) == len(y_points_all)

		# +++++++++++++++++++++++++++++++++++++
		# use this function to break this monotonic data into as many bezier segments as necessary
		k = make_beziers_from_datarange(x_points_all, y_points_all, i, z, bonename, chan)
		i = max(k)
		keepset.update(k)
		pass  # end "while i < len(bonelist)"
	
	# now i have found every frame# that is important for this axis
	if DEBUG and len(keepset) > 1:
		# ignore everything that found only 1, cuz that would mean just startpoint and endpoint
		# add 1 to the length cuz frame 0 is implicitly important to all axes
		print(f"'{bonename}' {chan} : keep {len(keepset)+1}/{len(bonelist)}")
	return keepset

def _simplify_boneframes_rotation(bonename: str,
								  bonelist: List[vmdstruct.VmdBoneFrame],
								  expected_delta_rate:float) -> Set[int]:
	"""
	Wrapper function for the sake of organization.
	:param bonename: str name of the bone being operated on
	:param bonelist: list of all boneframes that correspond to this bone
	:param expected_delta_rate: float average/expected rate-of-change, radians per frame
	:return: set of ints, referring to indices within bonelist that are "important frames"
	"""
	chan = "R"
	
	keepset = set()
	i = 0
	while i < (len(bonelist) - 1):
		# start walking down this list
		# assume that i is the start point of a potentially over-keyed section
		i_this = bonelist[i]
		i_this_quat = core.euler_to_quaternion(i_this.rot)
		
		# todo problem: how do i distinguish between when it is most efficient to group a bunch of frames as zeros, vs
		#  when it's really just a veeeeery slow lead-in to a bezier-matchable curve?
		# +++++++++++++++++++++++++++++++++++++
		# zero-rotation shortcut
		z = i+1  # to make pycharm shut up
		# while (z < len(bonelist)) and rotation_close(bonelist[i].rot, bonelist[z].rot):
		while (z < len(bonelist)) and bonelist[i].rot == bonelist[z].rot:
			z += 1
		if z != i + 1:  # if the while-loop went thru at least 1 loop,
			z -= 1  # back off one value, since that's the value that no longer matches
			if DEBUG >= 3:
				print(f"MATCH! bone='{bonename}' {chan} : i-z= {i}-{z} : pts={z-i+1} (ZERO CHANGE)")
			keepset.add(z)  # add this endpoint
			i = z
			continue
			
		# +++++++++++++++++++++++++++++++++++++
		# now, walk FORWARD from here until i identify a frame z that might be an 'endpoint' of an over-key section
		for z in range(i + 1, len(bonelist)):
			z_this_quat = core.euler_to_quaternion(bonelist[z].rot)
			# walk forward from here, testing frames as i go
			# if i can succesfully reverse-slerp everything from i to z, then z is a valid endpoint!
			# success means all reverse-slerp dimensions are close to equal
			endpoint_good = True
			temp_reverse_slerp_diffs = []
			
			# NEW IDEA: put a ceiling on the number of points that i test! even if i=7 and z=1007, only test 200 points
			#  evenly spaced between those two ends. it's still really slow, but it's not O(n^2) any more ;)
			for q in get_some_interp_testpoints(i + 1, z, maxnum=BONE_ROTATION_MAX_SAMPLES):
				q_this_quat = core.euler_to_quaternion(bonelist[q].rot)
				# calculate reverse-slerp for this start/end/intermediate
				# note: if start==end, then divergence=0 and avg=distance in radians
				avg, divergence = reverse_slerp(q_this_quat, i_this_quat, z_this_quat)
				# "avg" = average of independent results from all 3 x/y/z channels
				# "divergence" = greatest difference between these 3 results
				temp_reverse_slerp_diffs.append(divergence)
				# if any of the frames between i and z cannot be reverse-slerped, then break
				if divergence >= REVERSE_SLERP_TOLERANCE:
					endpoint_good = False
					break
			if not endpoint_good:
				# an endpoint z is "bad" if any of the points between i-z aren't reverse slerpable, i.e. i-z does not define a "linear" stretch.
				# when i find something that is a BAD endpoint, i know (assume?) that the one before was GOOD.
				# so, "return" z-1
				z -= 1
				if DEBUG >= 4:
					if temp_reverse_slerp_diffs:
						print(f"rev-slerp  : i-z= {i}-{z} : pts={z-i+1}" + (" : nextdiff=%.5f" % max(temp_reverse_slerp_diffs)))
					else:
						print(f"rev-slerp  : i-z= {i}-{z} : pts={z-i+1}")
				break
			else:
				# if i got thru all the points between i and z, and they all passed, then this z is the last known good endpoint
				# continue and test the next z
				pass
		
		if DEBUG >= 2 and (z-i >= BONE_ROTATION_MAX_SAMPLES):
			print(f"long seg   : i-z= {i}-{z} : pts={z-i+1}")
		
		# now i have z, and anything past z is DEFINITELY NOT the endpoint for this sequence
		# everything from i to z is "slerpable", meaning it is all falling on a linear arc
		# BUT, that doesn't mean it's all on one bezier! it might be several beziers in a row...

		
		# TODO new structure:
		#  use slerpability test to find stretch of "linear" frames
		#  break this apart into sections that contain no more than 160degree span of rotation
		#  break this apart into sections that are strictly monotonic
		#  break this apart into however many beziers are needed to fit the monotonic stretch
		
		# TODO bone 右足ＩＫ frames 586 - 627, 42degree malfunction, not sure why? NEEDS GRAPHING! but, it doesn't come up in the "synthesis" stage...

		# i,z are the begin,end of the linear slerpable section. but i cant/shouldnt analyze this entire chunk at once.
		# i2,z2 are the begin,end of the section after "overrotate check", so i know it contains rotation < 160 degrees.
		i2 = i
		# once the inner loops have walked up thru the whole linear slerpable section, THEN i find a new linear slerpable section.
		while i2 < z:
			# +++++++++++++++++++++++++++++++++++++
			# find ONE new endpoint that contains rotation < 160 degrees...
			z2 = break_due_to_overrotation(bonelist, i2, z)
			if DEBUG >= 2 and (z2 != z):
				print(f"overrotate : i-z= {i}-{z} : i2-z2= {i2}-{z2}")
			
			# if z2 == z, then no overrotate concerns were found, so do not "trim" at later stage
		
			# next, calculate the x and y datapoints that will be used for bezier fitting
			x_points_all, y_points_all = make_xy_from_segment_rotation(bonelist, i2, z2, expected_delta_rate)
			assert len(x_points_all) == len(y_points_all)
		
			# +++++++++++++++++++++++++++++++++++++
			# the y-datapoints should be STRICTLY MONOTONIC (increasing or decreasing), so break the current y-values
			#  apart until that's the case!
			# find ALL new endpoints due to monotonic ranges...
			local_minmax = break_due_to_monotonic_sections(y_points_all)
			# convert the local min/max from relative idx scope to i/z scope
			local_minmax = [v+i2 for v in local_minmax]
			if DEBUG >= 2 and (len(local_minmax) != 2):
				# if breakup is needed (often) then print a message
				print(f"monotonic  : i-z= {i}-{z} : i2-z2= {i2}-{z2} : numseg={len(local_minmax)-1} : list=" + str(local_minmax))
				# plt.plot(x_points_all, y_points_all, 'r+')
				# plt.show(block=True)
			if DEBUG_PLOTS:
				if len(x_points_all) > 2:
					print("reverse-slerp: bone='%s' : i-z= %d-%d" % (bonename, i, z))
					plt.plot(x_points_all, y_points_all, 'r+')
					plt.show(block=True)
		
			# iterate over ALL the local minimum/maximum points
			bez_ends = []
			for mm in range(len(local_minmax)-1):
				i3 = local_minmax[mm]
				z3 = local_minmax[mm+1]
				
				# i can either slice the previous results of make_xy_from_segment_rotation() or call it again?
				# x_points, y_points = make_xy_from_segment_rotation(bonelist, i3, z3, expected_delta_rate)
				
				x_points = x_points_all[i3-i2:z3-i2+1]
				y_points = y_points_all[i3-i2:z3-i2+1]
				
				# +++++++++++++++++++++++++++++++++++++
				# i3,z3 is linear slerpable AND has rotation <= 160 degrees AND is monotonic
				# NOW i can safely make beziers
				k = make_beziers_from_datarange(x_points, y_points, i3, z3, bonename, chan)
				bez_ends.extend(k)
				pass  # end "for each monotonic section"
			
			# if overrotate correction was needed (z2 != z), and there is more than one endpoint that got found,
			#  then i should ignore the final bezier endpoint i find cuz it might blend with the beginning of the
			#  next section! or something? basically the overrotate breakpoints aren't "real" breakpoints that should
			#  appear in the final VMD, it's just necessary to accurately compute stuff.
			if (z2 != z) and (len(bez_ends) != 1):
				bez_ends.pop(-1)

			# each bez endpoint it calculates gets saved as the ultimate answer
			keepset.update(bez_ends)
			# after calculating all the beziers, move i2 to the last/greatest bez endpoint i successfully found
			i2 = max(bez_ends)
			pass  # end "while i2 < z"
		i = i2
		pass  # end "while i < len(bonelist)"
	# now i have found every frame# that is important due to rotation changes
	if DEBUG and len(keepset) > 1:
		# if it found only 1, ignore it, cuz that would mean just startpoint and endpoint
		# add 1 to the length cuz frame 0 is implicitly important to all axes (added to set in outer level)
		print(f"'{bonename}' {chan} : keep {len(keepset) + 1}/{len(bonelist)}")
	return keepset

def make_beziers_from_datarange(x_points_all: List[float], y_points_all: List[float],
								i: int, z: int,
								bonename: str, chan: str,) -> List[int]:
	"""
	This function accepts a series of XY datapoints that define a strictly monotonic range.
	Then it uses a "greedy" algorithm to define that range with the fewest possible number of bezier curves.
	Its output is the INDICES of the frames that can define endpoints for reasonable bezier curves.

	I still need to figure out how to fix the bezier-fitting-error problems tho...
	Maybe it will be solved if I do the scaling outside this function, in some special way?

	:param x_points_all: list of float x-vals for xy pairs of data
	:param y_points_all: list of float y-vals for xy pairs of data
	:param i: int idx within bonelist where the datarange starts
	:param z: int idx within bonelist where the datarange ends (inclusive)
	:param bonename: str name of bone, for debug printing
	:param chan: str name of channel, for debug printing
	:return: list of ints in i/z scope
	"""
	# i know that the list of points I am given is STRICTLY MONOTONIC
	# so, attempt to fit some number of beziers to this section
	keeplist = []
	
	num_all_points = len(x_points_all)
	found_beziers = []  # list of all beziers i find (for debug plotting?)
	segment_count = 0  # which segment i am finding/have found
	
	v = 0  # v is the start of "this segment", w is the end of "this segment" (inclusive)
	# both v and w are always valid indices within the lists, will never equal the length
	
	# keep finding bezier segments until a segment ends on the final frame
	while v != (num_all_points-1):
		# w is the relative index within this i-to-z stretch
		# w is always a valid index within the lists
		# it starts at z, and counts down to i (should never actually hit i tho, should always pass when it's 2 points)
		for w in reversed(range(v, num_all_points)):
			# take a subset of the range of points
			x_points = x_points_all[v:w + 1]
			y_points = y_points_all[v:w + 1]
			
			# then run regression to find a reasonable interpolation curve for this stretch
			# this innately measures both the RMS error and the max error, and i can specify thresholds
			# if it cannot satisfy those thresholds it will split and try again
			bezier_list = vectorpaths.fit_cubic_bezier(x_points, y_points,
													   rms_err_tol=BEZIER_ERROR_THRESHOLD_BONE_POSITION_RMS,
													   max_err_tol=BEZIER_ERROR_THRESHOLD_BONE_POSITION_MAX)
			
			# if it has split, then it's not good for my purposes
			# note: i modified the code so that if it would split, it returns an empty list instead
			# TODO: it would be WAY more efficient if i could trust/use the splitting in the algorithm, but it changes
			#  the location of the endpoints without scaling the error metrics so each split makes it easier to be
			#  accepted, even without actually fitting any better
			if len(bezier_list) != 1:
				continue
			bez, rms_error, max_error = bezier_list[0]

			# under new sceme, the endpoints are not already at (0,0) and (127,127), so I gotta do that myself
			px, py = scale_two_lists(bez.px, bez.py, 127)

			# if any control points are not within the box, it's no good
			# (well, if its only slightly outside the box thats okay, i can clamp it)
			cpp = (px[1], py[1], px[2], py[2])
			if not all((0-CONTROL_POINT_BOX_THRESHOLD < p < 127+CONTROL_POINT_BOX_THRESHOLD) for p in cpp):
				continue
			
			# once i find a good interp curve match (if a match is found),
			found_beziers.append(bez)
			segment_count += 1
			keeplist.append(i + w)  # then save this proposed endpoint as a valid endpoint,
			if DEBUG >= 3:
				# i thru z is the full monotonic stretch
				# v thru w is one bezier curve on the stretch
				if (w == num_all_points-1) and (segment_count == 1):
					# if one stretch of input data can be matched to one bezier curve, then don't print the segcnt
					print(f"MATCH! bone='{bonename}' {chan} : i-z= {i}-{z} : v-w= {i+v}-{i+w} : pts={w-v+1}")
				else:
					# if there are more than 1 segment, then each also prints its index
					print(f"MATCH! bone='{bonename}' {chan} : i-z= {i}-{z} : v-w= {i+v}-{i+w} : pts={w-v+1} : #={segment_count}{'*' if (w == num_all_points-1) else ''}")
				# # only show the graph if it is more than a simple two-point line segment
				# if (w-v+1 > 2) and DEBUG_PLOTS:
				# 	bez.plotcontrol()
				# 	bez.plot()
				# 	plt.plot(x_points, y_points, 'r+')
				# 	plt.show(block=True)
					
			v = w  # where this segment ends is where the next segment will begin
			break
			# if i let it iterate all the way down to 2 points then it is guaranteed to find a match (cuz linear)
			# actually it's probably also guaranteed to pass at 3 points. do i want that? hm... probably not?
			pass  # end "w walking backwards from z to i"
		pass  # end "loop until v == z"
	if DEBUG >= 3 and DEBUG_PLOTS:
		# todo: print ALL datapoints and ALL beziers on one graph!
		for bez in found_beziers:
			bez.plotcontrol()
			bez.plot()
		plt.plot(x_points_all, y_points_all, 'r+')
		plt.show(block=True)
	
	return keeplist

def _finally_put_it_all_together(bonelist: List[vmdstruct.VmdBoneFrame], keepset: Set[int]) -> List[vmdstruct.VmdBoneFrame]:
	"""
	I have found the minimal set of frames needed to define the motion of this bone with respect to each separate
	channel... when I unify the sets from each source, I am inserting new points into the middle of most segments.
	If a bezier curve can be fit onto points A thru Z, then it's guaranteed that a bezier curve can be fit onto
	points A thru M and separately onto points M thru Z.
	So now I am re-generating the beziers and this time I actually change the interp parameters.
	
	:param bonelist: list of all boneframes that correspond to this bone
	:param keepset: set of ints, referring to indices within bonelist that are "important frames"
	:return: list of the boneframes that 'keepset' refers to, with the interpolation parameters modified
	"""
	
	# if DEBUG >= 2:
	# 	logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
	
	if isinstance(bonelist[0], vmdstruct.VmdBoneFrame):
		isbone = True
	elif isinstance(bonelist[0], vmdstruct.VmdCamFrame):
		isbone = False
	else:
		raise ValueError()
	
	# turn the set into sorted list for walking
	keepframe_indices = sorted(list(keepset))
	
	# frame 0 always gets in, so just add it now
	# don't even need to modify it's interp curves, since it's the first frame its curves dont matter
	output = [bonelist[keepframe_indices[0]]]
	
	# for each of them, re-calculate the best interpolation curve for each channel based on the frames between the keepframes
	for a in range(len(keepset) - 1):
		# for each start/end pair,
		idx_this = keepframe_indices[a]
		idx_next = keepframe_indices[a + 1]
		# for each channel (x/y/z/rot),
		# look at all the points in between (including endpoints),
		if isbone:
			allxally = [make_xy_from_segment_scalar(bonelist, idx_this, idx_next, lambda x: x.pos[0], EXPECTED_DELTA_BONE_XPOS), # x pos
						make_xy_from_segment_scalar(bonelist, idx_this, idx_next, lambda x: x.pos[1], EXPECTED_DELTA_BONE_YPOS), # y pos
						make_xy_from_segment_scalar(bonelist, idx_this, idx_next, lambda x: x.pos[2], EXPECTED_DELTA_BONE_ZPOS), # z pos
						make_xy_from_segment_rotation(bonelist, idx_this, idx_next, EXPECTED_DELTA_BONE_ROTATION_RADIANS),       # rotation
						]
		else:
			allxally = [make_xy_from_segment_scalar(bonelist, idx_this, idx_next, lambda x: x.pos[0], EXPECTED_DELTA_CAM_XPOS), # x pos
						make_xy_from_segment_scalar(bonelist, idx_this, idx_next, lambda x: x.pos[1], EXPECTED_DELTA_CAM_YPOS), # y pos
						make_xy_from_segment_scalar(bonelist, idx_this, idx_next, lambda x: x.pos[2], EXPECTED_DELTA_CAM_ZPOS), # z pos
						make_xy_from_segment_scalar(bonelist, idx_this, idx_next, lambda x: x.fov, EXPECTED_DELTA_CAM_FOV),     # fov
						make_xy_from_segment_scalar(bonelist, idx_this, idx_next, lambda x: x.dist, EXPECTED_DELTA_CAM_DIST),   # dist
						make_xy_from_segment_rotation(bonelist, idx_this, idx_next, EXPECTED_DELTA_CAM_ROTATION_RADIANS),       # rotation
						]
		all_interp_params = []
		# for each channel (x/y/z/rot),
		# generate the proper bezier interp curve,
		for d in range(len(allxally)):
			x_points, y_points = allxally[d]
			# todo: make "return_best_onelevel" iterate until the error stops decreasing, even past when it drops under the target
			bezier_list = vectorpaths.fit_cubic_bezier(x_points, y_points,
													   rms_err_tol=BEZIER_ERROR_THRESHOLD_BONE_POSITION_RMS,
													   max_err_tol=BEZIER_ERROR_THRESHOLD_BONE_POSITION_MAX,
													   max_reparam_iter=50,
													   return_best_onelevel=True)
			
			a = bezier_list[0]
			bez, rms_error, max_error = a
			
			# if rms_error > BEZIER_ERROR_THRESHOLD_BONE_POSITION_RMS or max_error > BEZIER_ERROR_THRESHOLD_BONE_POSITION_MAX:
			if max_error > BEZIER_ERROR_THRESHOLD_BONE_POSITION_RMS * 2:
				print("bad fit : i,z=%d,%d, chan=%d : rmserr %f maxerr %f" % (idx_this, idx_next, d, rms_error, max_error))
				print(bez.p)
				# bez.plotcontrol()
				# bez.plot()
				# plt.plot(x_points, y_points, 'r+')
				# plt.show(block=True)

			# under new sceme, the endpoints are not already at (0,0) and (127,127), so I gotta do that myself
			px, py = scale_two_lists(bez.px, bez.py, 127)

			# clamp all the control points to valid [0-127] range, and also make them be integers
			cpp = (px[1], py[1], px[2], py[2])  # ax ay bx by
			params = [round(core.clamp(v, 0, 127)) for v in cpp]
			all_interp_params.append(params)
			
		# for each channel (x/y/z/rot),
		# store the params into the proper field of frame_next,
		# this MUST MATCH THE ORDER that i used to fill "allxally"
		frame_next = bonelist[idx_next].copy()
		if isbone:
			frame_next.interp_x = all_interp_params[0]
			frame_next.interp_y = all_interp_params[1]
			frame_next.interp_z = all_interp_params[2]
			frame_next.interp_r = all_interp_params[3]
		else:
			frame_next.interp_x = all_interp_params[0]
			frame_next.interp_y = all_interp_params[1]
			frame_next.interp_z = all_interp_params[2]
			frame_next.interp_fov = all_interp_params[3]
			frame_next.interp_dist = all_interp_params[4]
			frame_next.interp_r = all_interp_params[5]
		
		# and finally store the modified frame in the ultimate output list.
		output.append(frame_next)
	# verify that i stored one frame for each value in keepset
	assert len(output) == len(keepset)
	return output


def simplify_boneframes(allbonelist: List[vmdstruct.VmdBoneFrame]) -> List[vmdstruct.VmdBoneFrame]:
	"""
	dont yet care about phys on/off... but, eventually i should.
	only care about x/y/z/rotation

	:param allbonelist:
	:return:
	"""
	
	# verify there is no overlapping frames, just in case
	allbonelist = vmdutil.assert_no_overlapping_frames(allbonelist)
	# sort into dict form to process each morph independently
	bonedict = vmdutil.dictify_framelist(allbonelist)
	
	# for progress printouts
	totalbonelen = len(allbonelist)
	sofarbonelen = 0
	
	# the final list of all boneframes that i am keeping
	allbonelist_out = []
	
	num_skipped = 0
	
	# print("number of bones %d" % len(bonedict))
	# analyze each morph one at a time
	for bonename, bonelist in bonedict.items():
		# if bonename != "センター":
		# 	continue
		# if bonename != "上半身":
		# 	continue
		# if bonename != "右足ＩＫ" and bonename != "左足ＩＫ" and bonename != "上半身" and bonename != "センター":
		# 	continue
		# if bonename != "右足ＩＫ":
		# 	continue
		# if bonename != "上半身2":
		# 	continue
		# if bonename != "左腕捩":
		# 	continue
		# print("BONE '%s' LEN %d" % (bonename, len(bonelist)))
		sofarbonelen += len(bonelist)
		core.print_progress_oneline(sofarbonelen / totalbonelen)
		
		if len(bonelist) <= 2:
			allbonelist_out.extend(bonelist)
			num_skipped += 1
			continue
		
		# since i need to analyze what's "important" along 4 different channels,
		# i think it's best to store a set of the indices of the frames that i think are important?
		keepset = set()
		
		# the first frame is always kept.
		keepset.add(0)
		
		#######################################################################################
		if SIMPLIFY_BONE_POSITION:
			k = _simplify_boneframes_scalar(bonename, bonelist, "posX", lambda x: x.pos[0], EXPECTED_DELTA_BONE_XPOS)
			keepset.update(k)
			k = _simplify_boneframes_scalar(bonename, bonelist, "posY", lambda x: x.pos[1], EXPECTED_DELTA_BONE_YPOS)
			keepset.update(k)
			k = _simplify_boneframes_scalar(bonename, bonelist, "posZ", lambda x: x.pos[2], EXPECTED_DELTA_BONE_ZPOS)
			keepset.update(k)
			# now i have found every frame# that is important due to position changes
			if DEBUG and len(keepset) > 2:
				# if it found only 2, ignore it, cuz that would mean just startpoint and endpoint
				print(f"'{bonename}' posALL : keep {len(keepset)}/{len(bonelist)}")
		
		#######################################################################################
		# now, i walk along the frames analyzing the ROTATION channel. this is the hard part.
		if SIMPLIFY_BONE_ROTATION:
			k = _simplify_boneframes_rotation(bonename, bonelist, EXPECTED_DELTA_BONE_ROTATION_RADIANS)
			keepset.update(k)
		
		#######################################################################################
		# now done searching for the "important" points, filled "keepset"
		if DEBUG and len(keepset) > 2:
			# if it found only 2, dont print cuz that would mean just startpoint and endpoint
			print("'%s' : RESULT : keep %d/%d = %.2f%%" % (
				bonename, len(keepset), len(bonelist), 100 * len(keepset) / len(bonelist)))
		
		# recap: i have found the minimal set of frames needed to define the motion of this bone,
		# i.e. the endpoints where a bezier can define the motion between them.
		# when i unify the sets from each source, i am makign those segments shorter.
		# if a bezier curve can be fit onto points A thru Z, then it's guaranteed that a bezier curve can
		# be fit onto points A thru M and separately onto points M thru Z.
		# i know it's possible, so, thats what i'm doing now.
		
		r = _finally_put_it_all_together(bonelist, keepset)
		allbonelist_out.extend(r)
		pass  # end "for each bonename, bonelist"
	print("BONE RESULTS (inner):")
	print("    identified %d unique bones, processed %d" % (len(bonedict), len(bonedict) - num_skipped))
	print("    keep frames %d/%d = %.2f%%" % (len(allbonelist_out), len(allbonelist), 100 * len(allbonelist_out) / len(allbonelist)))

	return allbonelist_out

def simplify_camframes(allcamlist: List[vmdstruct.VmdCamFrame]) -> List[vmdstruct.VmdCamFrame]:
	"""
	only care about x/y/z/rotation

	:param allcamlist:
	:return:
	"""
	
	# print("number of cams %d" % len(camdict))
	
	if len(allcamlist) <= 2:
		return allcamlist
	
	# since i need to analyze what's "important" along 6 different channels,
	# i think it's best to store a set of the indices of the frames that i think are important?
	keepset = set()
	
	# the first frame is always kept.
	keepset.add(0)
	
	camlist = allcamlist
	
	#######################################################################################
	if SIMPLIFY_CAM_POSITION:
		k = _simplify_boneframes_scalar("cam", camlist, "posX", lambda x: x.pos[0], EXPECTED_DELTA_CAM_XPOS)
		keepset.update(k)
		k = _simplify_boneframes_scalar("cam", camlist, "posY", lambda x: x.pos[1], EXPECTED_DELTA_CAM_YPOS)
		keepset.update(k)
		k = _simplify_boneframes_scalar("cam", camlist, "posZ", lambda x: x.pos[2], EXPECTED_DELTA_CAM_ZPOS)
		keepset.update(k)
		# now i have found every frame# that is important due to position changes
		if DEBUG and len(keepset) > 2:
			# if it found only 2, ignore it, cuz that would mean just startpoint and endpoint
			print(f"'cam' posALL : keep {len(keepset)}/{len(camlist)}")
	
	#######################################################################################
	if SIMPLIFY_CAM_FOV:
		k = _simplify_boneframes_scalar("cam", camlist, "fov", lambda x: x.fov, EXPECTED_DELTA_CAM_FOV)
		keepset.update(k)
	
	#######################################################################################
	if SIMPLIFY_CAM_DIST:
		k = _simplify_boneframes_scalar("cam", camlist, "dist", lambda x: x.dist, EXPECTED_DELTA_CAM_DIST)
		keepset.update(k)
	
	#######################################################################################
	# now, i walk along the frames analyzing the ROTATION channel. this is the hard part.
	if SIMPLIFY_CAM_ROTATION:
		k = _simplify_boneframes_rotation("cam", camlist, EXPECTED_DELTA_CAM_ROTATION_RADIANS)
		keepset.update(k)
	
	#######################################################################################
	
	# recap: i have found the minimal set of frames needed to define the motion of this cam,
	# i.e. the endpoints where a bezier can define the motion between them.
	# when i unify the sets from each source, i am makign those segments shorter.
	# if a bezier curve can be fit onto points A thru Z, then it's guaranteed that a bezier curve can
	# be fit onto points A thru M and separately onto points M thru Z.
	# i know it's possible, so, thats what i'm doing now.
	
	allcamlist_out = _finally_put_it_all_together(camlist, keepset)
	
	print("CAM RESULTS (inner):")
	print("    keep frames %d/%d = %.2f%%" % (len(allcamlist_out), len(allcamlist), 100 * len(allcamlist_out) / len(allcamlist)))

	return allcamlist_out


def measure_avg_change_per_frame(vmd: vmdstruct.Vmd):
	# H = plt.hist([j for j in ANGLE_SHARPNESS_FACTORS if j!=0 and j!=1], bins=40, density=True)
	# print("factors=", len(ANGLE_SHARPNESS_FACTORS))
	# H = plt.hist(ANGLE_SHARPNESS_FACTORS, bins=16, density=True)
	# plt.show()
	print("")
	
	# conqueror full key (no foot ik, smaller pos dataset):
	# morph 0.175
	# xpos 0.094
	# ypos 0.080
	# zpos 0.069
	# rot 0.078 cutoff at 0.5
	
	# marionette:
	# morph 0.098
	# xpos 0.155
	# ypos 0.199
	# zpos 0.160
	# rot  0.078 cutoff at 0.5
	
	# animaru w/ exp (not full keyed!):
	# morph 0.515 (!!!), massive spike at 0.5 and at 1.0
	# xpos 0.195
	# ypos 0.188
	# zpos 0.265 (no pos channels have big spike at zero)
	# rot 0.130 cutoff at 0.7
	
	# hibana (full keyed)
	# xpos 0.096
	# ypos 0.110
	# zpos 0.053
	# rot 0.091 cutoff at 0.6
	
	# getting "kinda close" is important, getting the exact right value is not!
	# actually i dont need the morph value at all lol
	# xpos ~ 0.15
	# ypos ~ 0.18
	# zpos ~ 0.16
	# rot ~ 0.10
	
	UPPER_OUTLIER_BOUND = 0.96
	LOWER_OUTLIER_BOUND = 1e-2
	
	if vmd.morphframes:
		allmorphlist = vmdutil.assert_no_overlapping_frames(vmd.morphframes)
		allmorphdict = vmdutil.dictify_framelist(allmorphlist)
		
		delta_rate_dataset = []
		for morphname, morphlist in allmorphdict.items():
			# i only care about delta between frames, if there is only one frame then i dont care
			if len(morphlist) < 3: continue
			print(f"morph '{morphname}' len {len(morphlist)}")
			# for each pair of frames,
			for i in range(len(morphlist)-1):
				c_this = morphlist[i]
				c_next = morphlist[i + 1]
				# get the val-change-per-frame,
				delta_val = (c_next.val - c_this.val)
				delta_time = (c_next.f - c_this.f)
				delta_rate = abs(delta_val) / delta_time
				# if the delta is not zero, add it to the set
				# 000.00100000
				if delta_rate > 1e-3:
				# if not delta_val == 0:
					# the dataset should be weighted by length, i think
					delta_rate_dataset.extend([delta_rate] * delta_time)
		# now that i have the deltas for all morphs, get the avg and get the histogram
		if delta_rate_dataset:
			print(min(delta_rate_dataset))
			avg = sum(delta_rate_dataset) / len(delta_rate_dataset)
			print(f"average morph delta rate = {round(avg,5)}")
			H = plt.hist(delta_rate_dataset, bins=40, range=(0.0, 1.0), density=True)
			plt.show(block=True)
			pass
	
	if vmd.boneframes:
		allbonelist = vmdutil.assert_no_overlapping_frames(vmd.boneframes)
		allbonedict = vmdutil.dictify_framelist(allbonelist)
		
		delta_rate_dataset_x = []
		delta_rate_dataset_y = []
		delta_rate_dataset_z = []
		delta_rate_dataset_rot = []
		for bonename, bonelist in allbonedict.items():
			# i only care about delta between frames, if there is only one frame then i dont care
			if len(bonelist) < 3: continue
			if bonename not in standard_skeleton_bones: continue
			print(f"bone '{bonename}' len {len(bonelist)}")
			# for each pair of frames,
			for i in range(len(bonelist)-1):
				c_this = bonelist[i]
				c_next = bonelist[i + 1]
				delta_time = (c_next.f - c_this.f)
				
				# X
				# get the val-change-per-frame,
				delta_val = (c_next.pos[0] - c_this.pos[0])
				delta_rate = abs(delta_val) / delta_time
				# if the delta is not zero, add it to the set
				# if thresh=1e-3, avg=0.10
				# if thresh=1e-2, avg=0.155
				if delta_rate > LOWER_OUTLIER_BOUND:
					# the dataset should be weighted by length, i think
					delta_rate_dataset_x.extend([delta_rate] * delta_time)
				
				# Y
				# get the val-change-per-frame,
				delta_val = (c_next.pos[1] - c_this.pos[1])
				delta_rate = abs(delta_val) / delta_time
				# if the delta is not zero, add it to the set
				# if thresh=1e-3, avg=0.141
				# if thresh=1e-2, avg=0.198
				if delta_rate > LOWER_OUTLIER_BOUND:
					delta_rate_dataset_y.extend([delta_rate] * delta_time)
				
				# Z
				# get the val-change-per-frame,
				delta_val = (c_next.pos[2] - c_this.pos[2])
				delta_rate = abs(delta_val) / delta_time
				# if the delta is not zero, add it to the set
				# if thresh=1e-3, avg=
				# if thresh=1e-2, avg=0.160
				if delta_rate > LOWER_OUTLIER_BOUND:
					delta_rate_dataset_z.extend([delta_rate] * delta_time)
				
				# rotation
				# get the val-change-per-frame,
				delta_val = get_quat_angular_distance(core.euler_to_quaternion(c_this.rot),
													  core.euler_to_quaternion(c_next.rot))
				delta_rate = abs(delta_val) / delta_time
				# if the delta is not zero, add it to the set
				# if thresh=0,    avg=0.055
				# if thresh=1e-2, avg=0.079
				if delta_rate > LOWER_OUTLIER_BOUND:
					delta_rate_dataset_rot.extend([delta_rate] * delta_time)
		
		fig, axs = plt.subplots(2, 2)
		
		# now that i have the deltas for all bones, get the avg and get the histogram
		if delta_rate_dataset_x:
			# first, discard the top 5% of values for being outliers
			delta_rate_dataset_x = sorted(delta_rate_dataset_x)[0:int(len(delta_rate_dataset_x)*UPPER_OUTLIER_BOUND)]
			avg = sum(delta_rate_dataset_x) / len(delta_rate_dataset_x)
			print(f"average bone x-position delta rate = {round(avg,5)}")
			axs[0,0].hist(delta_rate_dataset_x, bins=40, density=True)
			axs[0,0].set_title("bone x-pos delta")
		
		# now that i have the deltas for all bones, get the avg and get the histogram
		if delta_rate_dataset_y:
			# first, discard the top 5% of values for being outliers
			delta_rate_dataset_y = sorted(delta_rate_dataset_y)[0:int(len(delta_rate_dataset_y)*UPPER_OUTLIER_BOUND)]
			avg = sum(delta_rate_dataset_y) / len(delta_rate_dataset_y)
			print(f"average bone y-position delta rate = {round(avg,5)}")
			axs[0,1].hist(delta_rate_dataset_y, bins=40, density=True)
			axs[0,1].set_title("bone y-pos delta")
		
		# now that i have the deltas for all bones, get the avg and get the histogram
		if delta_rate_dataset_z:
			# first, discard the top 5% of values for being outliers
			delta_rate_dataset_z = sorted(delta_rate_dataset_z)[0:int(len(delta_rate_dataset_z)*UPPER_OUTLIER_BOUND)]
			avg = sum(delta_rate_dataset_z) / len(delta_rate_dataset_z)
			print(f"average bone z-position delta rate = {round(avg,5)}")
			axs[1,0].hist(delta_rate_dataset_z, bins=40, density=True)
			axs[1,0].set_title("bone z-pos delta")
		
		# now that i have the deltas for all bones, get the avg and get the histogram
		if delta_rate_dataset_rot:
			# first, discard the top 5% of values for being outliers
			delta_rate_dataset_rot = sorted(delta_rate_dataset_rot)[0:int(len(delta_rate_dataset_rot)*UPPER_OUTLIER_BOUND)]
			avg = sum(delta_rate_dataset_rot) / len(delta_rate_dataset_rot)
			print(f"average bone rot delta rate = {round(avg,5)}")
			axs[1,1].hist(delta_rate_dataset_rot, bins=40, density=True)
			axs[1,1].set_title("bone rot delta")

		plt.show(block=True)
		pass
	
	if vmd.camframes:
		camlist = vmd.camframes
		
		delta_rate_dataset_fov = []
		delta_rate_dataset_dist = []
		delta_rate_dataset_x = []
		delta_rate_dataset_y = []
		delta_rate_dataset_z = []
		delta_rate_dataset_rot = []

		print(f"cam len {len(camlist)}")
		# for each pair of frames,
		for i in range(len(camlist) - 1):
			c_this = camlist[i]
			c_next = camlist[i + 1]
			delta_time = (c_next.f - c_this.f)
			
			# fov
			# get the val-change-per-frame,
			delta_val = (c_next.fov - c_this.fov)
			delta_rate = abs(delta_val) / delta_time
			# if the delta is not zero, add it to the set
			# 000.00100000
			# if thresh=1e-3, avg=0.10
			# if thresh=1e-2, avg=0.155
			if delta_rate > LOWER_OUTLIER_BOUND:
				# the dataset should be weighted by length, i think
				delta_rate_dataset_fov.extend([delta_rate] * delta_time)
			
			# dist
			# get the val-change-per-frame,
			delta_val = (c_next.dist - c_this.dist)
			delta_rate = abs(delta_val) / delta_time
			# if the delta is not zero, add it to the set
			# 000.00100000
			# if thresh=1e-3, avg=0.10
			# if thresh=1e-2, avg=0.155
			if delta_rate > LOWER_OUTLIER_BOUND:
				# the dataset should be weighted by length, i think
				delta_rate_dataset_dist.extend([delta_rate] * delta_time)
			
			# X
			# get the val-change-per-frame,
			delta_val = (c_next.pos[0] - c_this.pos[0])
			delta_rate = abs(delta_val) / delta_time
			# if the delta is not zero, add it to the set
			# 000.00100000
			# if thresh=1e-3, avg=0.10
			# if thresh=1e-2, avg=0.155
			if delta_rate > LOWER_OUTLIER_BOUND:
				# the dataset should be weighted by length, i think
				delta_rate_dataset_x.extend([delta_rate] * delta_time)
			
			# Y
			# get the val-change-per-frame,
			delta_val = (c_next.pos[1] - c_this.pos[1])
			delta_rate = abs(delta_val) / delta_time
			# if the delta is not zero, add it to the set
			# 000.00100000
			# if thresh=1e-3, avg=0.141
			# if thresh=1e-2, avg=0.198
			if delta_rate > LOWER_OUTLIER_BOUND:
				delta_rate_dataset_y.extend([delta_rate] * delta_time)
			
			# Z
			# get the val-change-per-frame,
			delta_val = (c_next.pos[2] - c_this.pos[2])
			delta_rate = abs(delta_val) / delta_time
			# if the delta is not zero, add it to the set
			# 000.00100000
			# if thresh=1e-3, avg=
			# if thresh=1e-2, avg=0.160
			if delta_rate > LOWER_OUTLIER_BOUND:
				delta_rate_dataset_z.extend([delta_rate] * delta_time)
			
			# rotation
			# get the val-change-per-frame,
			delta_val = get_quat_angular_distance(core.euler_to_quaternion(c_this.rot),
												  core.euler_to_quaternion(c_next.rot))
			delta_rate = abs(delta_val) / delta_time
			# if the delta is not zero, add it to the set
			# 000.00100000
			# if thresh=0,    avg=0.055
			# if thresh=1e-2, avg=0.079
			if delta_rate > LOWER_OUTLIER_BOUND:
				delta_rate_dataset_rot.extend([delta_rate] * delta_time)
		
		fig, axs = plt.subplots(2, 3)
		
		# now that i have the deltas for all bones, get the avg and get the histogram
		if delta_rate_dataset_x:
			# first, discard the top 5% of values for being outliers
			delta_rate_dataset_x = sorted(delta_rate_dataset_x)[0:int(len(delta_rate_dataset_x) * UPPER_OUTLIER_BOUND)]
			avg = sum(delta_rate_dataset_x) / len(delta_rate_dataset_x)
			print(f"average cam x-position delta rate = {round(avg,5)}")
			axs[0, 0].hist(delta_rate_dataset_x, bins=40, density=True)
			axs[0, 0].set_title("cam x-pos delta")
		
		# now that i have the deltas for all bones, get the avg and get the histogram
		if delta_rate_dataset_y:
			# first, discard the top 5% of values for being outliers
			delta_rate_dataset_y = sorted(delta_rate_dataset_y)[0:int(len(delta_rate_dataset_y) * UPPER_OUTLIER_BOUND)]
			avg = sum(delta_rate_dataset_y) / len(delta_rate_dataset_y)
			print(f"average cam y-position delta rate = {round(avg,5)}")
			axs[0, 1].hist(delta_rate_dataset_y, bins=40, density=True)
			axs[0, 1].set_title("cam y-pos delta")
		
		# now that i have the deltas for all bones, get the avg and get the histogram
		if delta_rate_dataset_z:
			# first, discard the top 5% of values for being outliers
			delta_rate_dataset_z = sorted(delta_rate_dataset_z)[0:int(len(delta_rate_dataset_z) * UPPER_OUTLIER_BOUND)]
			avg = sum(delta_rate_dataset_z) / len(delta_rate_dataset_z)
			print(f"average cam z-position delta rate = {round(avg,5)}")
			axs[1, 0].hist(delta_rate_dataset_z, bins=40, density=True)
			axs[1, 0].set_title("cam z-pos delta")
		
		# now that i have the deltas for all bones, get the avg and get the histogram
		if delta_rate_dataset_rot:
			# first, discard the top 5% of values for being outliers
			delta_rate_dataset_rot = sorted(delta_rate_dataset_rot)[0:int(len(delta_rate_dataset_rot) * UPPER_OUTLIER_BOUND)]
			avg = sum(delta_rate_dataset_rot) / len(delta_rate_dataset_rot)
			print(f"average cam rot delta rate = {round(avg,5)}")
			axs[1, 1].hist(delta_rate_dataset_rot, bins=40, density=True)
			axs[1, 1].set_title("cam rot delta")
			
		# now that i have the deltas for all bones, get the avg and get the histogram
		if delta_rate_dataset_fov:
			# first, discard the top 5% of values for being outliers
			delta_rate_dataset_fov = sorted(delta_rate_dataset_fov)[0:int(len(delta_rate_dataset_fov) * UPPER_OUTLIER_BOUND)]
			avg = sum(delta_rate_dataset_fov) / len(delta_rate_dataset_fov)
			print(f"average cam fov delta rate = {round(avg,5)}")
			axs[0,2].hist(delta_rate_dataset_fov, bins=40, density=True)
			axs[0,2].set_title("cam fov delta")
		
		# now that i have the deltas for all bones, get the avg and get the histogram
		if delta_rate_dataset_dist:
			# first, discard the top 5% of values for being outliers
			delta_rate_dataset_dist = sorted(delta_rate_dataset_dist)[0:int(len(delta_rate_dataset_dist) * UPPER_OUTLIER_BOUND)]
			avg = sum(delta_rate_dataset_dist) / len(delta_rate_dataset_dist)
			print(f"average cam dist delta rate = {round(avg,5)}")
			axs[1,2].hist(delta_rate_dataset_dist, bins=40, density=True)
			axs[1,2].set_title("cam dist delta")
		
		plt.show(block=True)
		pass


def fully_key_motion_for_testing(vmd: vmdstruct.Vmd) -> vmdstruct.Vmd:
	start = time.time()
	vmd2 = vmd.copy()
	if vmd.morphframes:
		core.MY_PRINT_FUNC("fully keying morph frames...")
		morphlist = vmdutil.assert_no_overlapping_frames(vmd.morphframes)
		highest_timestep = max(a.f for a in morphlist)
		all_timesteps = list(range(highest_timestep+1))
		new_morphlist = vmdutil.fill_missing_boneframes_new(morphlist, desired_frames=all_timesteps, moreinfo=True,
															enable_append_prepend=False)
		vmd2.morphframes = new_morphlist

	if vmd.boneframes:
		core.MY_PRINT_FUNC("fully keying bone frames...")
		bonelist = vmdutil.assert_no_overlapping_frames(vmd.boneframes)
		highest_timestep = max(a.f for a in bonelist)
		all_timesteps = list(range(highest_timestep+1))
		new_bonelist = vmdutil.fill_missing_boneframes_new(bonelist, desired_frames=all_timesteps, moreinfo=True,
														   enable_append_prepend=False)
		vmd2.boneframes = new_bonelist
		
	if vmd.camframes:
		core.MY_PRINT_FUNC("fully keying cam frames...")
		camlist = vmd.camframes
		highest_timestep = max(a.f for a in camlist)
		all_timesteps = list(range(highest_timestep+1))
		new_camlist = vmdutil.fill_missing_boneframes_new(camlist, desired_frames=all_timesteps, moreinfo=True,
														  enable_append_prepend=False,
														  fix_fov=False)
		vmd2.camframes = new_camlist
	
	fillend = time.time()
	#TODO: function to prettyprint times
	core.MY_PRINT_FUNC(f"TIME TO FULLY KEY: {round(fillend - start)}sec")
	
	return vmd2
	
def profile_camera_heuristics():
	cameras = []
	cameras.append("../../../dances/a[a]ddiction {reol}/addiction cam (184)/[A]ddictionカメラ.vmd")
	cameras.append("../../../dances/a[a]ddiction {reol}/addiction cam (tsweitao)/Addiction_Camera_ver2.00_by_TsWEITAO.vmd")
	cameras.append(r"../../../dances\Abracadabra {Brown Eyed Girls}\Abracadabra (NatsumiSan)/camera.vmd")
	cameras.append(r"../../../dances\ANIMAる {Umetora}\ANIMAru cam (地動説)/ANIMAるCamera配布用.vmd")
	cameras.append(r"../../../dances\Donut Hole {Hachi}\Donut Hole camera (DG-RINER)/ドーナツホール - Camera Motion.vmd")
	cameras.append(r"../../../dances\Apple Pie {Fiestar}\Apple Pie camera (404nF)/apple pie_cam-interpolated.vmd")
	cameras.append(r"../../../dances\Apple Pie {Fiestar}\Apple Pie camera (404nF)/apple pie_cam-original.vmd")
	cameras.append(r"../../../dances\Roki {MikitoP}\Roki Camera (クリアクロス)/Loki_Clear Cross Camera (Matching Original Song).vmd")
	cameras.append(r"../../../dances\LUVORATORRRRRY! {Reol}\Luvoratory cam (だんしゃくいも)/LUVORATORRRRRY! new cam.vmd")
	cameras.append(r"../../../dances/Kimagure Mercy {HachiojiP}\Kimagure Mercy [5] (moka)/camera.vmd")
	cameras.append(r"../../../dances\Otome Kaibou {DECO.27}\Otome Kaibou cam (アット)/乙女解剖カメラモーション配布.vmd")
	cameras.append(r"../../../dances\Chocolate Cream {Laysha}\camera (Dr. Cossack)/camera (changed by dr. cossack).vmd")
	cameras.append(r"../../../dances\SNOBBISM {Neru}\Snobbism cam (mina mint)/SNOBBISM cam v3.0.vmd")

	for vmdname in cameras:
		vmd_orig = vmdlib.read_vmd(vmdname, moreinfo=True)
		vmd_orig = fully_key_motion_for_testing(vmd_orig)
		measure_avg_change_per_frame(vmd_orig)
	return


def main(moreinfo=True):
	###################################################################################
	# prompt for inputs
	# vmdname = core.MY_FILEPROMPT_FUNC("VMD file", ".vmd")

	# vmdname = "../../../marionette motion 1person.vmd"
	vmdname = "../../../marionette motion 1person CLEAN.vmd"
	# vmdname = "../../../IA_Conqueror_full_key_version.vmd"
	# vmdname = r"../../../dances\ANIMAる {Umetora}\ANIMAru (京まりん)/ANIMAる(with expression).vmd"
	# vmdname = r"../../../dances\Hibana {DECO.27}\Hibana (getz)/Hibana.vmd"
	# vmdname = '../../../Addiction_TdaFacial.vmd'
	# TODO BUG: why does Donut Hole INCREASE the number of frames so drastically??? 298 -> 1900
	#  is my full-interpolating function wrong?
	#  is my bez-matching criteria too strict?
	#  it has no wraparound warnings, it should guaranteed find the same or smaller number of frames!!
	vmdname = r"../../../dances\Donut Hole {Hachi}\Donut Hole camera (DG-RINER)/ドーナツホール - Camera Motion.vmd"

	
	vmd_orig = vmdlib.read_vmd(vmdname, moreinfo=moreinfo)
	
	core.MY_PRINT_FUNC("")
	vmd_orig_full = fully_key_motion_for_testing(vmd_orig)
	
	
	anychange = False
	vmd_simple = vmd_orig.copy()
	
	if vmd_orig_full.morphframes:
		core.MY_PRINT_FUNC("")
		core.MY_PRINT_FUNC("now attempting to simplify morphs...")
		start = time.time()
		newmorphs = simplify_morphframes(vmd_orig_full.morphframes)
		morphend = time.time()
		print(f"TIME FOR ALL MORPHS: {round(morphend - start)}sec")
		if newmorphs != vmd_orig_full.morphframes:
			print('morphs changed')
			print("net change frames %d/%d = %.2f%%" % (len(newmorphs), len(vmd_orig.morphframes), 100 * len(newmorphs) / len(vmd_orig.morphframes)))
			anychange = True
			vmd_simple.morphframes = newmorphs
			
	if vmd_orig_full.boneframes:
		core.MY_PRINT_FUNC("")
		core.MY_PRINT_FUNC("now attempting to simplify bones...")
		start = time.time()
		newbones = simplify_boneframes(vmd_orig_full.boneframes)
		boneend = time.time()
		print(f"TIME FOR ALL BONES: {round(boneend - start)}sec")
		if newbones != vmd_orig_full.boneframes:
			print('bones changed')
			print("net change frames %d/%d = %.2f%%" % (len(newbones), len(vmd_orig.boneframes), 100 * len(newbones) / len(vmd_orig.boneframes)))
			anychange = True
			vmd_simple.boneframes = newbones
			
			
	if vmd_orig_full.camframes:
		core.MY_PRINT_FUNC("")
		core.MY_PRINT_FUNC("now attempting to simplify camera frames...")
		start = time.time()
		newcams = simplify_camframes(vmd_orig_full.camframes)
		# need to fix the fov by making them all ints!
		for camframe in newcams:
			camframe.fov = round(camframe.fov)
		camend = time.time()
		print(f"TIME FOR ALL CAM FRAMES: {round(camend - start)}sec")
		if newcams != vmd_orig_full.camframes:
			print('cams changed')
			print("net change frames %d/%d = %.2f%%" % (len(newcams), len(vmd_orig.camframes), 100 * len(newcams) / len(vmd_orig.camframes)))
			anychange = True
			vmd_simple.camframes = newcams
	
	core.MY_PRINT_FUNC("")
	
	# todo validation: fully key vmd_simple and compare against vmd_full to quantify greatest/avg deviation
	###################################################################################
	# write outputs

	if not anychange:
		core.MY_PRINT_FUNC("nothing changed, nothing to write")
		return None
	else:
		output_filename_vmd = core.filepath_insert_suffix(vmdname, "_simplified")
		output_filename_vmd = core.filepath_get_unused_name(output_filename_vmd)
		vmdlib.write_vmd(output_filename_vmd, vmd_simple, moreinfo=moreinfo)
	
	core.MY_PRINT_FUNC("Done!")
	return None

def plot_3d(data, is_euler=False):
	original_point = [1, 0, 0]
	
	# if input data is a list of quats, convert them to eulers
	if is_euler:
		data_e = data
		data_q = [core.euler_to_quaternion(q) for q in data]
	else:
		data_e = [core.quaternion_to_euler(q) for q in data]
		data_q = data
	
	# print all the points in euler-space
	for e in data_e:
		print("{:8.3f}, {:8.3f}, {:8.3f}".format(e[0], e[1], e[2]))
	
	point_list = []
	for qrot in data_q:
		# rotate [1,0,0] around [0,0,0] by the given amount
		# THIS IS NOT PERFECT, this does not represent the x-rotation of the quat at all! but it's better than nothing?
		# TODO find a better way of printing this, bunch of arrows instead of bunch of dots
		newpoint = core.rotate3d((0, 0, 0), qrot, original_point)
		# store the resulting XYZ coordinates
		point_list.append(newpoint)
	
	# now graph them
	fig = plt.figure()
	ax = fig.add_subplot(111, projection='3d')
	x, y, z = zip(*point_list)
	ax.scatter(x, y, z, label="points")
	# x,y,z = zip(*point_list_new)
	# ax.scatter(x,y,z, label="new")
	ax.scatter(0, 0, 0, marker='+', color='k', label="origin")  # plot the origin too
	ax.set_xlim(-1, 1)
	ax.set_ylim(-1, 1)
	ax.set_zlim(-1, 1)
	STARTPOINT = core.rotate3d((0, 0, 0), data_q[0], original_point)
	ENDPOINT = core.rotate3d((0, 0, 0), data_q[-1], original_point)
	ax.scatter(*STARTPOINT, marker='x', color='r', label='START')
	ax.scatter(*ENDPOINT, marker='x', color='b', label='END')
	ax.legend()
	plt.show(block=True)


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
	
	# cProfile.run('main()', 'uninterpolate_stats')
	# ppp = pstats.Stats('uninterpolate_stats')
	# ppp.sort_stats(pstats.SortKey.CUMULATIVE)
	# ppp.print_stats()
	
	# x = [0] + [50]*50 + [100]
	# y = [0] + [50]*50 + [100]
	# print(vectorpaths.fit_cubic_bezier(x, y, rms_err_tol=1.0))
	
	# e1 = [0, 0, 0]
	# e2 = [0, 10, 0]
	# e3 = [0, 20, 0]
	# e4 = [43, 25, -4]
	# e5 = [43, 35, -4]
	# q1 = core.euler_to_quaternion(e1)
	# q2 = core.euler_to_quaternion(e2)
	# q3 = core.euler_to_quaternion(e3)
	# q4 = core.euler_to_quaternion(e4)
	# q5 = core.euler_to_quaternion(e5)
	#
	# d12 = get_difference_quat(q1, q2)
	# d23 = get_difference_quat(q2, q3)
	# d45 = get_difference_quat(q4, q5)
	#
	# print(d12)
	# print(d23)
	# print(d45)
	#
	# dist1 = get_quat_angular_distance(q1, q2)
	# dist2 = get_quat_angular_distance(q1, q3)
	# print(dist1)
	# print(dist2)
	# dist1 = get_quat_angular_distance(q1, q4)
	# dist2 = get_quat_angular_distance(q1, q5)
	# print(dist1)
	# print(dist2)
	# print(get_quat_angular_distance(q1, core.euler_to_quaternion((180, 0, 0))))
	# print(get_quat_angular_distance(q1, core.euler_to_quaternion((0, 180, 0))))
	# print(get_quat_angular_distance(q1, core.euler_to_quaternion((0, 0, 180))))
	# pass
	
	# data = [[-34.18498160983529, 162.36696123640758, -47.77082064976655],
	# 		[-33.254664043042155, 166.45073669252278, -51.87984353641723],
	# 		[-32.0425151793791, 171.39295902289882, -56.85758479140585],
	# 		[-30.312845492276253, 176.89607074752024, -62.42481334883806],
	# 		[-27.887332931654115, -177.3761874021451, -68.26338866456251],
	# 		[-24.670456884890783, -171.76023745536244, -74.05532823555019],
	# 		[-20.65589689213871, -166.54581281354416, -79.53089393235882],
	# 		[-15.913903709063252, -161.94521858255777, -84.50036877773108],
	# 		]
	#
	# code block to validate the SLERP code via 3d plotting
