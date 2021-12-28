import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_io as io

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.05 - 12/27/2021"


# read two vertex CSVs
# match up their vertexes by nearest-matching
# copy UV data then write out
def main():
	print("Read two vertex CSVs")
	print("Copy the UV data in the 'source' onto the vertices at the corresponding locations in 'destination'")
	
	# promt vertex CSV name
	print("Please enter name of SOURCE vertex CSV:")
	input_filename_vertex_source = core.prompt_user_filename("CSV file", ".csv")
	rawlist_vertex_source = io.read_file_to_csvlist(input_filename_vertex_source, use_jis_encoding=True)
	
	# verify that these are the correct kind of CSVs
	if rawlist_vertex_source[0] != core.pmxe_vertex_csv_header:
		core.pause_and_quit("Err: '{}' is not a valid vertex CSV".format(input_filename_vertex_source))
	
	# promt vertex CSV name
	print("Please enter name of DEST vertex CSV:")
	input_filename_vertex_dest = core.prompt_user_filename("CSV file", ".csv")
	rawlist_vertex_dest = io.read_file_to_csvlist(input_filename_vertex_dest, use_jis_encoding=True)
	
	# verify that these are the correct kind of CSVs
	if rawlist_vertex_dest[0] != core.pmxe_vertex_csv_header:
		core.pause_and_quit("Err: '{}' is not a valid vertex CSV".format(input_filename_vertex_dest))
	
	##########################################################
	# note: in CSV, 2-3-4 = pos X-Y-Z, 5-6-7 = norm X-Y-Z, 9-10 = U-V
	print("running...")
	
	stats_nearest_distance_for_all_verts = []
	
	for asdf, destvert in enumerate(rawlist_vertex_dest):
		# if this isn't a vertex, skip it
		if destvert[0] != core.pmxe_vertex_csv_tag: continue
		# progress
		core.print_progress_oneline(asdf / len(rawlist_vertex_dest))

		dest_pos = destvert[2:5]
		# calculate the dist from this vert to each vert in source list
		# find the one single vertex that is closest in source!
		# the vert that is closest, copies its UV data
		
		nearest_vert_dist = 1000
		nearest_vert_uv = []
		for sourcevert in rawlist_vertex_source:
			# if this isn't a vertex, skip it
			if sourcevert[0] != core.pmxe_vertex_csv_tag: continue
			source_pos = sourcevert[2:5]
			dist = core.my_euclidian_distance([a-b for a,b in zip(source_pos, dest_pos)])
			if dist < nearest_vert_dist:
				nearest_vert_dist = dist
				nearest_vert_uv = sourcevert[9:11]
		# now i have found it!
		# store the distance for stats reasons
		stats_nearest_distance_for_all_verts.append(nearest_vert_dist)
		# copy the UV data (modify the dest-list)
		rawlist_vertex_dest[asdf][9:11] = nearest_vert_uv
		pass
	
	# stats! how close do the two models align?
	min_dist = min(stats_nearest_distance_for_all_verts)
	max_dist = max(stats_nearest_distance_for_all_verts)
	avg_dist = sum(stats_nearest_distance_for_all_verts) / len(stats_nearest_distance_for_all_verts)
	print("stats: min_dist = %.8f, max_dist = %.8f, avg_dist = %.8f" % (min_dist, max_dist, avg_dist))
	
	# write out
	# build the output file name and ensure it is free
	output_filename = core.filepath_insert_suffix(input_filename_vertex_dest, "_uvpaste")
	output_filename = core.filepath_get_unused_name(output_filename)
	print("Writing uvpaste result to '" + output_filename + "'...")
	# export modified CSV
	io.write_csvlist_to_file(output_filename, rawlist_vertex_dest, use_jis_encoding=True)
	
	return None
	
if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.RUN_WITH_TRACEBACK(main)
