import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.scripts_for_gui import morph_scale

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.01 - 7/23/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################



helptext = '''=================================================
morph_invert:
Swap the "base" and "morphed" states of a model.
Modify the default mesh to look like the morph is always applied, and modify the morph so that when it is enabled the model returns to what was previously the default.
This script will work for VERTEX, GROUP, UV, or MATERIAL morph, and does only 1 morph at a time.
Results when inverting a group morph might be unexpected, so be careful.

Output: PMX file '[modelname]_[morph#]inv.pmx'
'''

def morph_invert(pmx: pmxstruct.Pmx, target_index: int, __group_power=None) -> bool:
	# modify the model in-place
	morph = pmx.morphs[target_index]
	morphtype = morph.morphtype
	# 1=vert
	# 3=UV
	# 8=material
	core.MY_PRINT_FUNC("Found {} morph #{}: '{}' / '{}'".format(
		morphtype, target_index, morph.name_jp, morph.name_en))
	
	if morphtype == pmxstruct.MorphType.VERTEX:  # vertex
		# for each item in this morph:
		for d, item in enumerate(morph.items):
			item: pmxstruct.PmxMorphItemVertex  # type annotation for pycharm
			# apply the offset
			pmx.verts[item.vert_idx].pos[0] += item.move[0]
			pmx.verts[item.vert_idx].pos[1] += item.move[1]
			pmx.verts[item.vert_idx].pos[2] += item.move[2]
		# after applying to all items, then invert the whole morph
		pmx.morphs[target_index] = morph_scale.morph_scale(morph, -1)
	elif morphtype == pmxstruct.MorphType.UV:  # UV
		for d, item in enumerate(morph.items):
			item: pmxstruct.PmxMorphItemUV  # type annotation for pycharm
			# (vert_idx, A, B, C, D)
			# apply the offset
			pmx.verts[item.vert_idx].uv[0] += item.move[0]
			pmx.verts[item.vert_idx].uv[1] += item.move[1]
		# after applying to all items, then invert the whole morph
		pmx.morphs[target_index] = morph_scale.morph_scale(morph, -1)
	elif morphtype in (pmxstruct.MorphType.UV_EXT1, pmxstruct.MorphType.UV_EXT2,
					   pmxstruct.MorphType.UV_EXT3, pmxstruct.MorphType.UV_EXT4):  # UV1 UV2 UV3 UV4
		whichuv = morphtype.value - pmxstruct.MorphType.UV_EXT1.value
		for d, item in enumerate(morph.items):
			item: pmxstruct.PmxMorphItemUV  # type annotation for pycharm
			# apply the offset
			pmx.verts[item.vert_idx].addl_vec4s[whichuv][0] += item.move[0]
			pmx.verts[item.vert_idx].addl_vec4s[whichuv][1] += item.move[1]
			pmx.verts[item.vert_idx].addl_vec4s[whichuv][2] += item.move[2]
			pmx.verts[item.vert_idx].addl_vec4s[whichuv][3] += item.move[3]
		# after applying to all items, then invert the whole morph
		pmx.morphs[target_index] = morph_scale.morph_scale(morph, -1)
	elif morphtype == pmxstruct.MorphType.MATERIAL:  # material
		# to invert a material morph means inverting the material's visible/notvisible state as well as flipping the morph
		for d, item in enumerate(morph.items):
			item: pmxstruct.PmxMorphItemMaterial  # type annotation for pycharm
			if not (-1 < item.mat_idx < len(pmx.materials)):
				core.MY_PRINT_FUNC(
					"Warning: not sure how to handle item %d that refers to invalid material %d" % (d, item.mat_idx))
				continue
			was_mult = not item.is_add  # keep a record of whether the input was mult-type or add-type
			# unconditionally convert it to add-type for simpler inverting
			if not item.is_add:
				# this item is currently mult-type, gotta change it to be add-type!
				item = material_mult_to_add(pmx, item)
			
			# apply the effects of this material-morph-item to the appropriate material
			def _modify_the_material(base, morphamt):
				if isinstance(base, (int, float)):
					return base + morphamt
				else:
					return [b + m for b, m in zip(base, morphamt)]
			
			mat = pmx.materials[item.mat_idx]
			# toon/sph/tex RGBA modifications are totally ignored because those components of the material don't exist to be modified
			mat.alpha = _modify_the_material(mat.alpha, item.alpha)
			mat.specpower = _modify_the_material(mat.specpower, item.specpower)
			mat.edgealpha = _modify_the_material(mat.edgealpha, item.edgealpha)
			mat.edgesize = _modify_the_material(mat.edgesize, item.edgesize)
			mat.diffRGB = _modify_the_material(mat.diffRGB, item.diffRGB)
			mat.specRGB = _modify_the_material(mat.specRGB, item.specRGB)
			mat.ambRGB = _modify_the_material(mat.ambRGB, item.ambRGB)
			mat.edgeRGB = _modify_the_material(mat.edgeRGB, item.edgeRGB)
			# tex/toon/sph RGBAs dont have an entry in "base" to modify...
			# mat.texRGBA =   _modify_the_material((1, 1, 1, 1), item.texRGBA)
			# mat.toonRGBA =  _modify_the_material((1, 1, 1, 1), item.toonRGBA)
			# mat.sphRGBA =   _modify_the_material((1, 1, 1, 1), item.sphRGBA)
			
			# if the input was originally mult-type, try to go back to mult-type.
			# if it gets zero-div-err and stays as add-type, thats fine.
			if was_mult:
				item = material_add_to_mult(pmx, item)
			# store the (possibly modified) material-morph-item back into its proper location
			morph.items[d] = item
		
		# after applying to all items, then invert the whole morph
		pmx.morphs[target_index] = morph_scale.morph_scale(morph, -1)
	elif morphtype == pmxstruct.MorphType.BONE:
		core.MY_PRINT_FUNC("Unhandled morph type: %s" % str(morphtype))
		core.MY_PRINT_FUNC(
			"I really don't want to write the huge amount of code necessary to run forward-kinematics simulation for this one niche task")
		core.MY_PRINT_FUNC("quitting")
		return False
	elif morphtype == pmxstruct.MorphType.GROUP:
		if __group_power is not None:
			core.MY_PRINT_FUNC("Warning: group morphs inside other group morphs do not function. skipping.")
		else:
			core.MY_PRINT_FUNC("Group morph! Inverting all members of this group!")
		for d, item in enumerate(morph.items):
			item: pmxstruct.PmxMorphItemGroup  # type annotation for pycharm
			if not (-1 < item.morph_idx < len(pmx.morphs)):
				core.MY_PRINT_FUNC("Warning: not sure how to handle item %d that refers to invalid morph %d" % (d, item.morph_idx))
				continue
			
			if item.value != 1:
				core.MY_PRINT_FUNC("Warning: not sure how to handle item %d with power not equal to 1! skipping." % d)
				continue
			morph_invert(pmx, item.morph_idx)
			# the group morph actually stays the same, everything that's included within the group morphs are what get inverted!
	else:
		core.MY_PRINT_FUNC("Unhandled morph type: %s" % str(morphtype))
		core.MY_PRINT_FUNC("quitting")
		return False
	return True


def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	core.MY_PRINT_FUNC("")
	# valid input is any string that can matched aginst a morph idx
	s = core.MY_GENERAL_INPUT_FUNC(lambda x: morph_scale.get_idx_in_pmxsublist(x, pmx.morphs) is not None,
								   ["Please specify the target morph: morph #, JP name, or EN name (names are not case sensitive).",
									"Empty input will quit the script."])
	# do it again, cuz the lambda only returns true/false
	target_index = morph_scale.get_idx_in_pmxsublist(s, pmx.morphs)
	
	# when given empty text, done!
	if target_index == -1 or target_index is None:
		core.MY_PRINT_FUNC("quitting")
		return None
	
	# do the thing!
	r = morph_invert(pmx, target_index)
	
	if not r:
		core.MY_PRINT_FUNC("no changes, no writeout")
		return None
	
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, ("_%dinv" % target_index))
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None

def material_mult_to_add(pmx: pmxstruct.Pmx, item: pmxstruct.PmxMorphItemMaterial):
	newitem = item.copy()
	if not newitem.is_add:
		# this item is currently mult-type, gotta change it to be add-type!
		newitem.is_add = True
		
		# for each parameter, new = (base * current) - base
		def _mult_to_add(base, morph):
			if isinstance(base, (int,float)): return (base * morph) - base
			else: return [(b * c) - b for b, c in zip(base, morph)]
		
		mat = pmx.materials[item.mat_idx]
		newitem.alpha =     _mult_to_add(mat.alpha, item.alpha)
		newitem.specpower = _mult_to_add(mat.specpower, item.specpower)
		newitem.edgealpha = _mult_to_add(mat.edgealpha, item.edgealpha)
		newitem.edgesize =  _mult_to_add(mat.edgesize, item.edgesize)
		newitem.diffRGB =   _mult_to_add(mat.diffRGB, item.diffRGB)
		newitem.specRGB =   _mult_to_add(mat.specRGB, item.specRGB)
		newitem.ambRGB =    _mult_to_add(mat.ambRGB, item.ambRGB)
		newitem.edgeRGB =   _mult_to_add(mat.edgeRGB, item.edgeRGB)
		# tex/toon/sph RGBAs dont have an entry in "base" to reference...
		newitem.texRGBA =   _mult_to_add((1, 1, 1, 1), item.texRGBA)
		newitem.toonRGBA =  _mult_to_add((1, 1, 1, 1), item.toonRGBA)
		newitem.sphRGBA =   _mult_to_add((1, 1, 1, 1), item.sphRGBA)
	return newitem

def material_add_to_mult(pmx: pmxstruct.Pmx, item: pmxstruct.PmxMorphItemMaterial):
	# note: if the base alpha is 0, then no amount of mult can pull that up to 1! zero-div-error
	# therefore it will return the original add-type material-morph-item instead
	newitem = item.copy()
	if newitem.is_add:
		# this item is currently add-type, gotta change it to be mult-type!
		newitem.is_add = False
		
		# for each parameter, new = (base * current) - base
		def _add_to_mult(base, morph):
			if isinstance(base, (int,float)): return morph / base
			else: return [c / b for b, c in zip(base, morph)]
		
		mat = pmx.materials[item.mat_idx]
		try:
			newitem.alpha =     _add_to_mult(mat.alpha, item.alpha)
			newitem.specpower = _add_to_mult(mat.specpower, item.specpower)
			newitem.edgealpha = _add_to_mult(mat.edgealpha, item.edgealpha)
			newitem.edgesize =  _add_to_mult(mat.edgesize, item.edgesize)
			newitem.diffRGB =   _add_to_mult(mat.diffRGB, item.diffRGB)
			newitem.specRGB =   _add_to_mult(mat.specRGB, item.specRGB)
			newitem.ambRGB =    _add_to_mult(mat.ambRGB, item.ambRGB)
			newitem.edgeRGB =   _add_to_mult(mat.edgeRGB, item.edgeRGB)
			# tex/toon/sph RGBAs dont have an entry in "base" to reference...
			newitem.texRGBA =   _add_to_mult((1, 1, 1, 1), item.texRGBA)
			newitem.toonRGBA =  _add_to_mult((1, 1, 1, 1), item.toonRGBA)
			newitem.sphRGBA =   _add_to_mult((1, 1, 1, 1), item.sphRGBA)
		except ZeroDivisionError:
			return item
	return newitem


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
