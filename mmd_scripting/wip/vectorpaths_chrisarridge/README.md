# vectorpaths
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)

This is a refactoring and repackaging of [Volker Poplawski's Python implementation](https://github.com/volkerp/fitCurves) of the `fitCurves` code for fitting [cubic](https://en.wikipedia.org/wiki/B%C3%A9zier_curve#Cubic_B%C3%A9zier_curves) [bezier curves](https://en.wikipedia.org/wiki/B%C3%A9zier_curve) to sets of points.  The implementation was originally written in C by Philip J. Schneider and published as "Algorithm for Automatically Fitting Digitized Curves" from the book "Graphics Gems".  The original C code is available in [Eric Haines' Github repository](https://github.com/erich666/GraphicsGems).

This refactoring puts the code within a package `paths` and places the cubic bezier code within a class.  The fitting code has been optimised slightly to use more numpy internal array functions.  The code has also had debug logging added.

The original Python implementation is Copyright (c) 2014 Volker Poplawski, and the original C code Copyright (c) 1990 Philip J. Schneider (Academic Press).  The modifications in this implementation are Copyright (c) 2020 Chris Arridge.  This is distributed under the terms of the [MIT License](./LICENSE).

## Installation

`python setup.py install`

## Example
This test example creates a set of points along an Archimedian spiral
and fits them to a set of cubic beziers.
```python
	import paths

	t = np.linspace(0,30,100)
	r = 0 + 0.1*t
	xc = r*np.cos(t)
	yc = r*np.sin(t)

	beziers = paths.fit_cubic_bezier(xc, yc, 0.25)
	plt.plot(xc, yc, 'o')
	[a.plot(color='r') for a in beziers]
	plt.show()
```

## Demo
The Tkinter-based demo from Volker Poplawski has been updated to use this path class.

![demo](https://github.com/chrisarridge/fitCurves/raw/master/demo_screenshot.png "demo.py")
