from typing import List

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_vmd_parser as vmdlib
import mmd_scripting.core.nuthouse01_vmd_struct as vmdstruct
import mmd_scripting.core.nuthouse01_vmd_utils as vmdutil
import numpy as np
import matplotlib.pyplot as plt


_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.05 - 9/7/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################
# https://github.com/volkerp/fitCurves


helptext = '''=================================================
vmd_uninterpolate:
Modify a VMD and remove excess keyframes caused by deliberate over-keying.
This will make the VMD much smaller (filesize) and make it

Output: dunno
'''

WIGGLE = 0.00001

BEZIER_ERROR_THRESHOLD = 100

def bezier_generate(points):
	# TODO
	# receive a list of any number of (x,y) points
	# return a list of exactly 4 bezier control points
	return [(0,0), (0.3, 0.3), (0.6, 0.6), (1, 1)]

def bezier_quantify_error(points, bezier_params):
	# TODO
	# receive a bezier curve and the points that generated it
	# evaluate exactly how much error it represents
	# sum of square of errors? greatest amount of deviation? idk
	return 123

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
				if (delta_rate - WIGGLE) < delta_z < (delta_rate + WIGGLE):
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
		if 1:
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


def simplify_boneframes(allbonelist: List[vmdstruct.VmdBoneFrame]) -> List[vmdstruct.VmdBoneFrame]:
	"""
	dont yet care about phys on/off... but, eventually i should.
	only care about x/y/z/rotation
	
	:param allbonelist:
	:return:
	"""
	def state(U):
		if U == 0: return 0
		elif U > 0: return 1
		else: return 2
	
	output = []
	
	# verify there is no overlapping frames, just in case
	allbonelist = vmdutil.assert_no_overlapping_frames(allbonelist)
	# sort into dict form to process each morph independently
	bonedict = vmdutil.dictify_framelist(allbonelist)
	
	# analyze each morph one at a time
	for bonename, bonelist in bonedict.items():
		
		if len(bonelist) <= 2:
			output.extend(bonelist)
			continue
		
		# since i need to analyze what's "important" along 4 different channels,
		# i think it's best to store a set of the indices of the frames that i think are important?
		keepidx = set()
		
		# the first frame is always kept.
		keepidx.add(0)
		
		# i'll do the x independent from the y independent from the z
		for C in range(3):
			i = 0
			while i < (len(bonelist) - 1):
				# start walking down this list
				# assume that i is the start point of a potentially over-keyed section
				b_this = bonelist[i]
				b_next = bonelist[i+1]
				# find the delta for this channel
				b_delta = (b_next.pos[C] - b_this.pos[C]) / (b_next.f - b_this.f)
				# now, walk forward from here until i "return" a frame that has a different delta
				# "different" means only different state, i.e. rising/falling/zero
				b_state = state(b_delta)
				z = 0  # to make pycharm shut up
				for z in range(i + 1, len(bonelist)):
					# if i reach the end of the bonelist, then "return" the final valid index
					if z == len(bonelist) - 1:
						break
					z_this = bonelist[z]
					z_next = bonelist[z + 1]
					z_delta = (z_next.pos[C] - z_this.pos[C]) / (z_next.f - z_this.f)
					if state(z_delta) == b_state:
						# if this is potentially part of the same sequence, keep iterating
						pass
					else:
						# if this is definitely no longer part of the sequence, THEN i can break
						break
				# now i have found a z that might be an endpoint
				# anything past z is DEFINITELY NOT the endpoint for this sequence
				# from z, walk backward and test endpoint quality at each frame
				points = []
				y_start = b_this.pos[C]
				x_start = b_this.f
				for test in range(z, i, -1):
					# calculate the x,y (scale of 0 to 1) for all points between i and "test"
					y_end = bonelist[test].pos[C]
					y_range = y_end - y_start
					x_end = bonelist[test].f
					x_range = x_end - x_start
					points.clear()
					for P in range(i, test+1):
						point = bonelist[P]
						x_rel = (point.f - x_start) / x_range
						y_rel = (point.pos[C] - y_start) / y_range
						points.append((x_rel, y_rel))
					# TODO then run regression to find a reasonable interpolation curve for this stretch
					bez_params = bezier_generate(points)
					# then quantify "how good" this interpolation curve is
					# 		? use total integral of error
					# 		? use max amount of error
					bez_error = bezier_quantify_error(points, bez_params)
					# i think i want to run backwards until i find "an acceptably good match"
					# gonna need to do a bunch of testing to quantify what "acceptably good" looks like tho
					if bez_error < BEZIER_ERROR_THRESHOLD:
						# once i find a good interp curve match (if a match is found) then mark the start point and end point
						i = test
						keepidx.add(test)
						break
					# if none of the tested points are good, then 'test' is left with the value 'z'
					pass
				pass
			pass
		# now, i walk along the frames analyzing the ROTATION channel. this is the hard part.
		i = 0
		while i < (len(bonelist) - 1):
			# start walking down this list
			# assume that i is the start point of a potentially over-keyed section
			b_this = bonelist[i]
			b_next = bonelist[i + 1]
			# find the delta for this channel
		# TODO now that i have filled the "keepidx" set, turn those into frames
		#  for each of them, re-calculate the best interpolation curve for each channel based on the frames between the keepframes
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
