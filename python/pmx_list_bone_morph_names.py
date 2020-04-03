# Nuthouse01 - 04/02/2020 - v3.60
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	import nuthouse01_core as core
	import nuthouse01_pmx_parser as pmx_parser
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	core = pmx_parser = None




# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


def main():
	# print info to explain the purpose of this file
	core.MY_PRINT_FUNC("This script will print the JP and EN names of all bones and morphs in a PMX model.")
	# print info to explain what inputs it needs
	core.MY_PRINT_FUNC("Inputs: model PMX 'modelname.pmx'")
	# print info to explain what outputs it creates
	core.MY_PRINT_FUNC("Outputs: morph name list text file '[modelname]_morph_names.txt'")
	core.MY_PRINT_FUNC("         bone name list text file '[modelname]_bone_names.txt'")
	core.MY_PRINT_FUNC("")
	
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.prompt_user_filename(".pmx")
	pmx = pmx_parser.read_pmx(input_filename_pmx)
	realbones = pmx[5]		# get bones
	realmorphs = pmx[6]		# get morphs
	modelname_jp = pmx[0][1]
	modelname_en = pmx[0][2]
	
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
	bonelist_pairs = [a[0:2] for a in realbones]
	morphlist_pairs = [a[0:2] for a in realmorphs]
	bonelist_out += bonelist_pairs
	morphlist_out += morphlist_pairs
	
	
	# write out
	output_filename_bone = "%s_bone_names.txt" % core.get_clean_basename(input_filename_pmx)
	output_filename_bone = output_filename_bone.replace(" ", "_")
	output_filename_bone = core.get_unused_file_name(output_filename_bone)
	core.MY_PRINT_FUNC("...writing result to file '" + output_filename_bone + "'...")
	core.write_rawlist_to_txt(output_filename_bone, bonelist_out, use_jis_encoding=False)
	core.MY_PRINT_FUNC("done!")

	output_filename_morph = "%s_morph_names.txt" % core.get_clean_basename(input_filename_pmx)
	output_filename_morph = output_filename_morph.replace(" ", "_")
	output_filename_morph = core.get_unused_file_name(output_filename_morph)
	core.MY_PRINT_FUNC("...writing result to file '" + output_filename_morph + "'...")
	core.write_rawlist_to_txt(output_filename_morph, morphlist_out, use_jis_encoding=False)
	core.MY_PRINT_FUNC("done!")
	core.pause_and_quit("Done with everything! Goodbye!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 04/02/2020 - v3.60")
	if DEBUG:
		main()
	else:
		try:
			main()
		except (KeyboardInterrupt, SystemExit):
			# this is normal and expected, do nothing and die normally
			pass
		except Exception as ee:
			# if an unexpected error occurs, catch it and print it and call pause_and_quit so the window stays open for a bit
			core.MY_PRINT_FUNC(ee.__class__.__name__, ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
