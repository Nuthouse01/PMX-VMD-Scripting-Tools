
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

from PIL import Image
from progprint import progprint, progclean



def main():
	pmxname = core.prompt_user_filename(".pmx")
	pmxname_done = "edgeweightapplied.pmx"
	maskname = core.prompt_user_filename(".png")
	
	pmx1 = pmxlib.read_pmx(pmxname, moreinfo=True)
	
	im = Image.open(maskname).convert('RGBA')
	# isolate only one of the layers, all values should be equal
	r,g,b,a = im.split()
	
	px = r.load()

	# if uv = 1, then access index 4095 not 4096
	print(im.size)
	s = (im.size[0]-1, im.size[1]-1)

	print("numverts =", len(pmx1.verts))
	for d,v in enumerate(pmx1.verts):
		progprint(d / len(pmx1.verts))
		
		# have vertex v
		# convert uv coords to nearest pixel idx
		# which is x/y??
		# do i need to invert an axis?
		x = round(v.uv[0] * s[0])
		y = round(v.uv[1] * s[1])
		# get the pixel at this xy
		p = px[x,y]
		# print(p)
		
		# convert pixel value 0-255 to 0-1 edge factor
		# not sure whether i need to invert or not? 50/50 shot so lets go
		e = p / 255
		
		# store into v
		v.edgescale = e
		
		pass
	pmxlib.write_pmx(pmxname_done, pmx1, moreinfo=True)
	print("done")
	

if __name__ == "__main__":
	main()

