

# MASSIVE thanks to FelixJones on Github for already exporing & documenting the PMX file structure!
# https://gist.github.com/felixjones/f8a06bd48f9da9a4539f


# this file fully parses a PMX file and returns all of the data it contained, structured as a list of lists

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	import nuthouse01_core as core
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	core = None



# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False

# how many extra vec4s each vertex has with it
ADDL_VERTEX_VEC4 = 0
# type used to store an index for each thing, these are concatenated to dynamically make format strings
IDX_VERT = "x"
IDX_TEX = "x"
IDX_MAT = "x"
IDX_BONE = "x"
IDX_MORPH = "x"
IDX_RB = "x"



# return conventions: to handle fields that may or may not exist, many things are lists that don't strictly need to be
# if the data doesn't exist, it is an empty list
# that way the indices of other return fields are not affect when it is missing


def parse_pmx_header(raw) -> list:
	##################################################################
	# HEADER INFO PARSING
	# collects some returnable data, mostly just sets globals
	# returnable: ver, name_jp, name_en, comment_jp, comment_en
	
	expectedmagic = bytearray([0x50, 0x4D, 0x58, 0x20])
	fmt_magic = "4s f b"
	(magic, ver, numglobal) = core.my_unpack(fmt_magic, raw)
	if magic != expectedmagic:
		print("Warning: this file does not begin with the correct magic bytes. Maybe it was locked? Locks wont stop me!")
		print("Expected '%s' but found '%s'" % (expectedmagic.hex(), magic.hex()))
	
	# only first 8 bytes have known uses
	# more bytes have no known purpose but need to be accounted for anyway
	fmt_globals = str(numglobal) + "b"
	globalflags = core.my_unpack(fmt_globals, raw)	# this actually returns a tuple of ints, which works just fine, dont touch it
	# print(globalflags)
	# byte 0: encoding
	if globalflags[0] == 0:
		core.set_encoding("utf_16_le")
	elif globalflags[0] == 1:
		core.set_encoding("utf_8")
	else:
		print("unsupported value")
	# byte 1: additional vec4 per vertex
	global ADDL_VERTEX_VEC4
	ADDL_VERTEX_VEC4 = globalflags[1]
	# bytes 2-7: data size to use for index references
	global IDX_VERT, IDX_TEX, IDX_MAT, IDX_BONE, IDX_MORPH, IDX_RB
	vert_conv = {1:"B", 2:"H", 4:"i"}
	conv =      {1:"b", 2:"h", 4:"i"}
	IDX_VERT  = vert_conv[globalflags[2]]
	IDX_TEX   = conv[globalflags[3]]
	IDX_MAT   = conv[globalflags[4]]
	IDX_BONE  = conv[globalflags[5]]
	IDX_MORPH = conv[globalflags[6]]
	IDX_RB    = conv[globalflags[7]]
	# finally handle the model names & comments
	(name_jp, name_en, comment_jp, comment_en) = core.my_unpack("t t t t", raw)
	# print(name_jp, name_en, comment_jp, comment_en)
	
	# assemble all the info into a list for returning
	retme = [ver, name_jp, name_en, comment_jp, comment_en]
	return retme

def parse_pmx_vertices(raw) -> list:
	# first item is int, how many vertices
	i = core.my_unpack("i", raw)
	print("...# of verts            =", i)
	retme = []
	last_progress = -1
	for d in range(i):
		# first, basic stuff
		(posX, posY, posZ, normX, normY, normZ, u, v) = core.my_unpack("8f", raw)
		# then, some number of vec4s (probably none)
		addl_vec4s = []
		for z in range(ADDL_VERTEX_VEC4):
			this_vec4 = core.my_unpack("4f", raw) # already returns as a list of 4 floats, no need to unpack then repack
			addl_vec4s.append(this_vec4)
		weighttype = core.my_unpack("b", raw)
		weights = []
		if weighttype == 0:
			# BDEF1
			b1 = core.my_unpack(IDX_BONE, raw)
			weights = [b1]
		elif weighttype == 1:
			# BDEF2
			#(b1, b2, b1w) # already returns as a list of floats, no need to unpack then repack
			weights = core.my_unpack("2" + IDX_BONE + "f", raw)
		elif weighttype == 2:
			# BDEF4
			#(b1, b2, b3, b4, b1w, b2w, b3w, b4w) # already returns as a list of floats, no need to unpack then repack
			weights = core.my_unpack("4" + IDX_BONE + "4f", raw)
		elif weighttype == 3:
			# SDEF
			#(b1, b2, b1w, c1, c2, c3, r01, r02, r03, r11, r12, r13)
			weights = core.my_unpack("2" + IDX_BONE + "10f", raw)
		elif weighttype == 4:
			# it must be using QDEF, a type only for PMX v2.1 which I dont need to support so idgaf
			# (b1, b2, b3, b4, b1w, b2w, b3w, b4w)
			weights = core.my_unpack("4" + IDX_BONE + "4f", raw)
		else:
			print("invalid weight type for vertex")
		# then there is one final float after the weight crap
		edgescale = core.my_unpack("f", raw)
		# display progress printouts
		if d > last_progress:
			last_progress += 1000
			core.print_progress_oneline(d, i)

		# assemble all the info into a list for returning
		thisvert = [posX, posY, posZ, normX, normY, normZ, u, v, addl_vec4s, weighttype, weights, edgescale]
		retme.append(thisvert)
	return retme

def parse_pmx_surfaces(raw) -> list:
	# surfaces is just another name for faces
	# first item is int, how many vertex indices there are
	# each face is 3 vertex indices, so i will always be a multiple of 3
	i = core.my_unpack("i", raw)
	print("...# of faces            =", i)
	retme = []
	i = int(i / 3)
	last_progress = -1
	for d in range(i):
		# each entry is a group of 3 vertex indeces that make a face
		thisface = core.my_unpack("3" + IDX_VERT, raw)
		# display progress printouts
		if d > last_progress:
			last_progress += 1000
			core.print_progress_oneline(d, i)
		retme.append(thisface)
	return retme

def parse_pmx_textures(raw) -> list:
	# first item is int, how many textures
	i = core.my_unpack("i", raw)
	print("...# of textures         =", i)
	retme = []
	for d in range(i):
		filepath = core.my_unpack("t", raw)
		# print(filepath)
		retme.append(filepath)
	return retme

def parse_pmx_materials(raw) -> list:
	# first item is int, how many materials
	i = core.my_unpack("i", raw)
	print("...# of materials        =", i)
	retme = []
	for d in range(i):
		(name_jp, name_en, diffR, diffG, diffB, diffA, specR, specG, specB, specpower) = core.my_unpack("t t 4f 4f", raw)
		# print(name_jp, name_en)
		(ambR, ambG, ambB, flags, edgeR, edgeG, edgeB, edgeA, edgescale, tex_idx) = core.my_unpack("3f B 5f" + IDX_TEX, raw)
		no_backface_culling = flags & (1<<0) # does this mean it is 2-sided?
		cast_ground_shadow  = flags & (1<<1)
		cast_shadow         = flags & (1<<2)
		receive_shadow      = flags & (1<<3)
		use_edge            = flags & (1<<4)
		vertex_color        = flags & (1<<5) # v2.1 only
		draw_as_points      = flags & (1<<6) # v2.1 only
		draw_as_lines       = flags & (1<<7) # v2.1 only
		(sph_idx, sph_mode, toon_mode) = core.my_unpack(IDX_TEX + "b b", raw)
		if toon_mode == 0:
			# toon is using a texture reference
			toon_idx = core.my_unpack(IDX_TEX, raw)
		else:
			# toon is using one of the builtin toons, toon01.bmp thru toon10.bmp (values 0-9)
			toon_idx = core.my_unpack("b", raw)
		(comment, surface_ct) = core.my_unpack("t i", raw)
		# note: i structure the faces list into groups of 3 vertex indices, this is divided by 3 to match
		faces_ct = int(surface_ct / 3)
		
		# assemble all the info into a list for returning
		flaglist = [no_backface_culling, cast_ground_shadow, cast_shadow, receive_shadow, use_edge, vertex_color,
					draw_as_points, draw_as_lines]
		thismat = [name_jp, name_en, diffR, diffG, diffB, diffA, specR, specG, specB, specpower, ambR, ambG, ambB,
				   flaglist, edgeR, edgeG, edgeB, edgeA, edgescale, tex_idx, sph_idx, sph_mode, toon_mode, toon_idx,
				   comment, faces_ct]
		retme.append(thismat)
	return retme

def parse_pmx_bones(raw) -> list:
	# first item is int, how many bones
	i = core.my_unpack("i", raw)
	print("...# of bones            =", i)
	retme = []
	for d in range(i):
		(name_jp, name_en, posX, posY, posZ, parent_idx, deform_layer, flags1, flags2) = core.my_unpack("t t 3f" + IDX_BONE + "i 2B", raw)
		# print(name_jp, name_en)
		tail_type =              flags1 & (1<<0)
		rotateable =             flags1 & (1<<1)
		translateable =          flags1 & (1<<2)
		visible =                flags1 & (1<<3)
		enabled =                flags1 & (1<<4)
		ik =                     flags1 & (1<<5)
		inherit_rot =            flags2 & (1<<0)
		inherit_trans =          flags2 & (1<<1)
		fixed_axis =             flags2 & (1<<2)
		local_axis =             flags2 & (1<<3)
		deform_after_phys =      flags2 & (1<<4)
		external_parent =        flags2 & (1<<5)
		# important for structure: tail type, inherit, fixed axis, local axis, ext parent, IK
		maybe_inherit = []
		maybe_fixed_axis = []
		maybe_local_axis = []
		maybe_external_parent = []
		maybe_ik = []
		if tail_type:
			# use index for bone its pointing at
			tail_pointat = core.my_unpack(IDX_BONE, raw)
			maybe_tail = [tail_pointat]
		else:
			# use offset
			maybe_tail = core.my_unpack("3f", raw)
		if inherit_rot or inherit_trans:
			# (inherit_parent, inherit_influence) # returns as list, no need to unpack then repack
			maybe_inherit = core.my_unpack(IDX_BONE + "f", raw)
		if fixed_axis:
			# format is xyz obviously
			maybe_fixed_axis = core.my_unpack("3f", raw)
		if local_axis:
			(xx, xy, xz, zx, zy, zz) = core.my_unpack("3f 3f", raw)
			local_axis_x_xyz = [xx, xy, xz]
			local_axis_z_xyz = [zx, zy, zz]
			maybe_local_axis = [local_axis_x_xyz, local_axis_z_xyz]
		if external_parent:
			maybe_external_parent = core.my_unpack(IDX_BONE, raw)
		if ik:
			(ik_target, ik_loops, ik_anglelimit, num_ik_links) = core.my_unpack(IDX_BONE + "i f i", raw)
			maybe_ik = [ik_target, ik_loops, ik_anglelimit]
			ik_links = []
			for z in range(num_ik_links):
				(ik_link_idx, link_limits) = core.my_unpack(IDX_BONE + "b", raw)
				maybe_iklinks_limit = []
				if link_limits:
					(minX, minY, minZ, maxX, maxY, maxZ) = core.my_unpack("3f 3f", raw)
					iklinks_limit_min_xyz = [minX, minY, minZ]
					iklinks_limit_max_xyz = [maxX, maxY, maxZ]
					maybe_iklinks_limit = [iklinks_limit_min_xyz, iklinks_limit_max_xyz]
				ik_links.append([ik_link_idx, maybe_iklinks_limit])
			maybe_ik.append(ik_links)
			# ik list becomes:
			# [target, loops, anglelimit, [[link_idx, limits], [link_idx, limits], [link_idx, limits]] ]
			# where limits is a list with length 6 or empty list
			
		# assemble all the info into a list for returning
		# note that these are arranged within the list in a different order from how they are arranged in the binary
		# this way the flags which control optional fields are next to the fields they control
		thisbone = [name_jp, name_en, posX, posY, posZ, parent_idx, deform_layer, deform_after_phys,
					rotateable, translateable, visible, enabled,
					tail_type, maybe_tail, inherit_rot, inherit_trans, maybe_inherit, fixed_axis, maybe_fixed_axis,
					local_axis, maybe_local_axis, external_parent, maybe_external_parent, ik, maybe_ik]
		retme.append(thisbone)
	return retme

def parse_pmx_morphs(raw) -> list:
	# first item is int, how many morphs
	i = core.my_unpack("i", raw)
	print("...# of morphs           =", i)
	retme = []
	last_progress = -1
	for d in range(i):
		(name_jp, name_en, panel, morphtype, itemcount) = core.my_unpack("t t b b i", raw)
		# print(name_jp, name_en)
		these_items = []
		for z in range(itemcount):
			# for each morph in the group morph, or vertex in the vertex morph, or bone in the bone morph....
			# what to unpack varies on morph type, 9 possibilities + some for v2.1
			this_item = []
			if morphtype == 0:
				# group
				# (morph_idx, influence) # already returns as a list, no need to unpack and repack
				this_item = core.my_unpack(IDX_MORPH + "f", raw)
			elif morphtype == 1:
				# vertex
				# (vert_idx, transX, transY, transZ)
				this_item = core.my_unpack(IDX_VERT + "3f", raw)
			elif morphtype == 2:
				# bone
				# (bone_idx, transX, transY, transZ, rotX, rotY, rotZ, rotW)
				this_item = core.my_unpack(IDX_BONE + "3f 4f", raw)
			elif 3 <= morphtype <= 7:
				# UV
				# what these values do depends on the UV layer they are affecting, but the docs dont say what...
				# oh well, i dont need to use them so i dont care :)
				# (bone_idx, A, B, C, D)
				this_item = core.my_unpack(IDX_VERT + "4f", raw)
			elif morphtype == 8:
				# material
				# (mat_idx, is_add, diffR, diffG, diffB, diffA, specR, specG, specB) = core.unpack(IDX_MAT+"b 4f 3f", raw)
				# (specpower, ambR, ambG, ambB, edgeR, edgeG, edgeB, edgeA, edgesize) = core.unpack("f 3f 4f f", raw)
				# (texR, texG, texB, texA, sphR, sphG, sphB, sphA, toonR, toonG, toonB, toonA) = core.unpack("4f 4f 4f", raw)
				this_item = core.my_unpack(IDX_MAT + "b 4f 3f    f 3f 4f f    4f 4f 4f", raw)
			elif morphtype == 9:
				# (2.1 only) flip
				# (morph_idx, influence)
				this_item = core.my_unpack(IDX_MORPH + "f", raw)
			elif morphtype == 10:
				# (2.1 only) impulse
				# (rb_idx, is_local, movX, movY, movZ, rotX, rotY, rotZ)
				this_item = core.my_unpack(IDX_RB + "b 3f 3f", raw)
			else:
				print("unsupported morph type value")
			these_items.append(this_item)
		
		# display progress printouts
		if d > last_progress:
			last_progress += 10
			core.print_progress_oneline(d, i)
		# assemble the data into list for returning
		thismorph = [name_jp, name_en, panel, morphtype, these_items]
		retme.append(thismorph)
	return retme

def parse_pmx_dispframes(raw) -> list:
	# first item is int, how many dispframes
	i = core.my_unpack("i", raw)
	print("...# of dispframes       =", i)
	retme = []
	for d in range(i):
		(name_jp, name_en, is_special, itemcount) = core.my_unpack("t t b i", raw)
		# print(name_jp, name_en)
		these_items = []
		for z in range(itemcount):
			is_morph = core.my_unpack("b", raw)
			if is_morph:
				morph_idx = core.my_unpack(IDX_MORPH, raw)
				this_item = [is_morph, morph_idx]
			else:
				bone_idx = core.my_unpack(IDX_BONE, raw)
				this_item = [is_morph, bone_idx]
			these_items.append(this_item)
		# assemble the data into list for returning
		thisframe = [name_jp, name_en, is_special, these_items]
		retme.append(thisframe)
	return retme

def parse_pmx_rigidbodies(raw) -> list:
	# first item is int, how many rigidbodies
	i = core.my_unpack("i", raw)
	print("...# of rigidbodies      =", i)
	retme = []
	for d in range(i):
		(name_jp, name_en, bone_idx, group, nocollide_mask, shape) = core.my_unpack("t t" + IDX_BONE + "b H b", raw)
		# print(name_jp, name_en)
		# shape: 0=sphere, 1=box, 2=capsule
		(sizeX, sizeY, sizeZ, posX, posY, posZ, rotX, rotY, rotZ) = core.my_unpack("3f 3f 3f", raw)
		(mass, move_damp, rot_damp, repel, friction, physmode) = core.my_unpack("5f b", raw)
		# physmode: 0=follow bone, 1=physics, 2=physics rotate only (pivot on bone)
		
		# assemble the data into list for returning
		thisbody = [name_jp, name_en, bone_idx, group, nocollide_mask, shape, sizeX, sizeY, sizeZ, posX, posY, posZ,
					rotX, rotY, rotZ, mass, move_damp, rot_damp, repel, friction, physmode]
		retme.append(thisbody)
	return retme

def parse_pmx_joints(raw) -> list:
	# first item is int, how many joints
	i = core.my_unpack("i", raw)
	print("...# of joints           =", i)
	retme = []
	for d in range(i):
		(name_jp, name_en, jointtype, rb1_idx, rb2_idx, posX, posY, posZ) = core.my_unpack("t t b 2" + IDX_RB + "3f", raw)
		# jointtype: 0=spring6DOF, all others are v2.1 only!!!! 1=6dof, 2=p2p, 3=conetwist, 4=slider, 5=hinge
		# print(name_jp, name_en)
		(rotX, rotY, rotZ, posminX, posminY, posminZ, posmaxX, posmaxY, posmaxZ) = core.my_unpack("3f 3f 3f", raw)
		(rotminX, rotminY, rotminZ, rotmaxX, rotmaxY, rotmaxZ) = core.my_unpack("3f 3f", raw)
		(springposX, springposY, springposZ, springrotX, springrotY, springrotZ) = core.my_unpack("3f 3f", raw)

		# assemble the data into list for returning
		thisjoint = [name_jp, name_en, jointtype, rb1_idx, rb2_idx, posX, posY, posZ,
					 rotX, rotY, rotZ, posminX, posminY, posminZ, posmaxX, posmaxY, posmaxZ,
					 rotminX, rotminY, rotminZ, rotmaxX, rotmaxY, rotmaxZ,
					 springposX, springposY, springposZ, springrotX, springrotY, springrotZ]
		retme.append(thisjoint)
	return retme

def parse_pmx_softbodies(raw) -> list:
	# i don't plan to support v2.1 so I'm not gonna try to hard to understand the meaning of these data fields
	# this is mostly to consume the data so there are no bytes left over when done parsing a file to trigger warnings
	# note: this is also untested because i dont care about it lol
	i = core.my_unpack("i", raw)
	print("...# of softbodies       =", i)
	retme = []
	for d in range(i):
		(name_jp, name_en, shape, idx_mat, group, nocollide_mask, flags) = core.my_unpack("t t b" + IDX_MAT + "b H b", raw)
		# i should upack the flags here but idgaf
		(b_link_create_dist, num_clusters, total_mass, collision_marign, aerodynamics_model) = core.my_unpack("iiffi", raw)
		(vcf, dp, dg, lf, pr, vc, df, mt, rch, kch, sch, ah) = core.my_unpack("12f", raw)
		(srhr_cl, skhr_cl, sshr_cl, sr_splt_cl, sk_splt_cl, ss_splt_cl) = core.my_unpack("6f", raw)
		(v_it, p_it, d_it, c_it, mat_lst, mat_ast, mat_vst, num_anchors) = core.my_unpack("8i", raw)
		anchors_list = []
		for z in range(num_anchors):
			# (idx_rb, idx_vert, near_mode)
			this_anchor = core.my_unpack(IDX_RB + IDX_VERT + "b", raw)
			anchors_list.append(this_anchor)
		num_vertex_pin = core.my_unpack("i", raw)
		vertex_pin_list = []
		for z in range(num_vertex_pin):
			vertex_pin = core.my_unpack(IDX_VERT, raw)
			vertex_pin_list.append(vertex_pin)

		# assemble the data into list for returning
		thissoft = [name_jp, name_en, shape, idx_mat, group, nocollide_mask, flags,
					b_link_create_dist, num_clusters, total_mass, collision_marign, aerodynamics_model,
					vcf, dp, dg, lf, pr, vc, df, mt, rch, kch, sch, ah,
					srhr_cl, skhr_cl, sshr_cl, sr_splt_cl, sk_splt_cl, ss_splt_cl,
					v_it, p_it, d_it, c_it, mat_lst, mat_ast, mat_vst, anchors_list, vertex_pin_list]
		retme.append(thissoft)
	return retme




def read_pmx(pmx_filename: str) -> list:
	# assumes the calling function already verified correct file extension
	print("Begin reading PMX file '%s'" % pmx_filename)
	pmx_bytes = core.read_binfile_to_bytes(pmx_filename)
	print("...total size   = %sKB" % round(len(pmx_bytes) / 1024))
	print("Begin parsing PMX file '%s'" % pmx_filename)
	core.reset_unpack()
	A = parse_pmx_header(pmx_bytes)
	print("...PMX version  = v%s" % str(A[0]))
	print("...model name   = JP:'%s' / EN:'%s'" % (A[1], A[2]))
	B = parse_pmx_vertices(pmx_bytes)
	C = parse_pmx_surfaces(pmx_bytes)
	D = parse_pmx_textures(pmx_bytes)
	E = parse_pmx_materials(pmx_bytes)
	F = parse_pmx_bones(pmx_bytes)
	G = parse_pmx_morphs(pmx_bytes)
	H = parse_pmx_dispframes(pmx_bytes)
	I = parse_pmx_rigidbodies(pmx_bytes)
	J = parse_pmx_joints(pmx_bytes)
	if A[0] == 2.1:
		# if version==2.1, parse soft bodies
		K = parse_pmx_softbodies(pmx_bytes)
	else:
		# otherwise, dont
		K = []
	
	bytes_remain = len(pmx_bytes) - core.get_readfrom_byte()
	if bytes_remain != 0:
		print("Warning: finished parsing but %d bytes are left over at the tail!" % bytes_remain)
		print("The file may be corrupt or maybe it contains unknown/unsupported data formats")
		print(pmx_bytes[core.get_readfrom_byte():])
	print("Done parsing PMX file '%s'" % pmx_filename)
	return [A, B, C, D, E, F, G, H, I, J, K]




########################################################################################################################
# after all the funtions are defined, actually execute main()
if __name__ == '__main__':
	print("Nuthouse01 - 03/14/2020 - v3.01")
	print("")
	print("Specify a PMX file to attempt parsing (note that the output isn't actually used to do anything)")
	if DEBUG:
		input_filename = core.prompt_user_filename(".pmx")
		read_pmx(input_filename)
		core.pause_and_quit("Parsed without error")
	else:
		try:
			input_filename = core.prompt_user_filename(".pmx")
			read_pmx(input_filename)
			core.pause_and_quit("Parsed without error")
		except (KeyboardInterrupt, SystemExit):
			# this is normal and expected, do nothing and die normally
			pass
		except Exception as ee:
			# if an unexpected error occurs, catch it and print it and call core.pause_and_quit so the window stays open for a bit
			print(ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
