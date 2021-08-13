from time import time
from typing import List, TypeVar

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_io as io
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.overall_cleanup import translation_tools

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.04 - 8/12/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

DEBUG = False


# by default, do not display copyJP/exactmatch modifications
# if this is true, they will also be shown
SHOW_ALL_CHANGED_FIELDS = False


# these english names will be treated as tho they do not exist and overwritten no matter what:
FORBIDDEN_ENGLISH_NAMES = ["en", "d", "mat", "morph", "new morph", "bone", "new bone", "material", "new material"]



# sometimes chinese translation gives better results than japanese translation
# when false, force input to be interpreted as Japanese. When true, autodetect input language.
GOOGLE_AUTODETECT_LANGUAGE = True


# when this is true, it doesn't even attempt online translation. this way you can kinda run the script when
# you run into google's soft-ban.
DISABLE_INTERNET_TRANSLATE = False


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



# don't touch this
_DISABLE_INTERNET_TRANSLATE = False
# set up the acutal translator libraries & objects
jp_to_en_google = None
try:
	import googletrans
except ImportError as eee:
	print(eee)
	print("ERROR: failed to import primary translation provider library 'googletrans'")
	print("Please install this library with 'pip install googletrans'")
	googletrans = None
	DISABLE_INTERNET_TRANSLATE = True



# this is used when the results are ultimately printed
membername_to_shortname_dict = {"header":"header", "materials":"mat", "bones":"bone", "morphs":"morph", "frames":"frame"}
# this will associate the dicts that are optimized for each category, with that category
membername_to_specificdict_dict = {
	"bones": translation_tools.bone_dict,
	"morphs": translation_tools.morph_dict,
	"frames": translation_tools.frame_dict,
}


"""
translation plan

goal: translate everything accurately & efficiently, but also record what layer each translation came from.
user can tolerate ~1sec delay: code efficiency/speed is far less important than code cleanliness, compactness, readability
want to efficiently minimize # of Google Translate API calls, to avoid hitting the lockout
0 input already good > 1 copy JP > 2 category-specific exact match > 3 local picewise trans > 4 google piecewise trans > -1 fail
"""


# class with named fields is a bit better than just a list of lists with prescribed order
class StringTranslateRecord:
	def __init__(self, jp_old: str, en_old: str, cat_name: str, idx: int):
		self.jp_old = jp_old
		self.en_old = en_old
		self.cat = cat_name  # aka category aka type
		self.idx = idx  # aka which bone
		self.en_new = None  # if en_new is empty string, then i haven't settled on a source yet
		self.trans_source = None
	
	def __str__(self):
		s = "jp_old:%s en_old:%s cat:%s idx:%d en_new:%s trans_type:%s" % \
			(self.jp_old, self.en_old, self.cat, self.idx, self.en_new, self.trans_source)
		return s


def init_googletrans():
	# this should be a function called in main so if it fails, then it gets printed in console
	global jp_to_en_google
	global _DISABLE_INTERNET_TRANSLATE
	_DISABLE_INTERNET_TRANSLATE = DISABLE_INTERNET_TRANSLATE  # create a second global var so I can reset this one to default each time it runs
	if googletrans is None:
		core.MY_PRINT_FUNC("ERROR: Python library 'googletrans' not installed, translation will be very limited!!")
		core.MY_PRINT_FUNC("Please install this library with 'pip install googletrans' in Windows Command Prompt")
		jp_to_en_google = None
	else:
		# everything is fine, just set up the normal way
		jp_to_en_google = googletrans.Translator()


################################################################################################################

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

def _single_google_translate(jp_str: str) -> str:
	"""
	Actually send a single string to Google API for translation, unless internet trans is disabled.
	Options: _DISABLE_INTERNET_TRANSLATE and GOOGLE_AUTODETECT_LANGUAGE.
	
	:param jp_str: JP string to be translated
	:return: usually english-translated result
	"""
	if _DISABLE_INTERNET_TRANSLATE:
		return jp_str
	try:
		# acutally send a single string to Google for translation
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

STR_OR_STRLIST = TypeVar("STR_OR_STRLIST", str, List[str])
def google_translate(in_list: STR_OR_STRLIST, strategy=1) -> STR_OR_STRLIST:
	"""
	Take a list of strings & get them all translated by asking Google. Can use per-line strategy or new 'chunkwise' strategy.

	:param in_list: list of JP or partially JP strings
	:param strategy: 0=old per-line strategy, 1=new chunkwise strategy, 2=auto choose whichever needs less Google traffic
	:return: list of strings probably pure EN, but sometimes odd unicode symbols show up
	"""
	input_is_str = isinstance(in_list, str)
	if input_is_str: in_list = [in_list]  # force it to be a list anyway so I don't have to change my structure
	
	use_chunk_strat = True if strategy == 1 else False
	
	# in_list -> pretrans -> jp_chunks_set -> jp_chunks -> jp_chunks_packets -> results_packets -> results
	# jp_chunks + results -> google_dict
	# pretrans + google_dict -> outlist
	
	# 1. pre-translate to take care of common tasks
	indents, bodies, suffixes = translation_tools.pre_translate(in_list)
	
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
			curr_is_chunk = translation_tools.is_jp(C)
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
		trans = translation_tools.piecewise_translate(chunk, translation_tools.words_dict)
		if translation_tools.is_jp(trans):
			# if the localtrans failed, then the chunk needs to be sent to google later
			jp_chunks.append(chunk)
		else:
			# if it passed, no need to ask google what they mean cuz I already have a good translation for this chunk
			# this will be added to the dict way later
			localtrans_dict[chunk] = trans
	
	# 4. packetize them into fewer requests (and if auto, choose whether to use chunks or not)
	jp_chunks_packets = _packetize_translate_requests(jp_chunks)
	jp_bodies_packets = _packetize_translate_requests(bodies)
	if strategy == 2:    use_chunk_strat = (len(jp_chunks_packets) < len(jp_bodies_packets))
	
	# 5. check the translate budget to see if I can afford this
	if use_chunk_strat:
		num_calls = len(jp_chunks_packets)
	else:
		num_calls = len(jp_bodies_packets)
	
	global _DISABLE_INTERNET_TRANSLATE
	if _check_translate_budget(num_calls) and not _DISABLE_INTERNET_TRANSLATE:
		core.MY_PRINT_FUNC("... making %d requests to Google Translate web API..." % num_calls)
	else:
		# no need to print failing statement, the function already does
		# don't quit early, run thru the same full structure & eventually return a copy of the JP names
		core.MY_PRINT_FUNC("Just copying JP -> EN while Google Translate is disabled")
		_DISABLE_INTERNET_TRANSLATE = True
	
	# 6. send chunks to Google
	results_packets = []
	if use_chunk_strat:
		print("#items=", len(in_list), "#chunks=", len(jp_chunks), "#requests=", len(jp_chunks_packets))
		for d, packet in enumerate(jp_chunks_packets):
			core.print_progress_oneline(d / len(jp_chunks_packets))
			r = _single_google_translate(packet)
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
		google_plus_words.update(translation_tools.words_dict)
		google_plus_words.update(google_dict)
		google_plus_words.update(localtrans_dict)  # add dict entries from things that succeeded localtrans
		# ensure it's sorted big-to-small
		google_plus_words = translation_tools.sort_dict_with_longest_keys_first(google_plus_words)

		# sanity-check: i'm pretty sure that the keys of the 3 dicts should be guaranteed to be mutually exclusive?
		assert len(google_plus_words) == len(translation_tools.words_dict) + len(google_dict) + len(localtrans_dict)

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
				chunk_piecewise_subassemble = translation_tools.piecewise_translate(this_jp_chunk, google_plus_words)
				# IS THIS SUCCESSFUL?
				if translation_tools.is_jp(chunk_piecewise_subassemble):
					# no, this is not successful... I do not have all the individual pieces that make up this word
					# so just use the exact-match from google (that i removed a few lines above)
					google_plus_words[this_jp_chunk] = this_google_result
					num_google += 1
				else:
					# yes, this is successful... I would rather use the sub-assembled answer rather than the Google answer!
					google_plus_words[this_jp_chunk] = chunk_piecewise_subassemble
					num_subassemble += 1
					print("jp_chunk = '%s', google = '%s', subassemble = '%s'" %
						  (this_jp_chunk, this_google_result, chunk_piecewise_subassemble))
				# sort it again
				google_plus_words = translation_tools.sort_dict_with_longest_keys_first(google_plus_words)
	
			print("stats: num_google = %d, num_subassemble = %d" % (num_google, num_subassemble))
		
		# 8. piecewise translate using newly created dict
		# it has been fine-tuned and is now guaranteed to fully match against everything that it failed to match before
		outlist = translation_tools.piecewise_translate(bodies, google_plus_words)
		
	else:
		# old style: just translate the strings directly and return their results
		for d, packet in enumerate(jp_bodies_packets):
			core.print_progress_oneline(d / len(jp_bodies_packets))
			r = _single_google_translate(packet)
			results_packets.append(r)
		outlist = _unpacketize_translate_requests(results_packets)
	
	# last, reattach the indents and suffixes
	outlist_final = [i + b + s for i, b, s in zip(indents, outlist, suffixes)]
	
	if not _DISABLE_INTERNET_TRANSLATE:
		# if i did use internet translate, print this line when done
		core.MY_PRINT_FUNC("... done!")
	
	# return
	if input_is_str:
		return outlist_final[0]  # if original input was a single string, then de-listify
	else:
		return outlist_final  # otherwise return as a list


################################################################################################################

def build_StringTranslateRecord_list_from_pmx(pmx: pmxstruct.Pmx) -> List[StringTranslateRecord]:
	"""
	Iterate over a PMX object and build a list of StringTranslateRecord objects from it, that other functions can
	operate on in bulk. This does not attempt to translate them.

	:param pmx: entire PMX object
	:return: list of StringTranslateRecord objects.
	"""
	record_list = []
	
	categories = ["materials", "bones", "morphs", "frames"]
	for catname in categories:
		# use the string version of the member to access the actual member
		biglist = getattr(pmx, catname)
		# walk along that list, everything has the name_jp and name_en member so it's all good
		for d, item in enumerate(biglist):
			# skip "special" display frames, no translation for them!
			if isinstance(item, pmxstruct.PmxFrame) and item.is_special: continue
			# if the JP string is empty, replace it with JP_NULL
			if not item.name_jp or item.name_jp.isspace():
				item.name_jp = "JP_NULL"
			# strip away newline and return just in case, i saw a few examples where they showed up
			item.name_jp = item.name_jp.replace('\r', '').replace('\n', '')
			item.name_en = item.name_en.replace('\r', '').replace('\n', '')
			# build the StringTranslateRecord object
			record = StringTranslateRecord(jp_old=item.name_jp, en_old=item.name_en, cat_name=catname, idx=d)
			record_list.append(record)
	
	# also do the modelname basically the same way
	# strip away newline and return just in case, i saw a few examples where they showed up
	pmx.header.name_jp = pmx.header.name_jp.replace('\r', '').replace('\n', '')
	pmx.header.name_en = pmx.header.name_en.replace('\r', '').replace('\n', '')
	# build the StringTranslateRecord object, idx=0 for name
	record = StringTranslateRecord(jp_old=pmx.header.name_jp, en_old=pmx.header.name_en, cat_name="header", idx=0)
	record_list.append(record)
	
	return record_list

def _trans_source_EN_already_good(recordlist: List[StringTranslateRecord]) -> None:
	"""
	Check whether the english name that's already there is good!
	Modify in-place, no return.
	
	:param recordlist: list of all StringTranslateRecord objects
	"""
	# if it has succesfully translated from some other source, don't overwrite that result!
	remainlist = [R for R in recordlist if R.trans_source is None]
	if DEBUG: core.MY_PRINT_FUNC("stage1 useEN: remaining", len(remainlist))
	
	for item in remainlist:
		# these are all conditions that mean the current name is not good enough
		if item.en_old == "": continue
		if item.en_old.isspace(): continue
		if item.en_old.lower() in FORBIDDEN_ENGLISH_NAMES: continue
		# if not translation_tools.is_latin(item.en_old): continue
		if translation_tools.needs_translate(item.en_old): continue
		
		# if it passes all these checks, then it's a keeper!
		item.en_new = item.en_old
		item.trans_source = "good"
	return
		
def _trans_source_copy_JP(recordlist: List[StringTranslateRecord]) -> None:
	"""
	Check whether the JP name is already a valid EN name.
	Modify in-place, no return.
	:param recordlist: list of all StringTranslateRecord objects
	"""
	# if it has succesfully translated from some other source, don't overwrite that result!
	remainlist = [R for R in recordlist if R.trans_source is None]
	if DEBUG: core.MY_PRINT_FUNC("stage2 copyJP: remaining", len(remainlist))
	
	for item in remainlist:
		# return EN indent, JP(?) body, EN suffix
		indent, body, suffix = translation_tools.pre_translate(item.jp_old)
		
		# check if it is bad
		if body == "": continue
		if body.isspace(): continue
		if body.lower() in FORBIDDEN_ENGLISH_NAMES: continue
		# if not translation_tools.is_latin(body): continue
		if translation_tools.needs_translate(body): continue
	
		# if it's good, then it's a keeper!
		item.en_new = indent + body + suffix
		item.trans_source = "copyJP"
	return

def _trans_source_exact_match(recordlist: List[StringTranslateRecord]) -> None:
	"""
	Check whether the JP name exactly matches in the dict of common names for that type, and if there is a hit then I
	can use the standard translation.
	Modify in-place, no return.
	:param recordlist: list of all StringTranslateRecord objects
	"""
	# if it has succesfully translated from some other source, don't overwrite that result!
	remainlist = [R for R in recordlist if R.trans_source is None]
	if DEBUG: core.MY_PRINT_FUNC("stage3 exact: remaining", len(remainlist))
	
	for item in remainlist:
		# return EN indent, JP(?) body, EN suffix
		indent, body, suffix = translation_tools.pre_translate(item.jp_old)
		
		# does it have a dict associated with it?
		if item.cat in membername_to_specificdict_dict:
			specific = membername_to_specificdict_dict[item.cat]
			# is this body exactly in the dict?
			if body in specific:
				# then it's an exact match and that's good enough for me!
				item.en_new = indent + specific[body] + suffix
				item.trans_source = "exact"
	return

def _trans_source_piecewise_translate(recordlist: List[StringTranslateRecord]) -> None:
	"""
	Attempt piecewise translation using the translation_tools.words_dict.
	Modify in-place, no return.
	:param recordlist: list of all StringTranslateRecord objects
	"""
	# if it has succesfully translated from some other source, don't overwrite that result!
	remainlist = [R for R in recordlist if R.trans_source is None]
	if DEBUG: core.MY_PRINT_FUNC("stage4 piece: remaining", len(remainlist))
	
	########
	
	# actually do local translate
	remainlist_strings = [R.jp_old for R in remainlist]
	local_results = translation_tools.local_translate(remainlist_strings)
	# determine if each item passed or not, update the en_new and trans_type fields
	for item, result in zip(remainlist, local_results):
		# did it pass?
		if not translation_tools.needs_translate(result):
			# yes! hooray!
			item.en_new = result
			item.trans_source = "piece"
	return

def _trans_source_google_translate(recordlist: List[StringTranslateRecord]) -> None:
	"""
	Attempt Google translation. Usually guaranteed to succeed.
	Modify in-place, no return.
	:param recordlist: list of all StringTranslateRecord objects
	"""
	# if it has succesfully translated from some other source, don't overwrite that result!
	remainlist = [R for R in recordlist if R.trans_source is None]
	if DEBUG: core.MY_PRINT_FUNC("stage5 google: remaining", len(remainlist))
	
	if not remainlist: return
	########
	# actually do google translate
	core.MY_PRINT_FUNC("... identified %d items that need Internet translation..." % len(remainlist))
	try:
		remainlist_strings = [R.jp_old for R in remainlist]
		google_results = google_translate(remainlist_strings)
	except Exception as e:
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		core.MY_PRINT_FUNC("ERROR: Internet translate unexpectedly failed, attempting to recover...")
		# for each in translate-notdone, set status to fail, set newname to oldname (so it won't change)
		for item in remainlist:
			# item.trans_type = "FAIL"
			item.en_new = item.en_old
			# fail-state is when a new name has been assigned but type has not been set, this way it is easily overridden
		return

	# determine if each item passed or not, update the en_new and trans_type fields
	for item, result in zip(remainlist, google_results):
		# always (tentatively) accept the google result, pass or fail it's the best i've got
		item.en_new = result
		# determine whether it passed or failed for display purposes
		# failure is usually due to unusual geometric symbols, not due to japanese text, but sometimes it just fucks up
		# if it fails, leave the type as NONE so it might be overridden by other stages I guess
		if not translation_tools.needs_translate(result):
			item.trans_source = "google"
	return

def _trans_source_catchall_fail(recordlist: List[StringTranslateRecord]) -> None:
	"""
	Set the trans_type field for anything that didn't get caught.
	Modify in-place, no return.
	:param recordlist: list of all StringTranslateRecord objects
	"""
	# if it has succesfully translated from some other source, don't overwrite that result!
	remainlist = [R for R in recordlist if R.trans_source is None]
	if DEBUG: core.MY_PRINT_FUNC("stage6 fail: remaining", len(remainlist))
	
	for item in remainlist:
		# unconditionally replace any remaining "none" with "FAIL"
		item.trans_source = "FAIL"
		# if there is no tentatively-assigned translation, then keep the previous english name (no change)
		if item.en_new is None:
			item.en_new = item.en_old
	return
	

################################################################################################################


helptext = '''====================
translate_to_english:
This tool fills out empty EN names in a PMX model with translated versions of the JP names.
It tries to do some intelligent piecewise translation using a local dictionary but goes to Google Translate if that fails.
Machine translation is never 100% reliable, so this is only a stopgap measure to eliminate all the 'Null_##'s and wrongly-encoded garbage and make it easier to use in MMD. A bad translation is better than none at all!
Also, Google Translate only permits ~100 requests per hour, if you exceed this rate you will be locked out for 24(?) hours.
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
	input_filename_pmx = core.prompt_user_filename("PMX file", ".pmx")
	pmx = pmxlib.read_pmx(input_filename_pmx, moreinfo=True)
	return pmx, input_filename_pmx



def translate_to_english(pmx: pmxstruct.Pmx, moreinfo=False):
	
	# step zero: set up the translator thingy
	init_googletrans()
	
	# if JP model name is empty, give it something. same for comment.
	# if EN model name is empty, copy JP. same for comment.
	if pmx.header.name_jp == "":
		pmx.header.name_jp = "model"
	if pmx.header.comment_jp == "":
		pmx.header.comment_jp = "comment"
	if pmx.header.name_en == "":
		pmx.header.name_en = pmx.header.name_jp
	if pmx.header.comment_en == "":
		pmx.header.comment_en = pmx.header.comment_jp
		
	# step 1: create the list of translate records
	translate_record_list = build_StringTranslateRecord_list_from_pmx(pmx)
	
	#####################################################
	
	# step 2: the pipeline
	# the stages of this pipeline can be reorded to prioritize translations from different sources
	
	_trans_source_EN_already_good(translate_record_list)
	
	_trans_source_copy_JP(translate_record_list)
	
	_trans_source_exact_match(translate_record_list)
	
	_trans_source_piecewise_translate(translate_record_list)
	
	# _trans_source_EN_already_good(translate_record_list)
	
	_trans_source_google_translate(translate_record_list)
	
	# _trans_source_EN_already_good(translate_record_list)

	# catchall should always be last tho
	_trans_source_catchall_fail(translate_record_list)
	
	
	###########################################
	# done translating!!!!!
	###########################################
	
	# sanity check: if old result matches new result, then force type to be nochange
	for m in translate_record_list:
		if m.en_old == m.en_new and m.trans_source != "FAIL":
			m.trans_source = "good"
	
	# now, determine if i actually changed anything at all before bothering to try applying stuff
	type_fail = [R for R in translate_record_list if R.trans_source == "FAIL"]
	type_good = [R for R in translate_record_list if R.trans_source == "good"]
	type_copy = [R for R in translate_record_list if R.trans_source == "copyJP"]
	type_exact = [R for R in translate_record_list if R.trans_source == "exact"]
	type_local = [R for R in translate_record_list if R.trans_source == "piece"]
	type_google = [R for R in translate_record_list if R.trans_source == "google"]
	
	# number of things I could have translated
	total_fields = len(translate_record_list)
	# number of things that weren't already good (includes changed and fail)
	total_changed = total_fields - len(type_good)
	if type_fail:
		# warn about any strings that failed translation
		core.MY_PRINT_FUNC("WARNING: %d items were unable to be translated, try running the script again or doing translation manually." % len(type_fail))
	if total_changed == 0:
		core.MY_PRINT_FUNC("No changes are required")
		return pmx, False
		
	###########################################
	# step 3, apply!
	for item in translate_record_list:
		# writeback any source except "nochange"
		# even writeback fail type, because fail will be my best-effort translation
		# if its being translated thats cuz old_en is bad, so im not making it any worse
		# failure probably due to unusual geometric symbols, not due to japanese text
		if item.trans_source != "good":
			if item.cat == "header":  # this is header-type, meaning this is model name
				pmx.header.name_en = item.en_new
			else:
				# access the source list by the stored name (kinda dangerous)
				sourcelist = getattr(pmx, item.cat)
				# write into it by the stored index
				sourcelist[item.idx].name_en = item.en_new
	
	###########################################
	# step 4, print info!
	core.MY_PRINT_FUNC("Translated {} / {} = {:.1%} english fields in the model".format(
		total_changed, total_fields, total_changed / total_fields))
	if moreinfo or type_fail:
		# give full breakdown of each source if requested OR if any fail
		core.MY_PRINT_FUNC("Total fields={}, nochange={}, copy={}, exactmatch={}, piecewise={}, Google={}, fail={}".format(
			total_fields, len(type_good), len(type_copy), len(type_exact), len(type_local), len(type_google), len(type_fail)))
		#########
		# now print the table of before/after/etc
		if not moreinfo:
			# if moreinfo not enabled, only show fails
			maps_printme = [R for R in translate_record_list if R.trans_source == "FAIL"]
		elif SHOW_ALL_CHANGED_FIELDS:
			# if moreinfo is enabled and SHOW_ALL_CHANGED_FIELDS is set,
			# show everything that isn't nochange
			maps_printme = [R for R in translate_record_list if R.trans_source != "good"]
		else:
			# hide good/copyJP/exactmatch cuz those are uninteresting and guaranteed to be safe
			# only show piecewise and google translations and fails
			maps_printme = [R for R in translate_record_list if R.trans_source not in ("exact", "copyJP", "good")]
			
		# if there is anything to be printed,
		if maps_printme:
			# assemble & justify each column
			# columns: category, idx, trans_type, en_old, en_new, jp_old = 6 types
			# bone  15  google || EN: 'asdf' --> 'foobar' || JP: 'fffFFFff'
			cat = [membername_to_shortname_dict[vv.cat] for vv in maps_printme]
			idx = [str(vv.idx) for vv in maps_printme]
			source = [vv.trans_source for vv in maps_printme]
			enold = ["'%s'" % vv.en_old for vv in maps_printme]
			ennew = ["'%s'" % vv.en_new for vv in maps_printme]
			jpold =  ["'%s'" % vv.jp_old for vv in maps_printme]
			just_cat =    core.MY_JUSTIFY_STRINGLIST(cat)
			just_idx =    core.MY_JUSTIFY_STRINGLIST(idx, right=True)  # this is right-justify, all others are left
			just_source = core.MY_JUSTIFY_STRINGLIST(source)
			just_enold =  core.MY_JUSTIFY_STRINGLIST(enold)
			just_ennew =  core.MY_JUSTIFY_STRINGLIST(ennew)
			# jpold is final item, nothing to the right of it, so it doesn't need justified
			
			# now pretty-print the list of translations:
			for args in zip(just_cat, just_idx, just_source, just_enold, just_ennew, jpold):
				core.MY_PRINT_FUNC("{} {} {} || EN: {} --> {} || JP: {}".format(*args))
				
	###########################################
	# done! return!
	return pmx, True
	
	
def end(pmx, input_filename_pmx):
	# write out
	output_filename_pmx = core.filepath_insert_suffix(input_filename_pmx, "_translate")
	output_filename_pmx = core.filepath_get_unused_name(output_filename_pmx)
	pmxlib.write_pmx(output_filename_pmx, pmx, moreinfo=True)
	return None

def main():
	showhelp()
	pmx, name = showprompt()
	pmx, is_changed = translate_to_english(pmx, moreinfo=True)
	if is_changed:
		end(pmx, name)
	core.pause_and_quit("Done with everything! Goodbye!")


if __name__ == '__main__':
	core.MY_PRINT_FUNC(_SCRIPT_VERSION)
	core.MY_PRINT_FUNC(helptext)
	core.RUN_WITH_TRACEBACK(main)
