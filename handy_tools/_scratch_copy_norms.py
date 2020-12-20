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

import sys
try:
	sys.path.append("../")
	from python import nuthouse01_core as core
	from python import nuthouse01_pmx_parser as pmxlib
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	core = pmxlib = None




##################
# copy normals
###################

pmx_flatrot = pmxlib.read_pmx("nano feetflatrot.pmx")
pmx_point =   pmxlib.read_pmx("nano feetpoint3.pmx")

# copy normals of steephalf to point

for v_flatrot, v_point in zip(pmx_flatrot.verts, pmx_point.verts):
	v_point.norm = v_flatrot.norm

pmxlib.write_pmx("FINAL.pmx", pmx_point)
