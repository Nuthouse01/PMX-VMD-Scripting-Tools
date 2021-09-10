import json
# import numpy as np
import matplotlib.pyplot as plt
import logging

import vectorpaths

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Load points from JSON file.
with open('example2_data.json', 'r') as fh:
	data = json.load(fh)

plt.subplot(2,1,1)
plt.plot(data['test2']['x'], data['test2']['y'], '.k')

beziers = vectorpaths.fit_cubic_bezier(data['test2']['x'], data['test2']['y'], 5e4, None)
[b.plot(color='r') for b in beziers]

beziers = vectorpaths.fit_cubic_bezier(data['test2']['x'], data['test2']['y'], 5e4, 5e4)
[b.plot(color='g') for b in beziers]

beziers = vectorpaths.fit_cubic_bezier(data['test2']['x'], data['test2']['y'], 1e3, 1e4, max_reparam_iter=10)
[b.plot(color='b') for b in beziers]

plt.subplot(2,1,2)
plt.plot(data['test1']['x'], data['test1']['y'], '.k')

beziers = vectorpaths.fit_cubic_bezier(data['test1']['x'], data['test1']['y'], 5e4, None)
[b.plot(color='r') for b in beziers]

beziers = vectorpaths.fit_cubic_bezier(data['test1']['x'], data['test1']['y'], 5e4, 5e4)
[b.plot(color='g') for b in beziers]

beziers = vectorpaths.fit_cubic_bezier(data['test1']['x'], data['test1']['y'], 5e3, 1e4, max_reparam_iter=0)
[b.plot(color='b') for b in beziers]

plt.show()
