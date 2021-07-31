import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.00 - 6/10/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################



helptext = '''=================================================
model_offset:
Move the entire model by some X Y Z amount. This is a replacement for the buggy, broken, useless plugin that is built into PMXE.

Output: PMX file '[modelname]_shift.pmx'
'''


# this func converts str to list of floats, returns None if it cannot
def is_3float(x: str):
	try:
		xsplit = x.split(",")
		# must be able to split it into 3 pieces after splitting on comma
		if len(xsplit) != 3:
			core.MY_PRINT_FUNC("Input must be 3 items")
			return None
		# each piece must be able to convert to float
		ret = []
		for xs in xsplit:
			ret.append(float(xs))
		return ret
	except ValueError:
		core.MY_PRINT_FUNC("Could not convert input to decimal numbers")
		return None


def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	# to shift the model by a set amount:
	# first, ask user for X Y Z
	
	# create the prompt popup
	shift_str = core.MY_GENERAL_INPUT_FUNC(
		lambda x: (is_3float(x) is not None),
		["Enter the X,Y,Z amount to shift this model by:",
		 "Three decimal values separated by commas.",
		 "Empty input will quit the script."])
	
	# if empty, quit
	if shift_str == "":
		core.MY_PRINT_FUNC("quitting")
		return None
	# use the same func to convert the input string
	shift = is_3float(shift_str)
	
	####################
	# then execute the shift:
	for v in pmx.verts:
		# every vertex position
		for i in range(3):
			v.pos[i] += shift[i]
		# c, r0, r1 params of every SDEF vertex
		# these correspond to real positions in 3d space so they need to be modified
		if v.weighttype == pmxstruct.WeightMode.SDEF:
			for param in v.weight_sdef:
				for i in range(3):
					param[i] += shift[i]
				
	# bone position
	for b in pmx.bones:
		for i in range(3):
			b.pos[i] += shift[i]
			
	# rigid body position
	for rb in pmx.rigidbodies:
		for i in range(3):
			rb.pos[i] += shift[i]

	# joint position
	for j in pmx.joints:
		for i in range(3):
			j.pos[i] += shift[i]

	# that's it? that's it!
	
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_shift")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
