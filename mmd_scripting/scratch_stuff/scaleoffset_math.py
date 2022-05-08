import math

from mmd_scripting.core.nuthouse01_core import rotate2d

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.5.04 - 12/20/2020"


print("give XYZ of 2 points that you want to align, and XYZ of the 2 points you want them aligned to")
print("returns XYZ scale and XYZ offset needed to make them aligned")
print("the two locations should be different in all 3 dimensions")

DIMENSIONS = 3
CHECK_ROTATION = False

print("DIMENSIONS = %d" % DIMENSIONS)
print("")
print("format: floating point numbers separated by commas, no spaces")
moveme_1_str = input("moveme point 1: ")
dest_1_str =   input("  dest point 1: ")
moveme_2_str = input("moveme point 2: ")
dest_2_str =   input("  dest point 2: ")

points_str = [moveme_1_str, moveme_2_str, dest_1_str, dest_2_str]
points = []
for p in points_str:
	p_new = list(p.split(","))
	for i in range(DIMENSIONS):
		p_new[i] = float(p_new[i])
	points.append(p_new)

from1, from2, dest1, dest2 = points

# now have input received and converted
# now do math

# each dimension can be done independently
# assume scaling around 0,0,0

scale_all = []
offset_all = []
from1_scaled = []
from2_scaled = []
needs_angle = None

# first calc desired delta and actual delta
moveme_delta = [from1[i] - from2[i] for i in range(DIMENSIONS)]
dest_delta =   [dest1[i] - dest2[i] for i in range(DIMENSIONS)]


if DIMENSIONS == 2 and CHECK_ROTATION:
	# check if any rotation is needed!
	moveme_angle = math.atan2(moveme_delta[1], moveme_delta[0])
	dest_angle = math.atan2(dest_delta[1], dest_delta[0])
	# calculate angle difference
	needs_angle = round(math.degrees(dest_angle - moveme_angle),6)
	# apply the rotation to from1_scaled and from2_scaled
	print(from1)
	from1 = rotate2d((0,0),dest_angle - moveme_angle, from1)
	print(from1)
	from2 = rotate2d((0,0),dest_angle - moveme_angle, from2)
	moveme_delta = [from1[i] - from2[i] for i in range(DIMENSIONS)]

for i in range(DIMENSIONS):
	# determine scale factor: moveme * scale = dest, dest / moveme = scale
	scale = dest_delta[i] / moveme_delta[i]
	# store result
	scale_all.append(round(scale,6))
	# then apply scale factor, scale around 0,0,0
	from1_scaled.append(from1[i] * scale)
	from2_scaled.append(from2[i] * scale)

for i in range(DIMENSIONS):
	# then find offset needed to reach dest
	offset = dest1[i] - from1_scaled[i]
	# store results
	offset_all.append(round(offset,6))
	
# print results
print("")
print("do these things IN THIS ORDER:")
if DIMENSIONS == 2:
	print("rotate around 0,0 by this many degrees:")
	print(needs_angle)
print("scale around 0,0,0 by factor of:")
print(scale_all)
print("offset all geometry by:")
print(offset_all)


input("done")
