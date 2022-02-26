"""Implementation for a cubic Bezier class.

"""
import numpy as np
import matplotlib.pyplot as plt

# from . import _path_logger

class CubicBezier:
	def __init__(self, p, px=None, py=None):
		"""Initialise a Cubic Bezier object.

		The cubic bezier can be setup either by supplying an (4,2) array/list
		of control points, or as separate arrays for the x and y coordinates.

		:param p: (4,2) array of control points with x in [:,0] and y in[:,1]
		:param px: (4,) array of control point x coordinates.
		:param py: (4,) array of control point y coordinates.
		"""
		if px is not None and py is not None:
			if len(px)!=4 or len(py)!=4:
				raise ValueError('Cubic beziers have exactly four control points')
			else:
				self._px = np.array(px)
				self._py = np.array(py)
		else:
			if len(np.array(p).shape)!=2:
				raise ValueError('Array of points must be 2D')
			else:
				if np.array(p).shape[1]!=2:
					raise ValueError('Expect axis 1 to contain x,y coords')
				else:
					self._px = np.array(p)[:,0]
					self._py = np.array(p)[:,1]

	def __repr__(self):
		return 'CubicBezier p0=({:.3g},{:.3g}) p1=({:.3g},{:.3g}) p2=({:.3g},{:.3g}) p3=({:.3g},{:.3g})'.format(
				self._px[0],self._py[0], self._px[1],self._py[1],
				self._px[1],self._py[2], self._px[3],self._py[3])

	def __str__(self):
		return 'CubicBezier p0=({:.3g},{:.3g}) p1=({:.3g},{:.3g}) p2=({:.3g},{:.3g}) p3=({:.3g},{:.3g})'.format(
				self._px[0],self._py[0], self._px[1],self._py[1],
				self._px[1],self._py[2], self._px[3],self._py[3])

	@property
	def p(self):
		"""Return coordinates of control points as an (4,2) array.

		:return: (4,2) array of control point coordinates.
		"""
		return np.hstack([self._px[:,None],self._py[:,None]])

	@property
	def px(self):
		"""Return x coordinates of control points.

		:return: (4,) array of control point x coordinates.
		"""
		return self._px

	@px.setter
	def px(self, v):
		"""Set x coordinates of control points.

		:param v: (4,) array of new control point x coordinates."""
		self._px = v

	@property
	def py(self):
		"""Return y coordinates of control points.

		:return: (4,) array of control point x coordinates.
		"""
		return self._py

	@py.setter
	def py(self, v):
		"""Set y coordinates of control points.

		:param v: (4,) array of new control point x coordinates.
		"""
		self._py = v

	def x(self, t):
		"""Get x coordinate of the point t along the bezier.

		:param t: (n,) array of parameters, t
		:return: (n,) array of x coordinates at the points, t.
		"""
		return self._q(self._px, t)

	def y(self, t):
		"""Get y coordinate of the point t along the bezier.

		:param t: (n,) array of parameters, t
		:return: (n,) array of y coordinates at the points, t.
		"""
		return self._q(self._py, t)

	def xy(self, t):
		"""Get x and y coordinates of points as an (n,2) array.

		:param t: (n,) array of parameters, t
		:return: (n,2) array of coordinates at the points, t.
		"""
		p = np.zeros((len(t),2))
		p[:,0] = self._q(self._px, t)
		p[:,1] = self._q(self._py, t)
		return p

	def xyprime(self, t):
		"""Get dx/dt and dy/dt of points at t as an (n,2) array.

		:param t: (n,) array of parameters, t
		:return: (n,2) array of first derivatives at the points, t.
		"""
		p = np.zeros((len(t),2))
		p[:,0] = self._qprime(self._px, t)
		p[:,1] = self._qprime(self._py, t)
		return p

	def xyprimeprime(self, t):
		"""Get d^2x/dt^2 and d^2y/dt^2 of points at t as an (n,2) array.

		:param t: (n,) array of parameters, t
		:return: (n,2) array of second derivatives at the points, t.
		"""
		p = np.zeros((len(t),2))
		p[:,0] = self._qprimeprime(self._px, t)
		p[:,1] = self._qprimeprime(self._py, t)
		return p

	def dxdt(self, t):
		"""Return the first derivative dx/dt at the point(s) t

		:param t: (n,) array of parameters, t
		:return: (n,) array of dx/dt at the points, t.
		"""
		return self._qprime(self._px, t)

	def dydt(self, t):
		"""Return the first derivative dy/dt at the point(s) t

		:param t: (n,) array of parameters, t
		:return: (n,) array of dy/dt at the points, t.
		"""
		return self._qprime(self._py, t)

	def dx2dt2(self, t):
		"""Return the second derivative dx/dt at the point(s) t

		:param t: (n,) array of parameters, t
		:return: (n,) array of d^2x/dt^2 at the points, t.
		"""
		return self._qprimeprime(self._px, t)

	def dy2dt2(self, t):
		"""Return the Second derivative dy/dt at the point(s) t

		:param t: (n,) array of parameters, t
		:return: (n,) array of d^2y/dt^2 at the points, t.
		"""
		return self._qprimeprime(self._py, t)

	def plot(self, ax=None, num_t=50, **kwargs):
		"""Plot this bezier

		Other arguments are passed onto Matplotlib.pyplot.plot so that the
		curve can be styled, e.g., colour, width.

		:param ax: (optional) Matplotlib axes into which to plot the Bezier.
		:param num_t (optional) Number of points along the Bezier to plot.
		"""
		t = np.linspace(0, 1, num_t)
		if ax is None:
			plt.plot(self.x(t), self.y(t), **kwargs)
		else:
			ax.plot(self.x(t), self.y(t), **kwargs)

	def plotcontrol(self, ax=None, num_t=50, **kwargs):
		"""Plot this control polygon for this bezier

		Other arguments are passed onto Matplotlib.pyplot.plot so that the
		curve can be styled, e.g., colour, width.

		:param ax: (optional) Matplotlib axes into which to plot the Bezier.
		:param num_t (optional) Number of points along the Bezier to plot.
		"""
		if ax is None:
			plt.plot(self._px[0], self._py[0], 'ko', markerfacecolor='k', **kwargs)
			plt.plot(self._px[1], self._py[1], 'ko', fillstyle='none', **kwargs)
			plt.plot(self._px[2], self._py[2], 'ko', fillstyle='none', **kwargs)
			plt.plot(self._px[3], self._py[3], 'ko', markerfacecolor='k', **kwargs)
			plt.plot(self._px[0:2], self._py[0:2], '--k', **kwargs)
			plt.plot(self._px[2:4], self._py[2:4], '--k', **kwargs)
		else:
			ax.plot(self._px[0], self._py[0], 'ko', markerfacecolor='k', **kwargs)
			ax.plot(self._px[1], self._py[1], 'ko', fillstyle='none', **kwargs)
			ax.plot(self._px[2], self._py[2], 'ko', fillstyle='none', **kwargs)
			ax.plot(self._px[3], self._py[3], 'ko', markerfacecolor='k', **kwargs)
			ax.plot(self._px[0:2], self._py[0:2], '--k', **kwargs)
			ax.plot(self._px[2:4], self._py[2:4], '--k', **kwargs)

	@staticmethod
	def _q(p, t):
		"""Evaluate the cubic Bezier at points t.

		:param p: (n,) array of control points.
		:param t: (n,) array of parameter points
		:return: (n,) array of coordinates.
		"""
		return ((1.0-t)**3)*p[0] + (3*(1.0-t)**2*t)*p[1] + (3*(1.0-t)*t**2)*p[2] + (t**3)*p[3]

	@staticmethod
	def _qprime(p, t):
		"""Evaluate the first derivative of the cubic Bezier at points t

		:param p: (n,) array of control points.
		:param t: (n,) array of parameter points
		:return: (n,) array of first derivatives.
		"""
		return (3*(1.0-t)**2)*(p[1]-p[0]) + (6*(1.0-t)*t)*(p[2]-p[1]) + (3*t**2)*(p[3]-p[2])

	@staticmethod
	def _qprimeprime(p, t):
		"""Evaluate the second derivative of the cubic Bezier at points t

		:param p: (n,) array of control points.
		:param t: (n,) array of parameter points
		:return: (n,) array of second derivatives.
		"""
		return (6*(1.0-t))*(p[2]-2*p[1]+p[0]) + 6*(t)*(p[3]-2*p[2]+p[1])
