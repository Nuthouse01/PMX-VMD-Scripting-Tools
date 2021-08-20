import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib

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
	mode = core.MY_SIMPLECHOICE_FUNC((1,2), "pick your poison")
	# read
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)

	if mode==1:
		# vertex mode
		# improperly insert one vertex, this will cause all faces to be drawn between the wrong vertices
		# it will also mess up any vertex morphs
		# but, it should move basically the same?
		pmx.verts.insert(0, pmx.verts[0].copy())
		pass
	else:
		# bone mode
		# improperly insert one bone, this will cause all weighting to be wrong and all bone relationships to be wrong
		# it won't really be obvious till you try to move it tho
		pmx.bones.insert(0, pmx.bones[0].copy())
		pass
	
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
