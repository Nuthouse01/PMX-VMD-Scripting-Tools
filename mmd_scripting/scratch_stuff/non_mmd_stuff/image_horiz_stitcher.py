from PIL import Image

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.5.00 - 8/24/2020"



def get_concat_h(im111, im222):
	dst = Image.new('RGBA', (im111.width + im222.width, max(im111.height, im222.height)))
	dst.paste(im111, (0, 0))
	dst.paste(im222, (im111.width, 0))
	return dst




print("use this to stitch images together horizontally")
print("empty input when done listing files")



# s = input("image: ")
# im1 = Image.open(s)

# im2 = im1.resize((int(im1.width * 1080 / im1.height), 1080), resample=Image.BICUBIC)


imnew = Image.new('RGBA', (0,0))


outname = "stitch_"

while True:
	s = input("image: ")
	if s == "": break
	outname += s[0:s.rfind(".")]
	im2 = Image.open(s)
	# im2 = im1.resize((int(im1.width * 1080 / im1.height), 1080), resample=Image.BICUBIC)

	imnew = get_concat_h(imnew, im2)
		
imnew.save(outname + ".png")









