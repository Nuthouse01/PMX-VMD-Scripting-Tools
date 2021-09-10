""" Tkinter demo gui for bezier fitting algorithm

	(c) Volker Poplawski 2014

	Updated to use new path class (10 May 2020, Chris Arridge).  Changes
	Copyright (c) Chris Arridge 2020.
"""
# from __future__ import print_function
import numpy as np
import vectorpaths
try:
	from Tkinter import *
except ImportError:
	from tkinter import *
import logging

# left click to add a datapoint
# left click and drag an existing point to move it
# middle click to delete last datapoint

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

# center of bounding box
def cntr(x1, y1, x2, y2):
	return x1+(x2-x1)/2, y1+(y2-y1)/2


# tkinter Canvas plus some addons
class MyCanvas(Canvas):
	def create_polyline(self, points, **kwargs):
		p = np.array(points)
		for i in range(len(p)-1):
			self.create_line(p[i,0], p[i,1], p[i+1,0], p[i+1,1], kwargs)


	def create_bezier(self, b, tag):
		self.create_polyline(b.xy(np.linspace(0,1,50)), tag=tag, fill='blue', width='2') # there are better ways to draw a bezier
		# # uncomment these to show the control points
		# self.create_line( *b.p[0], *b.p[1], tag=tag)
		# self.create_point(b.px[1], b.py[1], 2, fill='black', tag=tag)
		# self.create_line( *b.p[3], *b.p[2], tag=tag)
		# self.create_point(b.px[2], b.py[2], 2, fill='black', tag=tag)


	def create_point(self, x, y, r, **kwargs):
		return self.create_oval(x-r, y-r, x+r, y+r, kwargs)


	def pos(self, idOrTag):
		return cntr(*self.coords(idOrTag))


	def itemsAtPos(self, x, y, tag):
		return [item for item in self.find_overlapping(x, y, x, y) if tag in self.gettags(item)]


class MainObject:
	def run(self):
		root = Tk()

		self.canvas = MyCanvas(root, bg='white', width=400, height=400)
		self.canvas.pack(side=LEFT)

		frame = Frame(root, relief=SUNKEN, borderwidth=1)
		frame.pack(side=LEFT, fill=Y)
		label = Label(frame, text='RMS Error')
		label.pack()
		self.spinbox = Spinbox(frame, width=8, from_=0.0, to=1000000.0, command=self.onSpinBoxValueChange)
		self.spinbox.insert(0, 10.0)
		self.spinbox.pack()

		self.points = []
		self.draggingPoint = None

		self.canvas.bind('<ButtonPress-1>', self.onButton1Press)
		self.canvas.bind('<ButtonPress-2>', self.onButton2Press)
		self.canvas.bind('<B1-Motion>', self.onMouseMove)
		self.canvas.bind('<ButtonRelease-1>', self.onButton1Release)

		root.mainloop()


	def onButton1Press(self, event):
		items = self.canvas.itemsAtPos(event.x, event.y, 'point')
		if items:
			self.draggingPoint = items[0]
		else:
			self.points.append(self.canvas.create_point(event.x, event.y, 4, fill='red', tag='point'))
			self.redraw()


	def onButton2Press(self, _):
		self.canvas.delete(self.points.pop())
		self.redraw()


	def onMouseMove(self, event):
		if self.draggingPoint:
			self.canvas.coords(self.draggingPoint, event.x-4, event.y-4, event.x+4, event.y+4)
			self.redraw()


	def onButton1Release(self, _):
		self.draggingPoint = None


	def onSpinBoxValueChange(self):
		self.redraw()


	def redraw(self):
		# redraw line that connects the datapoints
		self.canvas.delete('polyline')
		self.canvas.create_polyline([self.canvas.pos(pId) for pId in self.points], fill='grey', tag='polyline')
		self.canvas.tag_lower('polyline')

		# redraw bezier
		if len(self.points) < 2:
			return

		# redraw all the beziers
		self.canvas.delete('bezier')
		points = np.array([self.canvas.pos(p) for p in self.points])
		# print(points)
		beziers = vectorpaths.fit_cubic_bezier(points[:,0], points[:,1], float(self.spinbox.get())**2)
		for bezier in beziers:
			self.canvas.create_bezier(bezier, tag='bezier')


if __name__ == '__main__':
	o = MainObject()
	o.run()
