import mmd_scripting.core.nuthouse01_core as core

_SCRIPT_VERSION = "Script version:  <author> - <pkg version when created> - <date when created>"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


helptext = '''=================================================
<script name>:
<explanation>

Output: <outputs>'
'''

def main(moreinfo=True):
	###################################################################################
	# prompt for inputs
	#
	#
	#
	###################################################################################
	# do something
	#
	#
	#
	###################################################################################
	# write outputs
	#
	#
	#
	core.MY_PRINT_FUNC("")
	# output_filename_vmd = core.filepath_insert_suffix(input_filename_vmd, "_renamed")
	# output_filename_vmd = core.filepath_get_unused_name(output_filename_vmd)
	# vmdlib.write_vmd(output_filename_vmd, vmd, moreinfo=moreinfo)
	
	core.MY_PRINT_FUNC("Done!")
	return None

if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
