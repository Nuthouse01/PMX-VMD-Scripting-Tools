import math

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.scripts_for_gui import morph_scale

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.00 - 6/10/2021"

"""
DO FEET THE BEST WAY
!!!
in the final model, first vertex morph is applied, then bone morph is applied
requires: vertex morph from pointed feet pose to flat feet pose
sequence:
1. invert v morph that goes point > flat, save as feetflat
2. use "avg normals face" and "avg normals near" to create set of normals for when feet are flat
3. create "rigid" version of flat mesh, save as feetflatrigid
4. import feetflatrigid into point for comparing
5. determine what bone rotation to apply to point that gets me the closest to flat, save as morph (also apply this rotation to the toe IK bones and get their yz delta into the bone morph too)
6. with bone rotation applied (looks like shit) do "update model" on pointed version, go to list view, copy all bones, then undo
7. paste into list view of feetflat, will move bones to be aligned with flat-foot geometry, save!
8. apply inverse bone rotation to feetflat in transform view, do "update model", save as feetflatrot
9. get v morph from feetpoint to feetflatrot
10. apply b + v to feetpoint to verify it's close, only bdef2 zones are divergent

11. invert v-point-to-rot to apply, then "update model" with b-rot-to-almost to apply, then save feetalmost
12. get v morph from feetalmost to feetflat, copy to feetpoint
13. correct the morph by rotation-per-weight
14. merge the point-to-rot vmorph and almost-to-flat(rotated) vmorph using "join morph (boolean)"
15. transfer-by-order normals from feetflatrot to feetpoint
"""


matchbones = (17, 21, 30, 31,)
# rotamt = (28, 28, -28, -28,)
rotamt = (-28, -28, 28, 28,)
# first try opposite values from the point-to-flat morph


###################
# rotate morph
###################

def main():
	m = core.prompt_user_filename("PMX file", ".pmx")
	
	pmx = pmxlib.read_pmx(m)
	
	core.MY_PRINT_FUNC("")
	# valid input is any string that can matched aginst a morph idx
	s = core.MY_GENERAL_INPUT_FUNC(lambda x: morph_scale.get_idx_in_pmxsublist(x, pmx.morphs) is not None,
								   ["Please specify the target morph: morph #, JP name, or EN name (names are not case sensitive).",
		"Empty input will quit the script."])
	# do it again, cuz the lambda only returns true/false
	morph = morph_scale.get_idx_in_pmxsublist(s, pmx.morphs)
	print(pmx.morphs[morph].name_jp)

	newmorphitems = []
	
	print("target morph controls %d verts" % len(pmx.morphs[morph].items))
	count = 0
	
	for item in pmx.morphs[morph].items:
		item:pmxstruct.PmxMorphItemVertex
		
		v = pmx.verts[item.vert_idx]
		w = v.weight
		# already know its all mode1
		
		rot = 0
		# only care about BDEF2, right? or sdef
		# if not a bdef2 vertex, then rot=0 meaning no change
		if v.weighttype in (pmxstruct.WeightMode.BDEF2, pmxstruct.WeightMode.SDEF):
			for b,r in zip(matchbones, rotamt):
				# get the weight %, multiply it by how much the bone is rotated by
				if w[0][0] == b:
					rot += r * w[0][1]
				elif w[1][0] == b:
					rot += r * w[1][1]
			# count how many actually get rotated
			if rot != 0: count += 1
		# convert from degrees to radians for rotate2d()
		rot = math.radians(rot)
	
		# now the YZ component of the morph vector is rotated around the origin
		ny, nz = core.rotate2d((0,0), rot, item.move[1:3])
		newitem = pmxstruct.PmxMorphItemVertex(item.vert_idx, [item.move[0], ny, nz])
		newmorphitems.append(newitem)
	
	print("partial-rotated %d verts" % count)
	
	newmorph = pmxstruct.PmxMorph("v-rot", "v-rot",
								  morphtype=pmxstruct.MorphType.VERTEX,
								  panel=pmxstruct.MorphPanel.OTHER,
								  items=newmorphitems)
	pmx.morphs.append(newmorph)
	# done iter, now write
	OUT = core.filepath_get_unused_name("NEW.pmx")
	pmxlib.write_pmx(OUT, pmx)
	print("done")



if __name__ == "__main__":
	print(_SCRIPT_VERSION)
	main()

