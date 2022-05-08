import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_io as io
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.5.03 - 10/10/2020"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


helptext = '''=================================================
pmx_list_bone_morph_names:
This very simple script will print the JP and EN names of all bones and morphs in a PMX model.
This is only useful for users who don't have access to PMXEditor.

Outputs: morph name list text file '[modelname]_morph_names.txt'
         bone name list text file '[modelname]_bone_names.txt'
'''


def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	realbones = pmx.bones		# get bones
	realmorphs = pmx.morphs		# get morphs
	modelname_jp = pmx.header.name_jp
	modelname_en = pmx.header.name_en
	
	bonelist_out = [
		["modelname_jp", "'" + modelname_jp + "'"],
		["modelname_en", "'" + modelname_en + "'"],
		["bonename_jp", "bonename_en"]
	]
	morphlist_out = [
		["modelname_jp", "'" + modelname_jp + "'"],
		["modelname_en", "'" + modelname_en + "'"],
		["morphname_jp", "morphname_en"]
	]

	# in both lists, idx0 = name_jp, idx1 = name_en
	bonelist_pairs =  [[a.name_jp, a.name_en] for a in realbones]
	morphlist_pairs = [[a.name_jp, a.name_en] for a in realmorphs]
	bonelist_out += bonelist_pairs
	morphlist_out += morphlist_pairs
	
	
	# write out
	basename_pmx = core.filepath_splitext(input_filename_pmx)[0]
	output_filename_bone = basename_pmx + "_bone_names.txt"
	output_filename_bone = core.filepath_get_unused_name(output_filename_bone)
	core.MY_PRINT_FUNC("...writing result to file '%s'..." % output_filename_bone)
	io.write_csvlist_to_file(output_filename_bone, bonelist_out, use_jis_encoding=False)

	output_filename_morph = basename_pmx + "_morph_names.txt"
	output_filename_morph = core.filepath_get_unused_name(output_filename_morph)
	core.MY_PRINT_FUNC("...writing result to file '%s'..." % output_filename_morph)
	io.write_csvlist_to_file(output_filename_morph, morphlist_out, use_jis_encoding=False)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
