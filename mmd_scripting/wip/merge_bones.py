import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.overall_cleanup.weight_cleanup import normalize_weights

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.00 - 6/10/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


helptext = '''=================================================
merge_bones:
This is used for transferring the weights of bone X to bone Y, to effectively merge the bones.
Specifically this is intended for merging "helper" bones that inherit only a portion of the rotatation from their parent.
But you can use it to merge any 2 bones if you wish.

Output: model PMX file '[modelname]_weightmerge.pmx'
'''


# stage 1: script(function) to flatten/merge helper bones
def transfer_bone_weights(pmx: pmxstruct.Pmx, to_bone: int, from_bone: int, scalefactor=1.0):
	# TODO: test this! ensure that this math is logically correct! not 100% convinced
	if to_bone == from_bone: return
	# !!! WARNING: result is not normal, need to normalize afterward !!!
	# clamp just cuz
	scalefactor = core.clamp(scalefactor, 0.0, 1.0)
	# for each vertex, determine if that vert is controlled by from_bone
	for d,vert in enumerate(pmx.verts):
		w = vert.weight
		if vert.weighttype == pmxstruct.WeightMode.BDEF1:
			# BDEF1
			if w[0][0] == from_bone: # match!
				if scalefactor == 1:
					w[0][0] = to_bone
				else:
					# TODO: rethink this? test this? not 100% convinced this is correct
					# if the from_bone had 100% weight but only a .5 factor, then this should only move half as much as the to_bone
					# the other half of the weight would come from the parent of the to_bone, i suppose?
					to_bone_parent = pmx.bones[to_bone].parent_idx
					if to_bone_parent == -1: # if to_bone is root and has no parent,
						w[0][0] = to_bone
					else: # if to_parent is valid, convert to BDEF2
						vert.weighttype = pmxstruct.WeightMode.BDEF2
						vert.weight = [[to_bone, scalefactor],
									   [to_bone_parent, 1-scalefactor]]
		elif vert.weighttype in (pmxstruct.WeightMode.BDEF2, pmxstruct.WeightMode.SDEF):
			# BDEF2, SDEF
			# (b1, b2, b1w)
			# replace the from_bone ref with to_bone, but also need to modify the value
			# a = b1w out, z = b1w in, f = scalefactor
			# a = z*f / (z*f + (1-z))
			if w[0][0] == from_bone:
				w[0][0] = to_bone
				z = w[0][1]
				newval = (z*scalefactor) / (z*scalefactor + (1-z))
				w[0][1] = newval
				w[1][1] = 1 - newval
			elif w[1][0] == from_bone:
				w[1][0] = to_bone
				z = 1 - w[0][1]
				newval = 1 - (z*scalefactor) / (z*scalefactor + (1-z))
				w[0][1] = newval
				w[1][1] = 1 - newval
		elif vert.weighttype in (pmxstruct.WeightMode.BDEF4, pmxstruct.WeightMode.QDEF):
			# BDEF4, QDEF
			# (b1, b2, b3, b4, b1w, b2w, b3w, b4w)
			for pair in vert.weight:
				if pair[0] == from_bone and pair[1] != 0:
					pair[0] = to_bone
					pair[1] *= scalefactor
	# done! no return, modifies PMX list directly
	return None


def is_float(x):
	try:
		v = float(x)
		return True
	except ValueError:
		core.MY_PRINT_FUNC("Please enter a decimal number")
		return False


def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	##################################
	# user flow:
	# ask for the helper bone (to be merged)
	# ask for the destination bone (merged onto)
	# try to infer proper merge factor, if it cannot infer then prompt user
	# then write out to file
	##################################
		
	dest_idx = 0
	while True:
		# any input is considered valid
		s = core.MY_GENERAL_INPUT_FUNC(lambda x: True,
									   ["Please specify the DESTINATION bone that weights will be transferred to.",
										"Enter bone #, JP name, or EN name (names are case sensitive).",
										"Empty input will quit the script."])
		# if empty, leave & do nothing
		if s == "":
			dest_idx = -1
			break
		# then get the bone index from this
		# search JP names first
		dest_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == s)
		if dest_idx is not None: break  # did i find a match?
		# search EN names next
		dest_idx = core.my_list_search(pmx.bones, lambda x: x.name_en == s)
		if dest_idx is not None: break  # did i find a match?
		# try to cast to int next
		try:
			dest_idx = int(s)
			if 0 <= dest_idx < len(pmx.bones):
				break  # is this within the proper bounds?
			else:
				core.MY_PRINT_FUNC("valid bone indexes are 0-%d" % (len(pmx.bones) - 1))
		except ValueError:
			pass
		core.MY_PRINT_FUNC("unable to find matching bone for name '%s'" % s)
	
	if dest_idx == -1:
		core.MY_PRINT_FUNC("quitting")
		return None
	
	dest_tag = "bone #{} JP='{}' / EN='{}'".format(dest_idx, pmx.bones[dest_idx].name_jp, pmx.bones[dest_idx].name_jp)
	source_idx = 0
	while True:
		# any input is considered valid
		s = core.MY_GENERAL_INPUT_FUNC(lambda x: True,
									   ["Please specify the SOURCE bone that will be merged onto %s." % dest_tag,
										"Enter bone #, JP name, or EN name (names are case sensitive).",
										"Empty input will quit the script."])
		# if empty, leave & do nothing
		if s == "":
			source_idx = -1
			break
		# then get the morph index from this
		# search JP names first
		source_idx = core.my_list_search(pmx.bones, lambda x: x.name_jp == s)
		if source_idx is not None: break  # did i find a match?
		# search EN names next
		source_idx = core.my_list_search(pmx.bones, lambda x: x.name_en == s)
		if source_idx is not None: break  # did i find a match?
		# try to cast to int next
		try:
			source_idx = int(s)
			if 0 <= source_idx < len(pmx.bones):
				break  # is this within the proper bounds?
			else:
				core.MY_PRINT_FUNC("valid bone indexes are 0-%d" % (len(pmx.bones) - 1))
		except ValueError:
			pass
		core.MY_PRINT_FUNC("unable to find matching bone for name '%s'" % s)
	
	if source_idx == -1:
		core.MY_PRINT_FUNC("quitting")
		return None
	
	# print to confirm
	core.MY_PRINT_FUNC("Merging bone #{} JP='{}' / EN='{}' ===> bone #{} JP='{}' / EN='{}'".format(
		source_idx, pmx.bones[source_idx].name_jp, pmx.bones[source_idx].name_en,
		dest_idx, pmx.bones[dest_idx].name_jp, pmx.bones[dest_idx].name_en
	))
	# now try to infer the merge factor
	
	f = 0.0
	if pmx.bones[source_idx].inherit_rot and pmx.bones[source_idx].inherit_parent_idx == dest_idx and pmx.bones[source_idx].inherit_ratio != 0:
		# if using partial rot inherit AND inheriting from dest_idx AND ratio != 0, use that
		# think this is good, if twistbones exist they should be children of preferred
		f = pmx.bones[source_idx].inherit_ratio
	elif pmx.bones[source_idx].parent_idx == dest_idx:
		# if they have a direct parent-child relationship, then factor is 1
		f = 1
	else:
		# otherwise, prompt for the factor
		factor_str = core.MY_GENERAL_INPUT_FUNC(is_float, "Unable to infer relationship, please specify a merge factor:")
		if factor_str == "":
			core.MY_PRINT_FUNC("quitting")
			return None
		f = float(factor_str)
		
	# do the actual transfer
	transfer_bone_weights(pmx, dest_idx, source_idx, f)
	
	# run the weight-cleanup function
	_ = normalize_weights(pmx)
	
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_weightmerge")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
