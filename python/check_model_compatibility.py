_SCRIPT_VERSION = "Script version:  Nuthouse01 - 10/10/2020 - v5.03"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	# these imports work if running from GUI
	from . import nuthouse01_core as core
	from . import nuthouse01_vmd_parser as vmdlib
	from . import nuthouse01_vpd_parser as vpdlib
	from . import nuthouse01_pmx_parser as pmxlib
except ImportError as eee:
	try:
		# these imports work if running from double-click on THIS script
		import nuthouse01_core as core
		import nuthouse01_vmd_parser as vmdlib
		import nuthouse01_vpd_parser as vpdlib
		import nuthouse01_pmx_parser as pmxlib
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = vmdlib = vpdlib = pmxlib = None


########################################################################################################################
# constants & options
########################################################################################################################


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


# if true, print items that match as well as items that miss
# if false, print only items that miss
PRINT_MATCHING_ITEMS = False


helptext = '''=================================================
check_model_compatability:
This tool will check for compabability between a given model (PMX) and a given dance motion (VMD) or pose (VPD).
This means checking whether the model supports all the bones and/or morphs the VMD/VPD is trying to use.
All bone/morph names are compared using the JP names.

This requires both a PMX model and a VMD motion to run.
'''


def main(moreinfo=True):
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	# prompt VMD file name
	core.MY_PRINT_FUNC("")
	core.MY_PRINT_FUNC("Please enter name of VMD motion or VPD pose file to check compatability with:")
	input_filename = core.MY_FILEPROMPT_FUNC(".vmd .vpd")
	if not input_filename.lower().endswith(".vpd"):
		# the actual VMD part isn't even used, only bonedict and morphdict
		vmd = vmdlib.read_vmd(input_filename, moreinfo=moreinfo)
	else:
		vmd = vpdlib.read_vpd(input_filename, moreinfo=moreinfo)
	bonedict = vmdlib.parse_vmd_used_dict(vmd.boneframes, frametype="bone", moreinfo=moreinfo)
	morphdict = vmdlib.parse_vmd_used_dict(vmd.morphframes, frametype="morph", moreinfo=moreinfo)
	
	core.MY_PRINT_FUNC("")
	
	# must use same encoding as I used when the VMD was unpacked, since the hex bytes only have meaning in that encoding
	core.set_encoding("shift_jis")
	
	##############################################
	# check morph compatability
	
	# build list of morphs used in the dance VMD
	morphs_in_vmd = list(morphdict.keys())
	
	# build list of ALL morphs in the PMX
	morphs_in_model = [pmxmorph.name_jp for pmxmorph in pmx.morphs]
	
	# ensure that the VMD contains at least some morphs, to prevent zero-divide error
	if len(morphs_in_vmd) == 0:
		core.MY_PRINT_FUNC("MORPH SKIP: VMD '%s' does not contain any morphs that are used in a meaningful way." % core.get_clean_basename(input_filename))
	elif len(morphs_in_model) == 0:
		core.MY_PRINT_FUNC("MORPH SKIP: PMX '%s' does not contain any morphs." % core.get_clean_basename(input_filename_pmx))
	else:
		
		# convert pmx-morph names to bytes
		# these can plausibly fail shift_jis encoding because they came from the UTF-8 pmx file
		morphs_in_model_b = []
		for a in morphs_in_model:
			try:
				b = core.encode_string_with_escape(a)
			except UnicodeEncodeError as e:
				newerrstr = "%s: '%s' codec cannot encode char '%s' within string '%s'" % (
					e.__class__.__name__, e.encoding, e.reason[e.start:e.end], e.reason)
				core.MY_PRINT_FUNC(newerrstr)
				b = bytearray()
			morphs_in_model_b.append(b)
		
		# convert vmd-morph names to bytes
		# these might be truncated but cannot fail because they were already decoded from the shift_jis vmd file
		morphs_in_vmd_b = [core.encode_string_with_escape(a) for a in morphs_in_vmd]
		
		matching_morphs = {}
		missing_morphs = {}
		# iterate over list of morphs
		for vmdmorph, vmdmorph_b in zip(morphs_in_vmd, morphs_in_vmd_b):
			# question: does "vmdmorph" match something in "morphs_in_model"?
			# BUT, doing comparison in bytes-space to handle escape characters: vmdmorph_b vs morphs_in_model_b
			# NOTE: MMD does not try to use "begins-with" matching like I had hoped/assumed, it only looks for exact matches
			# return list of ALL matches, this way i can raise an error if there are multiple matches
			# exact match
			modelmorphmatch_b = [a for a in morphs_in_model_b if a == vmdmorph_b]
			
			# copy the key,val in one of the dicts depending on results of matching attempt
			if len(modelmorphmatch_b) == 0:
				# MISS! key is the VMD morph name since that's the best clue Ive got
				missing_morphs[vmdmorph] = morphdict[vmdmorph]
			elif len(modelmorphmatch_b) == 1:
				# MATCH! key is the PMX morph name it matched against, since it might be a longer version wtihout escape char
				matching_morphs[core.decode_bytes_with_escape(modelmorphmatch_b[0])] = morphdict[vmdmorph]
			else:
				# more than 1 morph was a match!?
				core.MY_PRINT_FUNC("Warning: VMDmorph '%s' matched multiple PMXmorphs, its behavior is uncertain." % vmdmorph)
				modelmorphmatch = [core.decode_bytes_with_escape(a) for a in modelmorphmatch_b]
				# core.MY_PRINT_FUNC(modelmorphmatch)
				matching_morphs[modelmorphmatch[0]] = morphdict[vmdmorph]
		
		# display results!
		r = "PASS" if len(matching_morphs) == len(morphs_in_vmd) else "FAIL"
		core.MY_PRINT_FUNC("MORPH {}: {} / {} = {:.1%} of the morphs are supported".format(
			r, len(matching_morphs), len(morphs_in_vmd), len(matching_morphs) / len(morphs_in_vmd)))
			
		# if there are no missing morphs (all match), don't print anything at all
		if missing_morphs:
			if not moreinfo:
				core.MY_PRINT_FUNC("For detailed list, please re-run with 'more info' enabled")
			else:
				# convert the dicts to lists and sort for printing
				# sort in-place descending by 2nd element as primary
				missing_morphs_list = sorted(list(missing_morphs.items()), key=core.get2nd, reverse=True)
				# justify the names!
				missing_just = core.MY_JUSTIFY_STRINGLIST(["'" + m[0] + "'" for m in missing_morphs_list])
				# re-attach the justified names to the usage numbers
				missing_morphs_list = list(zip(missing_just, [m[1] for m in missing_morphs_list]))
				
				core.MY_PRINT_FUNC("")
				core.MY_PRINT_FUNC("Unsupported morphs: name + times used")
				for m, num in missing_morphs_list:
					core.MY_PRINT_FUNC("  %s  ||  %d" % (m, int(num)))
				
				# only print the matching morphs if there are some, and if enabled by options
				if matching_morphs and PRINT_MATCHING_ITEMS:
					matching_morphs_list = list(matching_morphs.items())
					matching_morphs_list.sort(key=core.get2nd, reverse=True)  # sort in-place descending by 2nd element as primary
					matching_just = core.MY_JUSTIFY_STRINGLIST(["'" + m[0] + "'" for m in matching_morphs_list])
					matching_morphs_list = list(zip(matching_just, [m[1] for m in matching_morphs_list]))
					core.MY_PRINT_FUNC("")
					core.MY_PRINT_FUNC("Supported morphs: name + times used")
					for m, num in matching_morphs_list:
						core.MY_PRINT_FUNC("  %s  ||  %d" % (m, int(num)))
			
	##############################################
	# check bone compatability
	core.MY_PRINT_FUNC("")
	
	# build list of bones used in the dance VMD
	bones_in_vmd = list(bonedict.keys())
	
	# build list of ALL bones in the PMX
	# first item of pmxbone is the jp name
	bones_in_model = [pmxbone.name_jp for pmxbone in pmx.bones]
	
	# ensure that the VMD contains at least some bones, to prevent zero-divide error
	if len(bones_in_vmd) == 0:
		core.MY_PRINT_FUNC("BONE SKIP: VMD '%s' does not contain any bones that are used in a meaningful way." % core.get_clean_basename(input_filename))
	elif len(bones_in_model) == 0:
		core.MY_PRINT_FUNC("BONE SKIP: PMX '%s' does not contain any bones." % core.get_clean_basename(input_filename_pmx))
	else:
		
		# convert pmx-bone names to bytes
		# these can plausibly fail shift_jis encoding because they came from the UTF-8 pmx file
		bones_in_model_b = []
		for a in bones_in_model:
			try:
				b = core.encode_string_with_escape(a)
			except UnicodeEncodeError as e:
				newerrstr = "%s: '%s' codec cannot encode char '%s' within string '%s'" % (
					e.__class__.__name__, e.encoding, e.reason[e.start:e.end], e.reason)
				core.MY_PRINT_FUNC(newerrstr)
				b = bytearray()
			bones_in_model_b.append(b)
		
		# convert vmd-bone names to bytes
		# these might be truncated but cannot fail because they were already decoded from the shift_jis vmd file
		bones_in_vmd_b = [core.encode_string_with_escape(a) for a in bones_in_vmd]
		
		matching_bones = {}
		missing_bones = {}
		# iterate over list of bones that pass the size check
		for vmdbone, vmdbone_b in zip(bones_in_vmd, bones_in_vmd_b):
			# question: does "vmdbone" match something in "bones_in_model"?
			# BUT, doing comparison in bytes-space to handle escape characters: vmdbone_b vs bones_in_model_b
			# NOTE: MMD does not try to use "begins-with" matching like I had hoped/assumed, it only looks for exact matches
			# return list of ALL matches, this way i can raise an error if there are multiple matches
			# exact match
			modelbonematch_b = [a for a in bones_in_model_b if a == vmdbone_b]
			
			# copy the key,val in one of the dicts depending on results of matching attempt
			if len(modelbonematch_b) == 0:
				# MISS! key is the VMD bone name since that's the best clue Ive got
				missing_bones[vmdbone] = bonedict[vmdbone]
			elif len(modelbonematch_b) == 1:
				# MATCH! key is the PMX bone name it matched against, since it might be a longer version wtihout escape char
				matching_bones[core.decode_bytes_with_escape(modelbonematch_b[0])] = bonedict[vmdbone]
			else:
				# more than 1 bone was a match!?
				core.MY_PRINT_FUNC("Warning: VMDbone '%s' matched multiple PMXbones, its behavior is uncertain." % vmdbone)
				modelbonematch = [core.decode_bytes_with_escape(a) for a in modelbonematch_b]
				# core.MY_PRINT_FUNC(modelbonematch)
				matching_bones[modelbonematch[0]] = bonedict[vmdbone]
		
		# display results!
		r = "PASS" if len(matching_bones) == len(bones_in_vmd) else "FAIL"
		core.MY_PRINT_FUNC("BONE {}: {} / {} = {:.1%} of the bones are supported".format(
			r, len(matching_bones), len(bones_in_vmd), len(matching_bones) / len(bones_in_vmd)))

		# if there are no missing bones (all match), don't print anything at all
		if missing_bones:
			if not moreinfo:
				core.MY_PRINT_FUNC("For detailed list, please re-run with 'more info' enabled")
			else:
				# convert the dicts to lists and sort for printing
				# sort in-place descending by 2nd element as primary
				missing_bones_list = sorted(list(missing_bones.items()), key=core.get2nd, reverse=True)
				# justify the names!
				missing_just = core.MY_JUSTIFY_STRINGLIST(["'" + m[0] + "'" for m in missing_bones_list])
				# re-attach the justified names to the usage numbers
				missing_bones_list = list(zip(missing_just, [m[1] for m in missing_bones_list]))
				
				core.MY_PRINT_FUNC("")
				core.MY_PRINT_FUNC("Unsupported bones: name + times used")
				for m, num in missing_bones_list:
					core.MY_PRINT_FUNC("  %s  ||  %d" % (m, int(num)))
				
				# only print the matching bones if there are some, and if enabled by options
				if matching_bones and PRINT_MATCHING_ITEMS:
					matching_bones_list = list(matching_bones.items())
					matching_bones_list.sort(key=core.get2nd, reverse=True)  # sort in-place descending by 2nd element as primary
					matching_just = core.MY_JUSTIFY_STRINGLIST(["'" + m[0] + "'" for m in matching_bones_list])
					matching_bones_list = list(zip(matching_just, [m[1] for m in matching_bones_list]))
					core.MY_PRINT_FUNC("")
					core.MY_PRINT_FUNC("Supported bones: name + times used")
					for m, num in matching_bones_list:
						core.MY_PRINT_FUNC("  %s  ||  %d" % (m, int(num)))
		
		# NEW: among matching bones, check whether any bones have unsupported translation/rotation
		for bonestr in sorted(list(matching_bones.keys())):
			# get the bone to get whether rot/trans enabled
			bone = core.my_list_search(pmx.bones, lambda x: x.name_jp == bonestr, getitem=True)
			# get all the frames from the VMD that are relevant to this bone
			thisboneframes = [f for f in vmd.boneframes if f.name == bonestr]
			# does the VMD use rotation? probably, check anyway
			vmd_use_rot = any(f.rot != [0,0,0] for f in thisboneframes)
			if vmd_use_rot and not (bone.has_rotate and bone.has_enabled):
				# raise some sort of warning
				w = "Warning: supported bone '%s' uses rotation in VMD, but rotation not allowed by PMX" % bonestr
				core.MY_PRINT_FUNC(w)
			# does the VMD use translation?
			vmd_use_trans = any(f.pos != [0,0,0] for f in thisboneframes)
			if vmd_use_trans and not (bone.has_translate and bone.has_enabled):
				# raise some sort of warning
				w = "Warning: supported bone '%s' uses move/shift in VMD, but move/shift not allowed by PMX" % bonestr
				core.MY_PRINT_FUNC(w)
		
	core.MY_PRINT_FUNC("")
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	print(_SCRIPT_VERSION)
	if DEBUG:
		# print info to explain the purpose of this file
		core.MY_PRINT_FUNC(helptext)
		core.MY_PRINT_FUNC("")
		
		main()
		core.pause_and_quit("Done with everything! Goodbye!")
	else:
		try:
			# print info to explain the purpose of this file
			core.MY_PRINT_FUNC(helptext)
			core.MY_PRINT_FUNC("")
			
			main()
			core.pause_and_quit("Done with everything! Goodbye!")
		except (KeyboardInterrupt, SystemExit):
			# this is normal and expected, do nothing and die normally
			pass
		except Exception as ee:
			# if an unexpected error occurs, catch it and print it and call pause_and_quit so the window stays open for a bit
			core.MY_PRINT_FUNC(ee.__class__.__name__, ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
