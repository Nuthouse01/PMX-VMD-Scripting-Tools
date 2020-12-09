
# simple resource to just implement a progress tracker system
# print "0%" thru "100%" as a thing runs so you can guesstimate how long it will take to finish
# "normal" one-line overwrite method is to print string then \r and not \n, so "cursor" is moved to beginning of line and next print will overwrite what you just did
# (pycharm does not like leaving the cursor at the beginning of the line)
# so it works in pycharm, to "overwrite" a line you need to leave the "cursor" at the end of the line
# therefore you need to BEGIN each print statement with a \r

# to reduce number of prints, only print when progress threshold has increased by more than 5%
LAST_PRINT = -1
PRINT_INTERVAL = 0.01

def progprint(p):
	# if p is less than last print, probably starting over from 0. print no matter what
	# or, if p has passed the interval amount, then also print
	global LAST_PRINT
	if p <= LAST_PRINT or p >= (LAST_PRINT + PRINT_INTERVAL):
		# i am printing this! so, save it
		LAST_PRINT = p
		# actually print
		printme = "\r" + "{:6.1%}".format(p)
		print(printme, end="")
		# print(printme)
	return

def progclean():
	# back to beginning of line, wipe the progress printout, and back to beginning of line again
	print("\r      \r", end="")
	