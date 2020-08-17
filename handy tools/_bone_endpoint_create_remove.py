# Nuthouse01 - 07/24/2020 - v4.63
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# second, wrap custom imports with a try-except to catch it if files are missing
import sys
try:
	sys.path.append("../")
	from python import nuthouse01_core as core
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	core = None

# name = 1
# eng name = 2
# xyz = 5 6 7
# rot/move/ik/vis/en = 8 9 10 11 12
# parentname = 13
# link offset=0, bone=1: 14
# link bone: 15
# link offset: 16 17 18


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


def main():
	# print info to explain the purpose of this file
	print("This will create or remove hidden bone 'endpoints' for other bones to visually link to. It will swap offset to bonelink or bonelink to offset.")
	print("When swapping offset to bonelink, it creates new endpoint bones for the parent to point at.")
	print("When swapping bonelink to offset, the endpoint bones are not deleted; they still exist, they are simply not used for visual linking.")
	# print info to explain what inputs it needs
	print("Inputs: bone CSV 'whatever.csv', if going offset->bonelink then it contains only bones with offsets, if going bonelink->offset it contains the parent bones & the endpoint bones.")
	# print info to explain what outputs it creates
	print("Outputs: bone CSV 'whatever_endpoints.csv' to be loaded into PMXE")
	
	# ask for mode: create endpoint or remove endpoint
	print("Are you creating or removing endpoints? 1 = Create, 2 = Remove")
	r = core.prompt_user_choice((1, 2))
	
	# prompt bone CSV name
	print("Please enter name of bone CSV input file:")
	input_filename_bone = core.prompt_user_filename(".csv")
	rawlist_bone = core.read_file_to_csvlist(input_filename_bone, use_jis_encoding=True)
	
	# verify that these are the correct kind of CSVs
	if rawlist_bone[0] != core.pmxe_bone_csv_header:
		core.pause_and_quit("Err: '{}' is not a valid bone CSV".format(input_filename_bone))
	
	
	# name = 1
	# eng name = 2
	# xyz = 567
	# rot/move/ik/vis/en = 89101112, = 1/0/0/0/1
	# parentname = 13
	# link offset=0, bone=1: 14
	# link bone: 15
	# link offset: 161718
	
	# template for endpoint
	basicendpoint = ["Bone", "", "", 0, 0, 6.791944, 11.69057, 0.111029, 1, 0, 0, 0, 1, "", 0, "",
					 0, 0, 0, 0, 0, 0, 1, "", 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, "", 0, 57.29578]
	
	# count number modified
	num_endpoints_modified = 0
	
	if r == 1:
		# create endpoint:
		newendpoint_list = []
		for line in rawlist_bone:
			if line[0] != core.pmxe_bone_csv_tag:
				continue
			# inputs should all be set to "offset" mode, not already have endpoints
			if line[14] == 1:
				# jp name + eng name
				print("Warning, bone '{}/{}' is not using a offset link, skipping".format(line[1], line[2]))
				continue
				
			# verify offset is not 0,0,0
			if line[16] == 0 and line[17] == 0 and line[18] == 0:
				# jp name + eng name
				print("Warning, bone '{}/{}' has offset of 0/0/0, skipping".format(line[1], line[2]))
				continue
			
			num_endpoints_modified += 1
			# create new bone for endpoint
			# compared to template, overwrite: name, eng name, position, parent
			newendpoint = list(basicendpoint) # copy
			# use jp character for "end"
			newendpoint[1] = line[1] + "先"	# jp name
			newendpoint[2] = line[2] + " end"	# eng name
			newendpoint[5] = line[5] + line[16]	# xpos
			newendpoint[6] = line[6] + line[17]	# ypos
			newendpoint[7] = line[7] + line[18]	# zpos
			newendpoint[13] = line[1]			# parent
			# new bones get stored in a new list while im iterating over existing list
			newendpoint_list.append(newendpoint)
			# change existing bone to point at this new bone
			line[14] = 1
			# use jp character for "end"
			line[15] = line[1] + "先"
			
		# then they get combined & written out together
		rawlist_bone += newendpoint_list
		print("Added " + str(num_endpoints_modified) + " endpoints")

	else:
		# remove endpoint:
		for line in rawlist_bone:
			if line[0] != core.pmxe_bone_csv_tag:
				continue
			
			# # inputs will be the bones to be removed AND their current endpoints, must distinguish between them
			# # if a bone's parent is found within the input list, then it is an endpoint, skip it
			# if core.my_sublist_find(rawlist_bone, 1, line[13]) is not None:
			# 	continue

			# if it is set to "offset" mode instead of "link" then skip it
			if line[14] == 0:
				continue
			
			# if it is on "link" mode but not linking to anything, skip it
			if line[15] == "":
				continue
				
			# this bone is linked to some other bone. find the other bone it is pointing at
			target = core.my_sublist_find(rawlist_bone, 1, line[15])
			if target is None:
				# jp name + eng name
				print("Warning, bone '{}/{}' is linking to a bone that isn't included in the input file, skipping".format(line[1], line[2]))
				continue
			
			num_endpoints_modified += 1
			line[14] = 0	# change non-endpoint to be offset mode
			line[16] = target[5] - line[5]	# x offset
			line[17] = target[6] - line[6]	# y offset
			line[18] = target[7] - line[7]	# z offset
			# thats it!
		print("Removed " + str(num_endpoints_modified) + " endpoints")
	
	# write out
	output_filename_bone = input_filename_bone[0:-4] + "_endpoints.csv"
	output_filename_bone = core.get_unused_file_name(output_filename_bone)
	print("...writing result to file '" + output_filename_bone + "'...")
	core.write_csvlist_to_file(output_filename_bone, rawlist_bone, use_jis_encoding=True)
	
	core.pause_and_quit("Done with everything! Goodbye!")
	return None


if __name__ == '__main__':
	print("Nuthouse01 - 07/24/2020 - v4.63")
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
			print(ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
