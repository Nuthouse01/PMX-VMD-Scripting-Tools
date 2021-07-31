import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.00 - 6/10/2021"

# GOAL: sort vertices by UV coordinates
# PROBLEM: verts that have matching UV coords?
# SOLUTION: use xyz as tiebreaker... if uv exact match and xyz exact match, then order probably doesnt matter
# also need to update references to vertices
# vertices are referenced in faces, morphs (uv and vertex morphs), and soft bodies (should be handled just for completeness' sake)

# NOTES:
# this is used to guarantee matching vertex order for geometry that should be the "same" but comes from different sources
# this ordering is totally useless if the two versions have different numbers of vertices though!
# reduce the PMX to the smallest units possible & sort one by one


def main():
	pmxname = core.prompt_user_filename("PMX file", ".pmx")
	
	pmx = pmxlib.read_pmx(pmxname, moreinfo=True)
	
	# first, attach the vert index to the vert object, so i can determine the before-after map
	idxlist = list(range(len(pmx.verts)))
	vertlist = list(zip(pmx.verts, idxlist))
	# lambda func to use for sorting: returns a list of keys to sort by
	# use + to append lists
	# this key will sort by u then by v then by x then by y then by z
	sortkey = lambda x: x[0].uv + x[0].pos
	# then, sort the list
	print("sorting")
	vertlist.sort(key=sortkey)
	
	# unzip
	new_vertlist = [a for a, b in vertlist]
	old_idxs =     [b for a, b in vertlist]
	
	# put the newly sorted list into the pmx struct
	pmx.verts = new_vertlist
	
	# build a map of old index to new index
	old_to_new = dict(zip(old_idxs,idxlist))
	
	# now update all faces
	print("doing faces")
	for f in pmx.faces:
		for i in range(3):
			f[i] = old_to_new[f[i]]
			
	# now update all morphs
	print("doing morphs")
	for m in pmx.morphs:
		if m.morphtype == pmxstruct.MorphType.VERTEX:  #vertex
			for item in m.items:
				item.vert_idx = old_to_new[item.vert_idx]
		if m.morphtype in (pmxstruct.MorphType.UV,
						   pmxstruct.MorphType.UV_EXT1,
						   pmxstruct.MorphType.UV_EXT2,
						   pmxstruct.MorphType.UV_EXT3,
						   pmxstruct.MorphType.UV_EXT4, ): # uv
			for item in m.items:
				item.vert_idx = old_to_new[item.vert_idx]
		
	# softbodies: eh, who cares
	pmxname_done = core.filepath_insert_suffix(pmxname, "_Vsort")
	pmxlib.write_pmx(pmxname_done, pmx, moreinfo=True)
	print("done")
	

if __name__ == "__main__":
	print(_SCRIPT_VERSION)
	main()

