import math
from typing import List

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.scripts_for_gui import bone_add_semistandard_auto_armtwist

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.00 - 7/13/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


# MAX_ALLOWABLE_DEVIATION = 0.01
MAX_ALLOWABLE_DEVIATION = 0.0001


helptext = '''=================================================
bone_set_arm_localaxis:
This will set the "local axis" parameters for the shoulder/arm/elbow/wrist bones. It will also check if the armtwist/wristtwist bones are in a perfectly colinear position, and if not, it will move them so that they are colinear.

Output: PMX file '[modelname]_localaxis.pmx'
'''


# left and right prefixes
jp_l =    "左"
jp_r =    "右"
# names for relevant bones
jp_shoulder =   "肩" # "shoulder"
jp_shoulderP =  "肩P" # "shoulderP"
jp_arm =		"腕" # "arm"
jp_armtwist =	"腕捩" # "arm twist"
jp_elbow =		"ひじ" # "elbow"
jp_wristtwist = "手捩" # "wrist twist"
jp_wrist =		"手首" # "wrist"


def find_colinear_deviation_vector(axis_end1: List[float], axis_end2: List[float], point: List[float]) -> List[float]:
	"""
	Determine how far (and what direction) the armtwist bone is from being perfectly colinear between the arm and
	elbow bones. Return the vector from the closest colinear point to the given point.
	:param axis_end1: XYZ position of one end of axis
	:param axis_end2: XYZ position of the other end of the axis
	:param point: XYZ position of the point which we want to make colinear
	:return: XYZ vector, subtract this from 'point' to make it perfectly colinear
	"""
	# first, figure out what direction the axis is going
	line_to_match = [a - b for a, b in zip(axis_end2, axis_end1)]
	line_to_match = core.normalize_distance(line_to_match)
	
	desired_direction = (0.0, 0.0, 1.0)
	
	# https://math.stackexchange.com/a/60556/889783
	q_axis = core.my_cross_product(line_to_match, desired_direction)
	q_axis = core.normalize_distance(q_axis)
	q_angle = math.acos(core.my_dot(line_to_match, desired_direction))
	# "the usual axis-angle to quaternion conversion"
	quat = [math.cos(q_angle / 2)] + [a * math.sin(q_angle / 2) for a in q_axis]
	
	# OKAY! now i have "quat" which describes how much to rotate axis_end2 to make it directly ABOVE axis_end1
	# rotate the "point" by this amount as well. if perfectly colinear it will match the x and y of axis_end1
	rotated_point = core.rotate3d(axis_end1, quat, point)
	# figure out how much the point needs to be moved to be perfectly colinear...
	delta = [a - b for a, b in zip(rotated_point, axis_end1)]
	# force the z-component to be 0, want to move it into the line, not move it ALONG the line
	delta[2] = 0
	# undo the rotation and transform this delta back into the original coordinate space
	rotated_delta = core.rotate3d((0.0, 0.0, 0.0), core.my_quat_conjugate(quat), delta)
	return rotated_delta

def set_bone_localaxis(pmx: pmxstruct.Pmx, me: pmxstruct.PmxBone, pointat: pmxstruct.PmxBone):
	# set tail
	me.tail_usebonelink = True
	me.tail = pointat.idx_within(pmx.bones)
	# set localaxis
	xaxis = [f - i for i, f in zip(me.pos, pointat.pos)]
	xaxis = core.normalize_distance(xaxis)
	yaxis = bone_add_semistandard_auto_armtwist.calculate_perpendicular_offset_vector(xaxis)
	zaxis = core.my_cross_product(xaxis, yaxis)
	me.has_localaxis = True
	me.localaxis_x = xaxis
	me.localaxis_z = zaxis
	return None

def set_all_arm_localaxis(pmx: pmxstruct.Pmx, moreinfo=False) -> None:
	"""
	Set the localaxis for the shoulder, arm, elbow, hand, armtwist, and handtwist bones.
	Also sets each bone to be pointing at the correct bone/thing.
	Also, if the twistbones are not in colinear position, move them so they are.
	:param pmx: the whole PMX object
	:param moreinfo: moreinfo
	"""
	# TODO: check before/after to see if any of these changes were "significant"
	for side in (jp_l, jp_r):
		# these should DEFINITElY 100% guaranteed exist. err if they do not.
		shoulder = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + jp_shoulder), getitem=True)
		arm = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + jp_arm), getitem=True)
		elbow = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + jp_elbow), getitem=True)
		wrist = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + jp_wrist), getitem=True)
		
		# 1, shoulder!
		set_bone_localaxis(pmx, shoulder, arm)

		# 2, shoulderP! if it exists.
		shoulderP = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + jp_shoulderP), getitem=True)
		if shoulderP is not None:
			# disable tail
			shoulderP.tail_usebonelink = True
			shoulderP.tail = -1
			# set localaxis to same as shoulder
			shoulderP.has_localaxis = True
			shoulderP.localaxis_x = shoulder.localaxis_x
			shoulderP.localaxis_z = shoulder.localaxis_z
		
		# 3, arm!
		set_bone_localaxis(pmx, arm, elbow)
		
		# 4, armtwist
		armtwist = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + jp_armtwist), getitem=True)
		if armtwist is not None:
			# how far is the armtwist bone from being perfectly colinear?
			deviation = find_colinear_deviation_vector(arm.pos, elbow.pos, armtwist.pos)
			# if the deviation is unacceptably large, then modify it
			deviation_dist = core.my_euclidian_distance(deviation)
			if (deviation_dist > MAX_ALLOWABLE_DEVIATION) or moreinfo:
				core.MY_PRINT_FUNC("Existing twistbone '{}' is {} units away from the proper axis".format(
					armtwist.name_jp, round(deviation_dist,5)))
			if deviation_dist > MAX_ALLOWABLE_DEVIATION:
				core.MY_PRINT_FUNC("This deviation is unacceptably large, now moving the bone into colinear position")
				# correct the bone by subtracting the deviation
				armtwist.pos = [p - d for p, d in zip(armtwist.pos, deviation)]
			# regardless of that, guarantee that fixedaxis is enabled and correct
			xaxis = [e - a for e, a in zip(elbow.pos, arm.pos)]
			xaxis = core.normalize_distance(xaxis)
			armtwist.has_fixedaxis = True  # guarantee that fixedaxis is enabled
			armtwist.fixedaxis = xaxis
			# also set the tail and localaxis
			set_bone_localaxis(pmx, armtwist, elbow)
			
		# 5, elbow, same as arm
		set_bone_localaxis(pmx, elbow, wrist)
		
		# 6, elbowtwist or wristtwist, same as armtwist
		wristtwist = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + jp_wristtwist), getitem=True)
		if wristtwist is not None:
			# how far is the wristtwist bone from being perfectly colinear?
			deviation = find_colinear_deviation_vector(elbow.pos, wrist.pos, wristtwist.pos)
			# if the deviation is unacceptably large, then modify it
			deviation_dist = core.my_euclidian_distance(deviation)
			if (deviation_dist > MAX_ALLOWABLE_DEVIATION) or moreinfo:
				core.MY_PRINT_FUNC("Existing twistbone '{}' is {} units away from the proper axis".format(
					wristtwist.name_jp, round(deviation_dist,5)))
			if deviation_dist > MAX_ALLOWABLE_DEVIATION:
				core.MY_PRINT_FUNC("This deviation is unacceptably large, now moving the bone into colinear position")
				# correct the bone by subtracting the deviation
				wristtwist.pos = [p - d for p, d in zip(wristtwist.pos, deviation)]
			# regardless of that, guarantee that fixedaxis is enabled and correct
			xaxis = [e - a for e, a in zip(elbow.pos, arm.pos)]
			xaxis = core.normalize_distance(xaxis)
			wristtwist.has_fixedaxis = True  # guarantee that fixedaxis is enabled
			wristtwist.fixedaxis = xaxis
			# also set the tail and localaxis
			set_bone_localaxis(pmx, wristtwist, wrist)
			
		# 7, wrist
		# if the wrist bone isnt pointing at anything then there is nothing for me to do
		if (wrist.tail == -1) or (wrist.tail == [0.0, 0.0, 0.0]):
			pass
		else:
			# if it IS pointing at something, then i can set the localaxis based on that!
			if wrist.tail_usebonelink:
				endpoint = pmx.bones[wrist.tail].pos
			else:
				endpoint = [a+b for a,b in zip(wrist.pos, wrist.tail)]
			xaxis = [f - i for i, f in zip(wrist.pos, endpoint)]
			xaxis = core.normalize_distance(xaxis)
			yaxis = bone_add_semistandard_auto_armtwist.calculate_perpendicular_offset_vector(xaxis)
			zaxis = core.my_cross_product(xaxis, yaxis)
			wrist.has_localaxis = True
			wrist.localaxis_x = xaxis
			wrist.localaxis_z = zaxis
	return None

def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	set_all_arm_localaxis(pmx, moreinfo)
	
	core.MY_PRINT_FUNC("")
	
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_localaxis")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
	