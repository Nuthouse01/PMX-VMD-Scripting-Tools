import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_vmd_parser as vmdlib
import mmd_scripting.core.nuthouse01_vpd_parser as vpdlib

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.5.03 - 10/10/2020"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

########################################################################################################################
# constants & options
########################################################################################################################




########################################################################################################################
# MAIN & functions
########################################################################################################################

def convert_vpd_to_vmd(vpd_path: str, moreinfo=True):
	"""
	Read a VPD pose file from disk, convert it, and write to disk as a VMD motion file.
	The resulting VMD will be empty except for bone/morph frames at time=0.
	The output will have the same path and basename, but the opposite file extension.
	
	:param vpd_path: filepath to input vpd, absolute or relative to CWD
	:param moreinfo: default false. if true, get extra printouts with more info about stuff.
	"""
	# read the VPD into memory as a VMD object
	vmd = vpdlib.read_vpd(vpd_path, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("")
	# identify an unused filename for writing the output
	base = core.filepath_splitext(vpd_path)[0]
	base += ".vmd"
	vmd_outpath = core.filepath_get_unused_name(base)
	# write the output VMD file
	vmdlib.write_vmd(vmd_outpath, vmd, moreinfo=moreinfo)
	# done!
	return


def convert_vmd_to_vpd(vmd_path: str, moreinfo=True):
	"""
	Read a VMD motion file from disk, convert it, and write to disk as a VPD pose file.
	All frames of the VMD are ignored except for frames at time=0.
	The output will have the same path and basename, but the opposite file extension.
	
	:param vmd_path: filepath to input vmd, absolute or relative to CWD
	:param moreinfo: default false. if true, get extra printouts with more info about stuff.
	"""
	# read the entire VMD, all in this one function
	vmd = vmdlib.read_vmd(vmd_path, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("")
	# identify an unused filename for writing the output
	base = core.filepath_splitext(vmd_path)[0]
	base += ".vpd"
	vpd_outpath = core.filepath_get_unused_name(base)
	# write the output VPD file
	vpdlib.write_vpd(vpd_outpath, vmd, moreinfo=moreinfo)
	# done!
	return


helptext = '''=================================================
convert_vmd_to_txt:
This tool will convert VPD pose data to/from VMD motion data. Not sure why you would want to do that, but now you can.
VMD -> VPD and VPD -> VMD are both supported.

The output will have the same path and basename, but the opposite file extension.
'''


def main(moreinfo=False):
	# prompt for "convert text -> VMD" or "VMD -> text"
	core.MY_PRINT_FUNC("For VPD->VMD, please enter the name of a .vpd file.\nOr for VMD->VPD, please enter the name of a .vmd file.")
	core.MY_PRINT_FUNC("")
	input_filename = core.MY_FILEPROMPT_FUNC("VMD or VPD file",(".vmd",".vpd"))
	
	if input_filename.lower().endswith(".vpd"):
		# POSE -> MOTION
		convert_vpd_to_vmd(input_filename, moreinfo=moreinfo)
	else:
		# MOTION -> POSE
		convert_vmd_to_vpd(input_filename, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None
	
########################################################################################################################
# after all the funtions are defined, actually execute main()
########################################################################################################################

if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
