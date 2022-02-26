import numpy as np
import matplotlib.pyplot as plt
import logging

import vectorpaths

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Construct points along Archimedian spiral.
t = np.linspace(0,30,100)
r = 0 + 0.1*t
xc = r*np.cos(t)
yc = r*np.sin(t)

plt.subplot(1,2,1)
plt.plot(xc, yc, 'o')
# Fit bezier curves with a maximum error of 0.25.
beziers = vectorpaths.fit_cubic_bezier(xc, yc, 0.25)
print('Accuracy of 0.25 requires {} bezier patches'.format(len(beziers)))
[b.plot(color='r') for b in beziers]

# Fit bezier curves with a maximum error of 0.05.
beziers = vectorpaths.fit_cubic_bezier(xc, yc, 0.05)
print('Accuracy of 0.05 requires {} bezier patches'.format(len(beziers)))
[b.plot(color='b') for b in beziers]
plt.xlim([-4,4])
plt.ylim([-4,4])
plt.gca().set_aspect('equal')

plt.subplot(1,2,2)
plt.plot(xc, yc, 'o')
[b.plot(color='b') for b in beziers]
[b.plotcontrol() for b in beziers]
plt.xlim([-4,4])
plt.ylim([-4,4])
plt.gca().set_aspect('equal')
plt.show()
