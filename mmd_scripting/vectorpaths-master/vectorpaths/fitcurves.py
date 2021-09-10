"""Code to fit Cubic Beziers to a set of points.

The original code was C++ code by Philip J. Schneider and published in
'Graphics Gems' (Academic Press, 1990) 'Algorithm for Automatically Fitting
Digitized Curves'.  This code is based on a Python implementation by
Volker Poplawski (Copyright (c) 2014).
"""
import numpy as np
import logging

from . import CubicBezier
from . import _path_logger


def fit_cubic_bezier(xc, yc, rms_err_tol, max_err_tol=None,
	max_reparam_iter=20):
	"""Fit a set of cubic bezier curves to points (xc,yc).

	:param xc: (n,) array of x coordinates of the points to fit.
	:param yc: (n,) array of y coordinates of the points to fit.
	:param rms_err_tol: RMS error tolerance (in units of xc and yc).
	:param max_err_tol: Tolerance for maximum error (in units of xc and yc).
	:param max_reparam_iter: Maximum number of reparameterisation iterations.
	"""
	_path_logger.debug('Fitting points')

	if len(xc)!=len(yc):
		raise ValueError('Number of x and y points does not match')
	p = np.zeros((len(xc),2))
	p[:,0] = xc
	p[:,1] = yc

	# Compute unit tangents at the end points of the points.
	left_tangent = _normalise(p[1,:]-p[0,:])
	right_tangent = _normalise(p[-2,:]-p[-1,:])

	return _fit_cubic(p, left_tangent, right_tangent, rms_err_tol,
						max_err_tol, 0, max_reparam_iter=max_reparam_iter)

def _fit_cubic(p, left_tangent, right_tangent, rms_err_tol, max_err_tol,
				depth, max_reparam_iter=20):
	"""Recursive routine to fit cubic bezier to a set of data points.

	:param p: (n,2) array of (x,y) coordinates of points to fit.
	:param left_tangent: (,2) tangent vector at the left-hand end.
	:param right_tangent: (,2) tangent vector at the right-hand end.
	:param rms_err_tol: RMS error tolerance (in units of xc and yc).
	:param max_err_tol: Tolerance for maximum error (in units of xc and yc).
	:param max_reparam_iter: Maximum number of reparameterisation iterations.
	"""
	REPARAM_TOL_MULTIPLIER = 4

	def _acceptable_error(rms_error, max_error, rms_err_tol, max_err_tol):
		if rms_error<rms_err_tol:
			if max_err_tol is not None:
				if max_error<max_err_tol:
					return True
				else:
					return False
			else:
				return True
		else:
			return False

	# Use heuristic if region only has two points in it.
	if (len(p) == 2):
		_path_logger.debug('Depth {}: Using heuristic for two points'.format(depth))
		dist = np.linalg.norm(p[0,:] - p[1,:])/3.0
		left = left_tangent*dist
		right = right_tangent*dist
		return [CubicBezier([p[0,:], p[0,:]+left, p[1,:]+right, p[1,:]])]

	# We have more than two points so try to fit a curve.
	u = _chord_length_parameterise(p)
	bezier = generate_bezier(p, u, left_tangent, right_tangent)

	# Compute the error of the fit.  If the error is acceptable then
	# return this bezier.
	rms_error, max_error, split_point = _compute_errors_and_split(p, bezier, u)
	if _acceptable_error(rms_error, max_error, rms_err_tol, max_err_tol):
		_path_logger.debug('Depth {}: Optimal solution found with RMS={} and maximum error={}'.format(depth, rms_error, max_error))
		return [bezier]

	# The error is too large, if it's not too big then try to find an
	# alternative reparameterisation that has a smaller error.
	if rms_error < REPARAM_TOL_MULTIPLIER*rms_err_tol:
		_path_logger.debug('Depth {}: Reparameterising RMS={} maximum error={}'.format(depth, rms_error, max_error))

		for i in range(max_reparam_iter):
			_path_logger.debug('Depth {}: Reparameterising step {:2d}/{:2d} with RMS={} maximum error={}'.format(depth, i, max_reparam_iter, rms_error, max_error))
			uprime = _reparameterise(bezier, p, u)
			bezier = generate_bezier(p, uprime, left_tangent, right_tangent)
			rms_error, max_error, split_point = _compute_errors_and_split(p, bezier, uprime)
			if _acceptable_error(rms_error, max_error, rms_err_tol, max_err_tol):
				_path_logger.debug('Depth {}: Optimal reparameterised solution found with RMS={} maximum error={}'.format(depth, rms_error, max_error))
				return [bezier]
			u = uprime
		_path_logger.debug('Depth {}: No optimal reparameterised solution found with RMS={} maximum error={} and split={} and length={}'.format(depth, rms_error, max_error, split_point, len(p)))

	# We can't refine this anymore, so try splitting at the maximum error point
	# and fit recursively.
	_path_logger.debug('Depth {}: Splitting'.format(depth))
	beziers = []
	centre_tangent = _normalise(p[split_point-1,:] - p[split_point+1,:])
	beziers += _fit_cubic(p[:split_point+1,:], left_tangent, centre_tangent, rms_err_tol, max_err_tol, depth+1, max_reparam_iter=max_reparam_iter)
	beziers += _fit_cubic(p[split_point:,:], -centre_tangent, right_tangent, rms_err_tol, max_err_tol, depth+1, max_reparam_iter=max_reparam_iter)

	return beziers


def generate_bezier(p, u, left_tangent, right_tangent):
	bezier = CubicBezier([p[0,:], [0,0], [0,0], p[-1,:]])

	# Compute the A matrix.
	A = np.zeros((len(u), 2, 2))
	A[:,0,:] = left_tangent[None,:] * (3*((1-u[:,None])**2))*u[:,None]
	A[:,1,:] = right_tangent[None,:] * 3*(1-u[:,None])*u[:,None]**2

	# Compute the C and X matrixes
	C = np.zeros((2, 2))
	C2 = np.zeros((2, 2))
	X = np.zeros(2)
	X2 = np.zeros(2)

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

def _chord_length_parameterise(p):
	"""Assign parameter values to points using relative distances"""

	rel_dist = np.zeros(len(p))
	rel_dist[1:] = np.linalg.norm(p[1:,:]-p[0:-1,:])
	u = np.cumsum(rel_dist)
	u /= u[-1]

	return u


def _reparameterise(bezier, p, u):
	delta = bezier.xy(u) - p
	numerator = np.sum(delta*bezier.xyprime(u))
	denominator = np.sum(bezier.xyprime(u)**2 + delta*bezier.xyprimeprime(u))
	if denominator==0.0:
		return u
	else:
		return u - numerator/denominator


def _compute_max_error(p, bezier, u):
	"""Compute the maximum error between a set of points and a bezier curve"""
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
	"""Compute the maximum and rms error between a set of points and a bezier curve"""
	dists = np.linalg.norm(bezier.xy(u)-p,axis=1)
	i = np.argmax(dists)
	rms = np.sqrt(np.mean(dists**2))

	if i==0:
		return 0.0, rms, len(p)//2
	elif i==len(p)-1:
		return 0.0, rms, len(p)//2
	else:
		return rms, dists[i], i


def _normalise(v):
	"""Normalise a vector"""
	if len(np.array(v).shape)==1:
		return v/np.linalg.norm(v)
	else:
		return np.divide(v, np.linalg.norm(v,axis=1)[:,None])
