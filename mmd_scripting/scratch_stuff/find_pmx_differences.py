import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.5.08 - 6/3/2021"



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
		
		# yield which index it was when there is a difference!!!
		
		if isinstance(A, float) and isinstance(B, float):
			# for floats specifically, replace exact compare with approximate compare
			if abs(A-B) >= FLOAT_THRESHOLD:
				yield [idx]
		# if both are iterable:
		elif isinstance(A, (list, tuple)) and isinstance(B, (list, tuple)):
			# if length is different, say it's different
			if len(A) != len(B):
				yield [idx]
			
			# if length is the same, then compare each element
			for returnval in recursively_compare(A, B):
				# this yields and lets me run each time it finds something that does not match
				yield [idx] + returnval

		# if not float and not iterable, then use standard compare
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
print(len(alldiff))

noverts = [d for d in alldiff if not (d[0] == 1 or d[0] == 2)]
print(len(noverts))
# for diff in noverts:
# 	print(diff)



# what do i want to see?
# first, make a dict. then gather all unique first elements from each of the returned lists, and make keys of those.
# what values go into these keys? the list of everything that started with that, minus the leading item which is now the key
# except, no, not a list of everything that started with that, it's another dict

# what do the frills look like when things are different lengths?

def recuse_diff_dict(list_of_lists):
	diff_dict = {}
	# # if this thing is all alone, return it
	if len(list_of_lists) == 1:
		return list_of_lists[0]
	curr = None
	sublist = []
	for i in range(len(list_of_lists)):
		if len(list_of_lists[i]) == 0:
			continue
		first_element = list_of_lists[i][0]
		item_without_first_element = list_of_lists[i][1:]  # this might be an empty list
		if first_element != curr:
			if curr is not None:
				# this is a new leading item! save the list i was building into the dict, and start a new one
				deeper_dict = recuse_diff_dict(sublist)
				diff_dict[curr] = deeper_dict  # store the thing i was building
				sublist = []  # reset the thing i was building
			curr = first_element  # move the "i was here last" pointer
		# add this item to the sublist, MIGHT BE EMPTY
		sublist.append(item_without_first_element)
	# also handle the last group
	# this is a new leading item! save the list i was building into the dict, and start a new one
	deeper_dict = recuse_diff_dict(sublist)
	diff_dict[curr] = deeper_dict  # store the thing i was building
	
	# for k in unique_first_elements:
	# 	# strip the first element
	# 	listthings_minus_first_element = [d[1:] for d in list_of_lists if len(d) > 1]
	# 	if listthings_minus_first_element:
	# 		# recurse!
	# 		deeper_dict = recuse_diff_dict(listthings_minus_first_element)
	# 	else:
	# 		deeper_dict = None
	# 	# put this result into the diff_dict under the key that leads it
	# 	diff_dict[k] = deeper_dict

	return diff_dict


something = recuse_diff_dict(alldiff)

print(something)