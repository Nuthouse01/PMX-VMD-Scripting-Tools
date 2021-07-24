from mmd_scripting.core import nuthouse01_core as core

_SCRIPT_VERSION = "Script version:  <author> - <pkg version when created> - <date when created>"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False

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
	# output_filename_vmd = "%s_renamed.vmd" % input_filename_vmd[0:-4]
	# output_filename_vmd = core.get_unused_file_name(output_filename_vmd)
	# vmdlib.write_vmd(output_filename_vmd, vmd, moreinfo=moreinfo)
	
	core.MY_PRINT_FUNC("Done!")
	return None

if __name__ == '__main__':
	print(_SCRIPT_VERSION)
	# print info to explain the purpose of this file
	core.MY_PRINT_FUNC(helptext)
	core.MY_PRINT_FUNC("")
	if DEBUG:
		main()
	else:
		try:
			# print info to explain the purpose of this file
			core.MY_PRINT_FUNC(helptext)
			core.MY_PRINT_FUNC("")
			
			main()
		except (KeyboardInterrupt, SystemExit):
			# this is normal and expected, do nothing and die normally
			pass
		except Exception as ee:
			# if an unexpected error occurs, catch it and print it and call pause_and_quit so the window stays open for a bit
			core.MY_PRINT_FUNC(ee.__class__.__name__, ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
	core.pause_and_quit("Done with everything! Goodbye!")
