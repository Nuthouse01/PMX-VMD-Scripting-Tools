import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.scripts_for_gui import morph_scale, model_shift

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.00 - 6/10/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################



helptext = '''=================================================
model_scale:
Scale the entire model around 0,0,0 by some X,Y,Z value.
This also scales all vertex and bone morphs by the same amount, so you don't need to do that separately.

Output: PMX file '[modelname]_scale.pmx'
'''




def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	# to shift the model by a set amount:
	# first, ask user for X Y Z
	
	# create the prompt popup
	scale_str = core.MY_GENERAL_INPUT_FUNC(
		lambda x: (model_shift.is_3float(x) is not None),
		["Enter the X,Y,Z amount to scale this model by:",
		 "Three decimal values separated by commas.",
		 "Empty input will quit the script."])
	
	# if empty, quit
	if scale_str == "":
		core.MY_PRINT_FUNC("quitting")
		return None
	# use the same func to convert the input string
	scale = model_shift.is_3float(scale_str)
	
	uniform_scale = (scale[0] == scale[1] == scale[2])
	if not uniform_scale:
		core.MY_PRINT_FUNC("Warning: when scaling by non-uniform amounts, rigidbody sizes will not be modified")
	
	####################
	# what does it mean to scale the entire model?
	# scale vertex position, sdef params
	# ? scale vertex normal vectors, then normalize? need to convince myself of this interaction
	# scale bone position, tail offset
	# scale fixedaxis and localaxis vectors, then normalize
	# scale vert morph, bone morph
	# scale rigid pos, size
	# scale joint pos, movelimits
	
	for v in pmx.verts:
		# vertex position
		for i in range(3):
			v.pos[i] *= scale[i]
		# vertex normal
		for i in range(3):
			if scale[i] != 0:
				v.norm[i] /= scale[i]
			else:
				v.norm[i] = 100000
		# then re-normalize the normal vector
		v.norm = core.normalize_distance(v.norm)
		# c, r0, r1 params of every SDEF vertex
		# these correspond to real positions in 3d space so they need to be modified
		if v.weighttype == pmxstruct.WeightMode.SDEF:
			for param in v.weight_sdef:
				for i in range(3):
					param[i] *= scale[i]
				
	for b in pmx.bones:
		# bone position
		for i in range(3):
			b.pos[i] *= scale[i]
		# bone tail if using offset mode
		if not b.tail_usebonelink:
			for i in range(3):
				b.tail[i] *= scale[i]
		# scale fixedaxis and localaxis vectors, then normalize
		if b.has_fixedaxis:
			for i in range(3):
				b.fixedaxis[i] *= scale[i]
			# then re-normalize
			b.fixedaxis = core.normalize_distance(b.fixedaxis)
		# scale fixedaxis and localaxis vectors, then normalize
		if b.has_localaxis:
			for i in range(3):
				b.localaxis_x[i] *= scale[i]
			for i in range(3):
				b.localaxis_z[i] *= scale[i]
			# then re-normalize
			b.localaxis_x = core.normalize_distance(b.localaxis_x)
			b.localaxis_z = core.normalize_distance(b.localaxis_z)

	for m in pmx.morphs:
		# vertex morph and bone morph (only translate, not rotate)
		if m.morphtype in (pmxstruct.MorphType.VERTEX, pmxstruct.MorphType.BONE):
			morph_scale.morph_scale(m, scale, bone_mode=1)
			
	for rb in pmx.rigidbodies:
		# rigid body position
		for i in range(3):
			rb.pos[i] *= scale[i]
		# rigid body size
		# NOTE: rigid body size is a special conundrum
		# spheres have only one dimension, capsules have two, and only boxes have 3
		# what's the "right" way to scale a sphere by 1,5,1? there isn't a right way!
		# boxes and capsules can be rotated and stuff so their axes dont line up with world axes, too
		# is it at least possible to rotate bodies so they are still aligned with their bones?
		# eh, why even bother with any of that. 95% of the time full-model scale will be uniform scaling.
		# only scale the rigidbody size if doing uniform scaling: that is guaranteed to be safe!
		if uniform_scale:
			for i in range(3):
				rb.size[i] *= scale[i]

	for j in pmx.joints:
		# joint position
		for i in range(3):
			j.pos[i] *= scale[i]
		# joint min slip
		for i in range(3):
			j.movemin[i] *= scale[i]
		# joint max slip
		for i in range(3):
			j.movemax[i] *= scale[i]

	# that's it? that's it!
	
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_scale")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
