# Created by Nuthouse01 - 7/12/2021 - v6.01

print("Package version: Nuthouse01 - 7/12/2021 - v6.01")

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

