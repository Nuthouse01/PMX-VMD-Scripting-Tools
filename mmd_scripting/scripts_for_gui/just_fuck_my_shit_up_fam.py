import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct

from mmd_scripting.overall_cleanup.dispframe_fix import dispframe_fix

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.04 - 8/19/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


helptext = '''=================================================
make a model into a horrifying abomination!
'''

def main(moreinfo=True):
	###################################################################################
	# prompt for inputs
	core.MY_PRINT_FUNC("Please enter name of PMX model file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	mode = core.MY_SIMPLECHOICE_FUNC((1,2,3,4),
									 ["pick your poison",
									  "1=burn victim",
									  "2=mangle",
									  "3=puddle",])
	# read
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)

	if mode==1:
		# vertex mode
		# improperly insert one vertex, this will cause all faces to be drawn between the wrong vertices
		# it will also mess up any vertex morphs
		# but, it should move basically the same?
		pmx.verts.insert(0, pmx.verts[0].copy())
		pass
	if mode==2:
		# bone mode
		# improperly insert one bone, this will cause all weighting to be wrong and all bone relationships to be wrong
		# it won't really be obvious till you try to move it tho
		pmx.bones.insert(0, pmx.bones[0].copy())
		pass
	if mode==3:
		# wobblifier
		# make every single bone a physics system, except for lowerbody and upperbody
		# first, delete all existing physics
		pmx.joints.clear()
		pmx.rigidbodies.clear()
		# then make all bones be visible
		for d,bone in enumerate(pmx.bones):
			bone.has_visible = True
			bone.has_enabled = True
			bone.deform_after_phys = False
		# add them to the display frames
		dispframe_fix(pmx, moreinfo=False)
		
		# then, create a rididbody for each bone
		template_rb = pmxstruct.PmxRigidBody(
			name_jp="", name_en="", bone_idx=-1, pos=[0,0,0], rot=[0,0,0], size=[0.3,0,0],
			shape=pmxstruct.RigidBodyShape.SPHERE, group=1, nocollide_set={1},
			phys_mode=pmxstruct.RigidBodyPhysMode.PHYSICS_ROTATEONLY,
			phys_mass=0.02, phys_move_damp=0.5, phys_rot_damp=0.5, phys_repel=0.2, phys_friction=0.5
		)
		for d,bone in enumerate(pmx.bones):
			new_rb = template_rb.copy()
			new_rb.name_jp = bone.name_jp
			new_rb.name_en = bone.name_en
			new_rb.pos = bone.pos.copy()
			new_rb.bone_idx = d
			pmx.rigidbodies.append(new_rb)
		# how does it look so far? it should just melt into a puddle i think?
	# if mode==4:
	# 	# next, create joints that connect everything
	# 	# each joint should be located at the parent bone
	# 	template_joint = pmxstruct.PmxJoint(
	# 		name_jp="", name_en="", jointtype=pmxstruct.JointType.SPRING_SIXDOF, rb1_idx=-1, rb2_idx=-1,
	# 		pos=[0,0,0], rot=[0,0,0],
	# 		movemin=[0,0,0], movemax=[0,0,0], movespring=[100, 100, 100],
	# 		rotmin=[0,0,0], rotmax=[0,0,0], rotspring=[100, 100, 100]
	# 	)
	# 	for d,bone in enumerate(pmx.bones):
	# 		if bone.parent_idx == -1: continue
	# 		parent = pmx.bones[bone.parent_idx]
	# 		new_joint = template_joint.copy()
	# 		new_joint.name_jp = bone.name_jp
	# 		new_joint.name_en = bone.name_en
	# 		new_joint.pos = parent.pos.copy()
	# 		new_joint.rb1_idx = bone.parent_idx
	# 		new_joint.rb2_idx = d
	# 		pmx.joints.append(new_joint)
	# 		pass
	# 	# lastly, set certain specific rigidbodies to NOT be physics-type so the system kinda stays upright
	# 	# lowerbody, upperbody, upperbody2?
	# 	lower_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == "下半身")
	# 	upper_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == "上半身")
	# 	make_bonetype = [lower_idx, upper_idx]
	# 	make_bonetype.extend(bone_get_ancestors(pmx.bones, lower_idx))
	# 	make_bonetype.extend(bone_get_ancestors(pmx.bones, upper_idx))
	# 	for i in make_bonetype:
	# 		pmx.rigidbodies[i].phys_mode = pmxstruct.RigidBodyPhysMode.BONE
	
	core.MY_PRINT_FUNC("")
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_ruined")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None

if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
