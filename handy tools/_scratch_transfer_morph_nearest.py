

import sys
try:
	sys.path.append("../")
	from python import nuthouse01_core as core
	from python import nuthouse01_pmx_parser as pmxlib
	from python import nuthouse01_pmx_struct as pmxstruct
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	core = pmxlib = pmxstruct = None

# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False

THRESHOLD = 0.002



def main():
	print("Transfer a morph from one model to another, assuming the geometry is in the same position")
	print("Needs source PMX, source morph, and dest PMX")
	
	# prompt PMX name
	print("Please enter name of DESTINATION PMX model file:")
	dest_name_pmx = core.prompt_user_filename(".pmx")
	dest_pmx = pmxlib.read_pmx(dest_name_pmx, moreinfo=True)
	
	# prompt PMX name
	print("Please enter name of SOURCE PMX model file:")
	source_name_pmx = core.prompt_user_filename(".pmx")
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
		if source_morph.morphtype != 1:
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
		already_used_verts = set()
		
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
			matching_verts = []
			dist_list = []
			for d,v2 in enumerate(dest_pmx.verts):
				dist = core.my_euclidian_distance([vertpos[i] - v2.pos[i] for i in range(3)])
				dist_list.append(dist)
				if dist < THRESHOLD:
					matching_verts.append(d)
			if not matching_verts:
				print("warning: unable to find any verts within the threshold for source vert ID %d" % vertid)
				print("nearest vert is dist=%f" % min(dist_list))
			for v in matching_verts:
				if v not in already_used_verts:
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
		
		# add it to the dest pmx
		dest_pmx.morphs.append(newmorph)
		
		pass  # end of while-loop
	
	
	print("DONE")
	pmxlib.write_pmx("TRANSFER.pmx", dest_pmx)
	
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
