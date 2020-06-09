# Nuthouse01 - 06/08/2020 - v4.07
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

import re
from time import time

# second, wrap custom imports with a try-except to catch it if files are missing
try:
	from . import nuthouse01_core as core
	from . import nuthouse01_pmx_parser as pmxlib
	from ._local_translation_dicts import translate_local
except ImportError as eee:
	try:
		import nuthouse01_core as core
		import nuthouse01_pmx_parser as pmxlib
		from _local_translation_dicts import translate_local
	except ImportError as eee:
		print(eee.__class__.__name__, eee)
		print("ERROR: failed to import some of the necessary files, all my scripts must be together in the same folder!")
		print("...press ENTER to exit...")
		input()
		exit()
		core = pmxlib = translate_local = None


# when debug=True, disable the catchall try-except block. this means the full stack trace gets printed when it crashes,
# but if launched in a new window it exits immediately so you can't read it.
DEBUG = False


# use this when each material's name is just "en" or something equally unhelpful
# this will prefer a successful "local translate" over an existing english name
PREFER_LOCAL_TRANSLATE = False


# sometimes chinese translation gives better results than japanese translation
# when false, force input to be interpreted as Japanese. When true, autodetect input language.
GOOGLE_AUTODETECT_LANGUAGE = True


# when this is true, it doesn't even attempt online translation. this way you can kinda run the script when
# you run into google's soft-ban.
DISABLE_INTERNET_TRANSLATE = False


# to reduce the number of translation requests, a list of strings is joined into one string broken by newlines
# hopefully that counts as "fewer requests" for google's API
# tho in testing, sometimes translations produce different results if on their own vs in a newline list... oh well
# or sometimes they lose newlines during translation
# more lines per request = riskier, but uses less of your transaction budget
TRANSLATE_MAX_LINES_PER_REQUEST = 15
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
	googletrans = None
	DISABLE_INTERNET_TRANSLATE = True



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
	core.MY_PRINT_FUNC("You have used %d / %d translation requests within the last %f hrs" %
		  (requests_in_timeframe, TRANSLATE_BUDGET_MAX_REQUESTS, TRANSLATE_BUDGET_TIMEFRAME))
	# make the decision
	if (requests_in_timeframe + num_proposed) <= TRANSLATE_BUDGET_MAX_REQUESTS:
		# this many translations is OK! go ahead!
		# write this transaction into the record
		record.append([now, num_proposed])
		core.write_rawlist_to_txt(recordpath, record, quiet=True)
		return True
	else:
		# cannot do the translate, this would exceed the budget
		# bonus value: how long until enough records expire that i can do this?
		if num_proposed >= TRANSLATE_BUDGET_MAX_REQUESTS:
			core.MY_PRINT_FUNC("BUDGET: you cannot make this many requests all at once")
		else:
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
			core.MY_PRINT_FUNC("BUDGET: you must wait %d minutes before you can do %d more translation requests with Google" % (waittime, num_proposed))
		
		return False


################################################################################################################

def contains_jap_chars(text) -> bool:
	# /[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]/
	"""
	3040 - 30ff
	3400 - 4dbf
	4e00 - 9fff
	f900 - faff
	ff01 - ff5e  # fullwidth chars like ０１２３ＩＫ...   FF01–FF5E(5D/93)  -->  21-7E(5D/93), diff=(FEE0/‭65248‬)
	ff66 - ff9f  # halfwidth katakana
	# ▲=25b2, ω=03c9, ∧=2227, □=25a1
	"""
	# is_jap = re.compile("[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f\uff10-\uff5a]")
	# match = is_jap.search(str(text))
	match = re.search("[▲△∧ω□\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f\uff10-\uff5a]", str(text))
	if match:
		# print("True;", str(text))
		return True
	# print("False;", str(text))
	return False


def my_string_pad(string: str, width: int) -> str:
	# how big does it already print as?
	currsize = len(string)
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
		core.print_progress_oneline(start_idx / len(jp_list))
		input_list = jp_list[start_idx:start_idx + TRANSLATE_MAX_LINES_PER_REQUEST]
		bigstr = "\n".join(input_list)
		bigresult = actual_translate(bigstr)
		result_list = bigresult.split("\n")
		if len(result_list) != len(input_list):
			core.MY_PRINT_FUNC("Warning: translation messed up and merged some lines, please manually fix the bad outputs")
			core.MY_PRINT_FUNC(len(result_list), len(input_list), result_list)
			result_list = ["error"] * len(input_list)
		retme += result_list
		start_idx += TRANSLATE_MAX_LINES_PER_REQUEST
	return retme


def actual_translate(jp_str: str) -> str:
	# acutally send a single string to Google for translation
	if DISABLE_INTERNET_TRANSLATE:
		return jp_str
	try:
		if GOOGLE_AUTODETECT_LANGUAGE:
			r = jp_to_en_google.translate(jp_str, dest="en")  # auto
		else:
			r = jp_to_en_google.translate(jp_str, dest="en", src="ja")  # jap
		return r.text
	except ConnectionError as e:
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		core.MY_PRINT_FUNC("Check your internet connection?")
		raise RuntimeError()
	except Exception as e:
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		if hasattr(e, "doc"):
			core.MY_PRINT_FUNC("Response from Google:")
			core.MY_PRINT_FUNC(e.doc.split("\n")[7])
			core.MY_PRINT_FUNC(e.doc.split("\n")[9])
		core.MY_PRINT_FUNC("Google API has rejected the translate request")
		core.MY_PRINT_FUNC("This is probably due to too many translate requests too quickly")
		core.MY_PRINT_FUNC("Strangely, this lockout does NOT prevent you from using Google Translate thru your web browser. So go use that instead.")
		core.MY_PRINT_FUNC("Get a VPN or try again in about 1 day (TODO: CONFIRM LOCKOUT TIME)")
		raise RuntimeError()


def fix_eng_name(name_jp: str, name_en: str) -> (str, None):
	# returns a new english name, might be the same as the existing english name
	# or returns None if tranlsation is needed
	
	# mode 1 priorities: without "prefer local translate"
	# first, return EN name if EN name already good english
	# second, return JP name if JP name already good english
	# third, return local translate JP -> EN if it succeeds
	# fourth, give up and go to google
	
	# mode 2 priorities: with "prefer local translate"
	# first, return JP name if JP name already good english
	# second, return local translate JP -> EN if it succeeds
	# third, return EN name if EN name already good english
	# fourth, give up and go to google
	
	# if en name is already good (not blank and not JP), just keep it
	if not PREFER_LOCAL_TRANSLATE and name_en and not name_en.isspace() and not contains_jap_chars(name_en):
		return name_en
	
	# jp name is already good english, copy jp name -> en name
	if name_jp and not name_jp.isspace() and not contains_jap_chars(name_jp):
		return name_jp
	
	# !!!! NEW LOCAL TRANSLATE FUNCTION !!!!
	local_result = translate_local(name_jp)
	# if local-translate succeeds, use it! (return None on fail)
	if not contains_jap_chars(local_result):
		return local_result
	
	# if en name is already good (not blank and not JP), just keep it
	if PREFER_LOCAL_TRANSLATE and name_en and not name_en.isspace() and not contains_jap_chars(name_en):
		return name_en
	
	# i can't translate it myself, then
	# translate jp name -> en name via google
	# return None so the translations can be done in bulk
	return None


helptext = '''====================
translate_to_english:
This tool fills out empty EN names in a PMX model with translated versions of the JP names.
It tries to do some intelligent piecewise translation using a local dictionary but goes to Google Translate if that fails.
Machine translation is never 100% reliable, so this is only a stopgap measure to eliminate all the 'Null_##'s and wrongly-encoded garbage and make it easier to use in MMD. A bad translation is better than none at all!
Also, Google Translate only permits ~100 requests per hour, if you exceed this rate you will be locked out for 24 hours (TODO: CONFIRM LOCKOUT TIME)
But my script has a built in limiter that will prevent you from translating if you would exceed the 100-per-hr limit.
'''

iotext = '''Inputs:  PMX file "[model].pmx"\nOutputs: PMX file "[model]_translate.pmx"
'''


def showhelp():
	# print info to explain the purpose of this file
	core.MY_PRINT_FUNC(helptext)
def showprompt():
	# print info to explain what inputs/outputs it needs/creates
	core.MY_PRINT_FUNC(iotext)
	
	# prompt PMX name
	core.MY_PRINT_FUNC("Please enter name of PMX model file:")
	input_filename_pmx = core.prompt_user_filename(".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=True)
	return pmx, input_filename_pmx

def translate_to_english(pmx, moreinfo=False):
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
	
	# repeat the following for each category of visible names:
	# materials=4, bones=5, morphs=6, dispframe=7
	for cat_id in range(4, 8):
		category = pmx[cat_id]
		# for each entry:
		for i, item in enumerate(category):
			if cat_id == 7 and item[2]:
				continue  # skip "special" display frames
			# jp=0,en=1
			# strip away newline and return just in case, i saw a few examples where they showed up
			item[0] = item[0].replace('\r','').replace('\n','')
			item[1] = item[1].replace('\r','').replace('\n','')
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
	
	# if model name is empty, give it something. same for comment
	if pmx[0][1] == "":
		pmx[0][1] = "model"
	if pmx[0][3] == "":
		pmx[0][3] = "comment"
		
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
	
	translate_local_count = len(translate_maps)
	
	# comment(jp=3,en=4)
	comment_state = 0
	comment_jp_clean = "" # the thing that is given to translate, if needed
	# new_en_name = fix_eng_name(pmx[0][3], pmx[0][4]) # this should disable translation of comments
	if not pmx[0][4] or pmx[0][4].isspace():
		new_en_name = pmx[0][3]
	else:
		new_en_name = pmx[0][4]
	if new_en_name is None:
		# googletrans is required, store and translate in bulk later
		comment_state = 1
		# DOES get printed (as too_long_to_print), DOES go to translation file (newlines replaced with something) AFTER going to internet
		#### SPECIAL HANDLING! replace newlines with something
		# comment = pmx[0][3].replace("\n", NEWLINE_ESCAPE_CHAR)
		comment_jp_clean = pmx[0][3].replace("\r", "")  # delete these linereturn chars
		comment_jp_clean = re.sub(r'\n\n+', r'\n\n', comment_jp_clean)  # collapse multiple newlines to just 2
		commentline_print = [label_dict[0], "4", "google", "OLD EN:", "too_long", "NEW EN:", "too_long_to_print", "JP:","too_long"]
		translate_maps.append(commentline_print)
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
		translate_maps.append(commentline_print)
		pmx[0][4] = new_en_name
	
	# return having changed nothing IF translate_queue is empty, translate_budget fails
	
	if (not translate_queue) and (not translate_maps) and (comment_state == 0):
		core.MY_PRINT_FUNC("No changes are required")
		return pmx, False
	
	translate_local_count += (comment_state == 2)
	
	# num + 1 + 1(if translating comment)
	num_items = len(translate_queue) + (comment_state == 1)
	core.MY_PRINT_FUNC("Identified %d items that need Internet translation" % num_items)
	if num_items:
		v = len(translate_queue) / TRANSLATE_MAX_LINES_PER_REQUEST
		if v != int(v): # "rounding up" in a hacky way cuz I dont want to import "math" library just for one ceil() call
			v = int(v) + 1
		num_calls = v + (comment_state == 1)
		core.MY_PRINT_FUNC("Making %d requests to Google Translate web API..." % num_calls)
		
		global DISABLE_INTERNET_TRANSLATE
		
		if not check_translate_budget(num_calls):
			# no need to print failing statement, the function already does
			# shift over to mymemory provider and continue if google is full
			core.MY_PRINT_FUNC("Just copying JP onto EN while Google Translate is disabled")
			DISABLE_INTERNET_TRANSLATE = False
		
		core.MY_PRINT_FUNC("Beginning translation, this may take several seconds")
		
		try:
			# now bulk-translate all the strings that are queued
			results = bulk_translate(translate_queue)
			# then assemble these results into the translate_map entries
			# also do apply the results
			for new_en_name, queue_idx in zip(results, translate_queue_idx):
				(cat_id, i) = queue_idx
				# special case for the header things
				if cat_id == 0:
					if i == 2:  # modelname
						newlist = [label_dict[cat_id], str(i), "google", "OLD EN:", pmx[0][2], "NEW EN:", new_en_name, "JP:", pmx[0][1]]
						translate_maps.append(newlist)
						pmx[cat_id][i] = new_en_name
				else:
					newlist = [label_dict[cat_id], str(i), "google", "OLD EN:", pmx[cat_id][i][1], "NEW EN:", new_en_name, "JP:", pmx[cat_id][i][0]]
					translate_maps.append(newlist)
					pmx[cat_id][i][1] = new_en_name
			# translate_maps is used for both printing and writing
			
			# if comment needs translated, do that separately
			if comment_state == 1:
				# already removed linereturn and collapsed newlines, ready to go
				newcomment = actual_translate(comment_jp_clean)
				newcomment = newcomment.replace('\n','\r\n')
				pmx[0][4] = newcomment
		except Exception as e:
			core.MY_PRINT_FUNC(e.__class__.__name__, e)
			core.MY_PRINT_FUNC("Internet translate unexpectedly failed, attempting to continue...")
	# done translating!!
	
	# now i use comment_state to know how to handle the comment
	
	#######################################
	# next stage is writing and printing, then wait for approval
	# printing requires formatting so things display in nice columns
	core.MY_PRINT_FUNC("Fixed %d instances where translation was needed (%d local + %d Google)" %
					   (len(translate_maps), translate_local_count, len(translate_maps) - translate_local_count))
	
	if moreinfo:
		# find max width of each column:
		width = [0] * 9
		for tmap in translate_maps:
			for i in range(9):
				width[i] = max(width[i], len(tmap[i]))
		# now pretty-print the proposed list of translations:
		for tmap in translate_maps:
			args = []
			# python's formatting tool doesn't play nice with odd-width chars so I'll do it manually
			for i in range(9):
				if i==5 or i==3:
					continue
				if i in (4,6,8):
					args.append(my_string_pad("'" + tmap[i] + "'", width[i]+2))
				else:
					args.append(my_string_pad(tmap[i], width[i]))
			core.MY_PRINT_FUNC("{}{} {} | EN: {} --> {} | {} {}".format(*args))
	
	
	return pmx, True
	
def end(pmx, input_filename_pmx):
	# write out
	# output_filename_pmx = "%s_translate.pmx" % core.get_clean_basename(input_filename_pmx)
	output_filename_pmx = input_filename_pmx[0:-4] + "_translate.pmx"
	output_filename_pmx = core.get_unused_file_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=True)
	return None

def main():
	showhelp()
	pmx, name = showprompt()
	pmx, is_changed = translate_to_english(pmx)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")


if __name__ == '__main__':
	core.MY_PRINT_FUNC("Nuthouse01 - 06/08/2020 - v4.07")
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
			core.MY_PRINT_FUNC(ee)
			core.pause_and_quit("ERROR: something truly strange and unexpected has occurred, sorry, good luck figuring out what tho")
