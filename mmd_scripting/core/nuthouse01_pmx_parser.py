import math
import time
from typing import List, Tuple

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_io as io
import mmd_scripting.core.nuthouse01_packer as pack
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.03 - 8/9/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# this file fully parses a PMX file and returns all of the data it contained as a custom object type

# MASSIVE thanks to FelixJones on Github for already exporing & documenting the PMX file structure!
# https://gist.github.com/felixjones/f8a06bd48f9da9a4539f


# by default encode files with utf-16
# utf-8 might make files very slightly smaller but i haven't tested it
ENCODE_WITH_UTF8 = False

# flag to indicate whether more info is desired or not
PMX_MOREINFO = False

# parsing progress printouts: depend on the actual number of bytes processed, very accurate & linear
# encoding progress printouts: manually estimate how long stuff will take and then track my progress against that
# DONT TOUCH THESE TWO
ENCODE_PERCENTPOINT_WEIGHTS = {}
ENCODE_PERCENTPOINT_SOFAR = 0

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
for non-vertex, value of -1 means N/A
for vertex, N/A is not possible
"""

# this relates the 'index' to the displayed path/name for each builtin toon
BUILTIN_TOON_DICT = {
	"toon01.bmp": 0,
	"toon02.bmp": 1,
	"toon03.bmp": 2,
	"toon04.bmp": 3,
	"toon05.bmp": 4,
	"toon06.bmp": 5,
	"toon07.bmp": 6,
	"toon08.bmp": 7,
	"toon09.bmp": 8,
	"toon10.bmp": 9,
}

BUILTIN_TOON_DICT_REVERSE = {v: k for k, v in BUILTIN_TOON_DICT.items()}

# return conventions: to handle fields that may or may not exist, many things are lists that don't strictly need to be
# if the data doesn't exist, it is an empty list
# that way the indices of other return fields stay the same even when a sometimes-field is missing

########################################################################################################################

def parse_pmx_header(raw: bytearray) -> pmxstruct.PmxHeader:
	##################################################################
	# HEADER INFO PARSING
	# collects some returnable data, mostly just sets globals
	# returnable: ver, name_jp, name_en, comment_jp, comment_en
	
	expectedmagic = bytearray("PMX ", "utf-8")
	fmt_magic = "4s f b"
	(magic, ver, numglobal) = pack.my_unpack(fmt_magic, raw)
	if magic != expectedmagic:
		core.MY_PRINT_FUNC("WARNING: This file does not begin with the correct magic bytes. Maybe it was locked? Locks wont stop me!")
		core.MY_PRINT_FUNC("         Expected '%s' but found '%s'" % (expectedmagic.hex(), magic.hex()))
	
	# hotfix: round the version info so it matches friendly numbers like 2.1
	ver = round(ver, 5)
	
	# only first 8 bytes have known uses
	# more bytes have no known purpose but need to be accounted for anyway
	if numglobal != 8:
		core.MY_PRINT_FUNC("WARNING: This PMX has '%d' global flags, this behavior is undefined!!!" % numglobal)
		core.MY_PRINT_FUNC("         Technically the format supports any number of global flags but I only know the meanings of the first 8")
	fmt_globals = str(numglobal) + "b"
	globalflags = pack.my_unpack(fmt_globals, raw)	# this actually returns a tuple of ints, which works just fine, dont touch it
	if numglobal != 8:
		core.MY_PRINT_FUNC("         Global flags = %s" % str(globalflags))
	
	# byte 0: encoding
	if globalflags[0] == 0:   pack.set_encoding("utf_16_le")
	elif globalflags[0] == 1: pack.set_encoding("utf_8")
	else:                     raise RuntimeError("unsupported encoding value '%d'" % globalflags[0])
	
	# byte 1: additional vec4 per vertex
	# store this in a global so it can be more easily passed to the vertex section
	global ADDL_VERTEX_VEC4
	ADDL_VERTEX_VEC4 = globalflags[1]
	
	# bytes 2-7: data size to use for index references
	# store these in globals as well because passing them around as arguments would be annoying
	# see comment around line 50 for more info
	global IDX_VERT, IDX_TEX, IDX_MAT, IDX_BONE, IDX_MORPH, IDX_RB
	vert_conv = {1:"B", 2:"H", 4:"i"}
	IDX_VERT  = vert_conv[globalflags[2]]
	conv =      {1:"b", 2:"h", 4:"i"}
	IDX_TEX   = conv[globalflags[3]]
	IDX_MAT   = conv[globalflags[4]]
	IDX_BONE  = conv[globalflags[5]]
	IDX_MORPH = conv[globalflags[6]]
	IDX_RB    = conv[globalflags[7]]
	
	# finally handle the model names & comments
	# (name_jp, name_en, comment_jp, comment_en) = pack.my_unpack("t t t t", raw)
	name_jp = pack.my_string_unpack(raw)
	name_en = pack.my_string_unpack(raw)
	comment_jp = pack.my_string_unpack(raw)
	comment_en = pack.my_string_unpack(raw)
	
	# assemble all the info into a struct for returning
	return pmxstruct.PmxHeader(ver=ver,
							   name_jp=name_jp, name_en=name_en,
							   comment_jp=comment_jp, comment_en=comment_en)
	# return retme

def parse_pmx_vertices(raw: bytearray) -> List[pmxstruct.PmxVertex]:
	# first item is int, how many vertices
	i = pack.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of verts            =", i)
	retme = []
	bdef1_fmt = IDX_BONE
	bdef2_fmt = "2%s f" % IDX_BONE
	bdef4_fmt = "4%s 4f" % IDX_BONE
	sdef_fmt =  "2%s 10f" % IDX_BONE
	qdef_fmt =  bdef4_fmt
	
	def weightbinary_to_weightpairs(wtype: pmxstruct.WeightMode, w_i: List[float]) -> List[List[float]]:
		# convert the list of weights as stored in binary file into a more reasonable list of bone-weight pairs
		# this comes out of the parser so it should be perfect, no need to error-check the input
		w_o = []
		if wtype == pmxstruct.WeightMode.BDEF1:
			# 0 = BDEF1 = [b1]
			w_o = [[w_i[0], 1.0],
				  ]
		elif wtype in (pmxstruct.WeightMode.BDEF2, pmxstruct.WeightMode.SDEF):
			# 1 = BDEF2 = [b1, b2, b1w]
			# 3 = sdef =  [b1, b2, b1w] + weight_sdef = [[c1, c2, c3], [r01, r02, r03], [r11, r12, r13]]
			w_o = [[w_i[0], w_i[2]],
				  [w_i[1], 1.0 - w_i[2]],
				  ]
		elif wtype in (pmxstruct.WeightMode.BDEF4, pmxstruct.WeightMode.QDEF):
			# 2 = BDEF4 = [b1, b2, b3, b4, b1w, b2w, b3w, b4w]
			# 4 = qdef =  [b1, b2, b3, b4, b1w, b2w, b3w, b4w]  (only in pmx v2.1)
			w_o = [[w_i[0], w_i[4]],
				  [w_i[1], w_i[5]],
				  [w_i[2], w_i[6]],
				  [w_i[3], w_i[7]],
				  ]
		return w_o
	
	for d in range(i):
		# first, basic stuff
		(posX, posY, posZ, normX, normY, normZ, u, v) = pack.my_unpack("8f", raw)
		# then, some number of vec4s (probably none)
		addl_vec4s = []
		for z in range(ADDL_VERTEX_VEC4):
			this_vec4 = pack.my_unpack("4f", raw) # already returns as a list of 4 floats, no need to unpack then repack
			addl_vec4s.append(this_vec4)
		weighttype_int = pack.my_unpack("b", raw)
		weighttype = pmxstruct.WeightMode(weighttype_int)
		weights = []
		weight_sdef = []
		if weighttype == pmxstruct.WeightMode.BDEF1:
			# BDEF1
			b1 = pack.my_unpack(bdef1_fmt, raw)
			weights = [b1]
		elif weighttype == pmxstruct.WeightMode.BDEF2:
			# BDEF2
			#(b1, b2, b1w) # already returns as a list of floats, no need to unpack then repack
			weights = pack.my_unpack(bdef2_fmt, raw)
		elif weighttype == pmxstruct.WeightMode.BDEF4:
			# BDEF4
			#(b1, b2, b3, b4, b1w, b2w, b3w, b4w) # already returns as a list of floats, no need to unpack then repack
			weights = pack.my_unpack(bdef4_fmt, raw)
		elif weighttype == pmxstruct.WeightMode.SDEF:
			# SDEF
			#(b1, b2, b1w, c1, c2, c3, r01, r02, r03, r11, r12, r13)
			(b1, b2, b1w, c1, c2, c3, r01, r02, r03, r11, r12, r13) = pack.my_unpack(sdef_fmt, raw)
			weights = [b1, b2, b1w]
			weight_sdef = [[c1, c2, c3], [r01, r02, r03], [r11, r12, r13]]
		elif weighttype == pmxstruct.WeightMode.QDEF:
			# it must be using QDEF, a type only for PMX v2.1 which I dont need to support so idgaf
			# (b1, b2, b3, b4, b1w, b2w, b3w, b4w)
			weights = pack.my_unpack(qdef_fmt, raw)
		# else:
		# 	core.MY_PRINT_FUNC("invalid weight type for vertex", weighttype)
		# then there is one final float after the weight crap
		edgescale = pack.my_unpack("f", raw)
		
		weight_pairs = weightbinary_to_weightpairs(weighttype, weights)

		# display progress printouts
		core.print_progress_oneline(pack.UNPACKER_READFROM_BYTE / len(raw))
		# assemble all the info into a struct for returning
		thisvert = pmxstruct.PmxVertex(pos=[posX, posY, posZ], norm=[normX, normY, normZ], uv=[u, v],
									   weighttype=weighttype, weight=weight_pairs, weight_sdef=weight_sdef,
									   edgescale=edgescale, addl_vec4s=addl_vec4s)
		
		retme.append(thisvert)
	return retme

def parse_pmx_surfaces(raw: bytearray) -> List[List[int]]:
	# surfaces is just another name for faces
	# first item is int, how many vertex indices there are, NOT the actual number of faces
	# each face is 3 vertex indices, so "i" will always be a multiple of 3
	i = pack.my_unpack("i", raw)
	retme = []
	i = int(i / 3)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of faces            =", i)
	for d in range(i):
		# each entry is a group of 3 vertex indeces that make a face
		thisface = pack.my_unpack("3" + IDX_VERT, raw)
		# display progress printouts
		core.print_progress_oneline(pack.UNPACKER_READFROM_BYTE / len(raw))
		retme.append(thisface)
	return retme

def parse_pmx_textures(raw: bytearray) -> List[str]:
	# first item is int, how many textures
	i = pack.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of textures         =", i)
	retme = []
	for d in range(i):
		filepath = pack.my_string_unpack(raw)
		# print(filepath)
		retme.append(filepath)
	return retme

def parse_pmx_materials(raw: bytearray, textures: List[str]) -> List[pmxstruct.PmxMaterial]:
	# first item is int, how many materials
	i = pack.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of materials        =", i)
	retme = []
	for d in range(i):
		name_jp = pack.my_string_unpack(raw)
		name_en = pack.my_string_unpack(raw)
		# print(name_jp, name_en)
		(diffR, diffG, diffB, diffA, specR, specG, specB, specpower) = pack.my_unpack("4f 4f", raw)
		(ambR, ambG, ambB, flags, edgeR, edgeG, edgeB, edgeA, edgescale, tex_idx) = pack.my_unpack("3f B 5f" + IDX_TEX, raw)
		(sph_idx, sph_mode_int, builtin_toon) = pack.my_unpack(IDX_TEX + "b b", raw)
		if builtin_toon == 0:
			# toon is using a texture reference
			toon_idx = pack.my_unpack(IDX_TEX, raw)
		else:
			# toon is using one of the builtin toons, toon01.bmp thru toon10.bmp (values 0-9)
			toon_idx = pack.my_unpack("b", raw)
		comment = pack.my_string_unpack(raw)
		surface_ct = pack.my_unpack("i", raw)
		# note: i structure the faces list into groups of 3 vertex indices, this is divided by 3 to match
		faces_ct = int(surface_ct / 3)
		sph_mode = pmxstruct.SphMode(sph_mode_int)
		matflags = pmxstruct.MaterialFlags(flags)
		
		# convert tex_idx/sph_idx/toon_idx into the respective strings
		try:
			if tex_idx == -1:  tex_path = ""
			else:              tex_path = textures[tex_idx]
			if sph_idx == -1:  sph_path = ""
			else:              sph_path = textures[sph_idx]
			if toon_idx == -1: toon_path = ""
			elif builtin_toon: toon_path = BUILTIN_TOON_DICT_REVERSE[toon_idx]  # using a builtin toon
			else:              toon_path = textures[toon_idx]  # using a nonstandard toon
		except (IndexError, KeyError):
			core.MY_PRINT_FUNC("ERROR: material texture references are busted yo")
			raise

		# assemble all the data into a struct for returning
		thismat = pmxstruct.PmxMaterial(name_jp=name_jp, name_en=name_en, diffRGB=[diffR, diffG, diffB],
										specRGB=[specR, specG, specB], ambRGB=[ambR, ambG, ambB], alpha=diffA,
										specpower=specpower, edgeRGB=[edgeR, edgeG, edgeB], edgealpha=edgeA,
										edgesize=edgescale, tex_path=tex_path, toon_path=toon_path, sph_path=sph_path,
										sph_mode=sph_mode, comment=comment, faces_ct=faces_ct, matflags=matflags)
		
		retme.append(thismat)
	return retme

def parse_pmx_bones(raw: bytearray) -> List[pmxstruct.PmxBone]:
	# first item is int, how many bones
	i = pack.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of bones            =", i)
	retme = []
	for d in range(i):
		name_jp = pack.my_string_unpack(raw)
		name_en = pack.my_string_unpack(raw)
		(posX, posY, posZ, parent_idx, deform_layer, flags1, flags2) = pack.my_unpack("3f" + IDX_BONE + "i 2B", raw)
		# print(name_jp, name_en)
		tail_usebonelink =       bool(flags1 & (1<<0))
		rotateable =             bool(flags1 & (1<<1))
		translateable =          bool(flags1 & (1<<2))
		visible =                bool(flags1 & (1<<3))
		enabled =                bool(flags1 & (1<<4))
		ik =                     bool(flags1 & (1<<5))
		inherit_rot =            bool(flags2 & (1<<0))
		inherit_trans =          bool(flags2 & (1<<1))
		has_fixedaxis =          bool(flags2 & (1<<2))
		has_localaxis =          bool(flags2 & (1<<3))
		deform_after_phys =      bool(flags2 & (1<<4))
		has_external_parent =    bool(flags2 & (1<<5))
		# important for structure: tail type, inherit, fixed axis, local axis, ext parent, IK
		external_parent = None
		inherit_parent = inherit_influence = None
		fixedaxis = None
		local_axis_x_xyz = local_axis_z_xyz = None
		ik_target = ik_loops = ik_anglelimit = ik_links = None
		if tail_usebonelink:  # use index for bone its pointing at
			tail = pack.my_unpack(IDX_BONE, raw)
		else:  # use offset
			tail = pack.my_unpack("3f", raw)
		if inherit_rot or inherit_trans:
			(inherit_parent, inherit_influence) = pack.my_unpack(IDX_BONE + "f", raw)
		if has_fixedaxis:
			# format is xyz obviously
			fixedaxis = pack.my_unpack("3f", raw)
		if has_localaxis:
			(xx, xy, xz, zx, zy, zz) = pack.my_unpack("3f 3f", raw)
			local_axis_x_xyz = [xx, xy, xz]
			local_axis_z_xyz = [zx, zy, zz]
		if has_external_parent:
			external_parent = pack.my_unpack("i", raw)
		if ik:
			(ik_target, ik_loops, ik_anglelimit, num_ik_links) = pack.my_unpack(IDX_BONE + "i f i", raw)
			# note: ik angle comes in as radians, i want to represent it as degrees
			ik_anglelimit = math.degrees(ik_anglelimit)
			ik_links = []
			for z in range(num_ik_links):
				(ik_link_idx, use_link_limits) = pack.my_unpack(IDX_BONE + "b", raw)
				if use_link_limits:
					(minX, minY, minZ, maxX, maxY, maxZ) = pack.my_unpack("3f 3f", raw)
					# note: these vals come in as XYZXYZ radians! must convert to degrees
					link = pmxstruct.PmxBoneIkLink(idx=ik_link_idx,
												   limit_min=[math.degrees(minX), math.degrees(minY), math.degrees(minZ)],
												   limit_max=[math.degrees(maxX), math.degrees(maxY), math.degrees(maxZ)])
				else:
					link = pmxstruct.PmxBoneIkLink(idx=ik_link_idx)
				ik_links.append(link)
				
		# assemble all the info into a struct for returning
		thisbone = pmxstruct.PmxBone(
			name_jp=name_jp, name_en=name_en, pos=[posX, posY, posZ], parent_idx=parent_idx,
			deform_layer=deform_layer, deform_after_phys=deform_after_phys,
			has_rotate=rotateable, has_translate=translateable, has_visible=visible, has_enabled=enabled,
			# all ik stuff
			has_ik=ik, ik_target_idx=ik_target, ik_numloops=ik_loops, ik_angle=ik_anglelimit, ik_links=ik_links,
			# all tail stuff
			tail_usebonelink=tail_usebonelink, tail=tail,
			# all partial-inherit stuff
			inherit_rot=inherit_rot, inherit_trans=inherit_trans, inherit_ratio=inherit_influence, inherit_parent_idx=inherit_parent,
			# all fixed-axis stuff
			has_fixedaxis=has_fixedaxis, fixedaxis=fixedaxis,
			# all local-axis stuff
			has_localaxis=has_localaxis, localaxis_x=local_axis_x_xyz, localaxis_z=local_axis_z_xyz,
			# all external parent stuff
			has_externalparent=has_external_parent, externalparent=external_parent)
		
		retme.append(thisbone)
	return retme

def parse_pmx_morphs(raw: bytearray) -> List[pmxstruct.PmxMorph]:
	# first item is int, how many morphs
	i = pack.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of morphs           =", i)
	retme = []
	for d in range(i):
		name_jp = pack.my_string_unpack(raw)
		name_en = pack.my_string_unpack(raw)
		(panel_int, morphtype_int, itemcount) = pack.my_unpack("b b i", raw)
		morphtype = pmxstruct.MorphType(morphtype_int)
		panel = pmxstruct.MorphPanel(panel_int)
		# print(name_jp, name_en)
		these_items = []
		# what to unpack varies on morph type, 9 possibilities + some for v2.1
		if morphtype == pmxstruct.MorphType.GROUP:
			# group
			for z in range(itemcount):
				(morph_idx, influence) = pack.my_unpack(IDX_MORPH + "f", raw)
				item = pmxstruct.PmxMorphItemGroup(morph_idx=morph_idx, value=influence)
				these_items.append(item)
		elif morphtype == pmxstruct.MorphType.VERTEX:
			# vertex
			for z in range(itemcount):
				(vert_idx, transX, transY, transZ) = pack.my_unpack(IDX_VERT + "3f", raw)
				item = pmxstruct.PmxMorphItemVertex(vert_idx=vert_idx, move=[transX, transY, transZ])
				these_items.append(item)
		elif morphtype == pmxstruct.MorphType.BONE:
			# bone
			for z in range(itemcount):
				(bone_idx, transX, transY, transZ, rotqX, rotqY, rotqZ, rotqW) = pack.my_unpack(IDX_BONE + "3f 4f", raw)
				rotX, rotY, rotZ = core.quaternion_to_euler([rotqW, rotqX, rotqY, rotqZ])
				item = pmxstruct.PmxMorphItemBone(bone_idx=bone_idx, move=[transX, transY, transZ], rot=[rotX, rotY, rotZ])
				these_items.append(item)
		elif morphtype in (pmxstruct.MorphType.UV,
						   pmxstruct.MorphType.UV_EXT1,
						   pmxstruct.MorphType.UV_EXT2,
						   pmxstruct.MorphType.UV_EXT3,
						   pmxstruct.MorphType.UV_EXT4):
			# UV
			# what these values do depends on the UV layer they are affecting, but the docs dont say what...
			# oh well, i dont need to use them so i dont care :)
			for z in range(itemcount):
				(vert_idx, A, B, C, D) = pack.my_unpack(IDX_VERT + "4f", raw)
				item = pmxstruct.PmxMorphItemUV(vert_idx=vert_idx, move=[A,B,C,D])
				these_items.append(item)
		elif morphtype == pmxstruct.MorphType.MATERIAL:
			# material
			# this_item = core.my_unpack(IDX_MAT + "b 4f 3f    f 3f 4f f    4f 4f 4f", raw)
			for z in range(itemcount):
				(mat_idx, is_add, diffR, diffG, diffB, diffA, specR, specG, specB) = pack.my_unpack(IDX_MAT + "b 4f 3f", raw)
				(specpower, ambR, ambG, ambB, edgeR, edgeG, edgeB, edgeA, edgesize) = pack.my_unpack("f 3f 4f f", raw)
				(texR, texG, texB, texA, sphR, sphG, sphB, sphA, toonR, toonG, toonB, toonA) = pack.my_unpack("4f 4f 4f", raw)
				item = pmxstruct.PmxMorphItemMaterial(
					mat_idx=mat_idx, is_add=is_add, alpha=diffA, specpower=specpower,
					diffRGB=[diffR, diffG, diffB], specRGB=[specR, specG, specB], ambRGB=[ambR, ambG, ambB],
					edgeRGB=[edgeR, edgeG, edgeB], edgealpha=edgeA, edgesize=edgesize,
					texRGBA=[texR, texG, texB, texA], sphRGBA=[sphR, sphG, sphB, sphA], toonRGBA=[toonR, toonG, toonB, toonA]
				)
				these_items.append(item)
		elif morphtype == pmxstruct.MorphType.FLIP:
			# (2.1 only) flip
			for z in range(itemcount):
				(morph_idx, influence) = pack.my_unpack(IDX_MORPH + "f", raw)
				item = pmxstruct.PmxMorphItemFlip(morph_idx=morph_idx, value=influence)
				these_items.append(item)
		elif morphtype == pmxstruct.MorphType.IMPULSE:
			# (2.1 only) impulse
			for z in range(itemcount):
				(rb_idx, is_local, movX, movY, movZ, rotX, rotY, rotZ) = pack.my_unpack(IDX_RB + "b 3f 3f", raw)
				item = pmxstruct.PmxMorphItemImpulse(rb_idx=rb_idx, is_local=is_local,
													 move=[movX, movY, movZ], rot=[rotX, rotY, rotZ])
				these_items.append(item)
		else:
			raise RuntimeError("unsupported morph type value", morphtype)
		
		# display progress printouts
		core.print_progress_oneline(pack.UNPACKER_READFROM_BYTE / len(raw))
		# assemble the data into struct for returning
		thismorph = pmxstruct.PmxMorph(name_jp=name_jp, name_en=name_en, panel=panel, morphtype=morphtype, items=these_items)
		retme.append(thismorph)
	return retme

def parse_pmx_dispframes(raw: bytearray) -> List[pmxstruct.PmxFrame]:
	# first item is int, how many dispframes
	i = pack.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of dispframes       =", i)
	retme = []
	for d in range(i):
		name_jp = pack.my_string_unpack(raw)
		name_en = pack.my_string_unpack(raw)
		(is_special, itemcount) = pack.my_unpack("b i", raw)
		# print(name_jp, name_en)
		these_items = []
		for z in range(itemcount):
			is_morph = pack.my_unpack("b", raw)
			if is_morph: idx = pack.my_unpack(IDX_MORPH, raw)
			else:        idx = pack.my_unpack(IDX_BONE, raw)
			this_item = pmxstruct.PmxFrameItem(is_morph=is_morph, idx=idx)
			these_items.append(this_item)
		# assemble the data into struct for returning
		thisframe = pmxstruct.PmxFrame(name_jp=name_jp, name_en=name_en, is_special=is_special, items=these_items)
		retme.append(thisframe)
	return retme

def parse_pmx_rigidbodies(raw: bytearray) -> List[pmxstruct.PmxRigidBody]:
	# first item is int, how many rigidbodies
	i = pack.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of rigidbodies      =", i)
	retme = []
	for d in range(i):
		name_jp = pack.my_string_unpack(raw)
		name_en = pack.my_string_unpack(raw)
		(bone_idx, group, collide_mask, shape_int) = pack.my_unpack(IDX_BONE + "b H b", raw)
		shape = pmxstruct.RigidBodyShape(shape_int)
		# print(name_jp, name_en)
		# shape: 0=sphere, 1=box, 2=capsule
		(sizeX, sizeY, sizeZ, posX, posY, posZ, rotX, rotY, rotZ) = pack.my_unpack("3f 3f 3f", raw)
		(mass, move_damp, rot_damp, repel, friction, physmode_int) = pack.my_unpack("5f b", raw)
		physmode = pmxstruct.RigidBodyPhysMode(physmode_int)
		# physmode: 0=follow bone, 1=physics, 2=physics rotate only (pivot on bone)
		
		# note: rotation comes in as XYZ radians, must convert to degrees for my struct
		rot = [math.degrees(rotX), math.degrees(rotY), math.degrees(rotZ)]
		
		# NOTE: group & nocollide_set are [1-16], same as displayed in PMXE!
		group += 1
		# convert collide_mask (byte with 1 bit for each group it should collide with) to nocollide_set
		nocollide_set = set()
		for a in range(16):
			# if the bit is NOT set in collide_mask, then add it to the no-collide set.
			if not (1<<a) & collide_mask:
				# add it to the set & unset that bit in the mask
				nocollide_set.add(a+1)
		
		# display progress printouts
		core.print_progress_oneline(pack.UNPACKER_READFROM_BYTE / len(raw))
		# assemble the data into struct for returning
		thisbody = pmxstruct.PmxRigidBody(name_jp=name_jp, name_en=name_en, bone_idx=bone_idx, pos=[posX, posY, posZ],
										  rot=rot, size=[sizeX, sizeY, sizeZ], shape=shape, group=group,
										  nocollide_set=nocollide_set, phys_mode=physmode, phys_mass=mass,
										  phys_move_damp=move_damp, phys_rot_damp=rot_damp, phys_repel=repel,
										  phys_friction=friction)
		retme.append(thisbody)
	return retme

def parse_pmx_joints(raw: bytearray) -> List[pmxstruct.PmxJoint]:
	# first item is int, how many joints
	i = pack.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of joints           =", i)
	retme = []
	for d in range(i):
		name_jp = pack.my_string_unpack(raw)
		name_en = pack.my_string_unpack(raw)
		(jointtype_int, rb1_idx, rb2_idx, posX, posY, posZ) = pack.my_unpack("b 2" + IDX_RB + "3f", raw)
		# jointtype: 0=spring6DOF, all others are v2.1 only!!!! 1=6dof, 2=p2p, 3=conetwist, 4=slider, 5=hinge
		jointtype = pmxstruct.JointType(jointtype_int)
		# print(name_jp, name_en)
		(rotX, rotY, rotZ, posminX, posminY, posminZ, posmaxX, posmaxY, posmaxZ) = pack.my_unpack("3f 3f 3f", raw)
		(rotminX, rotminY, rotminZ, rotmaxX, rotmaxY, rotmaxZ) = pack.my_unpack("3f 3f", raw)
		(springposX, springposY, springposZ, springrotX, springrotY, springrotZ) = pack.my_unpack("3f 3f", raw)
		
		# note: rot/rotmin/rotmax all come in as XYZ radians, must convert to degrees for my struct
		rot = [math.degrees(rotX), math.degrees(rotY), math.degrees(rotZ)]
		rotmin = [math.degrees(rotminX), math.degrees(rotminY), math.degrees(rotminZ)]
		rotmax = [math.degrees(rotmaxX), math.degrees(rotmaxY), math.degrees(rotmaxZ)]
		
		# display progress printouts
		core.print_progress_oneline(pack.UNPACKER_READFROM_BYTE / len(raw))
		# assemble the data into list for returning
		thisjoint = pmxstruct.PmxJoint(name_jp=name_jp, name_en=name_en, jointtype=jointtype,
			rb1_idx=rb1_idx, rb2_idx=rb2_idx, pos=[posX, posY, posZ], rot=rot,
			movemin=[posminX, posminY, posminZ], movemax=[posmaxX, posmaxY, posmaxZ],
			movespring=[springposX, springposY, springposZ], rotmin=rotmin,
			rotmax=rotmax, rotspring=[springrotX, springrotY, springrotZ]
			)
		retme.append(thisjoint)
	return retme

def parse_pmx_softbodies(raw: bytearray) -> List[pmxstruct.PmxSoftBody]:
	# i don't plan to support v2.1 so I'm not gonna try to hard to understand the meaning of these data fields
	# this is mostly to consume the data so there are no bytes left over when done parsing a file to trigger warnings
	# note: this is also untested because i dont care about it lol
	i = pack.my_unpack("i", raw)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of softbodies       =", i)
	retme = []
	for d in range(i):
		name_jp = pack.my_string_unpack(raw)
		name_en = pack.my_string_unpack(raw)
		(shape, idx_mat, group, nocollide_mask, flags) = pack.my_unpack("b" + IDX_MAT + "b H b", raw)
		# i should upack the flags here but idgaf
		(b_link_create_dist, num_clusters, total_mass, collision_marign, aerodynamics_model) = pack.my_unpack("iiffi", raw)
		(vcf, dp, dg, lf, pr, vc, df, mt, rch, kch, sch, ah) = pack.my_unpack("12f", raw)
		(srhr_cl, skhr_cl, sshr_cl, sr_splt_cl, sk_splt_cl, ss_splt_cl) = pack.my_unpack("6f", raw)
		(v_it, p_it, d_it, c_it, mat_lst, mat_ast, mat_vst, num_anchors) = pack.my_unpack("8i", raw)
		anchors_list = []
		for z in range(num_anchors):
			# (idx_rb, idx_vert, near_mode)
			this_anchor = pack.my_unpack(IDX_RB + IDX_VERT + "b", raw)
			anchors_list.append(this_anchor)
		num_vertex_pin = pack.my_unpack("i", raw)
		vertex_pin_list = []
		for z in range(num_vertex_pin):
			vertex_pin = pack.my_unpack(IDX_VERT, raw)
			vertex_pin_list.append(vertex_pin)

		# assemble the data into struct for returning
		thissoft = pmxstruct.PmxSoftBody(
			name_jp, name_en, shape, idx_mat, group, nocollide_mask, flags,
			b_link_create_dist, num_clusters, total_mass, collision_marign, aerodynamics_model,
			vcf, dp, dg, lf, pr, vc, df, mt, rch, kch, sch, ah,
			srhr_cl, skhr_cl, sshr_cl, sr_splt_cl, sk_splt_cl, ss_splt_cl,
			v_it, p_it, d_it, c_it, mat_lst, mat_ast, mat_vst, anchors_list, vertex_pin_list
		)
		retme.append(thissoft)
	return retme

########################################################################################################################

def build_texture_list(thispmx: pmxstruct.Pmx) -> List[str]:
	"""
	Build a list of every unique texture path string that is present in the model, in the order they are encountered.
	This does not include the "builtin toon" names, does not include "does not reference a file", does not include any
	duplicate entries.
	:param thispmx: entire PMX object
	:return: list of filepath strings
	"""
	# built the ordered list of unique filepaths among all materials, excluding the builtin toons
	# empty string means "does not reference a file"
	tex_list = []
	for mat in thispmx.materials:
		if (mat.tex_path not in tex_list) and (mat.tex_path != ""):
			tex_list.append(mat.tex_path)
		if (mat.sph_path not in tex_list) and (mat.sph_path != ""):
			tex_list.append(mat.sph_path)
		if (mat.toon_path not in tex_list) and (mat.toon_path != "") and (mat.toon_path not in BUILTIN_TOON_DICT):
				tex_list.append(mat.toon_path)
	return tex_list

def encode_pmx_lookahead(thispmx: pmxstruct.Pmx) -> Tuple[List[int], List[str]]:
	"""
	Count various things that need to be known ahead of time before I start packing.
	Specifically i need to get the "addl vec4 per vertex" and count the # of each type of thing.
	ALSO, build the list of unique filepaths among the materials.
	:param thispmx: entire PMX object
	:return: ([addl_vec4s, num_verts, num_tex, num_mat, num_bone, num_morph, num_rb, num_joint], tex_list)
	"""
	# specifically i need to get the "addl vec4 per vertex" and count the # of each type of thing
	addl_vec4s = max(len(v.addl_vec4s) for v in thispmx.verts)
	num_verts = len(thispmx.verts)
	# built the ordered list of unique filepaths among all materials, excluding the builtin toons
	tex_list = build_texture_list(thispmx)
	num_tex = len(tex_list)
	num_mat = len(thispmx.materials)
	num_bone = len(thispmx.bones)
	num_morph = len(thispmx.morphs)
	num_rb = len(thispmx.rigidbodies)
	num_joint = len(thispmx.joints)
	retme = [addl_vec4s, num_verts, num_tex, num_mat, num_bone, num_morph, num_rb, num_joint]
	return retme, tex_list

def encode_pmx_header(nice: pmxstruct.PmxHeader, lookahead: List[int]) -> bytearray:
	# in hindsight this is not the best code i've ever written, but it works
	expectedmagic = bytearray("PMX ", "utf-8")
	fmt_magic = "4s f b"
	# note: hardcoding number of globals as 8 when the format is technically flexible
	numglobal = 8
	out = pack.my_pack(fmt_magic, (expectedmagic, nice.ver, numglobal))
	
	# now build the list of 8 global flags
	fmt_globals = str(numglobal) + "b"
	globalflags = [-1] * 8
	# byte 0: encoding, i get to simply choose this
	if ENCODE_WITH_UTF8:
		pack.set_encoding("utf_8")
		globalflags[0] = 1
	else:
		pack.set_encoding("utf_16_le")
		globalflags[0] = 0
	# byte 1: additional vec4 per vertex
	global ADDL_VERTEX_VEC4
	ADDL_VERTEX_VEC4 = lookahead[0]
	globalflags[1] = lookahead[0]
	# bytes 2-7: data size to use for index references
	vertex_categorize = lambda x: 1 if x <= 255 else (2 if x <= 65535 else (4 if x <= 2147483647 else 0))
	other_categorize =  lambda x: 1 if x <= 127 else (2 if x <= 32767 else (4 if x <= 2147483647 else 0))
	globalflags[2] = vertex_categorize(lookahead[1])
	for i in range(3, 8):
		globalflags[i] = other_categorize(lookahead[i - 1])
	global IDX_VERT, IDX_TEX, IDX_MAT, IDX_BONE, IDX_MORPH, IDX_RB
	vert_conv = {1: "B", 2: "H", 4: "i"}
	conv = {1: "b", 2: "h", 4: "i"}
	IDX_VERT =  vert_conv[globalflags[2]]
	IDX_TEX =   conv[globalflags[3]]
	IDX_MAT =   conv[globalflags[4]]
	IDX_BONE =  conv[globalflags[5]]
	IDX_MORPH = conv[globalflags[6]]
	IDX_RB =    conv[globalflags[7]]
	out += pack.my_pack(fmt_globals, globalflags)
	# finally handle the model names & comments
	# (name_jp, name_en, comment_jp, comment_en)
	# out += pack.my_pack("t t t t", [nice.name_jp, nice.name_en, nice.comment_jp, nice.comment_en])
	out += pack.my_string_pack(nice.name_jp)
	out += pack.my_string_pack(nice.name_en)
	out += pack.my_string_pack(nice.comment_jp)
	out += pack.my_string_pack(nice.comment_en)
	return out

def encode_pmx_vertices(nice: List[pmxstruct.PmxVertex]) -> bytearray:
	# first item is int, how many vertices
	i = len(nice)
	out = pack.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of verts            =", i)
	# [posX, posY, posZ, normX, normY, normZ, u, v, addl_vec4s, weighttype, weights, edgescale]
	bdef1_fmt = IDX_BONE
	bdef2_fmt = "2%s f" % IDX_BONE
	bdef4_fmt = "4%s 4f" % IDX_BONE
	sdef_fmt1 =  "2%s f" % IDX_BONE
	sdef_fmt2 =  "9f"
	qdef_fmt =  bdef4_fmt
	
	global ENCODE_PERCENTPOINT_SOFAR
	progress_increment = ENCODE_PERCENTPOINT_WEIGHTS["verts"]
	
	def weightpairs_to_weightbinary(wtype: pmxstruct.WeightMode, w: List[List[float]]) -> List[float]:
		# convert the list of bone-weight pairs to the format/order used in the binary file
		# # how many pairs have a real bone or a real weight?
		# real_weight_count = sum([(a[0] > 0 or a[1]) != 0 for a in w])
		if wtype == pmxstruct.WeightMode.BDEF1:
			while len(w) < 1: w.append([0, 0])  # pad with [0,0] till we have enough members
			# 0 = BDEF1 = [b1]
			return [w[0][0]]
		elif wtype in (pmxstruct.WeightMode.BDEF2, pmxstruct.WeightMode.SDEF):
			while len(w) < 2: w.append([0, 0])  # pad with [0,0] till we have enough members
			# 1 = BDEF2 = [b1, b2, b1w]
			# 3 = sdef =  [b1, b2, b1w] + weight_sdef = [[c1, c2, c3], [r01, r02, r03], [r11, r12, r13]]
			return [w[0][0],
					w[1][0],
					w[0][1]]
		elif wtype in (pmxstruct.WeightMode.BDEF4, pmxstruct.WeightMode.QDEF):
			while len(w) < 4: w.append([0, 0])  # pad with [0,0] till we have enough members
			# 2 = BDEF4 = [b1, b2, b3, b4, b1w, b2w, b3w, b4w]
			# 4 = qdef =  [b1, b2, b3, b4, b1w, b2w, b3w, b4w]  (only in pmx v2.1)
			return [w[0][0], w[1][0], w[2][0], w[3][0],
					w[0][1], w[1][1], w[2][1], w[3][1],]
		raise ValueError("error: weighttype is not supported", wtype)
	
	for d, vert in enumerate(nice):
		# first, basic stuff
		packme = vert.pos + vert.norm + vert.uv  # concat these
		out += pack.my_pack("8f", packme)
		# then, some number of vec4s (probably none)
		# structure it like this so even if a user modifies the vec4s incorrectly it will still write fine
		for z in range(ADDL_VERTEX_VEC4):
			try:				out += pack.my_pack("4f", vert.addl_vec4s[z])
			except IndexError:	out += pack.my_pack("4f", [0, 0, 0, 0])
		
		out += pack.my_pack("b", vert.weighttype.value)
		# weights = vert[10]
		# 0 = BDEF1 = [b1]
		# 1 = BDEF2 = [b1, b2, b1w]
		# 2 = BDEF4 = [b1, b2, b3, b4, b1w, b2w, b3w, b4w]
		# 3 = sdef =  [b1, b2, b1w] + weight_sdef = [[c1, c2, c3], [r01, r02, r03], [r11, r12, r13]]
		# 4 = qdef =  [b1, b2, b3, b4, b1w, b2w, b3w, b4w]  (only in pmx v2.1)
		
		weightlist = weightpairs_to_weightbinary(vert.weighttype, vert.weight)

		if vert.weighttype == pmxstruct.WeightMode.BDEF1:
			# BDEF1
			out += pack.my_pack(bdef1_fmt, weightlist)
		elif vert.weighttype == pmxstruct.WeightMode.BDEF2:
			# BDEF2
			# (b1, b2, b1w)
			out += pack.my_pack(bdef2_fmt, weightlist)
		elif vert.weighttype == pmxstruct.WeightMode.BDEF4:
			# BDEF4
			# (b1, b2, b3, b4, b1w, b2w, b3w, b4w)
			out += pack.my_pack(bdef4_fmt, weightlist)
		elif vert.weighttype == pmxstruct.WeightMode.SDEF:
			# SDEF
			# ([b1, b2, b1w], [c1, c2, c3], [r01, r02, r03], [r11, r12, r13])
			out += pack.my_pack(sdef_fmt1, weightlist)
			out += pack.my_pack(sdef_fmt2, core.flatten(vert.weight_sdef))
		elif vert.weighttype == pmxstruct.WeightMode.QDEF:
			# it must be using QDEF, a type only for PMX v2.1 which I dont need to support so idgaf
			# (b1, b2, b3, b4, b1w, b2w, b3w, b4w)
			out += pack.my_pack(qdef_fmt, weightlist)
		# else:
		# 	core.MY_PRINT_FUNC("invalid weight type for vertex", vert.weighttype)
			
		# then there is one final float after the weight crap
		out += pack.my_pack("f", vert.edgescale)
		# display progress printouts
		ENCODE_PERCENTPOINT_SOFAR += progress_increment
		core.print_progress_oneline(ENCODE_PERCENTPOINT_SOFAR)
	return out

def encode_pmx_surfaces(nice: List[List[int]]) -> bytearray:
	# surfaces is just another name for faces
	# first item is int, how many !vertex indices! there are, NOT the actual number of faces
	# each face is 3 vertex indices
	i = len(nice)
	out = pack.my_pack("i", i * 3)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of faces            =", i)
	
	global ENCODE_PERCENTPOINT_SOFAR
	progress_increment = ENCODE_PERCENTPOINT_WEIGHTS["faces"]

	for d, face in enumerate(nice):
		# each entry is a group of 3 vertex indeces that make a face
		out += pack.my_pack("3" + IDX_VERT, face)
		# display progress printouts
		ENCODE_PERCENTPOINT_SOFAR += progress_increment
		core.print_progress_oneline(ENCODE_PERCENTPOINT_SOFAR)
	return out

def encode_pmx_textures(nice: List[str]) -> bytearray:
	# first item is int, how many textures
	# this section doesn't get any progress printouts cuz its relatively small i guess
	i = len(nice)
	out = pack.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of textures         =", i)
	for d, filepath in enumerate(nice):
		out += pack.my_string_pack(filepath)
	return out

def encode_pmx_materials(nice: List[pmxstruct.PmxMaterial], tex_list: List[str]) -> bytearray:
	# first item is int, how many materials
	i = len(nice)
	out = pack.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of materials        =", i)
	
	global ENCODE_PERCENTPOINT_SOFAR
	progress_increment = ENCODE_PERCENTPOINT_WEIGHTS["materials"]

	# this fmt is when the toon is using a texture reference
	mat_fmtA = "4f 4f 3f B 5f 2%s b b %s" % (IDX_TEX, IDX_TEX)
	# this fmt is when the toon is using a builtin toon, toon01.bmp thru toon10.bmp (values 0-9)
	mat_fmtB = "4f 4f 3f B 5f 2%s b b b" % IDX_TEX
	for d, mat in enumerate(nice):
		out += pack.my_string_pack(mat.name_jp)
		out += pack.my_string_pack(mat.name_en)
		
		flagsum = mat.matflags.value
		# convert the texture strings back into int references, also get builtin_toon back
		# i just built 'tex_list' from the materials so these lookups are guaranteed to succeed
		if mat.tex_path == "": tex_idx = -1
		else:                  tex_idx = tex_list.index(mat.tex_path)
		if mat.sph_path == "": sph_idx = -1
		else:                  sph_idx = tex_list.index(mat.sph_path)
		if mat.toon_path in BUILTIN_TOON_DICT:
			# then this is a builtin toon!
			builtin_toon = 1
			toon_idx = BUILTIN_TOON_DICT[mat.toon_path]
		else:
			# this is a nonstandard toon, look up the same as the tex or sph
			builtin_toon = 0
			if mat.toon_path == "": toon_idx = -1
			else:                   toon_idx = tex_list.index(mat.toon_path)
		# now put 'em all together in the proper order
		packme = [*mat.diffRGB, mat.alpha, *mat.specRGB, mat.specpower, *mat.ambRGB,
				  flagsum, *mat.edgeRGB, mat.edgealpha, mat.edgesize, tex_idx, sph_idx, mat.sph_mode.value,
				  builtin_toon, toon_idx]
		# the size for packing of the "toon_idx" arg depends on the "builtin_toon" arg, but the number and order is the same
		if builtin_toon:
			# toon is using one of the builtin toons, toon01.bmp thru toon10.bmp (values 0-9)
			out += pack.my_pack(mat_fmtB, packme)
		else:
			# toon is using a texture reference
			out += pack.my_pack(mat_fmtA, packme)
		# pack the comment
		out += pack.my_string_pack(mat.comment)
		# pack the number of faces in the material, times 3
		# note: i structure the faces list into groups of 3 vertex indices, this is divided by 3 to match, so now i need to undivide
		verts_ct = 3 * mat.faces_ct
		out += pack.my_pack("i", verts_ct)
		# display progress printouts
		ENCODE_PERCENTPOINT_SOFAR += progress_increment
		core.print_progress_oneline(ENCODE_PERCENTPOINT_SOFAR)

	return out

def encode_pmx_bones(nice: List[pmxstruct.PmxBone]) -> bytearray:
	# first item is int, how many bones
	i = len(nice)
	out = pack.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of bones            =", i)
	
	global ENCODE_PERCENTPOINT_SOFAR
	progress_increment = ENCODE_PERCENTPOINT_WEIGHTS["bones"]

	fmt_bone = "3f %s i 2B" % IDX_BONE
	fmt_bone_inherit = "%s f" % IDX_BONE
	fmt_bone_ik = "%s i f i" % IDX_BONE
	fmt_bone_ik_linkA = "%s b" % IDX_BONE
	fmt_bone_ik_linkB = "%s b 6f" % IDX_BONE
	for d, bone in enumerate(nice):
		# (name_jp, name_en, posX, posY, posZ, parent_idx, deform_layer)
		out += pack.my_string_pack(bone.name_jp)
		out += pack.my_string_pack(bone.name_en)
		
		packme = [*bone.pos, bone.parent_idx, bone.deform_layer]
		# next are the two flag-bytes (flags1, flags2)
		# reassemble the bits into a byte
		flagsum1 = 0
		flagsum1 += (1 << 0) if bool(bone.tail_usebonelink) else 0
		flagsum1 += (1 << 1) if bool(bone.has_rotate) else 0
		flagsum1 += (1 << 2) if bool(bone.has_translate) else 0
		flagsum1 += (1 << 3) if bool(bone.has_visible) else 0
		flagsum1 += (1 << 4) if bool(bone.has_enabled) else 0
		flagsum1 += (1 << 5) if bool(bone.has_ik) else 0
		flagsum2 = 0
		flagsum2 += (1 << 0) if bool(bone.inherit_rot) else 0
		flagsum2 += (1 << 1) if bool(bone.inherit_trans) else 0
		flagsum2 += (1 << 2) if bool(bone.has_fixedaxis) else 0
		flagsum2 += (1 << 3) if bool(bone.has_localaxis) else 0
		flagsum2 += (1 << 4) if bool(bone.deform_after_phys) else 0
		flagsum2 += (1 << 5) if bool(bone.has_externalparent) else 0
		packme += [flagsum1, flagsum2]
		out += pack.my_pack(fmt_bone, packme)
		
		# tail will always exist but type will vary
		if bone.tail_usebonelink:  # use index for bone its pointing at
			out += pack.my_pack(IDX_BONE, bone.tail)
		else:  # use offset
			out += pack.my_pack("3f", bone.tail)

		# then is all the "might or might not exist" stuff
		if bone.inherit_rot or bone.inherit_trans:
			out += pack.my_pack(fmt_bone_inherit, [bone.inherit_parent_idx, bone.inherit_ratio])
		if bone.has_fixedaxis:
			out += pack.my_pack("3f", bone.fixedaxis)  # format is xyz obviously
		if bone.has_localaxis:
			out += pack.my_pack("6f", [*bone.localaxis_x, *bone.localaxis_z])  # (xx, xy, xz, zx, zy, zz)
		if bone.has_externalparent:
			out += pack.my_pack("i", bone.externalparent)
		
		if bone.has_ik:  # ik:
			# (ik_target, ik_loops, ik_anglelimit, ik_numlinks)
			# note: my struct holds ik_angle as degrees, file spec holds it as radians
			out += pack.my_pack(fmt_bone_ik, [bone.ik_target_idx, bone.ik_numloops,
											  math.radians(bone.ik_angle), len(bone.ik_links)])
			for iklink in bone.ik_links:
				# bool(list) means "is the list non-empty and also not None"
				if iklink.limit_min and iklink.limit_max:
					# note: my struct holds limit_min/max as degrees, file spec holds it as radians
					limitminmax = []
					for lim in iklink.limit_min:
						limitminmax.append(math.radians(lim))
					for lim in iklink.limit_max:
						limitminmax.append(math.radians(lim))
					out += pack.my_pack(fmt_bone_ik_linkB, [iklink.idx, True, *limitminmax])
				else:
					out += pack.my_pack(fmt_bone_ik_linkA, [iklink.idx, False])
		# display progress printouts
		ENCODE_PERCENTPOINT_SOFAR += progress_increment
		core.print_progress_oneline(ENCODE_PERCENTPOINT_SOFAR)

	return out

def encode_pmx_morphs(nice: List[pmxstruct.PmxMorph]) -> bytearray:
	# first item is int, how many morphs
	i = len(nice)
	out = pack.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of morphs           =", i)

	global ENCODE_PERCENTPOINT_SOFAR
	progress_increment = ENCODE_PERCENTPOINT_WEIGHTS["morphitems"]

	fmt_morph = "b b i"
	fmt_morph_group = "%s f" % IDX_MORPH
	fmt_morph_flip = fmt_morph_group
	fmt_morph_vert = "%s 3f" % IDX_VERT
	fmt_morph_bone = "%s 3f 4f" % IDX_BONE
	fmt_morph_uv = "%s 4f" % IDX_VERT
	fmt_morph_mat = "%s b 4f 3f    f 3f 4f f    4f 4f 4f" % IDX_MAT
	fmt_morph_impulse = "%s b 3f 3f" % IDX_RB
	for d, morph in enumerate(nice):
		# (name_jp, name_en, panel, morphtype, itemcount)
		out += pack.my_string_pack(morph.name_jp)
		out += pack.my_string_pack(morph.name_en)
		
		out += pack.my_pack(fmt_morph,[morph.panel.value, morph.morphtype.value, len(morph.items)])
		
		# for each morph in the group morph, or vertex in the vertex morph, or bone in the bone morph....
		# what to unpack varies on morph type, 9 possibilities + some for v2.1
		if morph.morphtype == pmxstruct.MorphType.GROUP:  # group
			for z in morph.items:
				z: pmxstruct.PmxMorphItemGroup
				out += pack.my_pack(fmt_morph_group, [z.morph_idx, z.value])
		elif morph.morphtype == pmxstruct.MorphType.VERTEX:  # vertex
			for z in morph.items:
				z: pmxstruct.PmxMorphItemVertex
				out += pack.my_pack(fmt_morph_vert, [z.vert_idx, *z.move])
		elif morph.morphtype == pmxstruct.MorphType.BONE:  # bone
			for z in morph.items:
				z: pmxstruct.PmxMorphItemBone
				(rotqW, rotqX, rotqY, rotqZ) = core.euler_to_quaternion(z.rot)
				# (bone_idx, transX, transY, transZ, rotqX, rotqY, rotqZ, rotqW)
				out += pack.my_pack(fmt_morph_bone, [z.bone_idx, *z.move, rotqX, rotqY, rotqZ, rotqW])
		elif morph.morphtype in (pmxstruct.MorphType.UV,
								 pmxstruct.MorphType.UV_EXT1,
								 pmxstruct.MorphType.UV_EXT2,
								 pmxstruct.MorphType.UV_EXT3,
								 pmxstruct.MorphType.UV_EXT4):
			for z in morph.items:
				z: pmxstruct.PmxMorphItemUV
				# what these values do depends on the UV layer they are affecting, but the docs dont say what...
				# oh well, i dont need to use them so i dont care :)
				out += pack.my_pack(fmt_morph_uv, [z.vert_idx, *z.move])
		elif morph.morphtype == pmxstruct.MorphType.MATERIAL:  # material
			for z in morph.items:
				z: pmxstruct.PmxMorphItemMaterial
				# (mat_idx, is_add, diffR, diffG, diffB, diffA, specR, specG, specB) = core.unpack(IDX_MAT+"b 4f 3f", raw)
				# (specpower, ambR, ambG, ambB, edgeR, edgeG, edgeB, edgeA, edgesize) = core.unpack("f 3f 4f f", raw)
				# (texR, texG, texB, texA, sphR, sphG, sphB, sphA, toonR, toonG, toonB, toonA) = core.unpack("4f 4f 4f", raw)
				packme = [z.mat_idx, z.is_add, *z.diffRGB, z.alpha, *z.specRGB, z.specpower, *z.ambRGB, *z.edgeRGB,
						  z.edgealpha, z.edgesize, *z.texRGBA, *z.sphRGBA, *z.toonRGBA]
				out += pack.my_pack(fmt_morph_mat, packme)
		elif morph.morphtype == pmxstruct.MorphType.FLIP:  # (2.1 only) flip
			for z in morph.items:
				z: pmxstruct.PmxMorphItemFlip
				out += pack.my_pack(fmt_morph_flip, [z.morph_idx, z.value])
		elif morph.morphtype == pmxstruct.MorphType.IMPULSE:  # (2.1 only) impulse
			for z in morph.items:
				z: pmxstruct.PmxMorphItemImpulse
				# (rb_idx, is_local, movX, movY, movZ, rotX, rotY, rotZ)
				out += pack.my_pack(fmt_morph_impulse, [z.rb_idx, z.is_local, *z.move, *z.rot])
		else:
			core.MY_PRINT_FUNC("unsupported morph type value", morph.morphtype)
		
		# display progress printouts
		ENCODE_PERCENTPOINT_SOFAR += progress_increment * len(morph.items)
		core.print_progress_oneline(ENCODE_PERCENTPOINT_SOFAR)

	return out

def encode_pmx_dispframes(nice: List[pmxstruct.PmxFrame]) -> bytearray:
	# first item is int, how many dispframes
	i = len(nice)
	out = pack.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of dispframes       =", i)
	
	global ENCODE_PERCENTPOINT_SOFAR
	progress_increment = ENCODE_PERCENTPOINT_WEIGHTS["frameitems"]

	fmt_frame = "b i"
	fmt_frame_item_morph = "b %s" % IDX_MORPH
	fmt_frame_item_bone =  "b %s" % IDX_BONE
	for d, frame in enumerate(nice):
		# (name_jp, name_en, is_special, itemcount)
		out += pack.my_string_pack(frame.name_jp)
		out += pack.my_string_pack(frame.name_en)
		out += pack.my_pack(fmt_frame, [frame.is_special, len(frame.items)])
		
		for item in frame.items:
			if item.is_morph: out += pack.my_pack(fmt_frame_item_morph, [item.is_morph, item.idx])
			else:             out += pack.my_pack(fmt_frame_item_bone, [item.is_morph, item.idx])
		# display progress printouts
		ENCODE_PERCENTPOINT_SOFAR += progress_increment * len(frame.items)
		core.print_progress_oneline(ENCODE_PERCENTPOINT_SOFAR)
	
	return out

def encode_pmx_rigidbodies(nice: List[pmxstruct.PmxRigidBody]) -> bytearray:
	# first item is int, how many rigidbodies
	i = len(nice)
	out = pack.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of rigidbodies      =", i)
	
	global ENCODE_PERCENTPOINT_SOFAR
	progress_increment = ENCODE_PERCENTPOINT_WEIGHTS["rigidbodies"]

	fmt_rbody = "%s b H b 3f 3f 3f 5f b" % IDX_BONE
	for d, b in enumerate(nice):
		out += pack.my_string_pack(b.name_jp)
		out += pack.my_string_pack(b.name_en)
		
		# note: my struct holds rotation as XYZ degrees, must convert to radians for file
		rot = [math.radians(r) for r in b.rot]
		
		# NOTE: remember that group & nocollide set are all [1-16] while the binary wants [0-15]!!!!
		group = b.group - 1
		
		# create collide_mask from the collide_set
		# assume every group is marked to collide, then for each item in nocollide_set, unmark that bit
		collide_mask = (1<<16)-1
		for a in b.nocollide_set:
			collide_mask &= ~(1<<(a-1))
			
		packme = [b.bone_idx, group, collide_mask, b.shape.value, *b.size, *b.pos, *rot,
				  b.phys_mass, b.phys_move_damp, b.phys_rot_damp, b.phys_repel, b.phys_friction, b.phys_mode.value]
		out += pack.my_pack(fmt_rbody, packme)
		# display progress printouts
		ENCODE_PERCENTPOINT_SOFAR += progress_increment
		core.print_progress_oneline(ENCODE_PERCENTPOINT_SOFAR)
	
	return out

def encode_pmx_joints(nice: List[pmxstruct.PmxJoint]) -> bytearray:
	# first item is int, how many joints
	i = len(nice)
	out = pack.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of joints           =", i)
	
	global ENCODE_PERCENTPOINT_SOFAR
	progress_increment = ENCODE_PERCENTPOINT_WEIGHTS["joints"]

	fmt_joint = "b 2%s 3f 3f 3f 3f 3f 3f 3f 3f" % IDX_RB
	for d, j in enumerate(nice):
		out += pack.my_string_pack(j.name_jp)
		out += pack.my_string_pack(j.name_en)
		
		# note: my struct holds rot/rotmin/rotmax as XYZ degrees, must convert to radians for file
		rot = [math.radians(r) for r in j.rot]
		rotmin = [math.radians(r) for r in j.rotmin]
		rotmax = [math.radians(r) for r in j.rotmax]
		
		packme = [j.jointtype.value, j.rb1_idx, j.rb2_idx, *j.pos, *rot, *j.movemin,
				  *j.movemax, *rotmin, *rotmax, *j.movespring, *j.rotspring]
		out += pack.my_pack(fmt_joint, packme)
		# display progress printouts
		ENCODE_PERCENTPOINT_SOFAR += progress_increment
		core.print_progress_oneline(ENCODE_PERCENTPOINT_SOFAR)

	return out

def encode_pmx_softbodies(nice: List[pmxstruct.PmxSoftBody]) -> bytearray:
	# i don't plan to support v2.1 so I'm not gonna try to hard to understand the meaning of these data fields
	# this is mostly to consume the data so there are no bytes left over when done parsing a file to trigger warnings
	# note: this is also untested because i dont care about it lol
	i = len(nice)
	out = pack.my_pack("i", i)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...# of softbodies       =", i)
	
	global ENCODE_PERCENTPOINT_SOFAR
	progress_increment = ENCODE_PERCENTPOINT_WEIGHTS["softbodies"]

	fmt_sb = "b %s b H b iiffi 12f 6f 7i" % IDX_MAT
	fmt_sb_anchor = "%s %s b" % (IDX_RB, IDX_VERT)
	for d, s in enumerate(nice):
		out += pack.my_string_pack(s.name_jp)
		out += pack.my_string_pack(s.name_en)
		# (name_jp, name_en, shape, idx_mat, group, nocollide_mask, flags) = core.my_unpack("t t b" + IDX_MAT + "b H b", raw)
		# (b_link_create_dist, num_clusters, total_mass, collision_marign, aerodynamics_model) = core.my_unpack("iiffi", raw)
		# (vcf, dp, dg, lf, pr, vc, df, mt, rch, kch, sch, ah) = core.my_unpack("12f", raw)
		# (srhr_cl, skhr_cl, sshr_cl, sr_splt_cl, sk_splt_cl, ss_splt_cl) = core.my_unpack("6f", raw)
		# (v_it, p_it, d_it, c_it, mat_lst, mat_ast, mat_vst) = core.my_unpack("7i", raw)
		packme = [
			s.shape, s.idx_mat, s.group, s.nocollide_mask, s.flags,
			s.b_link_create_dist, s.num_clusters, s.total_mass, s.collision_margin, s.aerodynamics_model,
			s.vcf, s.dp, s.dg, s.lf, s.pr, s.vc, s.df, s.mt, s.rch, s.kch, s.sch, s.ah,
			s.srhr_cl, s.skhr_cl, s.sshr_cl, s.sr_splt_cl, s.sk_splt_cl, s.ss_splt_cl,
			s.v_it, s.p_it, s.d_it, s.c_it, s.mat_lst, s.mat_ast, s.mat_vst, s.anchors_list, s.vertex_pin_list
		]
		out += pack.my_pack(fmt_sb, packme)
		
		# (num_anchors)
		out += pack.my_pack("i", len(s.anchors_list))
		for anchor in s.anchors_list:
			# (idx_rb, idx_vert, near_mode)
			out += pack.my_pack(fmt_sb_anchor, anchor)
			
		# (num_pins)
		out += pack.my_pack("i", len(s.vertex_pin_list))
		for pin in s.vertex_pin_list:
			out += pack.my_pack(IDX_VERT, pin)
		# display progress printouts
		ENCODE_PERCENTPOINT_SOFAR += progress_increment
		core.print_progress_oneline(ENCODE_PERCENTPOINT_SOFAR)
	
	return out

def _prepare_progress_printouts_for_write_pmx(pmx: pmxstruct.Pmx) -> None:
	# since i know the total size of the VMD object, and how many of each thing is within it,
	# if i measure how long it takes to encode some number of each thing then I should be able to estimate
	# how long it takes to encode each section and/or the whole thing!
	# this function is to set global variables and stuff to aid with that goal

	# verts, faces, and morphs are the only significant time sinks
	# verts/faces/morphitems number ~10,000 to ~300,000
	# this totally dwarfs the other categories... ~100 mats, ~500 bones/rigidbodies/joints/dispframes
	# buuuuuuuuuuut i guess there's no harm in assigning weights to the smaller categories anyway
	
	relative_weights = {
		# "header":		0,
		"verts":		50,		# major
		"faces":		8,		# major
		# "textures":	0,
		"materials":	100,
		"bones":		80,
		"morphitems":	8,		# major
		"frameitems":	10,
		"rigidbodies":	80,
		"joints":		80,
		"softbodies":	900,
	}
	total_relative_size = 0
	total_relative_size += relative_weights["verts"] * len(pmx.verts)
	total_relative_size += relative_weights["faces"] * len(pmx.faces)
	total_relative_size += relative_weights["materials"] * len(pmx.materials)
	total_relative_size += relative_weights["bones"] * len(pmx.bones)
	total_relative_size += relative_weights["morphitems"] * sum(len(m.items) for m in pmx.morphs)
	total_relative_size += relative_weights["frameitems"] * sum(len(m.items) for m in pmx.frames)
	total_relative_size += relative_weights["rigidbodies"] * len(pmx.rigidbodies)
	total_relative_size += relative_weights["joints"] * len(pmx.joints)
	total_relative_size += relative_weights["softbodies"] * len(pmx.softbodies)
	# deliberately skip textures cuz it would be messy, and header cuz it's just one atomic indivisible item
	
	# now i have the total relative size... normalize to 100%=1 and all the relative weights get reduced by same amount
	factor = 1 / total_relative_size
	for category, relative_value in relative_weights.items():
		ENCODE_PERCENTPOINT_WEIGHTS[category] = relative_value * factor
	
	# print(ENCODE_PERCENTPOINT_WEIGHTS["verts"] * len(pmx.verts))
	# print(ENCODE_PERCENTPOINT_WEIGHTS["faces"] * len(pmx.faces))
	# print(ENCODE_PERCENTPOINT_WEIGHTS["materials"] * len(pmx.materials))
	# print(ENCODE_PERCENTPOINT_WEIGHTS["bones"] * len(pmx.bones))
	# print(ENCODE_PERCENTPOINT_WEIGHTS["morphitems"] * sum(len(m.items) for m in pmx.morphs))
	# print(ENCODE_PERCENTPOINT_WEIGHTS["frameitems"] * sum(len(m.items) for m in pmx.frames))
	# print(ENCODE_PERCENTPOINT_WEIGHTS["rigidbodies"] * len(pmx.rigidbodies))
	# print(ENCODE_PERCENTPOINT_WEIGHTS["joints"] * len(pmx.joints))
	# print(ENCODE_PERCENTPOINT_WEIGHTS["softbodies"] * len(pmx.softbodies))

	global ENCODE_PERCENTPOINT_SOFAR
	ENCODE_PERCENTPOINT_SOFAR = 0
	
	return

########################################################################################################################

def read_pmx(pmx_filename: str, moreinfo=False) -> pmxstruct.Pmx:
	global PMX_MOREINFO
	PMX_MOREINFO = moreinfo
	pmx_filename_clean = core.filepath_splitdir(pmx_filename)[1]
	# assumes the calling function already verified correct file extension
	core.MY_PRINT_FUNC("Begin reading PMX file '%s'" % pmx_filename_clean)
	pmx_bytes = io.read_binfile_to_bytes(pmx_filename)
	core.MY_PRINT_FUNC("...total size   = %s" % core.prettyprint_file_size(len(pmx_bytes)))
	core.MY_PRINT_FUNC("Begin parsing PMX file '%s'" % pmx_filename_clean)
	pack.reset_unpack()
	core.print_progress_oneline(0)
	A = parse_pmx_header(pmx_bytes)
	if PMX_MOREINFO: core.MY_PRINT_FUNC("...PMX version  = v%s" % str(A.ver))
	core.MY_PRINT_FUNC("...model name   = JP:'%s' / EN:'%s'" % (A.name_jp, A.name_en))
	B = parse_pmx_vertices(pmx_bytes)
	C = parse_pmx_surfaces(pmx_bytes)
	tex_list = parse_pmx_textures(pmx_bytes)
	E = parse_pmx_materials(pmx_bytes, tex_list)
	F = parse_pmx_bones(pmx_bytes)
	G = parse_pmx_morphs(pmx_bytes)
	H = parse_pmx_dispframes(pmx_bytes)
	I = parse_pmx_rigidbodies(pmx_bytes)
	J = parse_pmx_joints(pmx_bytes)
	if A.ver == 2.1:
		# if version==2.1, parse soft bodies
		K = parse_pmx_softbodies(pmx_bytes)
	else:
		# otherwise, dont
		K = []
	
	bytes_remain = len(pmx_bytes) - pack.UNPACKER_READFROM_BYTE
	if bytes_remain != 0:
		core.MY_PRINT_FUNC("Warning: finished parsing but %d bytes are left over at the tail!" % bytes_remain)
		core.MY_PRINT_FUNC("The file may be corrupt or maybe it contains unknown/unsupported data formats")
		core.MY_PRINT_FUNC(pmx_bytes[pack.UNPACKER_READFROM_BYTE:])
	core.MY_PRINT_FUNC("Done parsing PMX file '%s'" % pmx_filename_clean)
	retme = pmxstruct.Pmx(header=A,
						  verts=B,
						  faces=C,
						  # texes=D,
						  mats=E,
						  bones=F,
						  morphs=G,
						  frames=H,
						  rbodies=I,
						  joints=J,
						  sbodies=K)
	return retme


def write_pmx(pmx_filename: str, pmx: pmxstruct.Pmx, moreinfo=False) -> None:
	global PMX_MOREINFO
	PMX_MOREINFO = moreinfo
	pmx_filename_clean = core.filepath_splitdir(pmx_filename)[1]
	# recives object 	(......)
	# before writing, validate that the object is properly structured
	# if it fails, it prints a bunch & raises a RuntimeError
	pmx.validate()
	# assumes the calling function already verified correct file extension
	core.MY_PRINT_FUNC("Begin encoding PMX file '%s'" % pmx_filename_clean)

	if PMX_MOREINFO: core.MY_PRINT_FUNC("...PMX version  = v%s" % str(pmx.header.ver))
	core.MY_PRINT_FUNC("...model name   = JP:'%s' / EN:'%s'" % (pmx.header.name_jp, pmx.header.name_en))
	
	# arg "pmx" is the same structure created by "read_pmx()"
	# assume the object is perfect, no sanity-checking needed
	output_bytes = bytearray()
	
	# # stress-test code
	# pmx.verts = pmx.verts * 10
	# pmx.faces = pmx.faces * 10
	# pmx.materials = pmx.materials * 1000
	# pmx.bones = pmx.bones * 1000
	# pmx.morphs = pmx.morphs * 10
	# pmx.frames = pmx.frames * 10
	# pmx.rigidbodies = pmx.rigidbodies * 1000
	# pmx.joints = pmx.joints * 1000
	
	_prepare_progress_printouts_for_write_pmx(pmx)

	core.print_progress_oneline(0)
	lookahead, tex_list = encode_pmx_lookahead(pmx)
	output_bytes += encode_pmx_header(pmx.header, lookahead)
	output_bytes += encode_pmx_vertices(pmx.verts)
	output_bytes += encode_pmx_surfaces(pmx.faces)
	output_bytes += encode_pmx_textures(tex_list)
	output_bytes += encode_pmx_materials(pmx.materials, tex_list)
	output_bytes += encode_pmx_bones(pmx.bones)
	output_bytes += encode_pmx_morphs(pmx.morphs)
	output_bytes += encode_pmx_dispframes(pmx.frames)
	output_bytes += encode_pmx_rigidbodies(pmx.rigidbodies)
	output_bytes += encode_pmx_joints(pmx.joints)
	if pmx.header.ver == 2.1:
		# if version==2.1, parse soft bodies
		output_bytes += encode_pmx_softbodies(pmx.softbodies)

	# done encoding!!

	core.MY_PRINT_FUNC("Begin writing PMX file '%s'" % pmx_filename_clean)
	core.MY_PRINT_FUNC("...total size   = %s" % core.prettyprint_file_size(len(output_bytes)))
	io.write_bytes_to_binfile(pmx_filename, output_bytes)
	core.MY_PRINT_FUNC("Done writing PMX file '%s'" % pmx_filename_clean)
	# done with everything!
	return None


########################################################################################################################
def main():
	core.MY_PRINT_FUNC("Specify a PMX file to attempt parsing and writeback")
	input_filename = core.MY_FILEPROMPT_FUNC("PMX file", ".pmx")
	# input_filename = "pmxtest.pmx"
	
	TEMPNAME = "____pmxparser_selftest_DELETEME.pmx"
	Z = read_pmx(input_filename, moreinfo=True)
	write_pmx(TEMPNAME, Z, moreinfo=True)
	ZZ = read_pmx(TEMPNAME, moreinfo=True)
	bb = io.read_binfile_to_bytes(input_filename)
	bb2 = io.read_binfile_to_bytes(TEMPNAME)
	core.MY_PRINT_FUNC("")
	core.MY_PRINT_FUNC("TIMING TEST:")
	readtime = []
	writetime = []
	for i in range(10):
		core.MY_PRINT_FUNC(i)
		start = time.time()
		_ = read_pmx(input_filename)
		end = time.time()
		readtime.append(end - start)
	for i in range(10):
		core.MY_PRINT_FUNC(i)
		start = time.time()
		write_pmx(TEMPNAME, Z)
		end = time.time()
		writetime.append(end - start)
	core.MY_PRINT_FUNC("TIMING TEST RESULTS:", input_filename)
	core.MY_PRINT_FUNC("READ")
	core.MY_PRINT_FUNC("Avg = %f, min = %f, max = %f" % (sum(readtime)/len(readtime), min(readtime), max(readtime)))
	core.MY_PRINT_FUNC("WRITE")
	core.MY_PRINT_FUNC("Avg = %f, min = %f, max = %f" % (sum(writetime)/len(writetime), min(writetime), max(writetime)))
	core.MY_PRINT_FUNC("")
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
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.RUN_WITH_TRACEBACK(main)
