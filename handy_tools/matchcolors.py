"""Usage: python matchcolors.py good.jpg bad.jpg save-corrected-as.jpg"""

from imageio import imread, imsave
from scipy import mean, interp, ravel, array
import sys
from progprint import progprint, progclean
import pickle

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
	main()