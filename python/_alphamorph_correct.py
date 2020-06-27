# Nuthouse01 - 06/27/2020 - v4.50
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
except ImportError as eee:
	try:
		import nuthouse01_core as core
		import nuthouse01_pmx_parser as pmxlib
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = pmxlib = None


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


# just take a wild guess what this field controls
PRINT_AFFECTED_MORPHS = False

# TODO: reconsider whether zeroing out tex/toon/alpha is really necessary/helpful/correct... YYB doesn't do it
# opacity, edge size, edge alpha, tex, toon, sph
template =          [0, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0]
# the above template multiplies everything by 0, below the same result by subtracting 1 from everthing
template_minusone = [1, 0, 0, 0, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, -1, 0, 0, 0, -1, 0, 0, 0, -1, 0, 0, 0, -1]

helptext = '''====================
alphamorph_correct:
This function fixes improper "material hide" morphs in a model.
Many models simply set the opacity to 0, but forget to zero out the edging effects or other needed fields.
This also changes all alphamorphs to use the "multiply by 0" approach when the target material is opaque(visible) by default, and use the "add -1" approach when the target is transparent(hidden) by default.
'''

iotext = '''Inputs:  PMX file "[model].pmx"\nOutputs: PMX file "[model]_alphamorph.pmx"
'''

def showhelp():
	# print info to explain the purpose of this file
	core.MY_PRINT_FUNC(helptext)
def showprompt():
	# print info to explain what inputs/outputs it needs/creates
	core.MY_PRINT_FUNC(iotext)
	
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX model file:")
	input_filename_pmx = core.prompt_user_filename(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=True)
	return pmx, input_filename_pmx

def alphamorph_correct(pmx, moreinfo=False):
	num_fixed = 0
	total_morphs_affected = 0
	
	# for each morph:
	for d,morph in enumerate(pmx[6]):
		# if not a material morph, skip it
		if morph[3] != 8:
			continue
		this_num_fixed = 0
		# for each material in this material morph:
		for mat in morph[4]:
			# (mat_idx, is_add, diffR, diffG, diffB, diffA, specR, specG, specB, specpower, ambR, ambG, ambB, edgeR,
			# edgeG, edgeB, edgeA, edgesize, texR, texG, texB, texA, sphR, sphG, sphB, sphA, toonR, toonG, toonB, toonA)
			# is_add=1, diffA(opacity)=5, edgeA=16, edgesize=17, texA=21, sphA=25, toonA=29
			
			# if (mult opacity by 0) OR (add -1 to opacity), then this item is (trying to) hide the target material
			if (mat[1]==0 and mat[5]==0) or (mat[1]==1 and mat[5]==-1):
				# then replace the entire set of material-morph parameters
				# opacity, edge size, edge alpha, tex, toon, sph
				# if the target material is initially transparent, replace with add-negative-1
				if mat[0] != -1 and pmx[4][mat[0]][5] == 0:
					if mat[1:] != template_minusone:  # if it is not already good,
						mat[1:] = template_minusone  # rewrite the morph
						this_num_fixed += 1
				# if the target material is initally opaque, or targeting the whole model, replace with mult-by-0
				else:
					if mat[1:] != template:  # if it is not already good,
						mat[1:] = template  # rewrite the morph
						this_num_fixed += 1
		if this_num_fixed != 0:
			total_morphs_affected += 1
			num_fixed += this_num_fixed
			if moreinfo:
				core.MY_PRINT_FUNC("morph #{:<3} JP='{}' / EN='{}', fixed {} items".format(d, morph[0], morph[1], this_num_fixed))
	
	if num_fixed:
		core.MY_PRINT_FUNC("Fixed %d 'hide' morphs" % total_morphs_affected)


	# identify materials that start transparent but still have edging
	mats_fixed = 0
	for d,mat in enumerate(pmx[4]):
		# if opacity is zero AND edge is enabled AND edge has nonzero opacity AND edge has nonzero size
		if mat[5] == 0 and mat[13][4] and mat[17] != 0 and mat[18] != 0:
			edgeA = mat[17]
			edgeSize = mat[18]
			this_num_edgefixed = 0
			# THEN check for any material morphs that add opacity to this material
			for d2,morph in enumerate(pmx[6]):
				# if not a material morph, skip it
				if morph[3] != 8:
					continue
				# for each material in this material morph:
				for item in morph[4]:
					# if it is operating on the right material, and adding, and opacity > 0:
					if item[0] == d and item[1] == 1 and item[5] > 0:
						# set it to add the edge amounts from the material
						item[16] = edgeA
						item[17] = edgeSize
						this_num_edgefixed += 1
			# done looping over morphs
			# if it modified any locations, zero out the edge params in the material
			if this_num_edgefixed != 0:
				mat[17] = 0
				mat[18] = 0
				num_fixed += this_num_edgefixed
				mats_fixed += 1
				if moreinfo:
					core.MY_PRINT_FUNC("mat #{:<3} JP='{}' / EN='{}', fixed {} appear morphs".format(d, mat[0], mat[1], this_num_edgefixed))
	
	if mats_fixed:
		core.MY_PRINT_FUNC("Removed edging from %d initially hidden materials" % mats_fixed)
	
	if num_fixed == 0 and mats_fixed == 0:
		core.MY_PRINT_FUNC("No changes are required")
		return pmx, False
	
	return pmx, True

def end(pmx, input_filename_pmx):
	# write out
	# output_filename_pmx = "%s_alphamorph.pmx" % core.get_clean_basename(input_filename_pmx)
	output_filename_pmx = input_filename_pmx[0:-4] + "_alphamorph.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=True)
	return None

def main():
	showhelp()
	pmx, name = showprompt()
	pmx, is_changed = alphamorph_correct(pmx, PRINT_AFFECTED_MORPHS)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")

if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 06/27/2020 - v4.50")
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
			core.MY_PRINT_FUNC(ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
