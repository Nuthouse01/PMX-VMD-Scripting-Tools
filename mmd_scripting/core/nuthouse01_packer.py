import math
import re
import struct
from collections import defaultdict
from typing import Any

import mmd_scripting.core.nuthouse01_core as core

# TODO: change how I handle the custom 't' atoms to make things more efficient

########################################################################################################################
# these functions for binary file structure packing & unpacking
########################################################################################################################
# encoding notes:
# one known error case is that the "fullwidth tilde" = ～ = u"\uFF5E" cannot be represented in shift_jis
# 	this symbol can be in PMX files but will not be in VMD files
# 	MMD automatically replaces this with "wave dash" = 〜 = u"\u301c" when creating VMDs (which are saved in shift_jis)
# 	therefore I must do the same replacement in order to encode this as shift_jis
# also, shift_jis confuses the backslash \ and yen ¥
# 	in shift_jis, both get mapped to the same bytevalue and become indistinguishable
# 	in MMD, in the 4-group thing at the bottom with the dropdown lists, they both display as \
#	when I encode as shift_jis and write to file, they are printed as \
# 	in MMD, in the timeline on the left, they both display as ¥
#	(does it display in MMD as shift_jis_2004 or shift_jisx0208 but write to file as shift_jis? not really worth exploring)
# also, shift_jis confuses the overline ‾ and tilde ~ (the regular tilde, not the fullwidth tilde)
#	this is exactly the same as the backslash and yen, they are internally mapped to the same values so they are indistinguishable
#	when i encode as shift_jis and write to file, they are both printed as ~

# these functions add extra utility to the standard python packing/unpacking library
# they define a new atom "t" that represents an actual string type, if preceeded by numbers that indicates how many
#   bytes of space it uses, if NOT preceeded by numbers then it is represented in binary form as an int which indicates
#   how big the string is, followed by the actual string
# vmd format uses the "##t" syntax, pmx format uses the "t" syntax

# variable to keep track of where to start reading from next within the raw-file
UNPACKER_READFROM_BYTE = 0
# this should be hardcoded and never changed, something weird that nobody would ever use in a name
UNPACKER_ESCAPE_CHAR = "‡"
# encoding to use when packing/unpackign strings
UNPACKER_ENCODING = "utf8"
# dict to store all strings that failed to translate, plus counts
UNPACKER_FAILED_TRANSLATE_DICT = defaultdict(lambda: 0)
# flag to indicate whether the last decoding needed escaping or not, cuz returning as a tuple is ugly
UNPACKER_FAILED_TRANSLATE_FLAG = False
# simple regex to find char "t" along with as many digits appear in front of it as possible
t_fmt_pattern = r"\d*t"
t_fmt_re = re.compile(t_fmt_pattern)


# why do things with accessor functions? ¯\_(ツ)_/¯ cuz i want to
def reset_unpack():
	global UNPACKER_READFROM_BYTE
	UNPACKER_READFROM_BYTE = 0
	UNPACKER_FAILED_TRANSLATE_DICT.clear()


def set_encoding(newencoding: str):
	global UNPACKER_ENCODING
	UNPACKER_ENCODING = newencoding


def get_readfrom_byte():
	return UNPACKER_READFROM_BYTE


def print_failed_decodes():
	if len(UNPACKER_FAILED_TRANSLATE_DICT) != 0:
		core.MY_PRINT_FUNC("List of all strings that failed to decode, plus their occurance rate")
		core.MY_PRINT_FUNC(UNPACKER_FAILED_TRANSLATE_DICT)


def decode_bytes_with_escape(r: bytearray) -> str:
	"""
	Turns bytes into a string, with some special quirks. Reversible opposite of encode_string_with_escape().
	In VMDs the text fields are truncated to a set # of bytes, so it's possible that they might be cut off
	mid multibyte char, and therefore be undecodeable. Instead of losing this data, I decode what I can and
	the truncated char is converted to UNPACKER_ESCAPE_CHAR followed by hex digits that represent the remaining
	byte. It's not useful to humans, but it is better than simply losing the data.
	TODO: get example
	All cases I tested require at most 1 escape char, but just to be safe it recursively calls as much as needed.
	
	:param r: bytearray object which represents a string through encoding UNPACKER_ENCODING
	:return: decoded string, possibly ending with escape char and hex digits
	"""
	global UNPACKER_FAILED_TRANSLATE_FLAG
	try:
		s = r.decode(UNPACKER_ENCODING)				# try to decode the whole string
		return s
	except UnicodeDecodeError:
		UNPACKER_FAILED_TRANSLATE_FLAG = True
		s = decode_bytes_with_escape(r[:-1])		# if it cant, decode everything but the last byte
		extra = r[-1]  								# this is the last byte that couldn't be decoded
		s = "%s%s%x" % (s, UNPACKER_ESCAPE_CHAR, extra)
		return s


def encode_string_with_escape(a: str) -> bytearray:
	"""
	Turns a string into bytes, with some special quirks. Reversible opposite of decode_string_with_escape().
	In VMDs the text fields are truncated to a set # of bytes, so it's possible that they might be cut off
	mid multibyte char, and therefore be undecodeable. Instead of losing this data, I decode what I can and
	the truncated char is converted to UNPACKER_ESCAPE_CHAR followed by hex digits that represent the remaining
	byte. It's not useful to humans, but it is better than simply losing the data.
	TODO: get example
	All cases I tested require at most 1 escape char, but just to be safe it recursively calls as much as needed.
	
	:param a: string that might contain my custom escape sequence
	:return: bytearray after encoding
	"""
	try:
		if len(a) > 3:									# is it long enough to maybe contain an escape char?
			if a[-3] == UNPACKER_ESCAPE_CHAR:			# check if 3rd from end is an escape char
				n = encode_string_with_escape(a[0:-3])	# convert str before escape from str to bytearray
				n += bytearray.fromhex(a[-2:])			# convert hex after escape char to single byte and append
				return n
		return bytearray(a, UNPACKER_ENCODING)			# no escape char: convert from str to bytearray the standard way
	except UnicodeEncodeError:
		# if the decode fails, I hope it is because the input string contains a fullwidth tilde, that's the only error i know how to handle
		# NOTE: there are probably other things that can fail that I just dont know about yet
		new_a = a.replace(u"\uFF5E", u"\u301c")			# replace "fullwidth tilde" with "wave dash", same as MMD does
		try:
			return bytearray(new_a, UNPACKER_ENCODING)	# no escape char: convert from str to bytearray the standard way
		except UnicodeEncodeError as e:
			# overwrite the 'reason' field with the original string it was trying to encode
			e.reason = a
			# then return it to be handled outside
			raise e
			# # to reduce redundant printouts, all the info I wanna print is put into RuntimeError and caught somewhere higher up
			# newerrstr = "encode_string_with_escape: chr='%s', str='%s', encoding=%s, err=%s" % (a[e.start:e.end], a, e.encoding, e.reason),
			# newerr = RuntimeError(newerrstr)
			# raise newerr


def my_unpack(fmt:str, raw:bytearray) -> Any:
	"""
	Use a given format string to convert the next section of a binary file bytearray into type-correct variables.
	Uses global var UNPACKER_READFROM_BYTE to know where to start unpacking next.
	Very similar to python struct.unpack() function, except: 1) automatically tracks where it has unpacked & where it
	should unpack next via the size of the format strings, 2) if exactly 1 variable would be unpacked it is
	automatically de-listed and returned naked, 3) new atom type "t" is supported and indicates auto-length strings,
	4) new atom type "##t" is supported and indicates fixed-length strings.
	
	:param fmt: string-type format argument very similar to formats for python "struct" lib
	:param raw: bytearray being walked & unpacked
	:return: if fmt specifies several variables, return all as list. if exactly one, return the variable without list wrapper.
	"""
	retlist = []
	startfrom = 0
	# first find where all "t" atoms in the format string are
	t_atom_list = t_fmt_re.finditer(fmt)
	for t_atom in t_atom_list:
		# fmt_before definitely does not contain t: parse as normal & return value
		fmt_before = fmt[startfrom:t_atom.start()]  # fmt_before might be empty or blank, but that's handled inside the func
		before_vars = _unpack_other(fmt_before, raw)
		retlist.extend(before_vars)  # before_vars might be empty list but thats ok
		# fmt_t contains a "t" atom, guaranteed not blank, it gets specially handled
		fmt_t = fmt[t_atom.start():t_atom.end()]
		t_str = _unpack_text(fmt_t, raw)
		retlist.append(t_str)  # t_str guaranteed to exist and be a lone string
		# repeat the process starting from the section after the "t" atom
		startfrom = t_atom.end()
	# when there are no more "t" atoms, all that remains gets handled by default unpacker
	other_vars = _unpack_other(fmt[startfrom:], raw)
	retlist.extend(other_vars)  # other_vars might be empty list but thats ok
	# if it has length of 1, then de-listify it
	if len(retlist) == 1: return retlist[0]
	else:                 return retlist


def _unpack_other(fmt:str, raw:bytearray) -> list:
	"""
	Internal use only.
	Handle unpacking of all types other than "t" atoms. "fmt" is guaranteed to not contain any "t" atoms.
	
	:param fmt: string-type format argument very similar to formats for python "struct" lib
	:param raw: bytearray being walked & unpacked
	:return: list of all variables that were unpacked corresponding to fmt
	"""
	global UNPACKER_READFROM_BYTE
	if fmt == "" or fmt.isspace():
		return []  # if fmt is emtpy then don't attempt to unpack
	try:
		autofmt = "<" + fmt
		r = struct.unpack_from(autofmt, raw, UNPACKER_READFROM_BYTE)
		UNPACKER_READFROM_BYTE += struct.calcsize(autofmt)	# increment the global read-from tracker
	except Exception as e:
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		core.MY_PRINT_FUNC("unpack_other")
		# repackage the error to add additional info and throw it again to be caught at a higher level
		newerrstr = "err=" + str(e) + "\nfmt=" + fmt + "\nbytepos=" + str(UNPACKER_READFROM_BYTE)
		newerr = RuntimeError(newerrstr)
		raise newerr
	# convert from tuple to list
	retme = list(r)
	# new: check for NaN and replace with 0
	for i in range(len(retme)):
		foo = retme[i]
		if isinstance(foo, float):
			if math.isnan(foo):
				retme[i] = 0.0
				core.MY_PRINT_FUNC("Warning: found NaN in place of float shortly before bytepos %d, replaced with 0.0" % UNPACKER_READFROM_BYTE)
			if math.isinf(foo):
				retme[i] = 0.0
				core.MY_PRINT_FUNC("Warning: found INF in place of float shortly before bytepos %d, replaced with 0.0" % UNPACKER_READFROM_BYTE)
	return retme


def _unpack_text(fmt:str, raw:bytearray) -> str:
	"""
	Internal use only.
	Handle unpacking of "t" atoms. "fmt" is guaranteed to contain only a "t" atom, nothing else.
	
	:param fmt: string-type format argument very similar to formats for python "struct" lib
	:param raw: bytearray being walked & unpacked
	:return: string
	"""
	global UNPACKER_READFROM_BYTE
	global UNPACKER_FAILED_TRANSLATE_FLAG
	# input fmt string is exactly either "t" or "#t" or "##t", etc
	try:
		if fmt == "t":		# this mode exclusively used for PMX parsing
			# auto-text: a text type is an int followed by that many bytes
			i = struct.unpack_from("<i", raw, UNPACKER_READFROM_BYTE)	# get how many bytes to read for str
			UNPACKER_READFROM_BYTE += 4							# increment the global read-from tracker
			autofmt = "<" + str(i[0]) + "s"						# build fmt string that includes # of bytes to read
		else:				# this mode exclusively used for VMD parsing
			# manual-text: if a number is provided with it in the format string, then just read that number of bytes
			autofmt = "<" + fmt[:-1] + "s"						# build fmt string that includes # of bytes to read
			
		v = struct.unpack_from(autofmt, raw, UNPACKER_READFROM_BYTE)	# unpack the actual string(bytearray)
		UNPACKER_READFROM_BYTE += struct.calcsize(autofmt)		# increment the global read-from tracker
		r = v[0]												# un-listify the result
		
		if fmt != "t":
			# manual-text strings are null-terminated: everything after a null byte is invalid garbage to be discarded
			i = r.find(b'\x00')									# look for a null terminator
			if i != -1:											# if null is found...
				r = r[0:i]										# ...return only bytes before it
	except Exception as e:
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		core.MY_PRINT_FUNC("unpack_text")
		# repackage the error to add additional info and throw it again to be caught at a higher level
		newerrstr = "err=" + str(e) + "\nfmt=" + fmt + "\nbytepos=" + str(UNPACKER_READFROM_BYTE)
		newerr = RuntimeError(newerrstr)
		raise newerr
	# r is now a bytearray that should be mappable onto a string, unless it is cut off mid-multibyte-char
	s = decode_bytes_with_escape(r)
	# translated string is now in s (maybe with the escape char tacked on)
	# did it need escaping? add it to the dict for reporting later!
	if UNPACKER_FAILED_TRANSLATE_FLAG:
		UNPACKER_FAILED_TRANSLATE_FLAG = False
		UNPACKER_FAILED_TRANSLATE_DICT[s] += 1
	# still need to return as a list for concatenation reasons
	return s


def my_pack(fmt: str, args_in: Any) -> bytearray:
	"""
	Use a given format string to convert a list of args into the next section of a binary file bytearray.
	Very similar to python struct.unpack() function, except: 1) if the input arg is not a list/tuple it is automatically
	wrapped in a list, 2) new atom type "t" is supported and indicates auto-length strings, 3) new atom type "##t" is
	supported and indicates fixed-length strings.
	
	:param fmt: string-type format argument very similar to formats for python "struct" lib
	:param args_in: list of variables to pack, or a single variable not inside a list
	:return: bytearray representation of these args
	"""
	
	if isinstance(args_in, list):
		args = args_in						# if given list, pass thru unchanged
	elif isinstance(args_in, tuple):
		args = list(args_in)				# if given tuple, make it a list
	else:
		args = [args_in]					# if given lone arg, wrap it with a list
	
	retbytes = bytearray()
	startfrom = 0
	startfrom_args = 0
	
	# first find where all "t" atoms in the format string are
	# (note: returns an iterator, to get its length I need to walk the whole thing and then convert to list)
	t_atom_list = [t for t in t_fmt_re.finditer(fmt)]
	# then find where all strings in the input args list are
	str_idx_list = [d for d,a in enumerate(args) if isinstance(a, str)]
	# assert that they are the same length
	if len(t_atom_list) != len(str_idx_list):
		raise RuntimeError("given format string '%s' references %d strings, found %d in args list" %
						   (fmt, len(t_atom_list), len(str_idx_list)))
	
	for t_atom, str_idx in zip(t_atom_list, str_idx_list):
		# fmt_before definitely does not contain t: parse as normal & return value
		fmt_before = fmt[startfrom:t_atom.start()]  # fmt_before might be empty or blank, but that's handled inside the func
		bytes_before = _pack_other(fmt_before, args[startfrom_args:str_idx])
		retbytes += bytes_before  # bytes_before might be empty but thats ok
		# fmt_t contains a "t" atom, guaranteed not blank, it gets specially handled
		fmt_t = fmt[t_atom.start():t_atom.end()]
		bytes_t = _pack_text(fmt_t, args[str_idx])  # guaranteed to return non-empty
		retbytes += bytes_t
		# repeat the process starting from the section after the "t" atom
		startfrom = t_atom.end()
		startfrom_args = str_idx + 1
	# when there are no more "t" atoms, all that remains gets handled by default packer
	ret_other = _pack_other(fmt[startfrom:], args[startfrom_args:])
	retbytes += ret_other

	return retbytes


def _pack_other(fmt: str, args: list) -> bytearray:
	"""
	Internal use only.
	Handle packing of all types other than "t" atoms. "fmt" is guaranteed to not contain any "t" atoms.
	
	:param fmt: string-type format argument very similar to formats for python "struct" lib
	:param args: list filled with variables to pack
	:return: bytearray representation of the args
	"""
	if not args or fmt == "" or fmt.isspace():
		return bytearray()  # if fmt is emtpy or args is empty then don't attempt to pack
	try:
		b = struct.pack("<" + fmt, *args)	# now do the actual packing
		return bytearray(b)
	except Exception as e:
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		core.MY_PRINT_FUNC("pack_other")
		# repackage the error to add additional info and throw it again to be caught at a higher level
		newerrstr = "err=" + str(e) + "\nfmt=" + fmt + "\nargs=" + str(args)
		newerr = RuntimeError(newerrstr)
		raise newerr


def _pack_text(fmt: str, args: str) -> bytearray:
	"""
	Internal use only.
	Handle packing of "t" atoms. "fmt" is guaranteed to contain only a "t" atom, nothing else.
	
	:param fmt: string-type format argument very similar to formats for python "struct" lib
	:param args: string
	:return: bytearray representation of the input string
	"""
	try:
		n = encode_string_with_escape(args)		# convert str to bytearray
		if fmt == "t":			# auto-text
			# "t" means "i ##s" where ##=i. convert to bytearray, measure len, replace t with "i ##s"
			autofmt = "<i" + str(len(n)) + "s"
			autoargs = [len(n), n]
		else:					# manual-text
			autofmt = "<" + fmt[0:-1] + "s"		# simply replace trailing t with s
			autoargs = [n]
		
		b = struct.pack(autofmt, *autoargs)		# now do the actual packing
		return bytearray(b)
	except Exception as e:
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		core.MY_PRINT_FUNC("pack_text")
		# repackage the error to add additional info and throw it again to be caught at a higher level
		# these are the args before replacing t with s, and before converting strings to bytearrays
		newerrstr = "err=" + str(e) + "\nfmt=" + fmt + "\nargs=" + str(args)
		newerr = RuntimeError(newerrstr)
		raise newerr