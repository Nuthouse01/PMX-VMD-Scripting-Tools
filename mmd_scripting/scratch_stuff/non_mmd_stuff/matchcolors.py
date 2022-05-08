import pickle

from imageio import imread, imsave
from scipy import mean, interp, ravel, array

from mmd_scripting.scratch_stuff.progprint import progprint, progclean

_SCRIPT_VERSION = "Script version:  Nuthouse01 - 9/13/2020 - 5.01"

"""Usage: python matchcolors.py good.jpg bad.jpg save-corrected-as.jpg"""

def mkcurve(chan1,chan2):
	"""Calculate channel curve by averaging target values."""
	sums = {}
	asdf = ravel(chan1)
	asdff = len(asdf)
	for z, (v1, v2) in enumerate(zip(asdf, ravel(chan2))):
		progprint(z / asdff)
		try:
			sums[v1].append(v2)
		except KeyError:
			sums[v1] = [v2]
	c = array( [ (src,mean(vals)) for src,vals in sorted(sums.items()) ])
	nvals = interp(range(256), c[:,0], c[:,1], 0, 255)
	progclean()
	return dict(zip(range(256), nvals))

def correct_bad(good, bad, read=False):
	"""Match colors of the bad image to good image."""
	r, g, b = bad.transpose((2,0,1))
	r2, g2, b2 = good.transpose((2,0,1))
	corr = bad.copy()
	h, w = corr.shape[:2]
	if read:
		print("start r")
		rc = mkcurve(r,r2)
		print("start g")
		gc = mkcurve(g,g2)
		print("start b")
		bc = mkcurve(b,b2)
		print("pickling")
		with open('r.curve', 'wb') as rf:
			pickle.dump(rc, rf)	
		with open('g.curve', 'wb') as gf:
			pickle.dump(gc, gf)	
		with open('b.curve', 'wb') as bf:
			pickle.dump(bc, bf)	
	else:
		with open('r.curve', 'rb') as rf:
			rc = pickle.load(rf)	
		with open('g.curve', 'rb') as gf:
			gc = pickle.load(gf)	
		with open('b.curve', 'rb') as bf:
			bc = pickle.load(bf)	

	print("apply")
	for row in range(h):
		progprint(row / h)
		for col in range(w):
			r,g,b = corr[row,col]
			corr[row,col] = [rc[r], gc[g], bc[b]]
	progclean()
	return corr


def main():
	#good, bad, saveas = sys.argv[1:1+3]
	good = "Body_bunny2.png"
	bad = "Body_bunny_notats3.png"
	saveas = "Corrected.png"
	READCURVE = False
	good = imread(good)
	bad = imread(bad)
	assert(good.shape == bad.shape)
	corrected = correct_bad(good, bad, READCURVE)
	imsave(saveas, corrected)

if __name__ == "__main__":
	print(_SCRIPT_VERSION)
	main()
	
	
	
'''
def make_colorcorrect_curve(chan1: np.ndarray, chan2: np.ndarray, keepPercent=0.5) -> dict:
	"""Calculate channel curve by averaging target values."""
	# this will probably work better AFTER shrinking to blur the dot matrixes
	# chan1 = bad
	# chan2 = good
	assert chan1.shape[0:2] == chan2.shape[0:2]
	mapping_dict = {}
	for z, (row1, row2) in enumerate(zip(chan1, chan2)):
		# progprint only from 0% to 70%
		progprint((z / len(chan1)) / 1.42)
		for px1, px2 in zip(row1, row2):
			try:
				mapping_dict[px1].append(px2)
			except KeyError:
				mapping_dict[px1] = [px2]
	# mapping_dict: key=bad px value, val = list of px val at corresponding locations in good
	# turn it into a dict of [badval, mean(goodval) for all values of badval that appear
	
	means_dict = {}
	for key in mapping_dict:
		means_dict[key] = np.average(mapping_dict[key])
		
	# calculate the variance of the pixels that contribute to each pixel value
	stdev_dict = {}
	for key in mapping_dict:
		stdev_dict[key] = np.std(mapping_dict[key])
	
	# # unzip for printing
	# stdev_keys, stdev_vals = zip(*sorted(stdev_dict.items()))
	# means_keys, means_vals = zip(*sorted(means_dict.items()))

	# discard the pixels with the highest variance???
	# sort into ascending variance, so the head is the good part
	a = list(sorted(stdev_dict.items(), key=lambda x: x[1]))
	# take the first, like, half of the list? idk
	a = a[0:int(len(a) * keepPercent)]
	# unzip
	good_keys, good_vals = zip(*a)
	# discard the pixels that aren't in the good-list
	for key in list(means_dict.keys()):
		if key not in good_keys:
			means_dict.pop(key)
			
	# ensure it has proper endpoints
	if 0 not in means_dict:
		means_dict[0] = 0
	if 255 not in means_dict:
		means_dict[255] = 255
	
	means_keys_sparse, means_vals_sparse = zip(*sorted(means_dict.items()))

	# fill out any points that might be unfilled with linear interpolating between them
	for i in range(256):
		if i not in means_dict:
			v = np.interp(i, xp=means_keys_sparse, fp=means_vals_sparse, left=0, right=255)
			means_dict[i] = v
	# lastly, make all the means into INTEGERS
	for key in means_dict:
		means_dict[key] = round(means_dict[key])
		
	# means_keys_filled, means_vals_filled = zip(*sorted(means_dict.items()))
	# fig, [ax1,ax2] = plt.subplots(nrows=2, ncols=1, squeeze=True)
	# ax1.plot(stdev_keys, stdev_vals, label="stdev")
	# ax1.grid()
	# ax2.legend()
	# ax2.plot(means_keys, means_vals, label="raw map")
	# ax2.plot(means_keys_filled, means_vals_filled, label="new")
	# ax2.grid()
	# ax2.legend()
	# plt.show(block=True)

	# progclean()
	return means_dict

def colorcorrect_image(good: np.ndarray, bad: np.ndarray) -> np.ndarray:
	"""Match colors of the bad image to good image."""
	# NOTE: currently designed for GRAYSCALE! no plane-splitting nonsense
	r = bad
	r2 = good
	corr = bad.copy()
	h, w = corr.shape[:2]
	rc = make_colorcorrect_curve(r,r2, COLORCORRECT_VARIANCE_FILTER_PCT)

	# stuff = sorted(list(rc.items()))
	# for s in stuff:
	# 	print(s)
	# x,y = zip(*stuff)
	# plt.plot(x,y)
	# plt.show(block=True)
	
	for row in range(h):
		# progprint only from 70% to 100%
		progprint(((row / h)/3.33) + .7)
		for col in range(w):
			corr[row,col] = rc[corr[row,col]]
	progclean()
	return corr
'''