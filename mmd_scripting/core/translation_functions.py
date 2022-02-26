import re
from time import time
from typing import TypeVar, List, Tuple, Dict

import googletrans

from mmd_scripting.core import nuthouse01_core as core, nuthouse01_io as io, translation_dictionaries

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.04 - 8/19/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# to use builtin "string.translate() function", must assemble a dict where key is UNICODE NUMBER and value is string
prefix_dict_ord =          dict((ord(k), v) for k, v in translation_dictionaries.prefix_dict.items())
odd_punctuation_dict_ord = dict((ord(k), v) for k, v in translation_dictionaries.odd_punctuation_dict.items())
fullwidth_dict_ord =       dict((ord(k), v) for k, v in translation_dictionaries.ascii_full_to_basic_dict.items())


# all english names have consistent-sized indent when any amount of indent is present (doesn't come up very often)
STANDARD_INDENT = "  "


# enables a boatload of basic print statements pertaining to how translation works under the hood
DEBUG = False



# if you just wanna force it to not use google?
DISABLE_INTERNET_TRANSLATE = False


# new idea to make google translation more consistent (in some cases consistent = better but not always)
# only helps on very complex models that contain enough compound words that I can isolate each component word
USE_SUBASSEMBLE_IDEA = True


# to reduce the number of translation requests, a list of strings is joined into one string broken by newlines
# that counts as "fewer requests" for google's API
# tho in testing, sometimes translations produce different results if on their own vs in a newline list... oh well
# or sometimes they lose newlines during translation
# more lines per request = riskier, but uses less of your transaction budget
TRANSLATE_MAX_LINES_PER_REQUEST = 15
# how many requests are permitted per timeframe, to avoid the lockout
# true limit is ~100 so enforce limit of 90 just to be safe
TRANSLATE_BUDGET_MAX_REQUESTS = 90
# how long (hours) is the timeframe to protect
# true timeframe is ~1 hr so enforce limit of ~1.2hr just to be safe
TRANSLATE_BUDGET_TIMEFRAME = 1.0


# everything is fine, just set up the normal way
# i used to have a bunch of try-except to catch import errors and support if googletrans is not installed,
# but now it's part of my provided "RUN THIS TO INSTALL.bat" so it should always be present
jp_to_en_google = googletrans.Translator()


# type hint for functions that accept string-or-listofstring and return whatever they got in
STR_OR_STRLIST = TypeVar("STR_OR_STRLIST", str, List[str])

########################################################################################################################
########################################################################################################################
# regular expression stuff
# indent: whitespace or _ or anything from unicode box-drawing symbols block
indent_pattern = "^[\\s_\u2500-\u257f]+"
indent_pattern_re = re.compile(indent_pattern)
# strip: whitespace _ . -
padding_pattern = r"[\s_.-]*"
# prefix: match 右|左|中 but not 中指 (middle finger), one or more times
prefix_pattern = "^(([右左]|中(?!指))+)"
# suffix: match 右|左|中 and parent (but not motherbone) and end (but not toe), one or more times
suffix_pattern = "(([右左中]|(?<!全ての)親|(?<!つま)先)+)$"
prefix_pattern_re = re.compile(prefix_pattern + padding_pattern)
suffix_pattern_re = re.compile(padding_pattern + suffix_pattern)


# TODO: maybe instead of finding unusal jap chars, i should just find anything not basic ASCII alphanumeric characters?
# https://www.compart.com/en/unicode/block
jp_pattern = "\u3040-\u30ff"  # "hiragana" block + "katakana" block
jp_pattern += "\u3000-\u303f"  # "cjk symbols and punctuation" block, fullwidth space, brackets, etc etc
jp_pattern += "\u3400-\u4dbf"  # "cjk unified ideographs extension A"
jp_pattern += "\u4e00-\u9fff"  # "cjk unified ideographs"
jp_pattern += "\uf900-\ufaff"  # "cjk compatability ideographs"
jp_pattern += "\uff66-\uffee"  # "halfwidth and fullwidth forms" halfwidth katakana and other stuff
jp_re = re.compile("[" + jp_pattern + "]")

needstranslate_pattern = jp_pattern  # copy this stuff, "needstranslate" is a superset of "is_jp"
needstranslate_pattern += "\u2190-\u21ff"  # "arrows" block
needstranslate_pattern += "\u2500-\u257f"  # "box drawing" block, used as indentation sometimes
needstranslate_pattern += "\u25a0-\u25ff"  # "geometric shapes", common morphs ▲ △ □ ■ come from here
needstranslate_pattern += "\u2600-\u26ff"  # "misc symbols", ★ and ☆ come from here but everything else is irrelevant
needstranslate_pattern += "\uff01-\uff65"  # "halfwidth and fullwidth forms" fullwidth latin and punctuation aka ０１２３ＩＫ
needstranslate_pattern += "".join(translation_dictionaries.symbols_dict.keys())  # add "symbol dict" just in case there are some outlyers... some overlap with ranges but w/e
needstranslate_re = re.compile("[" + needstranslate_pattern + "]")



# not 100% confident this is right, there are probably other characters that can display just fine in MMD like accents
# TODO: check for other chars that can display in MMD just fine, try accents maybe?
def is_latin(text:str) -> bool:
	""" will display perfectly in EN MMD version """
	return all(ord(c) < 128 for c in text)


def is_jp(text:str) -> bool:
	""" is jp/cn and needs translation and can be plausibly translated """
	m = jp_re.search(text)
	return bool(m)


def needs_translate(text:str) -> bool:
	""" won't display right in MMD, either is jp/cn or is wierd unicode symbols """
	# m = needstranslate_re.search(text)
	m = not is_latin(text)
	return bool(m)


def is_alphanumeric(text:str) -> bool:
	""" whole string is a-z,A-Z,0-9 """
	# ord values [48-57, 65-90, 97-122, ]
	# return all((48 <= ord(c) <= 57 or 65 <= ord(c) <= 90 or 97 <= ord(c) <= 122) for c in text)
	for c in text:
		o = ord(c)
		if not (48 <= o <= 57 or 65 <= o <= 90 or 97 <= o <= 122): return False
	return True


def pre_translate(in_list: STR_OR_STRLIST) -> Tuple[STR_OR_STRLIST, STR_OR_STRLIST, STR_OR_STRLIST]:
	"""
	Handle common translation things like prefixes, suffixes, fullwidth alphanumeric characters, indents,
	and some types of punctuation. Returns 3-ple of EN indent, JP body, EN suffix. This way the translate can work on
	the important stuff and ignore the chaff.
	:param in_list: list of JP strings, or a single JP string
	:return: tuple of indent/body/suffix lists, or a single tuple
	"""
	# input str breakdown: (indent) (L/R prefix) (padding) [[[body]]] (padding) (L/R suffix)
	
	input_is_str = isinstance(in_list, str)
	if input_is_str: in_list = [in_list]  # force it to be a list anyway so I don't have to change my structure
	indent_list = []  # list to build & return
	body_list = []  # list to build & return
	suffix_list = []  # list to build & return
	for s in in_list:
		# 1: subst JP/fullwidth alphanumeric chars -> standard EN alphanumeric chars
		# https://en.wikipedia.org/wiki/Halfwidth_and_Fullwidth_Forms_(Unicode_block)
		# fullwidth chars like ０１２３ＩＫ are in range FF01–FF5E  and correspond to  21-7E
		# this also handles all the "odd_punctuation_dict" stuff
		# to handle them, use nifty str.translate() method, dict must have keys be ordinal unicode values tho
		out = s.translate(odd_punctuation_dict_ord)
		out = out.translate(fullwidth_dict_ord)
		# cannot use string.translate() for katakana_half_to_full_dict because several keys are 2-char strings
		out = piecewise_translate(out, translation_dictionaries.katakana_half_to_full_dict, join_with_space=False)
		
		# 2. check for indent
		indent_prefix = ""
		# get the entire indent: whitespace or _ or box
		indent_match = indent_pattern_re.search(out)
		if indent_match is not None:
			# found a matching indent!
			if indent_match.end() == len(out):
				# the indent consumed the entire string... skip this stage, do nothing, leave as is
				pass
			else:
				# remove the indent from the orig str
				out = out[indent_match.end():]
				# decide what to replace it with
				# if it contains an underscore, use under prefix... otherwise use 2-space indent
				indent_prefix = "_" if "_" in indent_match.group() else STANDARD_INDENT
		
		# 3: remove known JP prefix/suffix, assemble EN suffix to be reattached later
		en_suffix = ""
		# get the prefix
		prefix_match = prefix_pattern_re.search(out)
		if prefix_match is not None:
			if prefix_match.end() == len(out):
				# if the prefix consumed the entire string, skip this stage
				pass
			else:
				# remove the prefix from the orig str
				out = out[prefix_match.end():]
				# generate a new EN suffix from the prefix I removed
				en_suffix += prefix_match.group(1).translate(prefix_dict_ord)
		# get the suffix
		suffix_match = suffix_pattern_re.search(out)
		if suffix_match is not None:
			if suffix_match.start() == 0:
				# if the suffix consumed the entire string, skip this stage
				pass
			else:
				# remove the suffix from the orig str
				out = out[:suffix_match.start()]
				# generate a new EN suffix from the suffix I removed
				en_suffix += suffix_match.group(1).translate(prefix_dict_ord)
				
		# # 4: strip leading/ending spaces or whatever that might have been insulated by the prefix/suffix
		# out_strip = strip_re.sub("", out)
		# if out_strip == "":
		# 	# if stripping whitespace removes the entire string, then skip/undo this step
		# 	pass
		# else:
		# 	out = out_strip
		
		# 5: append all 3 to the list: return indent/suffix separate from the body
		indent_list.append(indent_prefix)
		body_list.append(out)
		suffix_list.append(en_suffix)
		
	if input_is_str:return indent_list[0], body_list[0], suffix_list[0]	 # if original input was a single string, then de-listify
	else:			return indent_list, body_list, suffix_list	# otherwise return as a list


def piecewise_translate(in_list: STR_OR_STRLIST, in_dict: Dict[str,str], join_with_space=True) -> STR_OR_STRLIST:
	"""
	Apply piecewise translation to inputs when given a mapping dict.
	Mapping dict will usually be the builtin comprehensive 'words_dict' or some results found from Google Translate.
	From each position in the string(ordered), check each map entry(ordered). Dict should have keys ordered from longest
	to shortest to avoid "undershadowing" problem.
	Always returns what it produces, even if not a complete translation. Outer layers are responsible for checking if
	the translation is "complete" before using it.
	
	:param in_list: list of JP strings, or a single JP string
	:param in_dict: dict of mappings from JP substrings to EN substrings
	:param join_with_space: optional, default true. if true, when substituting substrings, put spaces before/after.
	:return: list of resulting strings, or a single resulting string
	"""
	input_is_str = isinstance(in_list, str)
	if input_is_str: in_list = [in_list]  # force it to be a list anyway so I don't have to change my structure
	outlist = []  # list to build & return
	
	dictitems = list(in_dict.items())
	
	joinchar = " " if join_with_space else ""
	
	for out in in_list:
		if (not out) or out.isspace():  # support bad/missing data
			outlist.append("JP_NULL")
			continue
		# goal: substrings that match keys of "words_dict" get replaced
		# NEW ARCHITECTURE: starting from each char, try to match against the contents of the dict. longest items are first!
		i = 0
		while i < len(out):  # starting from each char of the string,
			found_match = False
			for (key, val) in dictitems:  # try to find anything in the dict to match against,
				if out.startswith(key, i):  # and if something is found starting from 'i',
					found_match = True
					# i am going to replace it key->val, but first maybe insert space before or after or both.
					# note: letter/number are the ONLY things that use joinchar. all punctuation and all JP stuff do not use joinchar.
					# if 'begin-1' is a valid index and the char at that index is letter/number, then PREPEND a space
					before_space = joinchar if i != 0 and is_alphanumeric(out[i-1]) else ""
					# if "begin+len(key)" is a valid index and the char at that index is letter/number, then APPEND a space
					after_space = joinchar if i+len(key) < len(out) and is_alphanumeric(out[i+len(key)]) else ""
					# now JOINCHAR is added, so now i substitute it
					out = out[0:i] + before_space + val + after_space + out[i+len(key):]
					# i don't need to examine or try to replace on any of these chars, so skip ahead a bit
					i += len(val) + int(bool(before_space)) + int(bool(after_space))
					# nothing else will match here, since I just replaced the thing, so break out of iterating on dict keys
					break
			if found_match is False:
				i += 1
		# once all uses of all keys have been replaced, then append the result
		outlist.append(out)
	
	if input_is_str:	return outlist[0]	# if original input was a single string, then de-listify
	else:				return outlist		# otherwise return as a list


def local_translate(in_list: STR_OR_STRLIST) -> STR_OR_STRLIST:
	"""
	Simple wrapper func to run both pre_translate and local_translate using words_dict.
	With DEBUG=True, it prints before/after.
	Results are best-effort translations, even if incomplete.
	
	:param in_list: list of JP strings, or a single JP string
	:return: list of resulting strings, or a single resulting string
	"""
	input_is_str = isinstance(in_list, str)
	if input_is_str: in_list = [in_list]  # force it to be a list anyway so I don't have to change my structure
	
	# first, run pretranslate: take care of the standard stuff
	# things like prefixes, suffixes, fullwidth alphanumeric characters, etc
	indents, bodies, suffixes = pre_translate(in_list)
	
	# second, run piecewise translation with the hardcoded "words dict"
	outbodies = piecewise_translate(bodies, translation_dictionaries.words_dict)
	
	# third, reattach the indents and suffixes
	outlist = [i + b + s for i,b,s in zip(indents, outbodies, suffixes)]
	
	# pretty much done! check whether it passed/failed outside this func
	if DEBUG:
		print("Localtranslate Results:")
		for s,o in zip(in_list, outlist):
			# did i translate the whole thing? check whether results are all "normal" characters
			print("%d :: %s :: %s" % (is_latin(o), s, o))
	
	if input_is_str:	return outlist[0]	# if original input was a single string, then de-listify
	else:				return outlist		# otherwise return as a list


########################################################################################################################
########################################################################################################################
########################################################################################################################
# Google Translate related functions


# def init_googletrans():
# 	# this should be a function called in main so if it fails, then it gets printed in console
# 	global jp_to_en_google
# 	global _DISABLE_INTERNET_TRANSLATE
# 	_DISABLE_INTERNET_TRANSLATE = DISABLE_INTERNET_TRANSLATE  # create a second global var so I can reset this one to default each time it runs
# 	if googletrans is None:
# 		core.MY_PRINT_FUNC("ERROR: Python library 'googletrans' not installed, translation will be very limited!!")
# 		core.MY_PRINT_FUNC("Please install this library with 'pip install googletrans' in Windows Command Prompt")
# 		jp_to_en_google = None
# 	else:
# 		# everything is fine, just set up the normal way
# 		jp_to_en_google = googletrans.Translator()


def _check_translate_budget(num_proposed: int) -> bool:
	"""
	Goal: block translations that would trigger the lockout.
	Create & maintain a persistent file that contains timestamps and # of requests, to know if my proposed number will
	exceed the budget. If it would still be under budget, then update the log assuming that the proposed requests will
	happen. options: TRANSLATE_BUDGET_MAX_REQUESTS, TRANSLATE_BUDGET_TIMEFRAME
	
	:param num_proposed: number of times I want to contact the google API
	:return: bool True = go ahead, False = stop
	"""
	# get the log of past translation requests
	# formatted as list of (timestamp, numrequests) sub-lists
	record = io.get_persistent_storage_json('googletrans-request-history')
	# if it doesn't exist in the json, then init it as empty list
	if record is None:
		record = []
	
	# get teh timestamp for now
	now = time()
	# walk backward so i can pop things safely, discard all request records that are older than <timeframe>
	for i in reversed(range(len(record))):
		entry = record[i]
		if (now - entry[0]) > (TRANSLATE_BUDGET_TIMEFRAME * 60 * 60):
			# print("debug: discard", record[i])
			record.pop(i)
	
	# then interpret the file: how many requests happened in the past <timeframe> ?
	requests_in_timeframe = sum([entry[1] for entry in record])
	core.MY_PRINT_FUNC("... you have used {} / {} translation requests within the last {:.4} hrs...".format(
		int(requests_in_timeframe), int(TRANSLATE_BUDGET_MAX_REQUESTS), TRANSLATE_BUDGET_TIMEFRAME))
	# make the decision
	if (requests_in_timeframe + num_proposed) <= TRANSLATE_BUDGET_MAX_REQUESTS:
		# this many translations is OK! go ahead!
		# write this transaction into the record
		newentry = [now, num_proposed]
		record.append(newentry)
		# write the record to file
		io.write_persistent_storage_json('googletrans-request-history', record)
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
				# how many entries do i need to hypothetically pop before it would free enough space for the
				# proposed amount to be accepted?
				if (requests_in_timeframe + num_proposed - to_be_popped) <= TRANSLATE_BUDGET_MAX_REQUESTS:
					break
			# when idx'th item becomes too old, then the current proposed number will be okay
			waittime = record[idx][0] + (TRANSLATE_BUDGET_TIMEFRAME * 60 * 60) - now
			# convert seconds to minutes
			waittime = round(waittime / 60)
			core.MY_PRINT_FUNC("BUDGET: you must wait %d minutes before you can do %d more translation requests with Google" % (waittime, num_proposed))
		
		return False


def _packetize_translate_requests(jp_list: List[str]) -> List[str]:
	"""
	Group/join a massive list of items to translate into fewer requests which each contain many separated by newlines.
	options: TRANSLATE_MAX_LINES_PER_REQUEST.
	
	:param jp_list: list of each JP name, names must not include newlines
	:return: list of combined names, which are many JP names joined by newlines
	"""
	retme = []
	start_idx = 0
	while start_idx < len(jp_list):
		sub_list = jp_list[start_idx : start_idx+TRANSLATE_MAX_LINES_PER_REQUEST]
		bigstr = "\n".join(sub_list)
		retme.append(bigstr)
		start_idx += TRANSLATE_MAX_LINES_PER_REQUEST
	return retme


def _unpacketize_translate_requests(list_after: List[str]) -> List[str]:
	"""
	Opposite of _packetize_translate_requests(). Breaks each string at newlines and flattens result into one long list.
	
	:param list_after: list of newline-joined strings
	:return: list of strings not containing newlines
	"""
	retme = []
	for after in list_after:
		results = after.split("\n")
		retme.extend(results)
	return retme


def _single_google_translate(jp_str: str, autodetect_language=True) -> str:
	"""
	Actually send a single string to Google API for translation, unless internet trans is disabled.
	
	:param jp_str: JP string to be translated
	:param autodetect_language: if true, let Google decide the input language. if False, assert that the input is JP
	:return: usually english-translated result
	"""
	try:
		# acutally send a single string to Google for translation
		if autodetect_language:
			r = jp_to_en_google.translate(jp_str, dest="en")  # auto
		else:
			r = jp_to_en_google.translate(jp_str, dest="en", src="ja")  # jap
		return r.text
	except ConnectionError as e:
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		core.MY_PRINT_FUNC("Check your internet connection?")
		raise
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
		raise


def google_translate(in_list: STR_OR_STRLIST, autodetect_language=True, chunks_only_kanji=True) -> STR_OR_STRLIST:
	"""
	Take a list of strings & get them all translated by asking Google.
	If chunks_only_kanji=True, only attempt to translate actual katakana or w/e, prevent non-ASCII non-JP stuff
	like ▲ ★ 〇 from going to google. If chunks_only_kanji=False, attempt to translate everything that isn't ASCII
	(might cause language autodetect to malfunction tho!)

	:param in_list: list of JP or partially JP strings
	:param autodetect_language: if true, let Google decide the input language. if False, assert that the input is JP
	:param chunks_only_kanji: True=chunks are "is_jp", False=chunks are "not is_latin"
	:return: list of strings probably pure EN, but sometimes odd unicode symbols show up
	"""
	input_is_str = isinstance(in_list, str)
	if input_is_str: in_list = [in_list]  # force it to be a list anyway so I don't have to change my structure
	
	# in_list -> pretrans -> jp_chunks_set -> jp_chunks -> jp_chunks_packets -> results_packets -> results
	# jp_chunks + results -> google_dict
	# pretrans + google_dict -> outlist
	
	# 1. pre-translate to take care of common tasks
	indents, bodies, suffixes = pre_translate(in_list)
	
	# 2. identify chunks
	jp_chunks_set = set()
	# idea: walk & look for transition from en to jp
	for S in bodies:  # for every string to translate,
		prev_is_chunk = False
		curr_is_chunk = False
		chunkstart = -1
		# virtually add a "not chunk" char before & after the input string...
		for I, C in enumerate(S):
			# IMPORTANT: use "is_jp" here and not "is_latin" so chunks are defined to be only actual JP stuff and not unicode whatevers
			# this means unicode whatevers will be breakpoints between chunks, and also will not be sent to googletrans
			if chunks_only_kanji: curr_is_chunk = is_jp(C)
			else:                 curr_is_chunk = not is_latin(C)
			# if this is the point where C transitions from "not chunk" to "chunk", then this is the START of a chunk
			if not prev_is_chunk and curr_is_chunk:
				chunkstart = I
			# if this is the point where C transitions from "chunk" to "not chunk", then this is the end of a chunk
			elif prev_is_chunk and not curr_is_chunk:
				jp_chunks_set.add(S[chunkstart:I])
			# current gets passed to previous for next loop, duh
			prev_is_chunk = curr_is_chunk
		# when done with looping, if the final character was "chunk" then we have a chunk that includes the final char
		if curr_is_chunk:
			jp_chunks_set.add(S[chunkstart:len(S)])
	
	# 3. remove chunks I can already solve
	# maybe localtrans can solve one chunk but not the whole string?
	# chunks are guaranteed to not be PART OF compound words. but they are probably compound words themselves.
	# run local trans on each chunk individually, and if it succeeds, then DON'T send it to google.
	localtrans_dict = dict()
	jp_chunks = []
	for chunk in list(jp_chunks_set):
		trans = piecewise_translate(chunk, translation_dictionaries.words_dict)
		if is_jp(trans):
			# if the localtrans failed, then the chunk needs to be sent to google later
			jp_chunks.append(chunk)
		else:
			# if it passed, no need to ask google what they mean cuz I already have a good translation for this chunk
			# this will be added to the dict way later
			localtrans_dict[chunk] = trans
	
	# 4. packetize them into fewer requests (and if auto, choose whether to use chunks or not)
	jp_chunks_packets = _packetize_translate_requests(jp_chunks)
	jp_bodies_packets = _packetize_translate_requests(bodies)
	
	# 5. check the translate budget to see if I can afford this
	num_calls = len(jp_chunks_packets)
	
	if not DISABLE_INTERNET_TRANSLATE and _check_translate_budget(num_calls):
		core.MY_PRINT_FUNC("... making %d requests to Google Translate web API..." % num_calls)
		
		# 6. send chunks to Google
		results_packets = []

		print("#items=", len(in_list), "#chunks=", len(jp_chunks), "#requests=", len(jp_chunks_packets))
		for d, packet in enumerate(jp_chunks_packets):
			core.print_progress_oneline(d / len(jp_chunks_packets))
			r = _single_google_translate(packet, autodetect_language)
			results_packets.append(r)
		
		# 7. assemble Google responses & re-associate with the chunks
		# order of inputs "jp_chunks" matches order of outputs "results"
		results = _unpacketize_translate_requests(results_packets)  # unpack
		map_jp_to_google = list(zip(jp_chunks, results))
		google_dict = dict(map_jp_to_google)  # build dict

		#########################
		# BEGIN NEW IDEA: what do i call this? "Google Results Sub-Assembly"? idk
		# first, sort so that when i iterate I am operating on the SHORTEST chunk first
		map_jp_to_google.sort(key=lambda x: len(x[0]))
		print(map_jp_to_google)
		# second, for each chunk:
		# can words_dict + google_dict (excluding this specific chunk's exact match) piecewise translate this chunk?
		google_plus_words = {}
		# combine words_dict + google_dict into one
		google_plus_words.update(google_dict)
		google_plus_words.update(translation_dictionaries.words_dict)
		google_plus_words.update(localtrans_dict)  # add dict entries from things that succeeded localtrans
		# ensure it's sorted big-to-small
		google_plus_words = translation_dictionaries.sort_dict_with_longest_keys_first(google_plus_words)

		# # sanity-check: i'm pretty sure that the keys of the 3 dicts should be guaranteed to be mutually exclusive?
		# assert len(google_plus_words) == len(translation_tools.words_dict) + len(google_dict) + len(localtrans_dict)

		if USE_SUBASSEMBLE_IDEA:
			# example: a model might contain chunks of:
			# "ニーソ" = knee sock, "ニーソ脱ぎ" = knee sock remove, "ニーソ上" = knee sock upper, and "ニーソヒール足首" = knee sock heel ankle
			# trying to apply all chunks from longest-length to shortest length would mean only the google translate for that specific
			# chunk gets used. but often, the longer chunks are translated worse... if I could pick the right order to try
			# substituting the chunks, I think I would prefer to translate ニーソ上 via ニーソ + 上 instead of the entire chunk.
			# maybe i could see if I can succesfully translate a chunk using all information except the exact-match for that chunk?
			num_google = 0
			num_subassemble = 0
			for this_jp_chunk, this_google_result in map_jp_to_google:
				# remove this specific chunk + its translation from the dict
				google_plus_words.pop(this_jp_chunk)
				# attempt piecewise translate for this chunk
				chunk_piecewise_subassemble = piecewise_translate(this_jp_chunk, google_plus_words)
				# IS THIS SUCCESSFUL?
				if is_jp(chunk_piecewise_subassemble):
					# no, this is not successful... I do not have all the individual pieces that make up this word
					# so just use the exact-match from google (that i removed a few lines above)
					google_plus_words[this_jp_chunk] = this_google_result
					num_google += 1
				else:
					# yes, this is successful... I would rather use the sub-assembled answer rather than the Google answer!
					google_plus_words[this_jp_chunk] = chunk_piecewise_subassemble
					num_subassemble += 1
					if DEBUG:
						print("jp_chunk = '%s', google = '%s', subassemble = '%s'" %
							  (this_jp_chunk, this_google_result, chunk_piecewise_subassemble))
				# sort it again
				google_plus_words = translation_dictionaries.sort_dict_with_longest_keys_first(google_plus_words)
			
			if DEBUG:
				print("stats: num_google = %d, num_subassemble = %d" % (num_google, num_subassemble))
		
		# 8. piecewise translate using newly created dict
		# it has been fine-tuned and is now guaranteed to fully match against everything that it failed to match before
		outlist = piecewise_translate(bodies, google_plus_words)
			
		# # old style: just translate the strings directly and return their results
		# for d, packet in enumerate(jp_bodies_packets):
		# 	core.print_progress_oneline(d / len(jp_bodies_packets))
		# 	r = _single_google_translate(packet, autodetect_language)
		# 	results_packets.append(r)
		# outlist = _unpacketize_translate_requests(results_packets)
		
		# last, reattach the indents and suffixes
		outlist_final = [i + b + s for i, b, s in zip(indents, outlist, suffixes)]
	
		core.MY_PRINT_FUNC("... done!")
		
	else:
		# no need to print failing statement, the "check translate budget" function already does
		# don't quit early, run thru the same full structure & eventually return a copy of the JP names
		core.MY_PRINT_FUNC("While Google Translate is disabled, just using best-effort (incomplete) local translate")
		bodies_best_effort = piecewise_translate(bodies, translation_dictionaries.words_dict)
		outlist_final = [i + b + s for i, b, s in zip(indents, bodies_best_effort, suffixes)]
	
	# return
	if input_is_str:
		return outlist_final[0]  # if original input was a single string, then de-listify
	else:
		return outlist_final  # otherwise return as a list
	
	