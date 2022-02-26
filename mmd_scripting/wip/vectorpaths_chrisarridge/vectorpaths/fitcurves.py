"""
Code to fit Cubic Beziers to a set of points.

The original code was C++ code by Philip J. Schneider and published in
'Graphics Gems' (Academic Press, 1990) 'Algorithm for Automatically Fitting
Digitized Curves'.
Python implementation by Volker Poplawski (Copyright (c) 2014).
Refactoring, optimization, and cleanup by Chris Arridge (Copyright (c) 2020).
"""
import numpy as np
# import logging

from . import CubicBezier
from . import _path_logger


def fit_cubic_bezier(xc, yc, rms_err_tol, max_err_tol=None,
					 max_reparam_iter=20,
					 return_best_onelevel=False):
	"""
	Fit a set of cubic bezier curves to points (xc,yc).
	The order of the datapoints matters, because the bezier attempts to visit
	the points in the order they are given.

	:param xc: (n,) array of x coordinates of the points to fit.
	:param yc: (n,) array of y coordinates of the points to fit.
	:param rms_err_tol: RMS error tolerance (in units of xc and yc).
	:param max_err_tol: (optional) Tolerance for maximum error (in units of xc and yc).
	:param max_reparam_iter: (optional) Maximum number of reparameterisation iterations.
	:param return_best_onelevel: if True, return the best-effort result without recursing
	:return: list of CubicBezier objects
	"""
	# _path_logger.debug('Fitting points')

	if len(xc)!=len(yc):
		raise ValueError('Number of x and y points does not match')
	p = np.zeros((len(xc),2))
	p[:,0] = np.array(xc)
	p[:,1] = np.array(yc)

	# Compute unit tangents at the end points of the points.
	left_tangent = _normalise(p[1,:]-p[0,:])
	right_tangent = _normalise(p[-2,:]-p[-1,:])

	return _fit_cubic(p, left_tangent, right_tangent, rms_err_tol, max_err_tol,
					  max_reparam_iter=max_reparam_iter,
					  return_best_onelevel=return_best_onelevel)

def _fit_cubic(p, left_tangent, right_tangent, rms_err_tol, max_err_tol,
			   max_reparam_iter=20,
			   depth=0,
			   return_best_onelevel=False):
	"""Recursive routine to fit cubic bezier to a set of data points.

	:param p: (n,2) array of (x,y) coordinates of points to fit.
	:param left_tangent: (,2) tangent vector at the left-hand end.
	:param right_tangent: (,2) tangent vector at the right-hand end.
	:param rms_err_tol: RMS error tolerance (in units of xc and yc).
	:param max_err_tol: Tolerance for maximum error (in units of xc and yc).
	:param max_reparam_iter: (optional) Maximum number of reparameterisation iterations.
	:param depth: (optional) count how deep the recursive rabbit hole goes, just for logging
	:param return_best_onelevel: (optional) if True, return the best-effort result without recursing
	:return: list of CubicBezier objects
	"""
	# this controls the error threshold for "the fit is so bad i'm just gonna split it right away instead of iterating"
	REPARAM_TOL_MULTIPLIER = 4

	def _acceptable_error(rms_error2, max_error2, rms_err_tol2, max_err_tol2):
		# if the RMS error passes AND the max error passes, return TRUE
		# but if the "max_err_tol" is None then that counts as the max error passing by default
		if rms_error2 < rms_err_tol2:
			if (max_err_tol2 is None) or (max_error2 < max_err_tol2):
				return True
			else:
				return False
		else:
			return False

	# Use heuristic if region only has two points in it.
	if len(p) == 2:
		_path_logger.debug('Depth {}: Using heuristic for two points'.format(depth))
		dist = np.linalg.norm(p[0,:] - p[1,:])/3.0
		left = left_tangent*dist
		right = right_tangent*dist
		return [(CubicBezier([p[0,:], p[0,:]+left, p[1,:]+right, p[1,:]]), 0, 0)]

	# We have more than two points so try to fit a curve.
	u = _chord_length_parameterise(p)
	bezier = generate_bezier(p, u, left_tangent, right_tangent)

	# Compute the error of the fit.
	rms_error, max_error, split_point = _compute_errors_and_split(p, bezier, u)
	
	# if i want to return the "best" without recursing, keep reparameterizing until it stops improving
	if return_best_onelevel:
		prev_rms_error = rms_error
		i = 0
		for _ in range(300):
			i += 1
			_path_logger.debug('Force onelevel: Reparameterising step {:2d}/??? with RMSerr={:.4f} and MAXerr={:.4f}'.format(i, rms_error, max_error))
			uprime = _reparameterise(bezier, p, u)  # compute an incrementally better set of "parameters"
			bezier = generate_bezier(p, uprime, left_tangent, right_tangent)  # generate a new bez from these params
			rms_error, max_error, split_point = _compute_errors_and_split(p, bezier, uprime)  # calculate the error of the new bez
			# if the rms is not improving quickly enough, stop.
			if prev_rms_error - rms_error < 0.0004:
				break
			u = uprime  # save the params for next loop iter
			prev_rms_error = rms_error  # save the params for next loop iter
		# okay, once it hits here then we've really bottomed out the rms. so how good is it? return regardless
		if _acceptable_error(rms_error, max_error, rms_err_tol, max_err_tol):
			_path_logger.debug('Force onelevel: Reparameterised solution! RMSerr={:.4f} and MAXerr={:.4f}'.format(rms_error, max_error))
		else:
			_path_logger.debug('Force onelevel: No reparameterised solution found with RMSerr={:.4f} and MAXerr={:.4f} and split={} and length={}'.format(rms_error, max_error, split_point, len(p)))
		return [(bezier, rms_error, max_error)]
	
	# If the error from the first fitting attempt is acceptable then return this bezier.
	if _acceptable_error(rms_error, max_error, rms_err_tol, max_err_tol):
		_path_logger.debug('Depth {}: First-try solution! RMSerr={:.4f} and MAXerr={:.4f}'.format(depth, rms_error, max_error))
		return [(bezier, rms_error, max_error)]

	# If the error is not too large, then try to find an alternative reparameterisation that has a smaller error.
	if rms_error < REPARAM_TOL_MULTIPLIER*rms_err_tol:

		for i in range(max_reparam_iter):
			_path_logger.debug('Depth {}: Reparameterising step {:2d}/{:2d} with RMSerr={:.4f} and MAXerr={:.4f}'.format(depth, i, max_reparam_iter, rms_error, max_error))
			uprime = _reparameterise(bezier, p, u)
			bezier = generate_bezier(p, uprime, left_tangent, right_tangent)
			rms_error, max_error, split_point = _compute_errors_and_split(p, bezier, uprime)
			if _acceptable_error(rms_error, max_error, rms_err_tol, max_err_tol):
				_path_logger.debug('Depth {}: Reparameterised solution! RMSerr={:.4f} and MAXerr={:.4f}'.format(depth, rms_error, max_error))
				return [(bezier, rms_error, max_error)]
			u = uprime
		_path_logger.debug('Depth {}: No reparameterised solution found with RMSerr={:.4f} and MAXerr={:.4f} and split={} and length={}'.format(depth, rms_error, max_error, split_point, len(p)))

	return []  # TODO kind of a hack
	# We can't refine this anymore, so try splitting at the maximum error point
	# and fit recursively.
	_path_logger.debug('Depth {}: Splitting at point {} of {}'.format(depth, split_point, len(p)))
	beziers = []
	centre_tangent = _normalise(p[split_point-1,:] - p[split_point+1,:])
	beziers += _fit_cubic(p[:split_point+1,:], left_tangent, centre_tangent, rms_err_tol, max_err_tol, max_reparam_iter=max_reparam_iter, depth=depth+1)
	beziers += _fit_cubic(p[split_point:,:], -centre_tangent, right_tangent, rms_err_tol, max_err_tol, max_reparam_iter=max_reparam_iter, depth=depth+1)

	return beziers


def generate_bezier(p, u, left_tangent, right_tangent) -> CubicBezier:
	"""
	Create a CubicBezier object from the list of points. It's generally a pretty close fit, but might need some
	reiteration later to get a better fit.
	:param p: (n,2) array of (x,y) coordinates of points to fit.
	:param u: (n,) array of floats, strictly increasing. the T-positions along the bezier that are "close" to the points p.
	:param left_tangent: (,2) tangent vector at the left-hand end.
	:param right_tangent: (,2) tangent vector at the right-hand end.
	:return: one CubicBezier object.
	"""
	bezier = CubicBezier([p[0,:], [0,0], [0,0], p[-1,:]])

	# Compute the A matrix.
	A = np.zeros((len(u), 2, 2))
	A[:,0,:] = left_tangent[None,:] * (3*((1-u[:,None])**2))*u[:,None]
	A[:,1,:] = right_tangent[None,:] * 3*(1-u[:,None])*u[:,None]**2

	# Compute the C and X matrixes
	C = np.zeros((2, 2))
	# C2 = np.zeros((2, 2))
	X = np.zeros(2)
	# X2 = np.zeros(2)

	# C[0,0] = dot(left tangent term, left tangent term)
	# C[0,1] = dot(left tangent term, right tangent term)
	# C[1,0] = dot(right tangent term, left tangent term)
	# C[1,1] = dot(right tangent term, right tangent term)
	tmp = CubicBezier([p[0,:], p[0,:], p[-1,:], p[-1,:]])
	C[0,0] = np.sum(A[:,0,0]*A[:,0,0] + A[:,0,1]*A[:,0,1])
	C[0,1] = np.sum(A[:,0,0]*A[:,1,0] + A[:,0,1]*A[:,1,1])
	C[1,0] = np.sum(A[:,1,0]*A[:,0,0] + A[:,1,1]*A[:,0,1])
	C[1,1] = np.sum(A[:,1,0]*A[:,1,0] + A[:,1,1]*A[:,1,1])
	dp_x = p[:,0] - tmp.x(u)
	dp_y = p[:,1] - tmp.y(u)
	X[0] = np.sum(A[:,0,0]*dp_x + A[:,0,1]*dp_y)
	X[1] = np.sum(A[:,1,0]*dp_x + A[:,1,1]*dp_y)

	# Compute the determinants of C and X.
	det_C0_C1 = C[0,0]*C[1,1] - C[1,0]*C[0,1]
	det_C0_X  = C[0,0]*X[1] - C[1][0]*X[0]
	det_X_C1  = X[0]*C[1,1] - X[1]*C[0,1]

	# Finally, derive alpha values
	alpha_l = 0.0
	alpha_r = 0.0
	if np.abs(det_C0_C1)>=1e-14:
		alpha_l = det_X_C1/det_C0_C1
		alpha_r = det_C0_X/det_C0_C1

	# If either alpha negative then we use the Wu/Barsky heuristic, and if
	# alpha is zero then there are coincident control points that give a
	# divide by zero during Newton-Raphson iteration.
	seg_length = np.linalg.norm(p[0,:] - p[-1,:])
	epsilon = 1.0e-6 * seg_length
	if alpha_l<epsilon or alpha_r<epsilon:
		# fall back on standard (probably inaccurate) formula, and subdivide further if needed.
		bezier.px[1] = bezier.px[0] + left_tangent[0]*seg_length/3.0
		bezier.py[1] = bezier.py[0] + left_tangent[1]*seg_length/3.0
		bezier.px[2] = bezier.px[3] + right_tangent[0]*seg_length/3.0
		bezier.py[2] = bezier.py[3] + right_tangent[1]*seg_length/3.0

	else:
		# First and last control points of the Bezier curve are positioned
		# exactly at the first and last data points.  Control points 1 and 2
		# are positioned an alpha distance on the left and right tangent
		# vectors left.
		bezier.px[1] = bezier.px[0] + left_tangent[0]*alpha_l
		bezier.py[1] = bezier.py[0] + left_tangent[1]*alpha_l
		bezier.px[2] = bezier.px[3] + right_tangent[0]*alpha_r
		bezier.py[2] = bezier.py[3] + right_tangent[1]*alpha_r

	return bezier

def _chord_length_parameterise(p) -> np.ndarray:
	"""
	Assign parameter values to points using relative distances.
	:param p: (n,2) array of (x,y) coordinates of points to fit.
	:return: (n,) array of floats, strictly increasing, [0.0-1.0], starts with 0 ends with 1.
	"""
	# this returns the "relative location of each point along the line-segment path that connects all the datapoints".
	# i.e. assuming the resulting bezier is roughly the same as the line-segment path, estimate the T value needed
	# to get the point along the bezier that is closest to the corresponding datapoint.
	rel_dist = np.zeros(len(p))
	rel_dist[1:] = np.linalg.norm(p[1:,:]-p[0:-1,:], axis=1)  # get the distance between each point and the one before it
	u = np.cumsum(rel_dist)  # each entry is the sum of itself plus all previous entries
	u /= u[-1]  # scale it down so the final entry is exactly 1.0
	return u


def _reparameterise(bezier, p, u) -> np.ndarray:
	"""
	When given a list of "parameters" (i.e. T-positions along the bezier that are close to the points p),
	recalculate and return a list of T-positions that are a slightly better match.
	:param bezier: CubicBezier object.
	:param p: (n,2) array of (x,y) coordinates of points to fit.
	:param u: (n,) array of floats, strictly increasing. the T-positions along the bezier that are "close" to the points p.
	:return: (n,) array of floats, strictly increasing. almost same as u, but a closer fit.
	"""
	delta_list = bezier.xy(u) - p  #(n,2)
	# ADD THE X COMPONENT TO THE Y COMPONENT, not sure why that's the right answer but it is
	# https://github.com/erich666/GraphicsGems/blob/master/gems/FitCurves.c line 343
	numerator_componentwise = delta_list*bezier.xyprime(u)  #(n,2)
	numerator = np.sum(numerator_componentwise, axis=1)  #(n,1)
	denominator_componentwise = bezier.xyprime(u)**2 + delta_list*bezier.xyprimeprime(u)  #(n,2)
	denominator = np.sum(denominator_componentwise, axis=1)  #(n,1)
	r = numerator/denominator  # do the divide (n,1)
	r = np.nan_to_num(r, copy=False, nan=0, posinf=0, neginf=0)  # handle any divide-by-zeros that happened
	return u - r


def _compute_max_error(p, bezier, u):
	"""Compute the maximum error between a set of points and a bezier curve"""
	# CURRENTLY UNUSED
	max_dist = 0.0
	split_point = len(p)//2

	dists = np.linalg.norm(bezier.xy(u)-p,axis=1)
	i = np.argmax(dists)

	if i==0:
		return 0.0, len(p)//2
	elif i==len(p)-1:
		return 0.0, len(p)//2
	else:
		return dists[i], i



def _compute_errors_and_split(p, bezier, u):
	"""
	Compute the maximum and rms error between a set of points and a bezier curve.
	If the point of max error is the head or tail, then split at the midpoint.
	:param p: (n,2) array of (x,y) coordinates of points to fit.
	:param bezier: CubicBezier object
	:param u: (n,) array of [0.0-1.0] floats, strictly increasing.
	:return: tuple of (RMS error, max error, idx of the point with the max error)
	"""
	dists = np.linalg.norm(bezier.xy(u)-p,axis=1)
	i = np.argmax(dists)
	rms = np.sqrt(np.mean(dists**2))

	if i==0 or i==len(p)-1:
		return rms, dists[i], len(p)//2
	else:
		return rms, dists[i], i


def _normalise(v):
	"""Normalise a vector"""
	if len(np.array(v).shape)==1:
		return v/np.linalg.norm(v)
	else:
		return np.divide(v, np.linalg.norm(v,axis=1)[:,None])
