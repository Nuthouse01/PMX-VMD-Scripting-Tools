# Nuthouse01 - 06/08/2020 - v4.07
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################


# MASSIVE thanks to FelixJones on Github for already exporing & documenting the PMX file structure!
# https://gist.github.com/felixjones/f8a06bd48f9da9a4539f


# this file fully parses a PMX file and returns all of the data it contained, structured as a list of lists

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from . import nuthouse01_core as core
except ImportError as eee:
	try:
		import nuthouse01_core as core
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = None



# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False

# by default encode files with utf-16
# utf-8 might make files very slightly smaller but i haven't tested it
ENCODE_WITH_UTF8 = False


# for progress printouts, estimates of how long each section will take relative to the whole (when parsing/encoding)
PARSE_PERCENT_VERT = 0.60
PARSE_PERCENT_FACE = 0.15
PARSE_PERCENT_VERTFACE = PARSE_PERCENT_FACE + PARSE_PERCENT_VERT
PARSE_PERCENT_MORPH = 0.25
ENCODE_PERCENT_VERT = 0
ENCODE_PERCENT_FACE = 0
ENCODE_PERCENT_VERTFACE = 0
ENCODE_PERCENT_MORPH = 0

# flag to indicate whether more info is desired or not
PMX_MOREINFO = False


# how many extra vec4s each vertex has with it
ADDL_VERTEX_VEC4 = 0
# type used to store an index for each thing, these are concatenated to dynamically make format strings
IDX_VERT = "x"
IDX_TEX = "x"
IDX_MAT = "x"
IDX_BONE = "x"
IDX_MORPH = "x"
IDX_RB = "x"

"""
more info about "indexes":
vertex: if <=255, use ubyte = B = type 1
        if <=65535 use ushort = H = type 2
        if <=2147483647 use int = i = type 4
        else crash
others: if <=127, use byte = b = type 1
        if <=32767 use short = h = type 2
        if <=2147483647 use int = i = type 4
        else crash
TODO: for non-vertex, value of -1 means N/A
for vertex, N/A is not possible
"""



# return conventions: to handle fields that may or may not exist, many things are lists that don't strictly need to be
# if the data doesn't exist, it is an empty list
# that way the indices of other return fields stay the same even when a sometimes-field is missing

########################################################################################################################

def parse_pmx_header(raw: bytearray) -> list:
	##################################################################
	# HEADER INFO PARSING
	# collects some returnable data, mostly just sets globals
	# returnable: ver, name_jp, name_en, comment_jp, comment_en
	
	expectedmagic = bytearray([0x50, 0x4D, 0x58, 0x20])
	fmt_magic = "4s f b"
	(magic, ver, numglobal) = core.my_unpack(fmt_magic, raw)
	if magic != expectedmagic:
		core.MY_PRINT_FUNC("Warning: this file does not begin with the correct magic bytes. Maybe it was locked? Locks wont stop me!")
		if PMX_MOREINFO: core.MY_PRINT_FUNC("Expected '%s' but found '%s'" % (expectedmagic.hex(), magic.hex()))
	
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
		core.MY_PRINT_FUNC("unsupported encoding value", globalflags[0])
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

def parse_pmx_vertices(raw: bytearray) -> list:
	# first item is int, how many vertices
	i = core.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of verts            =", i)
	retme = []
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
			core.MY_PRINT_FUNC("invalid weight type for vertex", weighttype)
		# then there is one final float after the weight crap
		edgescale = core.my_unpack("f", raw)
		# display progress printouts
		core.print_progress_oneline(PARSE_PERCENT_VERT * d / i)

		# assemble all the info into a list for returning
		thisvert = [posX, posY, posZ, normX, normY, normZ, u, v, addl_vec4s, weighttype, weights, edgescale]
		retme.append(thisvert)
	return retme

def parse_pmx_surfaces(raw: bytearray) -> list:
	# surfaces is just another name for faces
	# first item is int, how many vertex indices there are, NOT the actual number of faces
	# each face is 3 vertex indices, so "i" will always be a multiple of 3
	i = core.my_unpack("i", raw)
	retme = []
	i = int(i / 3)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of faces            =", i)
	for d in range(i):
		# each entry is a group of 3 vertex indeces that make a face
		thisface = core.my_unpack("3" + IDX_VERT, raw)
		# display progress printouts
		core.print_progress_oneline(PARSE_PERCENT_VERT + (PARSE_PERCENT_FACE * d / i))
		retme.append(thisface)
	return retme

def parse_pmx_textures(raw: bytearray) -> list:
	# first item is int, how many textures
	i = core.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of textures         =", i)
	retme = []
	for d in range(i):
		filepath = core.my_unpack("t", raw)
		# print(filepath)
		retme.append(filepath)
	return retme

def parse_pmx_materials(raw: bytearray) -> list:
	# first item is int, how many materials
	i = core.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of materials        =", i)
	retme = []
	for d in range(i):
		(name_jp, name_en, diffR, diffG, diffB, diffA, specR, specG, specB, specpower) = core.my_unpack("t t 4f 4f", raw)
		# print(name_jp, name_en)
		(ambR, ambG, ambB, flags, edgeR, edgeG, edgeB, edgeA, edgescale, tex_idx) = core.my_unpack("3f B 5f" + IDX_TEX, raw)
		no_backface_culling = bool(flags & (1<<0)) # does this mean it is 2-sided?
		cast_ground_shadow  = bool(flags & (1<<1))
		cast_shadow         = bool(flags & (1<<2))
		receive_shadow      = bool(flags & (1<<3))
		use_edge            = bool(flags & (1<<4))
		vertex_color        = bool(flags & (1<<5)) # v2.1 only
		draw_as_points      = bool(flags & (1<<6)) # v2.1 only
		draw_as_lines       = bool(flags & (1<<7)) # v2.1 only
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

def parse_pmx_bones(raw: bytearray) -> list:
	# first item is int, how many bones
	i = core.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of bones            =", i)
	retme = []
	for d in range(i):
		(name_jp, name_en, posX, posY, posZ, parent_idx, deform_layer, flags1, flags2) = core.my_unpack("t t 3f" + IDX_BONE + "i 2B", raw)
		# print(name_jp, name_en)
		tail_type =              bool(flags1 & (1<<0))
		rotateable =             bool(flags1 & (1<<1))
		translateable =          bool(flags1 & (1<<2))
		visible =                bool(flags1 & (1<<3))
		enabled =                bool(flags1 & (1<<4))
		ik =                     bool(flags1 & (1<<5))
		inherit_rot =            bool(flags2 & (1<<0))
		inherit_trans =          bool(flags2 & (1<<1))
		fixed_axis =             bool(flags2 & (1<<2))
		local_axis =             bool(flags2 & (1<<3))
		deform_after_phys =      bool(flags2 & (1<<4))
		external_parent =        bool(flags2 & (1<<5))
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
			maybe_external_parent = core.my_unpack("i", raw)
		if ik:
			(ik_target, ik_loops, ik_anglelimit, num_ik_links) = core.my_unpack(IDX_BONE + "i f i", raw)
			maybe_ik = [ik_target, ik_loops, ik_anglelimit]
			ik_links = []
			for z in range(num_ik_links):
				(ik_link_idx, use_link_limits) = core.my_unpack(IDX_BONE + "b", raw)
				maybe_iklinks_limit = []
				if use_link_limits:
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
		thisbone = [name_jp, name_en, posX, posY, posZ, parent_idx, deform_layer, deform_after_phys, # 0-7
					rotateable, translateable, visible, enabled, # 8-11
					tail_type, maybe_tail, inherit_rot, inherit_trans, maybe_inherit, fixed_axis, maybe_fixed_axis, # 12-18
					local_axis, maybe_local_axis, external_parent, maybe_external_parent, ik, maybe_ik] # 19-24
		retme.append(thisbone)
	return retme

def parse_pmx_morphs(raw: bytearray) -> list:
	# first item is int, how many morphs
	i = core.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of morphs           =", i)
	retme = []
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
				# (vert_idx, A, B, C, D)
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
				core.MY_PRINT_FUNC("unsupported morph type value", morphtype)
			these_items.append(this_item)
		
		# display progress printouts
		core.print_progress_oneline(PARSE_PERCENT_VERTFACE + (PARSE_PERCENT_MORPH * d / i))
		# assemble the data into list for returning
		thismorph = [name_jp, name_en, panel, morphtype, these_items]
		retme.append(thismorph)
	return retme

def parse_pmx_dispframes(raw: bytearray) -> list:
	# first item is int, how many dispframes
	i = core.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of dispframes       =", i)
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

def parse_pmx_rigidbodies(raw: bytearray) -> list:
	# first item is int, how many rigidbodies
	i = core.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of rigidbodies      =", i)
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

def parse_pmx_joints(raw: bytearray) -> list:
	# first item is int, how many joints
	i = core.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of joints           =", i)
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

def parse_pmx_softbodies(raw: bytearray) -> list:
	# i don't plan to support v2.1 so I'm not gonna try to hard to understand the meaning of these data fields
	# this is mostly to consume the data so there are no bytes left over when done parsing a file to trigger warnings
	# note: this is also untested because i dont care about it lol
	i = core.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of softbodies       =", i)
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

########################################################################################################################

def encode_pmx_lookahead(all_nice: list) -> tuple:
	# takes the ENTIRE pmx list-form as its input, not juse one section
	# need to do some lookahead scanning before I can properly begin with the header and whatnot
	# specifically i need to get the "addl vec4 per vertex" and count the # of each type of thing
	max_addl_verts = 0
	for v in all_nice[1]:
		max_addl_verts = max(max_addl_verts, len(v[8]))
	num_verts = len(all_nice[1])
	num_tex = len(all_nice[3])
	num_mat = len(all_nice[4])
	num_bone = len(all_nice[5])
	num_morph = len(all_nice[6])
	num_rb = len(all_nice[8])
	num_joint = len(all_nice[9])
	retme = (max_addl_verts, num_verts, num_tex, num_mat, num_bone, num_morph, num_rb, num_joint)
	return retme

def encode_pmx_header(nice: list, lookahead: tuple) -> bytearray:
	expectedmagic = bytearray([0x50, 0x4D, 0x58, 0x20])
	fmt_magic = "4s f b"
	# note: hardcoding number of globals as 8 when the format is technically flexible
	numglobal = 8
	out = core.my_pack(fmt_magic, (expectedmagic, nice[0], numglobal))
	
	# now build the list of 8 global flags
	fmt_globals = str(numglobal) + "b"
	globalflags = [-1] * 8
	# byte 0: encoding
	if ENCODE_WITH_UTF8:
		core.set_encoding("utf_8")
		globalflags[0] = 1
	else:
		core.set_encoding("utf_16_le")
		globalflags[0] = 0
	# byte 1: additional vec4 per vertex
	global ADDL_VERTEX_VEC4
	ADDL_VERTEX_VEC4 = lookahead[0]
	globalflags[1] = lookahead[0]
	# bytes 2-7: data size to use for index references
	vertex_categorize = lambda x: 1 if x <= 255 else (2 if x <= 65535 else (4 if x <= 2147483647 else 0))
	other_categorize = lambda x: 1 if x <= 127 else (2 if x <= 32767 else (4 if x <= 2147483647 else 0))
	globalflags[2] = vertex_categorize(lookahead[1])
	for i in range(3, 8):
		globalflags[i] = other_categorize(lookahead[i - 1])
	global IDX_VERT, IDX_TEX, IDX_MAT, IDX_BONE, IDX_MORPH, IDX_RB
	vert_conv = {1: "B", 2: "H", 4: "i"}
	conv = {1: "b", 2: "h", 4: "i"}
	IDX_VERT = vert_conv[globalflags[2]]
	IDX_TEX = conv[globalflags[3]]
	IDX_MAT = conv[globalflags[4]]
	IDX_BONE = conv[globalflags[5]]
	IDX_MORPH = conv[globalflags[6]]
	IDX_RB = conv[globalflags[7]]
	out += core.my_pack(fmt_globals, globalflags)
	# finally handle the model names & comments
	# (name_jp, name_en, comment_jp, comment_en)
	out += core.my_pack("t t t t", nice[1:5])
	return out

def encode_pmx_vertices(nice: list) -> bytearray:
	# first item is int, how many vertices
	i = len(nice)
	out = core.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of verts            =", i)
	# [posX, posY, posZ, normX, normY, normZ, u, v, addl_vec4s, weighttype, weights, edgescale]
	for d, vert in enumerate(nice):
		# first, basic stuff
		# (posX, posY, posZ, normX, normY, normZ, u, v) = core.my_unpack("8f", raw)
		out += core.my_pack("8f", vert[0:8])
		# then, some number of vec4s (probably none)
		for z in range(ADDL_VERTEX_VEC4):
			try:
				this_vec4 = vert[8][z]
			except IndexError:
				this_vec4 = [0, 0, 0, 0]
			# this_vec4 = core.my_unpack("4f", raw) # already returns as a list of 4 floats, no need to unpack then repack
			out += core.my_pack("4f", this_vec4)
		
		weighttype = vert[9]
		weights = vert[10]
		out += core.my_pack("b", weighttype)
		if weighttype == 0:
			# BDEF1
			out += core.my_pack(IDX_BONE, weights)
		elif weighttype == 1:
			# BDEF2
			# (b1, b2, b1w) # already returns as a list of floats, no need to unpack then repack
			out += core.my_pack("2" + IDX_BONE + "f", weights)
		elif weighttype == 2:
			# BDEF4
			# (b1, b2, b3, b4, b1w, b2w, b3w, b4w) # already returns as a list of floats, no need to unpack then repack
			out += core.my_pack("4" + IDX_BONE + "4f", weights)
		elif weighttype == 3:
			# SDEF
			# (b1, b2, b1w, c1, c2, c3, r01, r02, r03, r11, r12, r13)
			out += core.my_pack("2" + IDX_BONE + "10f", weights)
		elif weighttype == 4:
			# it must be using QDEF, a type only for PMX v2.1 which I dont need to support so idgaf
			# (b1, b2, b3, b4, b1w, b2w, b3w, b4w)
			out += core.my_pack("4" + IDX_BONE + "4f", weights)
		else:
			core.MY_PRINT_FUNC("invalid weight type for vertex", weighttype)
		# then there is one final float after the weight crap
		out += core.my_pack("f", vert[11])
		# display progress printouts
		core.print_progress_oneline(ENCODE_PERCENT_VERT * d / i)
	return out

def encode_pmx_surfaces(nice: list) -> bytearray:
	# surfaces is just another name for faces
	# first item is int, how many !vertex indices! there are, NOT the actual number of faces
	# each face is 3 vertex indices
	i = len(nice)
	out = core.my_pack("i", i * 3)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of faces            =", i)
	for d, face in enumerate(nice):
		# each entry is a group of 3 vertex indeces that make a face
		out += core.my_pack("3" + IDX_VERT, face)
		# display progress printouts
		core.print_progress_oneline(ENCODE_PERCENT_VERT + (ENCODE_PERCENT_FACE * d / i))
	return out

def encode_pmx_textures(nice: list) -> bytearray:
	# first item is int, how many textures
	i = len(nice)
	out = core.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of textures         =", i)
	for d, filepath in enumerate(nice):
		out += core.my_pack("t", filepath)
	return out

def encode_pmx_materials(nice: list) -> bytearray:
	# first item is int, how many materials
	i = len(nice)
	out = core.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of materials        =", i)
	for d, mat in enumerate(nice):
		# (name_jp, name_en, diffR, diffG, diffB, diffA, specR, specG, specB, specpower, ambR, ambG, ambB)
		out += core.my_pack("t t 4f 4f 3f", mat[0:13])
		# (flaglist)
		flagsum = 0
		for pos, flag in enumerate(mat[13]):
			# reassemble the bits into a byte
			flagsum += 1 << pos if bool(flag) else 0
		out += core.my_pack("B", flagsum)
		# (edgeR, edgeG, edgeB, edgeA, edgescale, tex_idx)
		out += core.my_pack("5f" + IDX_TEX, mat[14:20])
		# (sph_idx, sph_mode, toon_mode)
		out += core.my_pack(IDX_TEX + "b b", mat[20:23])
		if mat[22] == 0:
			# toon is using a texture reference
			out += core.my_pack(IDX_TEX, mat[23])
		else:
			# toon is using one of the builtin toons, toon01.bmp thru toon10.bmp (values 0-9)
			out += core.my_pack("b", mat[23])
		# (comment)
		out += core.my_pack("t", mat[24])
		# (surface_ct) note: i structure the faces list into groups of 3 vertex indices, this is divided by 3 to match
		out += core.my_pack("i", mat[25] * 3)
	
	return out

def encode_pmx_bones(nice: list) -> bytearray:
	# first item is int, how many bones
	i = len(nice)
	out = core.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of bones            =", i)
	flag1_idx = [12, 8, 9, 10, 11, 23]
	flag2_idx = [14, 15, 17, 19, 7, 21]
	for d, bone in enumerate(nice):
		# (name_jp, name_en, posX, posY, posZ, parent_idx, deform_layer)
		out += core.my_pack("t t 3f" + IDX_BONE + "i", bone[0:7])
		# next are the two flag-bytes
		flagsum1 = flagsum2 = 0
		for pos, idx in enumerate(flag1_idx):
			# reassemble the bits into a byte
			flagsum1 += 1 << pos if bool(bone[idx]) else 0
		for pos, idx in enumerate(flag2_idx):
			# reassemble the bits into a byte
			flagsum2 += 1 << pos if bool(bone[idx]) else 0
		out += core.my_pack("2B", [flagsum1, flagsum2])
		
		if bone[12]:  # tail_type:
			# use index for bone its pointing at
			out += core.my_pack(IDX_BONE, bone[13])
		else:
			# use offset
			out += core.my_pack("3f", bone[13])
		if bone[14] or bone[15]:  # inherit_rot or inherit_trans:
			out += core.my_pack(IDX_BONE + "f", bone[16])
		if bone[17]:  # fixed_axis:
			# format is xyz obviously
			out += core.my_pack("3f", bone[18])
		if bone[19]:  # local_axis:
			# (xx, xy, xz, zx, zy, zz)
			out += core.my_pack("6f", core.flatten(bone[20]))
		if bone[21]:  # external_parent:
			out += core.my_pack("i", bone[22])
		
		if bone[23]:  # ik:
			# (ik_target, ik_loops, ik_anglelimit)
			out += core.my_pack(IDX_BONE + "i f", bone[24][0:3])
			# (num_ik_links)
			out += core.my_pack("i", len(bone[24][3]))
			for iklink in bone[24][3]:
				# (ik_link_idx)
				out += core.my_pack(IDX_BONE, iklink[0])
				if not iklink[1]:
					# (use_link_limits)
					out += core.my_pack("b", False)
				else:
					# (use_link_limits, limits)
					out += core.my_pack("b 6f", core.flatten([True, iklink[1]]))
	
	return out

def encode_pmx_morphs(nice: list) -> bytearray:
	# first item is int, how many morphs
	i = len(nice)
	out = core.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of morphs           =", i)
	for d, morph in enumerate(nice):
		# (name_jp, name_en, panel, morphtype)
		out += core.my_pack("t t b b", morph[0:4])
		# (itemcount)
		out += core.my_pack("i", len(morph[4]))
		morphtype = morph[3]
		for zzz in morph[4]:
			# for each morph in the group morph, or vertex in the vertex morph, or bone in the bone morph....
			# what to unpack varies on morph type, 9 possibilities + some for v2.1
			if morphtype == 0:
				# group
				# (morph_idx, influence) # already returns as a list, no need to unpack and repack
				out += core.my_pack(IDX_MORPH + "f", zzz)
			elif morphtype == 1:
				# vertex
				# (vert_idx, transX, transY, transZ)
				out += core.my_pack(IDX_VERT + "3f", zzz)
			elif morphtype == 2:
				# bone
				# (bone_idx, transX, transY, transZ, rotX, rotY, rotZ, rotW)
				out += core.my_pack(IDX_BONE + "3f 4f", zzz)
			elif 3 <= morphtype <= 7:
				# UV
				# what these values do depends on the UV layer they are affecting, but the docs dont say what...
				# oh well, i dont need to use them so i dont care :)
				# (vert_idx, A, B, C, D)
				out += core.my_pack(IDX_VERT + "4f", zzz)
			elif morphtype == 8:
				# material
				# (mat_idx, is_add, diffR, diffG, diffB, diffA, specR, specG, specB) = core.unpack(IDX_MAT+"b 4f 3f", raw)
				# (specpower, ambR, ambG, ambB, edgeR, edgeG, edgeB, edgeA, edgesize) = core.unpack("f 3f 4f f", raw)
				# (texR, texG, texB, texA, sphR, sphG, sphB, sphA, toonR, toonG, toonB, toonA) = core.unpack("4f 4f 4f", raw)
				out += core.my_pack(IDX_MAT + "b 4f 3f    f 3f 4f f    4f 4f 4f", zzz)
			elif morphtype == 9:
				# (2.1 only) flip
				# (morph_idx, influence)
				out += core.my_pack(IDX_MORPH + "f", zzz)
			elif morphtype == 10:
				# (2.1 only) impulse
				# (rb_idx, is_local, movX, movY, movZ, rotX, rotY, rotZ)
				out += core.my_pack(IDX_RB + "b 3f 3f", zzz)
			else:
				core.MY_PRINT_FUNC("unsupported morph type value", morphtype)
		
		# display progress printouts
		core.print_progress_oneline(ENCODE_PERCENT_VERTFACE + (ENCODE_PERCENT_MORPH * d / i))
	return out

def encode_pmx_dispframes(nice: list) -> bytearray:
	# first item is int, how many dispframes
	i = len(nice)
	out = core.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of dispframes       =", i)
	for d, frame in enumerate(nice):
		# (name_jp, name_en, is_special)
		out += core.my_pack("t t b", frame[0:3])
		# (itemcount)
		out += core.my_pack("i", len(frame[3]))
		for entry in frame[3]:
			# is_morph = entry[0]
			out += core.my_pack("b", entry[0])
			if entry[0]:
				out += core.my_pack(IDX_MORPH, entry[1])
			else:
				out += core.my_pack(IDX_BONE, entry[1])
	return out

def encode_pmx_rigidbodies(nice: list) -> bytearray:
	# first item is int, how many rigidbodies
	i = len(nice)
	out = core.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of rigidbodies      =", i)
	for d, body in enumerate(nice):
		# thisbody = [name_jp, name_en, bone_idx, group, nocollide_mask, shape, sizeX, sizeY, sizeZ, posX, posY, posZ,
		# 			rotX, rotY, rotZ, mass, move_damp, rot_damp, repel, friction, physmode]
		out += core.my_pack("t t" + IDX_BONE + "b H b 3f 3f 3f 5f b", body)
	
	return out

def encode_pmx_joints(nice: list) -> bytearray:
	# first item is int, how many joints
	i = len(nice)
	out = core.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of joints           =", i)
	for d, joint in enumerate(nice):
		# thisjoint = [name_jp, name_en, jointtype, rb1_idx, rb2_idx, posX, posY, posZ,
		# 			 rotX, rotY, rotZ, posminX, posminY, posminZ, posmaxX, posmaxY, posmaxZ,
		# 			 rotminX, rotminY, rotminZ, rotmaxX, rotmaxY, rotmaxZ,
		# 			 springposX, springposY, springposZ, springrotX, springrotY, springrotZ]
		out += core.my_pack("t t b 2" + IDX_RB + "3f 3f 3f 3f 3f 3f 3f 3f", joint)
	return out

def encode_pmx_softbodies(nice: list) -> bytearray:
	# i don't plan to support v2.1 so I'm not gonna try to hard to understand the meaning of these data fields
	# this is mostly to consume the data so there are no bytes left over when done parsing a file to trigger warnings
	# note: this is also untested because i dont care about it lol
	i = len(nice)
	out = core.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of softbodies       =", i)
	for d, soft in enumerate(nice):
		# (name_jp, name_en, shape, idx_mat, group, nocollide_mask, flags) = core.my_unpack("t t b" + IDX_MAT + "b H b", raw)
		# (b_link_create_dist, num_clusters, total_mass, collision_marign, aerodynamics_model) = core.my_unpack("iiffi", raw)
		# (vcf, dp, dg, lf, pr, vc, df, mt, rch, kch, sch, ah) = core.my_unpack("12f", raw)
		# (srhr_cl, skhr_cl, sshr_cl, sr_splt_cl, sk_splt_cl, ss_splt_cl) = core.my_unpack("6f", raw)
		# (v_it, p_it, d_it, c_it, mat_lst, mat_ast, mat_vst) = core.my_unpack("7i", raw)
		out += core.my_pack("t t b" + IDX_MAT + "b H b iiffi 12f 6f 7i", soft[0:37])
		# (num_anchors)
		out += core.my_pack("i", len(soft[37]))
		for anchor in soft[37]:
			# (idx_rb, idx_vert, near_mode)
			out += core.my_pack(IDX_RB + IDX_VERT + "b", anchor)
		# (num_pins)
		out += core.my_pack("i", len(soft[38]))
		for pin in soft[38]:
			out += core.my_pack(IDX_VERT, pin)
	
	return out


########################################################################################################################

def read_pmx(pmx_filename: str, moreinfo=False) -> list:
	global PMX_MOREINFO
	PMX_MOREINFO = moreinfo
	pmx_filename_clean = core.get_clean_basename(pmx_filename) + ".pmx"
	# assumes the calling function already verified correct file extension
	core.MY_PRINT_FUNC("Begin reading PMX file '%s'" % pmx_filename_clean)
	pmx_bytes = core.read_binfile_to_bytes(pmx_filename)
	core.MY_PRINT_FUNC("...total size   = %sKB" % round(len(pmx_bytes) / 1024))
	core.MY_PRINT_FUNC("Begin parsing PMX file '%s'" % pmx_filename_clean)
	core.reset_unpack()
	A = parse_pmx_header(pmx_bytes)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...PMX version  = v%s" % str(A[0]))
	core.MY_PRINT_FUNC("...model name   = JP:'%s' / EN:'%s'" % (A[1], A[2]))
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
		core.MY_PRINT_FUNC("Warning: finished parsing but %d bytes are left over at the tail!" % bytes_remain)
		core.MY_PRINT_FUNC("The file may be corrupt or maybe it contains unknown/unsupported data formats")
		core.MY_PRINT_FUNC(pmx_bytes[core.get_readfrom_byte():])
	core.MY_PRINT_FUNC("Done parsing PMX file '%s'" % pmx_filename_clean)
	return [A, B, C, D, E, F, G, H, I, J, K]


def write_pmx(pmx_filename: str, pmx: list, moreinfo=False) -> None:
	global PMX_MOREINFO
	PMX_MOREINFO = moreinfo
	pmx_filename_clean = core.get_clean_basename(pmx_filename) + ".pmx"
	# recives object 	(......)
	# assumes the calling function already verified correct file extension
	core.MY_PRINT_FUNC("Begin encoding PMX file '%s'" % pmx_filename_clean)

	if PMX_MOREINFO: core.MY_PRINT_FUNC("...PMX version  = v%s" % str(pmx[0][0]))
	core.MY_PRINT_FUNC("...model name   = JP:'%s' / EN:'%s'" % (pmx[0][1], pmx[0][2]))
	
	# arg "pmx" is the same structure created by "read_pmx()"
	# assume the object is perfect, no sanity-checking needed
	output_bytes = bytearray()
	global ENCODE_PERCENT_VERT
	global ENCODE_PERCENT_FACE
	global ENCODE_PERCENT_VERTFACE
	global ENCODE_PERCENT_MORPH
	
	# total progress = verts + faces/3 + sum of morphs/3
	ALLPROGRESSIZE = len(pmx[1]) + len(pmx[2])/4 + sum([len(m[4]) for m in pmx[6]])/2
	ENCODE_PERCENT_VERT = len(pmx[1]) / ALLPROGRESSIZE
	ENCODE_PERCENT_FACE = (len(pmx[2]) / 4) / ALLPROGRESSIZE
	ENCODE_PERCENT_VERTFACE = ENCODE_PERCENT_VERT + ENCODE_PERCENT_FACE
	ENCODE_PERCENT_MORPH = (sum([len(m[4]) for m in pmx[6]]) / 2) / ALLPROGRESSIZE
	
	lookahead = encode_pmx_lookahead(pmx)
	output_bytes += encode_pmx_header(pmx[0], lookahead)
	output_bytes += encode_pmx_vertices(pmx[1])
	output_bytes += encode_pmx_surfaces(pmx[2])
	output_bytes += encode_pmx_textures(pmx[3])
	output_bytes += encode_pmx_materials(pmx[4])
	output_bytes += encode_pmx_bones(pmx[5])
	output_bytes += encode_pmx_morphs(pmx[6])
	output_bytes += encode_pmx_dispframes(pmx[7])
	output_bytes += encode_pmx_rigidbodies(pmx[8])
	output_bytes += encode_pmx_joints(pmx[9])
	if pmx[0][0] == 2.1:
		# if version==2.1, parse soft bodies
		output_bytes += encode_pmx_softbodies(pmx[10])

	# done encoding!!

	core.MY_PRINT_FUNC("Begin writing PMX file '%s'" % pmx_filename_clean)
	core.MY_PRINT_FUNC("...total size   = %sKB" % round(len(output_bytes) / 1024))
	core.write_bytes_to_binfile(pmx_filename, output_bytes)
	core.MY_PRINT_FUNC("Done writing PMX file '%s'" % pmx_filename_clean)
	# done with everything!
	return None


########################################################################################################################
def main():
	core.MY_PRINT_FUNC("Specify a PMX file to attempt parsing and writeback")
	input_filename = core.prompt_user_filename(".pmx")
	# input_filename = "pmxtest.pmx"
	Z = read_pmx(input_filename)
	write_pmx("____pmxparser_selftest_DELETEME.pmx", Z)
	ZZ = read_pmx("____pmxparser_selftest_DELETEME.pmx")
	core.MY_PRINT_FUNC("")
	bb = core.read_binfile_to_bytes(input_filename)
	bb2 = core.read_binfile_to_bytes("____pmxparser_selftest_DELETEME.pmx")
	core.MY_PRINT_FUNC("Is the binary EXACTLY identical to original?", bb == bb2)
	exact_result = Z == ZZ
	core.MY_PRINT_FUNC("Is the readback EXACTLY identical to original?", exact_result)
	if not exact_result:
		fuzzy_result = core.recursively_compare(Z, ZZ)
		core.MY_PRINT_FUNC("Is the readback ALMOST identical to the original?", not fuzzy_result)
		core.MY_PRINT_FUNC("Max difference between two floats:", core.MAXDIFFERENCE)
		core.MY_PRINT_FUNC("Number of floats that exceed reasonable threshold 0.0005:", fuzzy_result)
	core.pause_and_quit("Parsed without error")

########################################################################################################################
# after all the funtions are defined, actually execute main()
if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 06/08/2020 - v4.07")
	if DEBUG:
		main()
	else:
		try:
			main()
		except (KeyboardInterrupt, SystemExit):
			# this is normal and expected, do nothing and die normally
			pass
		except Exception as ee:
			# if an unexpected error occurs, catch it and print it and call core.pause_and_quit so the window stays open for a bit
			core.MY_PRINT_FUNC(ee.__class__.__name__, ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
