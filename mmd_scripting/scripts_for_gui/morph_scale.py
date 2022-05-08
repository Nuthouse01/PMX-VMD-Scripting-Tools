from typing import Union, List

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.01 - 7/23/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


# if this is false, the original morph is preserved and a new morph is created with a different name.
# if this is true, then there will be no renaming. the scaled morph will replace the original morph.
SCALE_MORPH_IN_PLACE = False


helptext = '''=================================================
morph_scale:
Scale the magnitude of a morph by a given value. The result is appended as a new, separate morph.
Example: increase the strength of a vertex morph by 2.5x, or reduce its strength to 0.7x what it was.
For bone morphs, you can scale the rotation component separately from the motion (translation) component.
This script will work for VERTEX, BONE, UV, or MATERIAL morph, and does only 1 morph at a time.

Output: PMX file '[modelname]_[morph#]scal.pmx'
'''

# function that takes a string & returns idx if it can match one, or None otherwise
def get_idx_in_pmxsublist(s: str, pmxlist: List):
	if s == "": return -1
	# then get the morph index from this
	# search JP names first
	t = core.my_list_search(pmxlist, lambda x: x.name_jp.lower() == s.lower())
	if t is not None: return t
	# search EN names next
	t = core.my_list_search(pmxlist, lambda x: x.name_en.lower() == s.lower())
	if t is not None: return t
	# try to cast to int next
	try:
		t = int(s)
		if 0 <= t < len(pmxlist):
			return t
		else:
			core.MY_PRINT_FUNC("valid indexes are [0-'%d']" % (len(pmxlist) - 1))
			return None
	except ValueError:
		core.MY_PRINT_FUNC("unable to find matching item for input '%s'" % s)
		return None





def morph_scale(morph: pmxstruct.PmxMorph, scale: Union[List[float], float], bone_mode=0) -> pmxstruct.PmxMorph:
	"""
	Supports BONE, VERTEX, UV, MATERIAL. That's it. Input "scale" can be a single float or list of up to 4.
	Return a new morph object.
	:param morph: morph to scale
	:param scale: numeric amount to scale by, positive or negative, can be 0
	:param bone_mode: what to scale if the morph is bone-type. 1 = motion(translation), 2 = rotation, 3 = both.
	:return: new morph after scaling
	"""
	
	# independent x/y/z scale for bone & vertex morphs
	# UV and UV# morphs have independent x/y/z/w
	# material morphs only use one value
	
	newmorph = morph.copy()
	morphtype = newmorph.morphtype
	
	# accept scale as either int/float or list of 3 int/float
	if isinstance(scale,(int,float)):
		scale = [scale] * 4
	if len(scale) < 4:
		scale.extend([1] * (4 - len(scale)))

	if morphtype == pmxstruct.MorphType.BONE:  # bone
		# bone_mode: 1 = motion(translation), 2 = rotation, 3 = both
		if bone_mode in (2,3):  # if ==2 or ==3, then do rotation
			for d, item in enumerate(newmorph.items):
				item: pmxstruct.PmxMorphItemBone  # type annotation for pycharm
				# i guess scaling in euclid-space is good enough? assuming all resulting components are <180
				# most bone morphs only rotate around one axis anyways
				item.rot = [x * s for x,s in zip(item.rot, scale)]
				
		if bone_mode in (1,3):  # if ==1 or ==3, then do translation
			for d, item in enumerate(newmorph.items):
				item: pmxstruct.PmxMorphItemBone  # type annotation for pycharm
				# scale the morph XYZ
				item.move = [x * s for x,s in zip(item.move, scale)]
				
	elif morphtype == pmxstruct.MorphType.VERTEX:  # vertex
		# for each item in this morph:
		for d, item in enumerate(newmorph.items):
			item: pmxstruct.PmxMorphItemVertex  # type annotation for pycharm
			# scale the morph XYZ
			item.move = [x * s for x, s in zip(item.move, scale)]
			
	elif morphtype in (pmxstruct.MorphType.UV,
								pmxstruct.MorphType.UV_EXT1,
								pmxstruct.MorphType.UV_EXT2,
								pmxstruct.MorphType.UV_EXT3,
								pmxstruct.MorphType.UV_EXT4):  # UV  UV1 UV2 UV3 UV4
		for d, item in enumerate(newmorph.items):
			item: pmxstruct.PmxMorphItemUV  # type annotation for pycharm
			# scale the morph UV
			item.move = [x * s for x, s in zip(item.move, scale)]
			
	elif morphtype == pmxstruct.MorphType.MATERIAL:  # material
		# core.MY_PRINT_FUNC("material morph is WIP")
		for d, item in enumerate(newmorph.items):
			item: pmxstruct.PmxMorphItemMaterial  # type annotation for pycharm
			if item.is_add:
				# to scale additive morphs, just scale like normal
				item.alpha *=     scale[0]
				item.specpower *= scale[0]
				item.edgealpha *= scale[0]
				item.edgesize *=  scale[0]
				item.diffRGB =  [d * scale[0] for d in item.diffRGB]
				item.specRGB =  [d * scale[0] for d in item.specRGB]
				item.ambRGB =   [d * scale[0] for d in item.ambRGB]
				item.edgeRGB =  [d * scale[0] for d in item.edgeRGB]
				item.texRGBA =  [d * scale[0] for d in item.texRGBA]
				item.toonRGBA = [d * scale[0] for d in item.toonRGBA]
				item.sphRGBA =  [d * scale[0] for d in item.sphRGBA]
			else:
				# but to scale multiplicative morphs, scale around 1! meaning subtract 1, then scale, then add 1
				item.alpha = ((item.alpha - 1) * scale[0]) + 1
				item.specpower = ((item.specpower - 1) * scale[0]) + 1
				item.edgealpha = ((item.edgealpha - 1) * scale[0]) + 1
				item.edgesize = ((item.edgesize - 1) * scale[0]) + 1
				item.diffRGB =  [((d - 1) * scale[0]) + 1 for d in item.diffRGB]
				item.specRGB =  [((d - 1) * scale[0]) + 1 for d in item.specRGB]
				item.ambRGB =   [((d - 1) * scale[0]) + 1 for d in item.ambRGB]
				item.edgeRGB =  [((d - 1) * scale[0]) + 1 for d in item.edgeRGB]
				item.texRGBA =  [((d - 1) * scale[0]) + 1 for d in item.texRGBA]
				item.toonRGBA = [((d - 1) * scale[0]) + 1 for d in item.toonRGBA]
				item.sphRGBA =  [((d - 1) * scale[0]) + 1 for d in item.sphRGBA]
	else:
		core.MY_PRINT_FUNC("Unhandled morph type: %s" % str(morphtype))
	return newmorph



def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	core.MY_PRINT_FUNC("")
	# valid input is any string that can matched aginst a morph idx
	s = core.MY_GENERAL_INPUT_FUNC(lambda x: get_idx_in_pmxsublist(x, pmx.morphs) is not None,
	   ["Please specify the target morph: morph #, JP name, or EN name (names are not case sensitive).",
		"Empty input will quit the script."])
	# do it again, cuz the lambda only returns true/false
	target_index = get_idx_in_pmxsublist(s, pmx.morphs)
	
	# when given empty text, done!
	if target_index == -1 or target_index is None:
		core.MY_PRINT_FUNC("quitting")
		return None
	
	# determine the morph type
	morphtype = pmx.morphs[target_index].morphtype
	core.MY_PRINT_FUNC("Found {} morph #{}: '{}' / '{}'".format(
		morphtype, target_index, pmx.morphs[target_index].name_jp, pmx.morphs[target_index].name_en))
	
	# if it is a bone morph, ask for translation/rotation/both
	bone_mode = 0
	if morphtype == pmxstruct.MorphType.BONE:
		bone_mode = core.MY_SIMPLECHOICE_FUNC((1,2,3),
			["Bone morph detected: do you want to scale the motion(translation), rotation, or both?",
			 "1 = motion(translation), 2 = rotation, 3 = both"])
	
	# ask for factor: keep looping this prompt until getting a valid float
	def is_float(x):
		try:
			_ = float(x)
			return True
		except ValueError:
			core.MY_PRINT_FUNC("Please enter a decimal number")
			return False
	factor_str = core.MY_GENERAL_INPUT_FUNC(is_float, "Enter the factor that you want to scale this morph by:")
	if factor_str == "":
		core.MY_PRINT_FUNC("quitting")
		return None
	factor = float(factor_str)
	
	# important values: target_index, factor, bone_mode
	##### do the actual scale!! deepcopy and return a new object.
	newmorph = morph_scale(pmx.morphs[target_index], factor, bone_mode)
	
	if SCALE_MORPH_IN_PLACE:
		# if scaling in place, then override the old one.
		pmx.morphs[target_index] = newmorph
	else:
		# otherwise, modify the name & append
		name_suffix = "*" + (str(factor)[0:6])
		newmorph.name_jp += name_suffix
		newmorph.name_en += name_suffix
		pmx.morphs.append(newmorph)
		
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, ("_%dscal" % target_index))
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
