"""
Created by Nuthouse01
Here's my package! I *think* if you just run the GUI it should run out-of-the-box with no extra configuration,
but to directly run any of the other files you need to execute "_RUN_THIS_TO_INSTALL.bat" and get this
directory properly registered as a "package" for your local Python.
Check out README.md for... well, everything I guess.
"""
__version__ = "v1.07.05"
__date__ = "2/26/2022"
__pkg_welcome__ = "mmd_scripting package: Nuthouse01 - %s - %s" % (__version__, __date__)
print(__pkg_welcome__)

# first, version check: verify that this is using python3
# i don't know if it will actually work in 3.4 but i know it will fail in any python2 version
# actually written/tested with 3.6.6 so guaranteed to work on that or higher
# between 3.4 and 3.6, who knows
import sys
if sys.version_info < (3, 6):
	print("Your version of Python is too old to run this script, please update!")
	print("Your current version = " + sys.version)
	print("Required version = (3.6.0) or higher")
	print("...press ENTER to exit...")
	input()
	exit()
