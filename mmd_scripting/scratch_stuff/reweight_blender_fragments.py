import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.01 - 7/12/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


# todo: once help text is properly filled out this will be gui-compatible
helptext = '''=================================================
asdfasdf
'''


"""
fragment detection algorithm:
there is a very slight airgap between all of the pieces, but each individual fragment is airtight. so the algorithm could look for vertices with exactly the same xyz as another vert to understand that they are in the same fragment! gonna be glacially slow tho, unless i do the hash trick

BRUTE FORCE ALGORITHM, no assumptions or optimizations
1. pick a vertex A that hasn't been used yet
2. create a new "fragment set" and add A to it
3. note the size of the "fragment set"
4. find all faces that include any vertex in the "fragment set", whenever i find one, add all verts that it includes to the "fragment set" as well
5. find all vertices that have the same exact coordinates as any vertex in the "fragment set", and add them to the "fragment set"
6. if the size of the fragment set is greater now than it was at step 3, repeat steps 3-6. otherwise, go to step 1.

observation: clustering! all verts of a fragment are contiguous, all faces of a fragment are contiguous.
observation: the first faces are built out of the first vertices, the second faces are built out of the second vertices, etc

optimization: when i flood into a face or vert, everything between that location and the start of the fragment is part of the fragment
optimization: when looking thru "all faces and/or verts", only scan forward X locations from the highest-index face/vert i have found so far
"""

MASS_FACTOR = 10



def dist_to_nearest_vertex(point, vert_set, pmx):
	distance_per_vert = []
	for v_id in vert_set:
		v = pmx.verts[v_id]
		delta = [a - b for a, b in zip(point, v.pos)]  # [x-x, y-y, z-z]
		dist = core.my_euclidian_distance(delta)
		distance_per_vert.append(dist)
	return min(distance_per_vert)

def dist_to_nearest_point_on_mesh_surface(point, vert_set, pmx, face_set):
	# TODO: i dont wanna slog thru the math and figure out how to do this
	# how do i calculate the distance from a point to the nearest point on the triangle-based surface of the fragment it is inside?
	# for each triangle:
	#	calcualte a plane,
	#	calculate the closest point on that plane,
	#	ask "is this point inside this triangle?" (HOW?),
	#	if yes then cool! save the dist to this point,
	#	if no then https://stackoverflow.com/questions/10983872/distance-from-a-point-to-a-polygon, save the dist to the nearest point on the perimiter of the triangle,
	# then you have created a list of the distances from the given point to the nearest point on the face or perimeter of every triangle,
	# so return the minimum distance from that list
	return 0


def main(moreinfo=True):
	# PROBLEM: the assumption of locality was not correct! verts for a chunk are not clustered! (i think?)
	
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX input file:")
	input_filename_pmx = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=moreinfo)
	
	# coordinates are stored as list[x, y, z], convert this --> tuple --> hash for much faster comparing
	vert_coord_hashes = [hash(tuple(v.pos)) for v in pmx.verts]
	
	list_of_vert_sets = []
	list_of_face_sets = []
	list_of_bone_indices = []
	list_of_rigidbody_indices = []
	
	# it's simpler to start with a full set of everything used, and then remove things as they are used
	# and its no less efficient
	all_unused_verts = set(list(range(len(pmx.verts))))
	
	start_vert = 0
	start_face = 0
	# continue looping for as long as there are verts not in a fragment
	while all_unused_verts:
		# 1. start a new sets for the vertices and faces
		vert_set = set()
		face_set = set()
		# 2. pick a vertex that hasn't been used yet and add it to the set, ez
		start_vert = min(all_unused_verts)
		print("start@%d:: " % start_vert, end="")
		vert_set.add(start_vert)
		'''
		# 2b. optimization: a fragment is guaranteed to have at least 4 faces (to make a closed 3d solid) and therefore at least 4 verts
		# can i safely assume that they are "sharp" corners and therefore there are 12 verts?
		for i in range(3):
			vert_set.add(start_vert + i)
		# also, init the faces set with the minimum of 4 faces, and add any verts included in those faces to the vert set
		for i in range(1):
			face_set.add(start_face + i)
			for v in pmx.faces[start_face + i]:  # for each vert in this face,
				vert_set.add(v)  # add this vert to the vert set
		# guarantee that it is contiguous from start_vert to the highest index that was in the faces
		vert_set = set(list(range(start_vert, max(vert_set)+1)))
		# now i have initialized the set with everything i know is guarnateed part of the fragment
		highest_known_vert = max(vert_set)
		highest_known_face = max(face_set)
		'''
		
		# begin looping & flooding until i don't detect any more
		while True:
			# 3. note the number of verts collected so far
			set_size_A = len(vert_set)
			
			# 4. find all faces that include any vertex in the "fragment set",
			# whenever i find one, add all verts that it includes to the "fragment set" as well
			
			# zero-assumption brute-force method:
			for f_id in range(len(pmx.faces)):
				face = pmx.faces[f_id]
				if face[0] in vert_set or face[1] in vert_set or face[2] in vert_set: # we got a hit!
					face_set.add(f_id)
					vert_set.add(face[0])
					vert_set.add(face[1])
					vert_set.add(face[2])
			'''
			# optimization: scan only faces index 'highest_known_face+1' thru 'highest_known_face'+LOOKAHEAD
			#	because 0 thru start_face is guaranteed to not be part of the group
			#	and start_face thru highest_known_face is already guaranteed to be part of the group
			#	if chunks are bigger than LOOKAHEAD, then it's not guaranteed to succeed or fail, could do either
			for f_id in range(highest_known_face+1, min(highest_known_face+LOOKAHEAD, len(pmx.faces))):
				face = pmx.faces[f_id]
				if face[0] in vert_set or face[1] in vert_set or face[2] in vert_set:
					# we got a hit!
					face_set.add(f_id)
					vert_set.add(face[0])
					vert_set.add(face[1])
					vert_set.add(face[2])
					# optimization: if this is farther than what i thought was the end, then everything before it should be added too
					if f_id > highest_known_face:
						for x in range(highest_known_face+1, f_id):
							face_set.add(x)
							vert_set.add(pmx.faces[x][0])
							vert_set.add(pmx.faces[x][1])
							vert_set.add(pmx.faces[x][2])
						highest_known_face = f_id
			'''
			set_size_B = len(vert_set)
			
			# update the set of vertex coord hashes for easier comparing
			vert_set_hashes = set([vert_coord_hashes[i] for i in vert_set])
			# 5. find all vertices that have the same exact coordinates as any vertex in the "fragment set",
			# then and add them to the "fragment set"
			
			# zero-assumption brute-force method:
			for v_id in range(len(vert_coord_hashes)):
				vert_hash = vert_coord_hashes[v_id]
				if vert_hash in vert_set_hashes: # we got a hit!
					vert_set.add(v_id)
			'''
			# optimization: scan only verts index 'highest_known_vert+1' thru 'highest_known_vert'+LOOKAHEAD
			#	because 0 thru start_vert is guaranteed to not be part of the group
			#	and start_vert thru highest_known_vert is already guaranteed to be part of the group
			#	if chunks are bigger than LOOKAHEAD, then it's not guaranteed to succeed or fail, could do either
			for v_id in range(highest_known_vert+1, min(highest_known_vert+LOOKAHEAD, len(pmx.verts))):
				vert_hash = vert_coord_hashes[v_id]
				if vert_hash in vert_set_hashes:
					# we got a hit!
					vert_set.add(v_id)
					# optimization: if this is farther than what i thought was the end, then everything before it should be added too
					if v_id > highest_known_vert:
						for x in range(highest_known_vert+1, v_id):
							vert_set.add(x)
						highest_known_vert = v_id
			'''
			set_size_C = len(vert_set)
			
			# print("+%d +%d, " % (set_size_B - set_size_A, set_size_C - set_size_B), end="")
			print("+%d, " % (set_size_C - set_size_A), end="")
			
			# 6. if the number of verts did not change, we are done
			if set_size_C == set_size_A:
				break
			pass
		print("final size: %d verts, %d faces" % (len(vert_set), len(face_set)))
		# print("min=%d, max=%d, contiguous=%s" % (min(vert_set), max(vert_set), str(bool(max(vert_set)-min(vert_set)==(len(vert_set)-1)))))
		# 7. now i have a complete fragment in vert_set and face_set !! :)
		list_of_vert_sets.append(vert_set)
		list_of_face_sets.append(face_set)
		# remove all "used" verts from the "unused" set
		all_unused_verts.difference_update(vert_set)
		# loop & populate another fragment
		pass
	# done with identifying all fragments!
	
	# double-check that all vertices got sorted into one and only one fragment
	assert sum([len(vs) for vs in list_of_vert_sets]) == len(pmx.verts)
	temp = set()
	for vs in list_of_vert_sets:
		temp.update(vs)
	assert len(temp) == len(pmx.verts)
	
	# double-check that all faces got sorted into one and only one fragment
	assert sum([len(fs) for fs in list_of_face_sets]) == len(pmx.faces)
	temp = set()
	for fs in list_of_face_sets:
		temp.update(fs)
	assert len(temp) == len(pmx.faces)
	
	print("")
	print("Identified %d discrete fragments!" % (len(list_of_vert_sets),))
	
	# BONES AND WEIGHTS
	for fragnum in range(len(list_of_vert_sets)):
		# name
		newbone_name = "fragment%d" % fragnum
		# position: average of all vertices in the fragment? sure why not
		# TODO is there a "better" way of calculating the average/centroid/center of mass? idk
		newbone_pos = [0,0,0]
		for v_id in list_of_vert_sets[fragnum]:
			# accumulate the XYZ for each vertex in the fragment
			newbone_pos[0] += pmx.verts[v_id].pos[0]
			newbone_pos[1] += pmx.verts[v_id].pos[1]
			newbone_pos[2] += pmx.verts[v_id].pos[2]
		# divide by the number of verts in the fragment to get the average
		newbone_pos[0] /= len(list_of_vert_sets[fragnum])
		newbone_pos[1] /= len(list_of_vert_sets[fragnum])
		newbone_pos[2] /= len(list_of_vert_sets[fragnum])
		# create the new bone object
		newbone_obj = pmxstruct.PmxBone(
			name_jp=newbone_name, name_en=newbone_name, pos=newbone_pos, parent_idx=0, deform_layer=0,
			deform_after_phys=False, has_rotate=True, has_translate=True, has_visible=True, has_enabled=True,
			has_ik=False, tail_usebonelink=False, tail=[0, 0, 0], inherit_rot=False, inherit_trans=False,
			has_fixedaxis=False, has_localaxis=False, has_externalparent=False,
		)
		# note the index it will be inserted at
		thisboneindex = len(pmx.bones)
		list_of_bone_indices.append(thisboneindex)
		# append it onto the list of bones
		pmx.bones.append(newbone_obj)
		# for each vertex in this fragment, give it 100% weight on that bone
		for v_id in list_of_vert_sets[fragnum]:
			v = pmx.verts[v_id]
			v.weighttype = pmxstruct.WeightMode.BDEF1 # BDEF1
			v.weight = [[thisboneindex, 1]]
		pass
	
	# RIGID BODIES
	for fragnum in range(len(list_of_vert_sets)):
		newbody_name = "body%d-0" % fragnum
		newbody_pos = pmx.bones[list_of_bone_indices[fragnum]].pos
		# hmmm, what do do here? this is the really hard part!
		# let's just make a sphere with radius equal to the distance to the nearest vertex of this fragment?
		# TODO: the bodies created from this are intersecting eachother when at rest!
		#  the distance to the closest vertex is greater than the distance to the closest point on the closest face!
		#  therefore there is a small bit of overlap
		newbody_radius = dist_to_nearest_vertex(newbody_pos, list_of_vert_sets[fragnum], pmx)
		
		# TODO: to "fill a fragment with several rigidbody spheres", you need to a) select a center for each, b) select a size for each
		#  the sizes can come from algorithm roughed out in dist_to_nearest_point_on_mesh_surface()
		#  the centers... idk? how can you do this?
		#  https://doc.babylonjs.com/toolsAndResources/utilities/InnerMeshPoints might be able to reuse some of the ideas from this?

		# phys params: set mass equal to the VOLUME of this new rigid body! oh that seems clever, i like that, bigger ones are heavier
		# if i figure out how to create multiple bodies, each body's mass should be proportional to its volume like this
		volume = 3.14 * (4 / 3) * (newbody_radius**3)
		mass = volume * MASS_FACTOR
		# phys params: use the default damping/friction/etc parameters cuz idk why not
		phys_move_damp = 0.95
		phys_rot_damp = 0.95
		phys_friction = 0.95
		phys_repel = 0.3  # bounciness?

		# this gif is with these params: https://gyazo.com/3d143f33b79c1151c1ccbffcc578448b
		
		# groups: for now, since each fragment is only one body, i can just ignore groups stuff
		# groups: later, if each fragment is several bodies... assign the groups in round-robin? each fragment will clip thru 1/15 of the
		# other fragments but i think that's unavoidable. also need to reserve group16 for the floor! so set each fragment's cluster of
		# bodies to nocollide with the group# assigned to that cluster, but respect all others.
		
		# bone_idx: if there are more than 1 rigidbodies associated with each fragment, one "main" body is connected to the bone
		# all the others are set to bone -1 and connected to the mainbody via joints
		newbody_obj = pmxstruct.PmxRigidBody(
			name_jp=newbody_name, name_en=newbody_name, bone_idx=list_of_bone_indices[fragnum],
			pos=newbody_pos, rot=[0,0,0], size=[newbody_radius,0,0], shape=pmxstruct.RigidBodyShape.SPHERE,
			group=1, nocollide_set=set(), phys_mode=pmxstruct.RigidBodyPhysMode.PHYSICS, phys_mass=mass,
			phys_move_damp=phys_move_damp, phys_rot_damp=phys_rot_damp, phys_repel=phys_repel, phys_friction=phys_friction
		)
		
		# note the index that this will be inserted at
		bodyindex = len(pmx.rigidbodies)
		list_of_rigidbody_indices.append(bodyindex)
		pmx.rigidbodies.append(newbody_obj)
		pass
	
	
	# JOINTS
	# if there is only one body per fragment then this is okay without any joints
	# if there are several bodies then we need to create joints from the "center" rigidbody to the others
	# even if you try to limit the joint to 0 rotation and 0 slide it still has some wiggle in it :( not perfectly rigid
	# TODO: i'll deal with this if and only if an algorithm for filling fragments with rigidbodies is created
	for fragnum in range(len(list_of_vert_sets)):
		pass
	
	
	core.MY_PRINT_FUNC("")
	
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_fragfix")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=moreinfo)
	core.MY_PRINT_FUNC("Done!")
	return None


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
