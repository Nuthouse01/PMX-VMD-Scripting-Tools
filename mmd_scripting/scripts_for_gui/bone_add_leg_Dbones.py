import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.core.nuthouse01_pmx_utils import insert_single_bone
from mmd_scripting.scripts_for_gui.bone_add_semistandard_auto_armtwist import fix_deform_for_children

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.05 - 8/22/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


helptext = '''=================================================
bone_add_leg_Dbones:
This will add D-bones to the legs, which are useful for applying constant offsets to a model's legs.
This is basically the same thing that the "Semistandard Bones Plugin" does, but mine checks for a few additional things and is less likely to cause buggy behavior.
Except that this doesn't re-weight the foot zone for the ToeEX bone.
You can run "Semistandard Bones Plugin", then run this, and then do "Merge Bones with Same Names" and it'll all be fine.

Output: model PMX file '[modelname]_Dbones.pmx'
'''

# left and right prefixes
jp_l =    "左"
jp_r =    "右"
# names for relevant bones
jp_leg = "足"
jp_knee = "ひざ"
jp_foot = "足首"
jp_toe = "つま先"
jp_Dleg = "足D"
jp_Dknee = "ひざD"
jp_Dfoot = "足首D"
jp_toeEX = "足先EX"

D_deform_layer = 2



def create_leg_d_bones(pmx: pmxstruct.Pmx, side: str):
	"""
	
	:param pmx:
	:param side:
	"""
	# create new bones that are copies of leg, knee, foot
	# insert after toe bone
	# transfer all vertex weight from original to D
	# transfer all rigidbody reference from original to D
	# within all bones that aren't the the Primary Leg Chain (or have D-bone names), change all references from original to D
	# add to disp frame
	
	# find leg
	leg_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + jp_leg))
	leg = pmx.bones[leg_idx]
	# find knee
	knee_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + jp_knee))
	knee = pmx.bones[knee_idx]
	# find foot
	foot_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + jp_foot))
	foot = pmx.bones[foot_idx]
	# find toe
	toe_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == (side + jp_toe))
	toe = pmx.bones[toe_idx]

	# create new bones that are modified copies of leg, knee, foot
	# cannot set the references to other bones until after they are inserted tho
	# parent_idx, inherit_parent_idx, tail
	legD = leg.copy()
	legD.name_jp = side + jp_Dleg
	legD.name_en = ""
	legD.has_visible = True
	legD.has_enabled = True
	legD.deform_layer = D_deform_layer
	legD.inherit_rot = True
	legD.inherit_ratio = 1
	legD.tail_usebonelink = True
	legD.tail = -1  ###
	legD.inherit_parent_idx = -1  ###
	
	kneeD = knee.copy()
	kneeD.name_jp = side + jp_Dknee
	kneeD.name_en = ""
	kneeD.has_visible = True
	kneeD.has_enabled = True
	kneeD.deform_layer = D_deform_layer
	kneeD.inherit_rot = True
	kneeD.inherit_ratio = 1
	kneeD.tail_usebonelink = True
	kneeD.tail = -1  ###
	kneeD.inherit_parent_idx = -1  ###

	footD = foot.copy()
	footD.name_jp = side + jp_Dfoot
	footD.name_en = ""
	footD.has_visible = True
	footD.has_enabled = True
	footD.deform_layer = D_deform_layer
	footD.inherit_rot = True
	footD.inherit_ratio = 1
	footD.tail_usebonelink = False
	footD.tail = [f - i for f,i in zip(toe.pos, foot.pos)]
	footD.inherit_parent_idx = -1  ###

	# now insert them
	legD_idx = max((leg_idx, knee_idx, foot_idx, toe_idx)) + 1
	kneeD_idx = legD_idx + 1
	footD_idx = legD_idx + 2
	insert_single_bone(pmx, legD, legD_idx)
	insert_single_bone(pmx, kneeD, kneeD_idx)
	insert_single_bone(pmx, footD, footD_idx)
	
	# now make them properly point to other bones
	legD.inherit_parent_idx = leg_idx
	legD.tail = kneeD_idx
	kneeD.parent_idx = legD_idx
	kneeD.inherit_parent_idx = knee_idx
	kneeD.tail = footD_idx
	footD.parent_idx = kneeD_idx
	footD.inherit_parent_idx = foot_idx
	
	bases = (jp_leg, jp_knee, jp_foot, jp_toe, jp_Dleg, jp_Dknee, jp_Dfoot)
	important_bone_names = [side + b for b in bases]
	
	# then, transfer all "responsibilities" from the original to the new
	# vertex weight, rigidbodies, reference by other bones
	def transfer_responsibility(old_idx, new_idx):
		# any weights currently set to "from_bone" get replaced with "to_bone"
		# i don't care what the weight type is i just find-and-replace
		for v in pmx.verts:
			for pair in v.weight:
				if pair[0] == old_idx:
					pair[0] = new_idx
		# move all rigidbodies attached to "from_bone" to "to_bone" instead
		for rb in pmx.rigidbodies:
			if rb.bone_idx == old_idx:
				rb.bone_idx = new_idx
		# move full-parent and partial-parent for any bone that isn't a Leg Chain or Dbone
		# also need to ensure that deform relationship is changed to match!
		for b in pmx.bones:
			if b.name_jp in important_bone_names: continue
			if b.parent_idx == old_idx:
				b.parent_idx = new_idx
			if b.inherit_parent_idx == old_idx:
				b.inherit_parent_idx = new_idx
				
		return
	
	transfer_responsibility(leg_idx, legD_idx)
	transfer_responsibility(knee_idx, kneeD_idx)
	transfer_responsibility(foot_idx, footD_idx)

	# ensure that the deform relationships are fixed, if needed
	num_changed = 0
	num_changed += fix_deform_for_children(pmx, legD_idx)
	num_changed += fix_deform_for_children(pmx, kneeD_idx)
	num_changed += fix_deform_for_children(pmx, footD_idx)
	
	if num_changed:
		core.MY_PRINT_FUNC("Updated deform for %d helper bones" % num_changed)
	
	# lastly, add these to the appropriate display frame immediately below the foot bone
	# find the foot bone in the display frames
	for frame in pmx.frames:
		for d, item in enumerate(frame.items):
			if item.is_morph: continue
			if item.idx == foot_idx:
				# create the items to insert
				legD_item = pmxstruct.PmxFrameItem(is_morph=False, idx=legD_idx)
				kneeD_item = pmxstruct.PmxFrameItem(is_morph=False, idx=kneeD_idx)
				footD_item = pmxstruct.PmxFrameItem(is_morph=False, idx=footD_idx)
				frame.items.insert(d+1, legD_item)
				frame.items.insert(d+2, kneeD_item)
				frame.items.insert(d+3, footD_item)
				break
	return

def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	create_leg_d_bones(pmx, jp_l)
	create_leg_d_bones(pmx, jp_r)
	
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_Dbones")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
