import copy
import math

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_io as io

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.5.03 - 10/10/2020"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################



# third, constants



# fourth, functions



# fifth, main()

def main():
	# print info to explain the purpose of this file
	print("This tool will rotate the given geometry such that the two 'prime vertices' specified have equal values along the desired axis")
	print("Choose from 6 modes to pick axis of alignment and axis of rotation")
	print("Also choose whether to force their position to 0 or their average")
	# print info to explain what inputs it needs
	print("Inputs: vertex CSV 'whatever.csv' containing all the geometry that will be rotated")
	# print info to explain what outputs it creates
	print("Outputs: vertex CSV 'whatever_aligned.csv' where all the input geometry has been rotated")
	print("")
	
	######################## mode selection #######################
	print("Choose an axis to align the points on, and an axis to rotate around:")
	print(" 1 = X-align, Y-rotate: create left-right symmetry by rotating left/right")	# DONE
	print(" 2 = X-align, Z-rotate: create left-right symmetry by tilting left/right") # DONE
	print(" 3 = Y-align, X-rotate: create front-back level by tilting front/back") # DONE
	print(" 4 = Y-align, Z-rotate: create left-right level by tilting left/right") # DONE
	print(" 5 = Z-align, X-rotate: create vertical by tilting front/back") # DONE
	print(" 6 = Z-align, Y-rotate: create left-right symmetry by rotating left/right") # DONE
	
	mode = core.prompt_user_choice((1,2,3,4,5,6))
	if mode == 1:
		# DEFAULT CASE
		axis = "X"
		Xidx = 2
		Zidx = 4
	elif mode == 2:
		axis = "X"
		Xidx = 2
		Zidx = 3
	elif mode == 3:
		axis = "Y"
		Xidx = 3
		Zidx = 4
	elif mode == 4:
		axis = "Y"
		Xidx = 3
		Zidx = 2
	elif mode == 5:
		axis = "Z"
		Xidx = 4
		Zidx = 3
	elif mode == 6:
		axis = "Z"
		Xidx = 4
		Zidx = 2
	else:
		axis = "wtf"
		Xidx = 9999
		Zidx = 9999
		print("congrats you somehow broke it")

	# choose whether to align to axis=0 or align to axis=avg
	print("After rotate, shift prime points to "+axis+"=0 or leave at "+axis+"=avg?")
	print(" 1 = "+axis+"=0")
	print(" 2 = "+axis+"=avg")
	useavg = core.prompt_user_choice((1,2))
	useavg = bool(useavg-1)
	
	# promt vertex CSV name
	# input: vertex CSV file with all the vertexes that I want to modify
	print("Please enter name of vertex CSV input file:")
	input_filename_vertex = core.prompt_user_filename("CSV file", ".csv")
	rawlist_vertex = io.read_file_to_csvlist(input_filename_vertex, use_jis_encoding=True)
	
	# verify that these are the correct kind of CSVs
	if rawlist_vertex[0] != core.pmxe_vertex_csv_header:
		core.pause_and_quit("Err: '{}' is not a valid vertex CSV".format(input_filename_vertex))
	
	# i plan to re-write this out as a csv file, so let's maintain as much of the input formatting as possible
	header = rawlist_vertex.pop(0)
	
	##########################################################
	# prompt for the two prime points:
	# text input 2 point IDs, to indicate the two points to align to x=0
	prime_vertex_one = input("Prime vertex ID #1: ")
	prime_points = []
	v1 = core.my_list_search(rawlist_vertex, lambda x: x[1] == int(prime_vertex_one), getitem=True)
	if v1 is None:
		core.pause_and_quit("Err: unable to find '" + prime_vertex_one + "' in vertex CSV, unable to operate")
	prime_points.append(copy.copy(v1))
	
	prime_vertex_two = input("Prime vertex ID #2: ")
	v2 = core.my_list_search(rawlist_vertex, lambda x: x[1] == int(prime_vertex_two), getitem=True)
	if v2 is None:
		core.pause_and_quit("Err: unable to find '" + prime_vertex_two + "' in vertex CSV, unable to operate")
	prime_points.append(copy.copy(v2))
	
	
	# CALCULATE THE AVERAGE
	# position of the two prime points... rotate around this point
	avgx = (prime_points[0][2] + prime_points[1][2]) / 2.0
	avgy = (prime_points[0][3] + prime_points[1][3]) / 2.0
	avgz = (prime_points[0][4] + prime_points[1][4]) / 2.0
	avg = [avgx, avgy, avgz]

	
	# note: rotating around Y-axis, so Y never ever comes into it. Z is my effective Y.
	# CALCULATE THE ANGLE:
	# first shift both prime points so that prime0 is on 0/0/0
	prime_points[1][2] -= prime_points[0][2]
	prime_points[1][3] -= prime_points[0][3]
	prime_points[1][4] -= prime_points[0][4]
	prime_points[0][2:5] = [0.0, 0.0, 0.0]
	# then calculate the angle between the two prime points
	# ensure deltaZ is positive: calculate the angle to whichever point has the greater z
	if prime_points[0][Zidx] < prime_points[1][Zidx]:
		vpx = prime_points[1][Xidx]
		vpz = prime_points[1][Zidx]
	else:
		vpx = -prime_points[1][Xidx]
		vpz = -prime_points[1][Zidx]
	# then use atan to calculate angle in radians
	angle = math.atan2(vpx, vpz)
	print("Angle = " + str(math.degrees(angle)))

	# APPLY THE ROTATION
	# horizontally rotate all points around the average point
	origin = (avg[Xidx-2], avg[Zidx-2])
	origin_nrm = (0.0, 0.0)
	for i,v in enumerate(rawlist_vertex):
		point = (v[Xidx], v[Zidx])
		newpoint = core.rotate2d(origin, angle, point)
		v[Xidx], v[Zidx] = newpoint
		# also rotate each normal!
		point_nrm = (v[Xidx+3], v[Zidx+3])
		newnrm = core.rotate2d(origin_nrm, angle, point_nrm)
		v[Xidx+3], v[Zidx+3] = newnrm
		# progress printout
		core.print_progress_oneline(i / len(rawlist_vertex))
	print("done rotating              ")
	# FORCE TO ZERO
	if not useavg:
		# first shift all geometry so that one of the prime points is on the x=0
		# choose to shift by prime0
		shift = avg[Xidx-2]
		for v in rawlist_vertex:
			v[Xidx] -= shift
			# # anything extremely close to 0 becomes set to exactly 0
			if -0.000000001 < v[Xidx] < 0.000000001:
				v[Xidx] = 0.0
		print("done shifting to zero              ")

	# write out
	# re-add the header line
	rawlist_vertex = [header] + rawlist_vertex
	# build the output file name and ensure it is free
	output_filename = input_filename_vertex[:-4] + "_aligned.csv"
	output_filename = core.filepath_get_unused_name(output_filename)
	print("Writing aligned result to '" + output_filename + "'...")
	# export modified CSV
	io.write_csvlist_to_file(output_filename, rawlist_vertex, use_jis_encoding=True)
	
	core.pause_and_quit("Done with everything! Goodbye!")
	
	return None



if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.RUN_WITH_TRACEBACK(main)
