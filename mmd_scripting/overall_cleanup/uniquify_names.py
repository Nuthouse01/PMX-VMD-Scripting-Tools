import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.5.03 - 10/10/2020"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################



# by default, don't unquify empty names, cuz this just turns them into "*1" "*2" "*3" etc
# which is argubaly even less useful than the default "Null_01" "Null_02" "Null_03" MMD turns them into
# but you can turn this on if you want i guess
ALSO_UNIQUIFY_NULL_NAMES = False


def uniquify_one_category(used_names: set, new_name: str) -> str:
	# translation occurred! attempt to uniquify the new name by appending *2 *3 etc
	while new_name in used_names:
		starpos = new_name.rfind("*")
		if starpos == -1:  # suffix does not exist
			new_name = new_name + "*1"
		else:  # suffix does exist
			try:
				suffixval = int(new_name[starpos + 1:])
			except ValueError:
				suffixval = 1
			new_name = new_name[:starpos] + "*" + str(suffixval + 1)
	# one leaving that loop, we finally have a unique name
	return new_name


helptext = '''====================
uniquify_names:
This function will uniquify all names of materials/bones/morphs/displayframes in the model. Bad things happen when names are not unique.
'''

iotext = '''Inputs:  PMX file "[model].pmx"\nOutputs: PMX file "[model]_unique.pmx"
'''


def showhelp():
	# print info to explain the purpose of this file
	core.MY_PRINT_FUNC(helptext)
def showprompt():
	# print info to explain what inputs/outputs it needs/creates
	core.MY_PRINT_FUNC(iotext)
	
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX model file:")
	input_filename_pmx = core.prompt_user_filename("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=True)
	return pmx, input_filename_pmx

def uniquify_names(pmx: pmxstruct.Pmx, moreinfo=False):
	
	# just uniquify the names
	# return counts of how many en/jp from each category were changed
	
	counts = [0] * 8
	counts_labels = ["material_JP","bone_JP","morph_JP","dispframe_JP","material_EN","bone_EN","morph_EN","dispframe_EN"]
	
	cat_id_list = list(range(4,8))
	category_list = [pmx.materials, pmx.bones, pmx.morphs, pmx.frames]
	for cat_id, category in zip(cat_id_list, category_list):
		used_en_names = set()
		used_jp_names = set()
		for i, item in enumerate(category):
			jp_name = item.name_jp
			en_name = item.name_en
			# first, uniquify the jp name
			if jp_name != "" or ALSO_UNIQUIFY_NULL_NAMES:
				new_jp_name = uniquify_one_category(used_jp_names, jp_name)
				used_jp_names.add(new_jp_name)
				if new_jp_name != jp_name:
					if moreinfo: core.MY_PRINT_FUNC("%s: #%d    %s --> %s" % (counts_labels[cat_id - 4], i, jp_name, new_jp_name))
					# count & store into the structure
					item.name_jp = new_jp_name
					counts[cat_id - 4] += 1
			# second, uniquify the en name
			if en_name != "" or ALSO_UNIQUIFY_NULL_NAMES:
				new_en_name = uniquify_one_category(used_en_names, en_name)
				used_en_names.add(new_en_name)
				if new_en_name != en_name:
					if moreinfo: core.MY_PRINT_FUNC("%s: #%d    %s --> %s" % (counts_labels[cat_id], i, en_name, new_en_name))
					# count & store into the structure
					item.name_en = new_en_name
					counts[cat_id] += 1
	
	counts_dict = {x:y for x,y in zip(counts_labels, counts) if y != 0}
	
	if not counts_dict:
		core.MY_PRINT_FUNC("No changes are required")
		return pmx, False
	
	# list how many of what were changed
	core.MY_PRINT_FUNC("The following numbers in each category/language were uniquified:")
	core.MY_PRINT_FUNC(counts_dict)
	
	return pmx, True
	
def end(pmx, input_filename_pmx):
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_unique")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=True)
	return None

def main():
	showhelp()
	pmx, name = showprompt()
	pmx, is_changed = uniquify_names(pmx)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
