
import sys
try:
	sys.path.append("../")
	from python import nuthouse01_core as core
	from python import nuthouse01_pmx_parser as pmxlib
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	core = pmxlib = None



# goal: recursively find all points of difference between two PMX files
# treating each pmx as a list-of-list-of-list-of-list, return the combination of indices that points at the different thing
# !!! assumes that the two files are nearly identical !!!


FLOAT_THRESHOLD = 0.0005
# recursively check for equality, using a loose comparison for floatingpoints
# operating on test file, the greatest difference introduced by quaternion transform is 0.000257
# lets set sanity-check threshold at double that, 0.0005
def recursively_compare(AAA,BBB):
	# inputs are two list-like items of equal (possibly zero) length
	# for each pair in the list,
	for idx,(A, B) in enumerate(zip(AAA, BBB)):
		
		# yield 1/true if it FAILS (different), do nothing if it matches
		# NO! i need to yield which index it was!
		if isinstance(A, float) and isinstance(B, float):
			# for floats specifically, replace exact compare with approximate compare
			if abs(A-B) >= FLOAT_THRESHOLD:
				yield [idx]
		# if both are iterable:
		elif isinstance(A, (list, tuple)) and isinstance(B, (list, tuple)):
			# if length is different, don't bother walking, just say it's different
			if len(A) != len(B):
				yield [idx]
			
			# if length is the same, then compare each element
			for returnval in recursively_compare(A, B):
				# this yields and lets me run each time it finds something that does not match
				yield [idx] + returnval

		# if not float and not list, then use standard compare
		else:
			if A != B:
				yield [idx]
	return





f1 = "foobar.pmx"
pmx1 = pmxlib.read_pmx(f1)

f2 = "whatev.pmx"
pmx2 = pmxlib.read_pmx(f2)


# i am giving the function two lists to walk in parallel, NOT two items
alldiff = recursively_compare(pmx1.list(), pmx2.list())
# it's an iterator thing so i need to iterate on it before it becomes a true list
# aka cast it to a list
alldiff = list(alldiff)
print(alldiff)

noverts = [d for d in alldiff if not (d[0] == 1 and d[2] == 2)]
print(len(noverts))
for diff in noverts:
	print(diff)


