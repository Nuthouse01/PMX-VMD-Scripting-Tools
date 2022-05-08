from typing import List

import mmd_scripting.core.nuthouse01_core as core
import mmd_scripting.core.nuthouse01_pmx_parser as pmxlib
import mmd_scripting.core.nuthouse01_pmx_struct as pmxstruct
from mmd_scripting.core import translation_dictionaries, translation_functions

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.04 - 8/19/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

# this switch will enable extra printouts throughout the script
DEBUG = False


# how much do i trust the existing english names? (if any exist)
# 1: max trust, i.e. check this first
# 2: after exact-match but before piecewise
# 3: after piecewise but before google
# 4: only if google fails
TRUST_EXISTING_ENGLISH_NAME = 1


# if your internet went out or something? idk why you would want to disable this, but you can
DISABLE_INTERNET_TRANSLATE = False


# sometimes chinese translation gives better results than japanese translation
# when false, force input to be interpreted as Japanese. When true, autodetect input language.
GOOGLE_AUTODETECT_LANGUAGE = False


# by default, do not display copyJP/exactmatch modifications
# if this is true, they will also be shown
SHOW_ALL_CHANGED_FIELDS = False


# these english names will be treated as tho they do not exist and overwritten no matter what:
FORBIDDEN_ENGLISH_NAMES = ["en", "d", "mat", "morph", "new morph", "bone", "new bone", "material", "new material"]




# this is used when the results are ultimately printed
membername_to_shortname_dict = {"header":"header", "materials":"mat", "bones":"bone", "morphs":"morph", "frames":"frame"}
# this will associate the dicts that are optimized for each category, with that category
membername_to_specificdict_dict = {
	"bones": translation_dictionaries.bone_dict,
	"morphs": translation_dictionaries.morph_dict,
	"frames": translation_dictionaries.frame_dict,
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
	if DEBUG: print("stage1 useEN: remaining", len(remainlist))
	
	for item in remainlist:
		# these are all conditions that mean the current name is not good enough
		if item.en_old == "": continue
		if item.en_old.isspace(): continue
		if item.en_old.lower() in FORBIDDEN_ENGLISH_NAMES: continue
		# if not translation_tools.is_latin(item.en_old): continue
		if translation_functions.needs_translate(item.en_old): continue
		
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
	if DEBUG: print("stage2 copyJP: remaining", len(remainlist))
	
	for item in remainlist:
		# return EN indent, JP(?) body, EN suffix
		indent, body, suffix = translation_functions.pre_translate(item.jp_old)
		
		# check if it is bad
		if body == "": continue
		if body.isspace(): continue
		if body.lower() in FORBIDDEN_ENGLISH_NAMES: continue
		# if not translation_tools.is_latin(body): continue
		if translation_functions.needs_translate(body): continue
	
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
	if DEBUG: print("stage3 exact: remaining", len(remainlist))
	
	for item in remainlist:
		# return EN indent, JP(?) body, EN suffix
		indent, body, suffix = translation_functions.pre_translate(item.jp_old)
		
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
	if DEBUG: print("stage4 piece: remaining", len(remainlist))
	
	########
	
	# actually do local translate
	remainlist_strings = [R.jp_old for R in remainlist]
	local_results = translation_functions.local_translate(remainlist_strings)
	# determine if each item passed or not, update the en_new and trans_type fields
	for item, result in zip(remainlist, local_results):
		# did it pass?
		if not translation_functions.needs_translate(result):
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
	if DISABLE_INTERNET_TRANSLATE: return
	# if it has succesfully translated from some other source, don't overwrite that result!
	remainlist = [R for R in recordlist if R.trans_source is None]
	if DEBUG: print("stage5 google: remaining", len(remainlist))
	
	if not remainlist: return
	########
	# actually do google translate
	core.MY_PRINT_FUNC("... identified %d items that need Internet translation..." % len(remainlist))
	try:
		remainlist_strings = [R.jp_old for R in remainlist]
		google_results = translation_functions.google_translate(remainlist_strings,
																autodetect_language=GOOGLE_AUTODETECT_LANGUAGE,
																chunks_only_kanji=True)
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
		if not translation_functions.needs_translate(result):
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
	if DEBUG: print("stage6 fail: remaining", len(remainlist))
	
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
	
	# # step zero: set up the translator thingy
	# init_googletrans()
	
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
	# the variable TRUST_EXISTING_ENGLISH_NAME controls the order of operations to some extent
	
	if TRUST_EXISTING_ENGLISH_NAME == 1: _trans_source_EN_already_good(translate_record_list)  #1
	_trans_source_copy_JP(translate_record_list)  #2
	_trans_source_exact_match(translate_record_list)  #3
	if TRUST_EXISTING_ENGLISH_NAME == 2: _trans_source_EN_already_good(translate_record_list)  #1
	_trans_source_piecewise_translate(translate_record_list)  #4
	if TRUST_EXISTING_ENGLISH_NAME == 3: _trans_source_EN_already_good(translate_record_list)  #1
	_trans_source_google_translate(translate_record_list)  #5
	if TRUST_EXISTING_ENGLISH_NAME == 4: _trans_source_EN_already_good(translate_record_list)  #1

	# catchall should always be last tho
	_trans_source_catchall_fail(translate_record_list)  #6
	
	
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
