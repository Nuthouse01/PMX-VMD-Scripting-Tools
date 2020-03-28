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
from time import sleep, time

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	import nuthouse01_core as core
	import nuthouse01_pmx_parser as pmxlib
	from _local_translation_dicts import frame_dict, morph_dict, bone_dict
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
	print("...press ENTER to exit...")
	input()
	exit()
	core = pmxlib = frame_dict = morph_dict = bone_dict = None


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


# if true, use the good Google Translate service
# if false use the worse but less restrictive MyMemory translate service
USE_GOOGLE_TRANSLATE = True


# when this is true, it doesn't even attempt online translation. this way you can kinda run the script when
# you run into google's soft-ban.
DISABLE_INTERNET_TRANSLATE = False


# newlines in model comment get replaced with this when writing to "proposed_translations.txt"
NEWLINE_ESCAPE_CHAR = "§"


# to reduce the number of translation requests, a list of strings is joined into one string broken by newlines
# hopefully that counts as "fewer requests" for google's API
# tho in testing, sometimes translations produce different results if on their own vs in a newline list... oh well
# or sometimes they lose newlines during translation
# more lines per request = riskier, but uses less of your transaction budget
TRANSLATE_MAX_LINES_PER_REQUEST = 30
# how many requests are permitted per timeframe, to avoid the lockout
# true limit is ~100 so enforce limit of 80 just to be safe
TRANSLATE_BUDGET_MAX_REQUESTS = 80
# how long (hours) is the timeframe to protect
# true timeframe is ~1 hr so enforce limit of ~1.2hr just to be safe
TRANSLATE_BUDGET_TIMEFRAME = 1.2


# set up the acutal translator libraries & objects
try:
	import googletrans
	jp_to_en_google = googletrans.Translator()
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import primary translation provider library 'googletrans'")
	print("Please install this library with 'pip install googletrans'")
	print("Switching to backup provider MyMemory in library 'translate'")
	USE_GOOGLE_TRANSLATE = False
	googletrans = None

try:
	import translate
	# jp_to_en_mymemory = Translator(provider="mymemory", to_lang="en", from_lang="autodetect")  # doesn't work?
	jp_to_en_mymemory = translate.Translator(provider="mymemory", to_lang="en", from_lang="ja")
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import backup translation provider library 'translate'")
	print("Please install this library with 'pip install translate'")
	translate = None


################################################################################################################
def check_translate_budget(num_proposed: int) -> bool:
	# goal: block translations that would trigger the lockout
	# approach: create a persistient file that contains timestamps and # of requests sent then, to know if my proposed requests will exceed the budget
	
	# first, get path to persistient storage file, also creates an empty file if it doesn't exist
	recordpath = core.get_persistient_storage_path("translate_record.txt")
	# then read the file into memory, quietly
	record = core.read_txt_to_rawlist(recordpath, quiet=True)
	# discard all request records that are older than <timeframe>
	now = time()
	i = 0
	while i < len(record):
		if (now - record[i][0]) > (TRANSLATE_BUDGET_TIMEFRAME * 60 * 60):
			# print("debug: discard", record[i])
			record.pop(i)
		else:
			i += 1
	# then interpret the file: how many requests happened in the past <timeframe>
	requests_in_timeframe = sum([entry[1] for entry in record])
	print("You have used %d / %d translation requests within the last %d hrs" %
		  (requests_in_timeframe, TRANSLATE_BUDGET_MAX_REQUESTS, TRANSLATE_BUDGET_TIMEFRAME))
	# make the decision
	if (requests_in_timeframe + num_proposed) <= TRANSLATE_BUDGET_MAX_REQUESTS:
		# this many translations is OK! go ahead!
		# write this transaction into the record
		record.append([now, num_proposed])
		core.write_rawlist_to_txt(record, recordpath, quiet=True)
		return True
	else:
		# cannot do the translate, this would exceed the budget
		# bonus value: how long until enough records expire that i can do this?
		to_be_popped = 0
		idx = 0
		for idx in range(len(record)):
			to_be_popped += record[idx][1]
			if (requests_in_timeframe + num_proposed - to_be_popped) <= TRANSLATE_BUDGET_MAX_REQUESTS:
				break
		# when record[idx] becomes too old, then the current proposed number will be okay
		waittime = record[idx][0] + (TRANSLATE_BUDGET_TIMEFRAME * 60 * 60) - now
		# convert seconds to minutes
		waittime = round(waittime / 60)
		print("BUDGET: you must wait %d minutes before you can do %d more translation requests with Google" % (waittime, num_proposed))
		
		return False


################################################################################################################

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
	# split/join a massive list of items to translate into fewer requests which each contain many separated by newlines
	retme = []
	start_idx = 0
	while start_idx < len(jp_list):
		core.print_progress_oneline(start_idx, len(jp_list))
		if USE_GOOGLE_TRANSLATE:
			if start_idx != 0:  # sleep 1sec each query except the first, to prevent google from getting mad
				sleep(1)
			input_list = jp_list[start_idx:start_idx + TRANSLATE_MAX_LINES_PER_REQUEST]
			bigstr = "\n".join(input_list)
			bigresult = actual_translate(bigstr)
			result_list = bigresult.split("\n")
			if len(result_list) != len(input_list):
				print("Warning: translation messed up and merged some lines, please manually fix the bad outputs")
				print(len(result_list), len(input_list), result_list)
				result_list = ["error"] * len(input_list)
			retme += result_list
			start_idx += TRANSLATE_MAX_LINES_PER_REQUEST
		else:
			# mymemory limit is # of words, not # of transactions, so there's no reason to join them together
			# this way is slower, however
			retme.append(actual_translate(jp_list[start_idx]))
			start_idx += 1
	return retme


def actual_translate(jp_str: str) -> str:
	# acutally send a single string to Google for translation
	if DISABLE_INTERNET_TRANSLATE:
		return jp_str
	if USE_GOOGLE_TRANSLATE:
		# google translate
		try:
			# TODO: is it better to specify jap, or to use autodetect?
			# r = jp_to_en_google.translate(jp_str, dest="en", src="ja")  # jap
			r = jp_to_en_google.translate(jp_str, dest="en")  # auto
			return r.text
		except Exception as e:
			print("error")
			if hasattr(e, "doc"):
				print("Response from Google:")
				print(e.doc.split("\n")[7])
				print(e.doc.split("\n")[9])
			print("Google API has rejected the translate request")
			print("This is probably due to too many translate requests too quickly")
			print("Strangely, this lockout does NOT prevent you from using Google Translate thru your web browser. So go use that instead.")
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
	
def begin():
	# print info to explain the purpose of this file
	print("This tool fills out empty EN names in a PMX model with translated versions of the JP names.")
	print("Machine translation is never 100% reliable, so this is only a stopgap measure to eliminate all the 'Null_##'s and wrongly-encoded garbage and make it easier to use in MMD.")
	print("A bad translation is better than none at all!")
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
	return pmx, input_filename_pmx

def translate_to_english(pmx):
	# run thru all groups, find what can be locally translated, queue up what needs to be googled
	# do the same for model name
	# decide what to do for model comment, but store separately (compress newlines here!)
	# check logfile thing to see if i am near my budget for translations
	# actual translation: bulk translate
	# 	if needed, individual-translate comment with newlines intact, get result with newlines intact
	# print results to screen, also write to file
	# 	when printing comment, print "too_long_to_show"
	# 	when writing comment, replace all newlines with SOMETHING
	# then wait for user to approve the translations, or decline
	# then read the translation file which might have been edited by user
	# then apply the actual translations to the model
	#	comment will need to have all SOMETHINGs returned back to newlines
	# finally return
	
	
	translate_maps = []
	# each entry looks like this:
	# source, sourceid, (local / google / unique), "OLD EN:", old_en, "NEW EN:", new_en, "JP:", jp
	
	translate_queue = []  # just list of strings
	translate_queue_idx = []  # list of corresponding category ID + index within that category
	
	label_dict = {0: "header", 4: "material", 5: "bone", 6: "morph", 7: "dispframe"}
	inv_label_dict = {value: key for key, value in label_dict.items()}
	
	# repeat the following for each category of visible names:
	# materials=4, bones=5, morphs=6, dispframe=7
	for cat_id in range(4, 8):
		category = pmx[cat_id]
		# for each entry:
		for i, item in enumerate(category):
			# jp=0,en=1
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
				# newlist = [label_dict[cat_id] + str(i), "local", en_name, new_en_name]
				# source, sourceid, (local / google), "OLD EN:", old_en, "NEW EN:", new_en, "JP:", jp
				newlist = [label_dict[cat_id], str(i), "local", "OLD EN:", en_name, "NEW EN:", new_en_name, "JP:", jp_name]
				translate_maps.append(newlist)
			else:
				# no change
				pass
	
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
		newlist = [label_dict[0], "2", "local", "OLD EN:", pmx[0][2], "NEW EN:", new_en_name, "JP:", pmx[0][1]]
		translate_maps.append(newlist)
		pmx[0][2] = new_en_name
		
	
	# comment(jp=3,en=4)
	comment_state = 0
	comment_jp_clean = ""
	commentline_print = []
	commentline_write = []
	new_en_name = fix_eng_name(pmx[0][3], pmx[0][4])
	if new_en_name is None:
		# googletrans is required, store and translate in bulk later
		comment_state = 1
		# DOES get printed (as too_long_to_print), DOES go to translation file (newlines replaced with something) AFTER going to internet
		#### SPECIAL HANDLING! replace newlines with something
		# comment = pmx[0][3].replace("\n", NEWLINE_ESCAPE_CHAR)
		comment_jp_clean = pmx[0][3].replace("\r", "")  # delete these linereturn chars
		comment_jp_clean = re.sub(r'\n\n+', r'\n\n', comment_jp_clean)  # collapse multiple newlines to just 2
		# comment = comment.replace("\n", NEWLINE_ESCAPE_CHAR)
		# new_en_name = actual_translate(comment)
		# translate_queue.append(comment)
		# translate_queue_idx.append([0, 4])
	elif new_en_name != pmx[0][4]:
		# translated without going to internet (copied from jp)
		comment_state = 2
		# DOES get printed (as too_long_to_print), DOES go to translation file (newlines replaced with something) as it is now
		# apply change & store in list for future printing
		commentline_print = [label_dict[0], "4", "local", "OLD EN:", "too_long", "NEW EN:", "too_long_to_print", "JP:", "too_long"]
		comment_jp_write = pmx[0][3].replace("\r", "").replace("\n", NEWLINE_ESCAPE_CHAR)
		comment_en_old_write = pmx[0][4].replace("\r", "").replace("\n", NEWLINE_ESCAPE_CHAR)
		comment_en_new_write = new_en_name.replace("\r", "").replace("\n", NEWLINE_ESCAPE_CHAR)
		commentline_write = [label_dict[0], "4", "local", "OLD EN:", comment_en_old_write, "NEW EN:", comment_en_new_write, "JP:", comment_jp_write]
		pmx[0][4] = new_en_name
	
	# return having changed nothing IF translate_queue is empty, translate_budget fails, or user declines
	
	if (not translate_queue) and (comment_state == 0):
		print("No changes are required")
		return pmx, False
	
	# num + 1 + 1(if translating comment)
	num_items = len(translate_queue) + (comment_state == 1)
	num_calls = (len(translate_queue) // TRANSLATE_MAX_LINES_PER_REQUEST) + 1 + (comment_state == 1)
	print("Identified %d items that need Internet translation" % num_items)
	print("Making %d requests to Google Translate web API..." % num_calls)
	
	global USE_GOOGLE_TRANSLATE
	
	if not check_translate_budget(num_calls):
		# shift over to mymemory provider and continue if google is full
		print("Switching from GoogleTranslate (preferred) to MyMemory (backup), expect slower translation and worse results")
		USE_GOOGLE_TRANSLATE = False
		# no need to print failing statement, the function already does
		return pmx, False
	
	print("Beginning translation, this may take several seconds")
	if USE_GOOGLE_TRANSLATE:
		print("Using Google Translate web API for translations")
	else:
		print("Using MyMemory free translate service for translation")
		
	# now bulk-translate all the strings that are queued
	results = bulk_translate(translate_queue)
	# then assemble these results into the translate_map entries, but DON'T APPLY THE RESULTS!
	for new_en_name, queue_idx in zip(results, translate_queue_idx):
		(cat_id, i) = queue_idx
		# special case for the header things
		if cat_id == 0:
			if i == 2:  # modelname
				newlist = [label_dict[cat_id], str(i), "google", "OLD EN:", pmx[0][2], "NEW EN:", new_en_name, "JP:", pmx[0][1]]
				translate_maps.append(newlist)
		else:
			newlist = [label_dict[cat_id], str(i), "google", "OLD EN:", pmx[cat_id][i][1], "NEW EN:", new_en_name, "JP:", pmx[cat_id][i][0]]
			translate_maps.append(newlist)
	# translate_maps is used for both printing and writing

	# if comment needs translated, do that separately
	if comment_state == 1:
		# already removed linereturn and collapsed newlines, ready to go
		newcomment = actual_translate(comment_jp_clean)
		commentline_print = [label_dict[0], "4", "google", "OLD EN:", "too_long", "NEW EN:", "too_long_to_print", "JP:", "too_long"]
		comment_jp_write = comment_jp_clean.replace("\n", NEWLINE_ESCAPE_CHAR)
		comment_en_old_write = pmx[0][4].replace("\r", "").replace("\n", NEWLINE_ESCAPE_CHAR)
		comment_en_new_write = newcomment.replace("\r", "").replace("\n", NEWLINE_ESCAPE_CHAR)
		commentline_write = [label_dict[0], "4", "google", "OLD EN:", comment_en_old_write, "NEW EN:", comment_en_new_write, "JP:", comment_jp_write]

	# done translating!!

	# now i use comment_state to know how to handle the comment
	# and i use commentline_print and _write to print it and write it
	
	#######################################
	# next stage is writing and printing, then wait for approval
	# printing requires formatting so things display in nice columns
	print("Found %d instances where renaming was needed:" % (len(translate_maps) + (comment_state != 0)))
	
	# find max width of each column:
	width = [0] * 9
	for i in range(len(commentline_print)):
		width[i] = max(width[i], string_width_cjk(commentline_print[i]))
	for tmap in translate_maps:
		for i in range(9):
			if i in (4,6,8):
				tmap[i] = "'" + tmap[i] + "'"
			width[i] = max(width[i], string_width_cjk(tmap[i]))
	# now pretty-print the proposed list of translations:
	for tmap in translate_maps:
		args = []
		# python's formatting tool doesn't play nice with odd-width chars so I'll do it manually
		for i in range(9):
			if i==5 or i==3:
				continue
			args.append(my_string_pad(tmap[i], width[i]))
		print("{}{} {} | EN: {} --> {} | {} {}".format(*args))
	if comment_state != 0:
		# pretend this was part of the list all along
		args = []
		# python's formatting tool doesn't play nice with odd-width chars so I'll do it manually
		for i in range(9):
			if i==5 or i==3:
				continue
			args.append(my_string_pad(commentline_print[i], width[i]))
		print("{}{} {} | EN: {} --> {} | {} {}".format(*args))
	
	# write
	writelist = list(translate_maps)
	if comment_state != 0:
		writelist.append(commentline_write)
	core.write_rawlist_to_txt(writelist, "proposed_translate.txt")
	
	# ask for approval
	print("Wait here and open 'proposed_translate.txt' for better display of JP chars or to manually edit the translation mapping")
	print("Do you accept these new names?  1 = Yes, 2 = No (abort)")
	r = core.prompt_user_choice((1,2))
	if r == 2:
		print("Aborting: no names were changed")
		return pmx, False

	###########################################
	# user has accepted the translations!!!
	# read back the proposed translation file
	readlist = core.read_txt_to_rawlist("proposed_translate.txt", quiet=True)
	
	# parse and apply what was read from the file
	for line in readlist:
		# unpack
		(cat_label, i, dum1, dum2, en_old, dum3, en_new, dum4, jp_name) = line
		cat_id = inv_label_dict[cat_label]
		# special case for the header things
		if cat_id == 0:
			if i == 2:  # modelname
				pmx[0][2] = en_new
			if i == 4:  # model comment
				# also un-escape the newlines
				pmx[0][4] = en_new.replace(NEWLINE_ESCAPE_CHAR, '\n')
		else:
			pmx[cat_id][i][1] = en_new
		
	return pmx, True
	
def end(pmx, input_filename_pmx):
	# write out
	output_filename_pmx = "%s_translate.pmx" % core.get_clean_basename(input_filename_pmx)
	# output_filename_pmx = input_filename_pmx[0:-4] + "_translate.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(pmx, output_filename_pmx)
	
	return None

def main():
	pmx, name = begin()
	pmx, is_changed = translate_to_english(pmx)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")


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
