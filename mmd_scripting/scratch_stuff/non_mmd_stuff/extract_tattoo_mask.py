import numpy as np
from PIL import Image

from mmd_scripting.scratch_stuff.progprint import progprint, progclean

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.5.01 - 09/13/2020"
"""
Given a no-tattoo body and a tattoo body, and a single color, calc the transparency needed
to create the tattoo mask sitting on top of the no-tattoo body to create the tattoo body.
"""

WITHTATS = "Body_bunny2.png"
WITHOUTTATS = "Body_bunny_notats3.png"
OUTPUT = "mask.png"


# pink1 = (249, 63, 125)
# pink2 = (200, 14, 90)
MASK_COLOR = (249, 63, 125)

# alpha blending: 255=opaque
# C = (alpha * A) + ((1 - alpha) * B)
# C = alpha * (A-B) + B

# # single pixel alpha blend
# def alpha_blend(px_bg, px_fg, alpha):
# 	# c = (alpha * px_fg) + ((1 - alpha) * px_bg)
# 	c = (alpha * (px_fg - px_bg)) + px_bg

# bulk alpha blend using numpy trickery
def alpha_blend_bulk(px_bg, px_fg, alpha_list):
	t = px_fg - px_bg
	t2 = alpha_list * t
	r = t2 + px_bg
	return r
	

def solvemask(notats, tats, color):
	print("prepping")
	# turn image object into list of pixels
	notats_data = list(notats.getdata())
	tats_data = list(tats.getdata())
	# convert to numpy float-mode
	notats_data = np.array(notats_data, dtype="float64") / 255
	tats_data = np.array(tats_data, dtype="float64") / 255
	
	color = np.array(color) / 255
	
	# for each pixel value, compare before & after to find what % of the specified color should be added
	# do this by trying all 0-255 possible alpha values
	# for each alpha value, do the alpha blending algorithm, get the resulting color, and compare against the "after" color
	# component-wise R G B difference, squared, averaged to get mean-square-error
	# select the alpha with the min MSE
	
	# pre-calculate the float versions of the alpha values
	alpha_list = np.arange(256, dtype="float64") / 255
	alpha_list = alpha_list.reshape((256,1))
	
	# this holds resulting alpha values
	alpha = np.zeros(tats_data.shape[0], dtype="uint8")
	# this is a temp buffer used to store the MSE
	blend_list = np.zeros(256, dtype="float64")
	mse = np.zeros(256, dtype="float64")
	
	print("running")
	for d, (before, after) in enumerate(zip(notats_data, tats_data)):
		progprint(d / tats_data.shape[0])
		# first check shortcuts
		if np.array_equal(before, after):
			alpha[d] = 0  # transparent
			continue
		if np.array_equal(before, color):
			alpha[d] = 255  # opaque
			continue
		# now do the hard way
		# calc resulting colors after multiplying with all possible alphas
		blend_list = alpha_blend_bulk(before, color, alpha_list)
		# now calculate the error
		mse = blend_list - after
		# then square
		mse = np.square(mse)
		# then mean
		mse = np.mean(mse, axis=1)
		# then find the lowest error
		bestfit = np.argmin(mse)
		alpha[d] = bestfit
		
		# print(before, after)
	progclean()
	print("done iterating")
	nonzero = np.count_nonzero(alpha)
	print("mask covers %f%%" % (100 * nonzero / alpha.size))
	opaque = np.count_nonzero(alpha == 255)
	print("mask opaque %f%%" % (100 * opaque / alpha.size))
	# # convert results from 1d array to 2d array
	# alpha = alpha.reshape(tats.size)
	return alpha


def main():
	print("reading")
	tats = Image.open(WITHTATS)
	notats = Image.open(WITHOUTTATS)
	assert(tats.mode == notats.mode)
	assert(tats.size == notats.size)
	
	print("notats = '%s'" % WITHOUTTATS)
	print("tats =   '%s'" % WITHTATS)
	print("color =  '%s'" % str(MASK_COLOR))
	print("output = '%s'" % OUTPUT)
	
	mask = solvemask(notats, tats, MASK_COLOR)
	
	# then build the result image from this color
	img = Image.new('RGB', tats.size, MASK_COLOR)
	# build a image-object from the mask
	img_mask = Image.new("L", tats.size)
	img_mask.putdata(mask)
	# stick the mask into the mono-color image
	img.putalpha(img_mask)
	img.save(OUTPUT)
	
	print("done!")
	return None
if __name__ == "__main__":
	print(_SCRIPT_VERSION)
	main()

