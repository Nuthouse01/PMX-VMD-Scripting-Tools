import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.00 - 6/10/2021"


THRESHOLD = 0.002
WIGGLE_ROOM = 0.1
EPSILON = 1e-7

def main():
	print("Transfer a morph from one model to another, assuming the geometry is in the same position")
	print("Needs source PMX, source morph, and dest PMX")
	
	# prompt PMX name
	print("Please enter name of DESTINATION PMX model file:")
	dest_name_pmx = core.prompt_user_filename("PMX file", ".pmx")
	dest_pmx = pmxlib.read_pmx(dest_name_pmx, moreinfo=True)
	
	# prompt PMX name
	print("Please enter name of SOURCE PMX model file:")
	source_name_pmx = core.prompt_user_filename("PMX file", ".pmx")
	source_pmx = pmxlib.read_pmx(source_name_pmx, moreinfo=True)
	
	while True:
		print("Please enter/paste JP name of morph to transfer:")
		s = input("name: >")
		# exit condition is empty input
		if s == "": break
		
		# find the morph with the matching name
		source_morph_idx = core.my_list_search(source_pmx.morphs, lambda x: x.name_jp == s)
		if source_morph_idx is None:
			print("err: could not find that name, try again")
			continue
		
		# verify vertex morph
		source_morph = source_pmx.morphs[source_morph_idx]
		if source_morph.morphtype != pmxstruct.MorphType.VERTEX:
			print("err: for now, only support vertex morphs")
			continue
		
		newmorph = pmxstruct.PmxMorph(name_jp = source_morph.name_jp,
									  name_en = source_morph.name_en,
									  panel = source_morph.panel,
									  morphtype = source_morph.morphtype,
									  items = [])
		# have source, have dest, have morph
		# begin iterating!
		# for each vert ref in vertex morph, go to vert in source PMX to get position
		#
		print("running...")
		already_used_verts = set()
		
		stats_nearest_distance_for_all_verts = []
		
		for asdf, morphitem in enumerate(source_morph.items):
			core.print_progress_oneline(asdf / len(source_morph.items))
			vertid = morphitem.vert_idx
			vertpos = source_pmx.verts[vertid].pos # get vertex xyz
			# find the vert or verts in dest_pmx that correspond to this vert in source_pmx
			# problem: multiple vertices at the same location
			# in most cases, all verts at a location will move the same amount... but not always? how to handle?
			# TODO check thru source pmx morph for "diverging" vertices like this? same location in source but not same offset?
			# if some get left behind that's OK, that's usually material borders, easy to use morph editor, only see materials I don't want to morph, and remove those verts from the morph
			# solution: all verts within some radius? not perfect solution
			# radius is hardcoded... if no dest vert found within radius, then what? warn & report nearest?
			# maybe find nearest vertex, and then find all vertices within 110% of that radius?
			
			# calculate dist from here to each vert in dest_pmx
			# find all verts within this dist threshold
			nearest_vert_dist = 1000
			short_dist_list = []
			# first, find every vertex within 0.1 units (just so i have a shorter list to sort)
			for d,v2 in enumerate(dest_pmx.verts):
				dist = core.my_euclidian_distance([a-b for a,b in zip(vertpos, v2.pos)])
				nearest_vert_dist = min(nearest_vert_dist, dist)
				# dist = core.my_euclidian_distance([vertpos[i] - v2.pos[i] for i in range(3)])
				if dist < 0.01:
					short_dist_list.append((dist, d))
			# if nothing is found, then maybe give some insight for why?
			if not short_dist_list:
				print("warning: unable to find any verts within the threshold for source vert ID %d, nearest vert is dist=%f" % (vertid, nearest_vert_dist))
				continue
			# then sort this list to find the smallest distance
			short_dist_list.sort(key=lambda x: x[0])
			nearest_vert_dist = short_dist_list[0][0]
			# accumulate for stats before applying wiggle room
			stats_nearest_distance_for_all_verts.append(nearest_vert_dist)
			# apply the wiggle room, and also set it to epsilon if less than that, so the dist is never exactly 0
			nearest_vert_dist *= WIGGLE_ROOM + 1
			nearest_vert_dist = max(nearest_vert_dist, EPSILON)
			# now get all vertices that are less than this compare value
			# i.e. get all vertices that are between (nearest) and (nearest + 10%)
			matching_verts = []
			for dist, v in short_dist_list:
				if dist <= nearest_vert_dist:
					matching_verts.append(v)
				else:
					break
			for v in matching_verts:
				if v in already_used_verts:
					# if the vertex has already been used, and the previous match wants to move it by a different amount
					#  than the current match, then i've got a problem...
					#  if both matches want to move by the same amount, then stay quiet
					already_used_morphitem = core.my_list_search(newmorph.items, lambda x: x.vert_idx == v, getitem=True)
					if already_used_morphitem.move != morphitem.move:
						print(f'warning: disagreement on how to move vertex {v}')
				else:
					# if it was not yet used, then use it!
					# morphitem.vert_idx === v
					# copy the way that the source morph wants to move this vert.
					already_used_verts.add(v)
					newitem = pmxstruct.PmxMorphItemVertex(vert_idx=v, move=morphitem.move)
					newmorph.items.append(newitem)
			
			pass  # end of for-each-morphitem loop
		
		# done building the new morph, hopefully
		# make the vertices sorted cuz i can
		newmorph.items.sort(key=lambda x: x.vert_idx)
		
		if len(newmorph.items) != len(source_morph.items):
			print("warning: length mismatch! source has %d and new has %d, this requires closer attention" %
				  (len(source_morph.items), len(newmorph.items)))
		
		# stats! how close do the two models correlate?
		min_dist = min(stats_nearest_distance_for_all_verts)
		max_dist = max(stats_nearest_distance_for_all_verts)
		avg_dist = sum(stats_nearest_distance_for_all_verts) / len(stats_nearest_distance_for_all_verts)
		print("stats: min_dist = %.8f, max_dist = %.8f, avg_dist = %.8f" % (min_dist, max_dist, avg_dist))
		# add it to the dest pmx
		dest_pmx.morphs.append(newmorph)
		
		pass  # end of while-loop
	
	
	output_filename_pmx = core.filepath_insert_suffix(dest_name_pmx, "_MORPHTRANSFER")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, dest_pmx)
	print("DONE")

	return None

if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.RUN_WITH_TRACEBACK(main)
