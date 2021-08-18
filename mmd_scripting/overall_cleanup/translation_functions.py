import re
from typing import TypeVar, List, Tuple, Dict

from mmd_scripting.overall_cleanup import translation_tools

# to use builtin "string.translate() function", must assemble a dict where key is UNICODE NUMBER and value is string
prefix_dict_ord =          dict((ord(k), v) for k, v in translation_tools.prefix_dict.items())
odd_punctuation_dict_ord = dict((ord(k), v) for k, v in translation_tools.odd_punctuation_dict.items())
fullwidth_dict_ord =       dict((ord(k), v) for k, v in translation_tools.ascii_full_to_basic_dict.items())

STANDARD_INDENT = "  "

DEBUG = False

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
needstranslate_pattern += "".join(translation_tools.symbols_dict.keys())  # add "symbol dict" just in case there are some outlyers... some overlap with ranges but w/e
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


STR_OR_STRLIST = TypeVar("STR_OR_STRLIST", str, List[str])
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
		out = piecewise_translate(out, translation_tools.katakana_half_to_full_dict, join_with_space=False)
		
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
	outbodies = piecewise_translate(bodies, translation_tools.words_dict)
	
	# third, reattach the indents and suffixes
	outlist = [i + b + s for i,b,s in zip(indents, outbodies, suffixes)]
	
	# pretty much done! check whether it passed/failed outside this func
	if DEBUG:
		for s,o in zip(in_list, outlist):
			# did i translate the whole thing? check whether results are all "normal" characters
			print("%d :: %s :: %s" % (is_latin(o), s, o))
	
	if input_is_str:	return outlist[0]	# if original input was a single string, then de-listify
	else:				return outlist		# otherwise return as a list