

import sys
try:
	sys.path.append("../")
	from python import nuthouse01_core as core
	from python import nuthouse01_pmx_parser as pmxlib
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	core = pmxlib = None

# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = True

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
		source_morph = core.my_sublist_find(source_pmx[6], 0, s)
		if source_morph is None:
			print("err: could not find that name, try again")
			continue
		
		# verify vertex morph
		if source_morph[3] != 1:
			print("err: for now, only support vertex morphs")
			continue
		
		newmorph = [source_morph[0], source_morph[1], source_morph[2], 1, []]
		# have source, have dest, have morph
		# begin iterating!
		# for each vert ref in vertex morph, go to vert in source PMX to get position
		#
		already_used_verts = set()
		
		for morphitem in source_morph[4]:
			vertid = morphitem[0]
			vert = source_pmx[1][vertid]
			vertpos = vert[0:3] # get vertex xyz
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
			for d,v2 in enumerate(dest_pmx[1]):
				dist = core.my_euclidian_distance([vertpos[i] - v2[i] for i in range(3)])
				dist_list.append(dist)
				if dist < THRESHOLD:
					matching_verts.append(d)
			if not matching_verts:
				print("warning: unable to find any verts within the threshold for source vert ID %d" % vertid)
				print("nearest vert is dist=%f" % min(dist_list))
			for v in matching_verts:
				if v not in already_used_verts:
					already_used_verts.add(v)
					newmorph[4].append([v] + morphitem[1:4])
			
			pass  # end of for-each-morphitem loop
		
		# done building the new morph, hopefully
		# make the vertices sorted cuz i can
		newmorph[4].sort(key=lambda x: x[0])
		
		if len(newmorph[4]) != len(source_morph[4]):
			print("warning: length mismatch! source has %d and new has %d, this requires closer attention" %
				  (len(source_morph[4]), len(newmorph[4])))
		
		# add it to the dest pmx
		dest_pmx[6].append(newmorph)
		
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
