import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_io as io

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.5.02 - 09/21/2020"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################



# third, constants



# fourth, functions



# fifth, main()

def main():
	print("")
	print("Move each vertex in set A to match the position of the closest vertex in set B")
	print("")
	
	######################## mode selection #######################
	
	# promt vertex CSV name
	# input: vertex CSV file with all the vertexes that I want to modify
	print("Please enter name of vertex CSV input file with the vertices to be moved:")
	input_filename_vertex_source = core.prompt_user_filename("CSV file", ".csv")
	rawlist_vertex_source = io.read_file_to_csvlist(input_filename_vertex_source, use_jis_encoding=True)
	
	# verify that these are the correct kind of CSVs
	if rawlist_vertex_source[0] != core.pmxe_vertex_csv_header:
		core.pause_and_quit("Err: '{}' is not a valid vertex CSV".format(input_filename_vertex_source))
	
	# promt vertex CSV name
	# input: vertex CSV file with all the vertexes that I want to modify
	print("Please enter name of vertex CSV input file with the destination geometry:")
	input_filename_vertex_dest = core.prompt_user_filename("CSV file", ".csv")
	rawlist_vertex_dest = io.read_file_to_csvlist(input_filename_vertex_dest, use_jis_encoding=True)
	
	# verify that these are the correct kind of CSVs
	if rawlist_vertex_dest[0] != core.pmxe_vertex_csv_header:
		core.pause_and_quit("Err: '{}' is not a valid vertex CSV".format(input_filename_vertex_dest))
	
	##########################################################
	
	# for each vertex in vertex_source, find the closest vertex in vertex_dest and move the source vertex to that dest position
	
	for v in rawlist_vertex_source:
		if v[0] != core.pmxe_vertex_csv_tag:
			continue
		# calculate the dist from this v to all d, and store the minimum
		min_coord = [0,0,0]
		min_val = 100
		for d in rawlist_vertex_dest:
			if d[0] != core.pmxe_vertex_csv_tag:
				continue
			dist = (v[2]-d[2])**2 + (v[3]-d[3])**2 + (v[4]-d[4])**2
			if dist < min_val:
				min_val = dist
				min_coord = d[2:5]
		# found the minimum
		# now apply it to v
		v[2:5] = min_coord
		
	# write out
	# build the output file name and ensure it is free
	output_filename = core.filepath_insert_suffix(input_filename_vertex_source, "_aligned")
	output_filename = core.filepath_get_unused_name(output_filename)
	print("Writing aligned result to '" + output_filename + "'...")
	# export modified CSV
	io.write_csvlist_to_file(output_filename, rawlist_vertex_source, use_jis_encoding=True)
	
	core.pause_and_quit("Done with everything! Goodbye!")
	
	return None



if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.RUN_WITH_TRACEBACK(main)
