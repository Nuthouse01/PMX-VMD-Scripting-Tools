# Nuthouse01 - 03/14/2020 - v3.01
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

import sys
# first, version check: verify that this is using python3
# i don't know if it will actually work in 3.4 but i know it will fail in any python2 version
# actually written/tested with 3.6.6 so guaranteed to work on that or higher
# between 3.4 and 3.6, who knows
if sys.version_info < (3, 4):
	print("Your version of Python is too old to run this script, please update!")
	print("Your current version = " + sys.version)
	print("...press ENTER to exit...")
	input()
	exit()

import re
import unicodedata

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	import nuthouse01_core as core
	import nuthouse01_pmx_parser as pmxlib
	from __translate_data import frame_dict, morph_dict, bone_dict
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	core = pmxlib = frame_dict = morph_dict = bone_dict = None



# TODO: execution-time ask which translation provider to use?
# TODO: create temp file which records time of online transactions to prevent crossing Google's threshold?
# TODO: print translations to CSV text file, say "review the CSV and edit", then read the CSV and apply those changes

USE_GOOGLE_TRANSLATE = True
# set up jp_to_en_mymemory thingy
# TODO: special error message for if this package isn't installed

if USE_GOOGLE_TRANSLATE:
	from googletrans import Translator
	jp_to_en_google = Translator()
else:
	from translate import Translator
	# jp_to_en_mymemory = Translator(provider="mymemory", to_lang="en", from_lang="autodetect")  # doesn't work?
	jp_to_en_mymemory = Translator(provider="mymemory", to_lang="en", from_lang="ja")



# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = True


# when this is true, uniquify each JP name and EN name by appending *1 *2 *3 etc on the end of the name
# bad things happen when names aren't unique, so this is recommended
ALSO_UNIQUIFY_NAMES = True


# when this is true, it doesn't even attempt online translation. this way you can kinda run the script when
# you run into google's soft-ban.
DISABLE_INTERNET_TRANSLATE = True

# NEWLINE_ESCAPE_CHAR = "| "


def contains_jap_chars(text) -> bool:
	# /[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]/
	"""
	3040 - 30ff
	3400 - 4dbf
	4e00 - 9fff
	f900 - faff
	ff10 - ff5a
	ff66 - ff9f
	"""
	is_jap = re.compile("[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f\uff10-\uff5a]")
	match = is_jap.search(str(text))
	if match:
		# print("True;", str(text))
		return True
	# print("False;", str(text))
	return False


def num_doublewide_chars(string: str) -> int:
	return sum((unicodedata.east_asian_width(c) in "WF") for c in string)

def string_width_cjk(string: str) -> int:
	return len(string) + num_doublewide_chars(string)

def my_string_pad(string: str, width: int) -> str:
	# how big does it already print as?
	currsize = string_width_cjk(string)
	# therefore I need to append this many spaces
	padnum = width - currsize
	if padnum <= 0:
		return string
	else:
		return string + (" " * padnum)

def bulk_translate(jp_list: list) -> list:
	# take a list of strings, joins them into one string with newlines
	# hopefully that counts as "fewer requests" for google's API
	# tho in testing, sometimes translations produce different results if on their own vs in a newline list... oh well
	MAX_NUM_LINES = 30
	num_calls = (len(jp_list) // 30) + 2
	print("Making %d requests to Internet translate service..." % num_calls)
	start_idx = 0
	retme = []
	while start_idx < len(jp_list):
		core.print_progress_oneline(start_idx, len(jp_list))
		# if start_idx != 0:  # sleep 1sec each pass except the first
		# 	time.sleep(1)
		templist = jp_list[start_idx:start_idx+MAX_NUM_LINES]
		bigstr = "\n".join(templist)
		bigresult = actual_translate(bigstr)
		result_list = bigresult.split("\n")
		if len(result_list) != len(templist):
			print("Warning: translation messed up and merged some lines, no good way to tell which ones")
			result_list = ["error"] * len(templist)
		retme += result_list
		start_idx += MAX_NUM_LINES
	return retme

def actual_translate(jp_str: str) -> str:
	# acutally send a string to Google for translation
	if DISABLE_INTERNET_TRANSLATE:
		return jp_str
	if USE_GOOGLE_TRANSLATE:
		# google translate
		try:
			# r = jp_to_en_google.translate(jp_str, dest="en", src="ja")
			r = jp_to_en_google.translate(jp_str, dest="en")
			return r.text
		except Exception as e:
			print("")
			if hasattr(e, "doc"):
				print("Response from Google:")
				print(e.doc.split("\n")[7])
				print(e.doc.split("\n")[9])
			print("Google API has rejected the translate request")
			print("This is probably due to too many translate requests too quickly")
			print("Strangely, this lockout does NOT prevent you from using Google Translate thru your web browser.")
			core.pause_and_quit("Get a VPN or try again in about 1 day (TODO: CONFIRM LOCKOUT TIME)")
	else:
		# some other inferior free translate service called "mymemory"
		r = jp_to_en_mymemory.translate(jp_str)
		if "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS FOR TODAY" in r:
			print("")
			print(r)
			print("MyMemory has rejected the translate request")
			print("This is due to a cap on how much you can translate in a day.")
			core.pause_and_quit("Get a VPN or try again in about 1 day")
		return r


def fix_eng_name(name_jp: str, name_en: str) -> (str, None):
	# returns a new english name, might be the same as the existing english name
	# or returns None if tranlsation is needed
	
	# if en name is empty OR contains jap/cn OR is just whitespace:
	if (not name_en) or name_en.isspace() or contains_jap_chars(name_en):
		# if jp name does not contain jap/cn:
		if not contains_jap_chars(name_jp):
			# jp name is already good english, copy jp name -> en name
			return name_jp
		elif name_jp in morph_dict:
			# return known-good translations of semistandard morphs
			return morph_dict[name_jp]
		elif name_jp in bone_dict:
			# return known-good translations of semistandard bones
			return bone_dict[name_jp]
		elif name_jp in frame_dict:
			# return known-good translations of semistandard display frame names
			return frame_dict[name_jp]
		else:
			# translate jp name -> en name
			# return None so the translations can be done in bulk
			return None
	else:
		# name is good, no translate needed
		return name_en
	
def uniquify_name(used_names: set, new_name: str) -> str:
	# translation occurred! attempt to uniquify the new name by appending *2 *3 etc
	while new_name in used_names:
		starpos = new_name.rfind("*")
		if starpos == -1:  # suffix does not exist
			new_name = new_name + "*1"
		else:  # suffix does exist
			try:
				suffixval = int(new_name[starpos + 1:])
			except ValueError:
				suffixval = 1
			new_name = new_name[:starpos] + "*" + str(suffixval + 1)
	# one leaving that loop, we finally have a unique name
	return new_name


def main():
	# print info to explain the purpose of this file
	print("This tool fills out empty EN names in a PMX model with translated versions of the JP names.")
	print("This also ensures the JP and EN names are all unique.")
	print("Machine translation is never 100% reliable, so this is only a stopgap measure to eliminate all the 'Null_##'s and wrongly-encoded garbage and make it easier to use in MMD.")
	print("If you are able to use PMXE, I recommend you use this tool FIRST, and use PMXE's translation feature SECOND so that the semistandard bones/morphs it understands will have their correct names.")
	print("If you can't use PMXE, a bad translation is better than none at all!")
	print("Also, Google Translate only permits ~100 requests per hour, if you exceed this rate you will be locked out for 24 hours (TODO: CONFIRM LOCKOUT TIME)")
	# print info to explain what inputs it needs
	print("Inputs: PMX file 'model.pmx'")
	# print info to explain what outputs it creates
	print("Outputs: PMX file '[model]_translate.pmx'")
	print("")
	
	# prompt PMX name
	print("Please enter name of PMX model file:")
	input_filename_pmx = core.prompt_user_filename(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx)
	
	translate_maps = []
	# each entry is
	
	translate_queue = []
	translate_queue_idx = []
	
	print("Beginning translation, this may take several seconds")

	# header=0 is special cuz its not iterable:
	# translate name(jp=1,en=2)
	new_en_name = fix_eng_name(pmx[0][1], pmx[0][2])
	if new_en_name is None:
		# googletrans is required, store and translate in bulk later
		translate_queue.append(pmx[0][1])
		translate_queue_idx.append([0, 2])
	elif new_en_name != pmx[0][2]:
		# translated without going to internet
		# apply change & store in list for future printing
		newlist = ["modelname:", "trans_local:", pmx[0][2], new_en_name]
		translate_maps.append(newlist)
		pmx[0][2] = new_en_name
	# comment(jp=3,en=4)
	new_en_name = fix_eng_name(pmx[0][3], pmx[0][4])
	if new_en_name is None:
		# googletrans is required, store and translate in bulk later
		#### SPECIAL HANDLING! replace newlines with something
		# comment = pmx[0][3].replace("\n", NEWLINE_ESCAPE_CHAR)
		comment = pmx[0][3].replace("\r", "") # delete these chars
		comment = re.sub(r'\n\n+', r'\n\n', comment)
		# comment = comment.replace("\n", NEWLINE_ESCAPE_CHAR)
		new_en_name = actual_translate(comment)
		# translate_queue.append(comment)
		# translate_queue_idx.append([0, 4])
		newlist = ["modelcomment:", "trans_google:", "too_long_to_print", "too_long_to_print"]
		translate_maps.append(newlist)
		pmx[0][4] = new_en_name
	elif new_en_name != pmx[0][4]:
		# translated without going to internet
		# apply change & store in list for future printing
		newlist = ["modelcomment:", "trans_local:", "too_long_to_print", "too_long_to_print"]
		translate_maps.append(newlist)
		pmx[0][4] = new_en_name
	
	label_dict = {4:"material:", 5:"bone:", 6:"morph:", 7:"dispframe:"}
	
	# repeat the following for each category of names:
	# materials=4, bones=5, morphs=6, dispframe=7
	for cat_id in range(4,8):
		category = pmx[cat_id]
		# for each entry:
		for i,item in enumerate(category):
			#jp=0,en=1
			jp_name = item[0]
			en_name = item[1]
			# second, translate en name
			new_en_name = fix_eng_name(jp_name, en_name)
			if new_en_name is None:
				# googletrans is required, store and translate in bulk later
				translate_queue.append(jp_name)
				translate_queue_idx.append([cat_id, i])
			elif new_en_name != en_name:
				# translated without going to internet
				# apply change & store in list for future printing
				item[1] = new_en_name
				newlist = [label_dict[cat_id] + str(i), "trans_local:", en_name, new_en_name]
				translate_maps.append(newlist)
			else:
				# no change
				pass
			
	# now bulk-translate all the strings that are queued
	if translate_queue:
		results = bulk_translate(translate_queue)
		# from the results, create list entries and also store the results
		for new_en_name, queue_idx in zip(results, translate_queue_idx):
			(cat_id, i) = queue_idx
			# special case for the header things
			if cat_id == 0:
				if i == 2:  # modelname
					newlist = ["modelname:", "trans_google:", pmx[0][2], new_en_name]
					translate_maps.append(newlist)
					pmx[0][2] = new_en_name
				# if i == 4:  # comment
				# 	newlist = ["modelcomment:", "trans_google:", "too_long_to_print", "too_long_to_print"]
				# 	translate_maps.append(newlist)
				# 	# need to undo the newline-hiding i did when giving it to Google
				# 	pmx[0][4] = new_en_name.replace(NEWLINE_ESCAPE_CHAR, "\n")
			else:
				newlist = [label_dict[cat_id] + str(i), "trans_google:", pmx[cat_id][i][1], new_en_name]
				translate_maps.append(newlist)
				pmx[cat_id][i][1] = new_en_name
	
	if ALSO_UNIQUIFY_NAMES:
		for cat_id in range(4, 8):
			category = pmx[cat_id]
			used_en_names = set()
			used_jp_names = set()
			for i, item in enumerate(category):
				jp_name = item[0]
				en_name = item[1]
				# first, uniquify the jp name
				new_jp_name = uniquify_name(used_jp_names, jp_name)
				used_jp_names.add(new_jp_name)
				if new_jp_name != jp_name:
					# build list entry & store into the structure
					newlist = [label_dict[cat_id] + str(i), "unique_JP:", jp_name, new_jp_name]
					translate_maps.append(newlist)
					item[0] = new_jp_name
				# second, uniquify the newly-translated en name
				new_en_name = uniquify_name(used_en_names, en_name)
				used_en_names.add(new_en_name)
				if new_en_name != en_name:
					# build list entry & store into the structure
					newlist = [label_dict[cat_id] + str(i), "unique_EN:", en_name, new_en_name]
					translate_maps.append(newlist)
					item[1] = new_en_name
	
	# done translating!!
	
	print("")
	
	# now display results!!
	print("Found %d instances where renaming was needed:" % len(translate_maps))
	if len(translate_maps) == 0:
		print("No changes are required")
		core.pause_and_quit("Done with everything! Goodbye!")
		return None
	
	# find max width of each column:
	width = [0,0,0,0]
	for tmap in translate_maps:
		for i in range(4):
			width[i] = max(width[i], string_width_cjk(tmap[i]))
	# now pretty-print the proposed list of translations:
	printme_list = []
	for tmap in translate_maps:
		args = []
		# python's formatting tool doesn't play nice with odd-width chars so I'll do it manually
		for i in range(4):
			args.append(my_string_pad(tmap[i], width[i]))
		# printme = "{} | EN: {} --> {} | JP: {} --> {}".format(*args)
		printme = "{} | {} | {} --> {}".format(*args)
		printme_list.append(printme)
		print(printme)
	# write list to file for better kanji displaying
	core.write_rawlist_to_txt(printme_list, "temp_translate.txt")
	# prompt for final confirmation
	print("Open 'temp_translate.txt' for better display of JP chars")
	print("Do you accept these new names?  1 = Yes, 2 = No (abort)")
	r = core.prompt_user_choice((1,2))
	if r == 2:
		core.pause_and_quit("Aborting: no names were changed")
		return None
	
	# write out
	output_filename_pmx = "%s_translate.pmx" % core.get_clean_basename(input_filename_pmx)
	# output_filename_pmx = input_filename_pmx[0:-4] + "_translate.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(pmx, output_filename_pmx)
	
	core.pause_and_quit("Done with everything! Goodbye!")
	return None


if __name__ == '__main__':
	print("Nuthouse01 - 03/14/2020 - v3.01")
	if DEBUG:
		main()
	else:
		try:
			main()
		except (KeyboardInterrupt, SystemExit):
			# this is normal and expected, do nothing and die normally
			pass
		except Exception as ee:
			# if an unexpected error occurs, catch it and print it and call pause_and_quit so the window stays open for a bit
			print(ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
