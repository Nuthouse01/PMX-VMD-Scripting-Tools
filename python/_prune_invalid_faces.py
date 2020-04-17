# Nuthouse01 - 04/17/2020 - v4.04
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


helptext = '''====================
prune_invalid_faces:
This script will delete any invalid faces in the model, a simple operation.
An invalid face is any face whose 3 defining vertices are not unique with respect to eachother.
'''

iotext = '''Inputs:  PMX file "[model].pmx"\nOutputs: PMX file "[model]_faceprune.pmx"
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

def prune_invalid_faces(pmx, moreinfo=False):
	#############################
	# ready for logic
	
	faces_to_remove = []
	# identify faces which need removing
	for i,face in enumerate(pmx[2]):
		# valid faces are defined by 3 unique vertices, if the vertices are not unique then the face is invalid
		if len(face) != len(set(face)):
			faces_to_remove.append(i)
	
	numdeleted = len(faces_to_remove)
	prevtotal = len(pmx[2])
	if numdeleted == 0:
		core.MY_PRINT_FUNC("No changes are required")
		return pmx, False

	# each material has some number of faces associated with it, those values must be changed when faces are deleted!
	# the question simply becomes, "how many faces within range [start, end] are being deleted"
	# the list of faces being deleted is in known-sorted order
	faces_removed_per_material = []
	end_del_face_idx = 0
	start_del_face_idx = 0
	face_id_end = 0
	for mat in pmx[4]:
		face_id_end += mat[25]  # this tracks the id of the final face in this material
		# walk thru the list of faces to remove until i find one that isn't part of the current material,
		# or until i reach the end of the list
		while end_del_face_idx < len(faces_to_remove) and faces_to_remove[end_del_face_idx] < face_id_end:
			end_del_face_idx += 1
		# within the list of faces to be deleted,
		# start_del_face_idx is the idx of the first face that falls within this material's scope,
		# and end_del_face_idx is the idx of the first face that falls within THE NEXT material's scope
		# therefore their difference is the number of faces to remove from the current material
		faces_removed_per_material.append(end_del_face_idx - start_del_face_idx)
		start_del_face_idx = end_del_face_idx
		
	# now, apply the changes to the size of each material
	newsum = 0
	for mat, loss in zip(pmx[4], faces_removed_per_material):
		mat[25] -= loss
		newsum += mat[25]
		
	# now, delete the acutal faces
	faces_to_remove.reverse()
	for f in faces_to_remove:
		pmx[2].pop(f)
	
	assert(len(pmx[2]) == newsum)  # assert material face allocation matches the actual total number of faces
	
	core.MY_PRINT_FUNC("Identified and deleted {} / {} = {:.1%} faces for being invalid".format(
		numdeleted, prevtotal, numdeleted/prevtotal))
	
	return pmx, True

def end(pmx, input_filename_pmx):
	# write out
	# output_filename_pmx = "%s_faceprune.pmx" % core.get_clean_basename(input_filename_pmx)
	output_filename_pmx = input_filename_pmx[0:-4] + "_faceprune.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=True)
	return None
	
def main():
	showhelp()
	pmx, name = showprompt()
	pmx, is_changed = prune_invalid_faces(pmx)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")


if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 04/17/2020 - v4.04")
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

