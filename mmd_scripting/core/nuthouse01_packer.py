import math
import struct
from collections import defaultdict
from typing import Any

import mmd_scripting.core.nuthouse01_core as core

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.03 - 8/9/2021"

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




# variable to keep track of where to start reading from next within the raw-file
UNPACKER_READFROM_BYTE = 0
# this should be hardcoded and never changed, something weird that nobody would ever use in a name
_UNPACKER_ESCAPE_CHAR = "‡"
# encoding to use when packing/unpackign strings
_UNPACKER_ENCODING = "utf8"
# dict to store all strings that failed to translate, plus counts
_UNPACKER_FAILED_TRANSLATE_DICT = defaultdict(lambda: 0)
# flag to indicate whether the last decoding needed escaping or not, cuz returning as a tuple is ugly
_UNPACKER_FAILED_TRANSLATE_FLAG = False


# why do things with accessor functions? ¯\_(ツ)_/¯ cuz i want to
def reset_unpack():
	global UNPACKER_READFROM_BYTE
	UNPACKER_READFROM_BYTE = 0
	_UNPACKER_FAILED_TRANSLATE_DICT.clear()
def set_encoding(newencoding: str):
	global _UNPACKER_ENCODING
	_UNPACKER_ENCODING = newencoding
def print_failed_decodes():
	if len(_UNPACKER_FAILED_TRANSLATE_DICT) != 0:
		core.MY_PRINT_FUNC("List of all strings that failed to decode, plus their occurance rate:")
		keys = ["'" + k + "':" for k in _UNPACKER_FAILED_TRANSLATE_DICT.keys()]
		keys_justified = core.MY_JUSTIFY_STRINGLIST(keys)
		for k,v in zip(keys_justified, _UNPACKER_FAILED_TRANSLATE_DICT.values()):
			core.MY_PRINT_FUNC("    %s  %d" % (k,v))


def decode_bytes_with_escape(r: bytearray) -> str:
	"""
	Turns bytes into a string, with some special quirks. Reversible opposite of encode_string_with_escape().
	In VMDs the text fields are truncated to a set # of bytes, so it's possible that they might be cut off
	mid multibyte char, and therefore be undecodeable. Instead of losing this data, I decode what I can and
	the truncated char is converted to UNPACKER_ESCAPE_CHAR followed by hex digits that represent the remaining
	byte. It's not useful to humans, but it is better than simply losing the data.
	TODO: get example?
	All cases I tested require at most 1 escape char, but just to be safe it recursively calls as much as needed.
	
	:param r: bytearray object which represents a string through encoding UNPACKER_ENCODING
	:return: decoded string, possibly ending with escape char and hex digits
	"""
	global _UNPACKER_FAILED_TRANSLATE_FLAG
	if len(r) == 0:
		# this is needed to prevent infinite recursion if something goes really really wrong
		return ""
	try:
		s = r.decode(_UNPACKER_ENCODING)				# try to decode the whole string
		return s
	except UnicodeDecodeError:
		_UNPACKER_FAILED_TRANSLATE_FLAG = True
		s = decode_bytes_with_escape(r[:-1])		# if it cant, decode everything but the last byte
		extra = r[-1]  								# this is the last byte that couldn't be decoded
		s = "%s%s%x" % (s, _UNPACKER_ESCAPE_CHAR, extra)
		return s


def encode_string_with_escape(a: str) -> bytearray:
	"""
	Turns a string into bytes, with some special quirks. Reversible opposite of decode_string_with_escape().
	In VMDs the text fields are truncated to a set # of bytes, so it's possible that they might be cut off
	mid multibyte char, and therefore be undecodeable. Instead of losing this data, I decode what I can and
	the truncated char is converted to UNPACKER_ESCAPE_CHAR followed by hex digits that represent the remaining
	byte. It's not useful to humans, but it is better than simply losing the data.
	TODO: get example?
	All cases I tested require at most 1 escape char, but just to be safe it recursively calls as much as needed.
	
	:param a: string that might contain my custom escape sequence
	:return: bytearray after encoding
	"""
	if len(a) == 0:
		# this is needed to prevent infinite recursion if something goes really really wrong
		return bytearray()
	try:
		if len(a) > 3:									# is it long enough to maybe contain an escape char?
			if a[-3] == _UNPACKER_ESCAPE_CHAR:			# check if 3rd from end is an escape char
				n = encode_string_with_escape(a[0:-3])	# convert str before escape from str to bytearray
				n += bytearray.fromhex(a[-2:])			# convert hex after escape char to single byte and append
				return n
		return bytearray(a, _UNPACKER_ENCODING)			# no escape char: convert from str to bytearray the standard way
	except UnicodeEncodeError:
		# if the decode fails, I hope it is because the input string contains a fullwidth tilde, that's the only error i know how to handle
		# NOTE: there are probably other things that can fail that I just dont know about yet
		new_a = a.replace(u"\uFF5E", u"\u301c")			# replace "fullwidth tilde" with "wave dash", same as MMD does
		try:
			return bytearray(new_a, _UNPACKER_ENCODING)	# no escape char: convert from str to bytearray the standard way
		except UnicodeEncodeError as e:
			# overwrite the 'reason' field with the original string it was trying to encode
			e.reason = a
			# then return it to be handled outside
			raise e

def my_pack(fmt:str, args_in: Any) -> bytearray:
	"""
	Wrapper around the "struct.pack()" function. Not able to pack string objects!
	Converts the given inputs to bytearray format according to the data sizes/types specified in the format string.
	The number of arguments in 'args_in' must exactly match the number of things specified by the format string.
	This always adds byte-alignment specifier "<" to the format string.
	This accepts list-of-inputs or single input arg.
	
	:param fmt: string-type format for python "struct" lib
	:param args_in: list of variables to pack, or a single variable not inside a list
	:return: bytearray representation of these args
	"""
	try:
		afmt = "<" + fmt
		if isinstance(args_in, (list, tuple)):
			# if input args are a list, then flatten the list in the args to struct.pack
			b = struct.pack(afmt, *args_in)  # now do the actual packing
		else:
			# otherwise, don't bother to listify and then delistify, just directly give it to struct.pack
			b = struct.pack(afmt, args_in)  # now do the actual packing
	except Exception as e:
		core.MY_PRINT_FUNC("error in my_pack(fmt, args_in)")
		core.MY_PRINT_FUNC("fmt=", fmt, "args_in=", args_in)
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		raise
	return bytearray(b)


def my_string_pack(S: str, L=None) -> bytearray:
	"""
	Packer function exclusively for packing strings.
	Uses the encoding that was last set with a "set_encoding()" function call.
	If L is given, it is the integer number of bytes that should be in the resulting bytearray. If the string would
	encode to fewer bytes, it is zero-padded. If the string would encode to more bytes, it is truncated.
	If L is *not* given, the string is encoded with an "auto-length" scheme, i.e. encoded as an integer which holds
	the length of the string's byte representation, followed by the byte representation.
	All VMD strings are manual-length, and all PMX strings are auto-length.
	
	:param S: the string to pack
	:param L: optional integer length, number of bytes in the resulting bytearray
	:return: bytearray representation of this string
	"""
	try:
		n = encode_string_with_escape(S)  # convert str to bytearray
		
		if L is None:
			# this mode exclusively used for PMX parsing
			# auto-length str: convert to bytearray, measure len, pack an int with that value before packing the string with exactly that length
			fmt = "i" + str(len(n)) + "s"
			b = my_pack(fmt, (len(n), n))  # now do the actual packing
		else:
			# this mode exclusively used for VMD parsing
			# manual-length str: if a number is provided, then just pack that number of bytes
			fmt = str(L) + "s"       # simply replace trailing t with s
			b = my_pack(fmt, n)  # now do the actual packing
	except Exception as e:
		core.MY_PRINT_FUNC("error in my_string_pack(S,L)")
		core.MY_PRINT_FUNC("S=", S, "L=", L)
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		raise
	
	return bytearray(b)


def my_unpack(fmt:str, data:bytearray) -> Any:
	"""
	Wrapper around the "struct.unpack_from()" function. Not able to unpack string objects!
	Parses the bytearray object into some number of friendly Python objects (ints, floats, bools, etc) according to
	the data sizes/types specified in the format string.
	If exactly 1 variable would be unpacked, it is automatically de-listed and returned naked.
	This also removes any NaN or INF values it finds and replaces them with real numbers instead.
	Uses global var UNPACKER_READFROM_BYTE to know where to start unpacking next (internally tracked, reset by
	"reset_unpack()" function).
	
	:param fmt: string-type format for python "struct" lib
	:param data: bytearray being walked & unpacked
	:return: one variable or a list of variables, depending on the contents of the format string
	"""
	global UNPACKER_READFROM_BYTE

	try:
		afmt = "<" + fmt
		r = struct.unpack_from(afmt, data, UNPACKER_READFROM_BYTE)
		UNPACKER_READFROM_BYTE += struct.calcsize(afmt)	# increment the global read-from tracker
	except Exception as e:
		core.MY_PRINT_FUNC("error in my_unpack(fmt, data)")
		core.MY_PRINT_FUNC("fmt=",fmt,"data=","really big!","bytepos=", UNPACKER_READFROM_BYTE)
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		raise
	# r is guaranteed to be a tuple... convert from tuple to list so i can always return list objects
	retme = list(r)
	# new: check for NaN and replace with 0
	for i in range(len(retme)):
		foo = retme[i]
		if isinstance(foo, float):
			if math.isnan(foo):
				retme[i] = 0.0
				core.MY_PRINT_FUNC("Warning: found NaN in place of float shortly before bytepos %d, replaced with 0.0" % UNPACKER_READFROM_BYTE)
			if math.isinf(foo):
				if foo > 0: retme[i] =  999999.0
				else:       retme[i] = -999999.0
				core.MY_PRINT_FUNC("Warning: found INF in place of float shortly before bytepos %d, replaced with +/- 999999.0" % UNPACKER_READFROM_BYTE)
	# retme is guaranteed to be a list
	# if it is only a single item, de-listify it here
	if len(retme) == 1: return retme[0]
	else:               return retme


def my_string_unpack(data: bytearray, L=None) -> str:
	"""
	Unpacker function exclusively for unpacking strings.
	Uses the encoding that was last set with a "set_encoding()" function call.
	If L is given, it is the integer number of bytes that should read from the bytearray and interpreted as a string.
	The string might possibly end in the middle of a multi-byte character and be undecodeable; see
	"decode_bytes_with_escape()" for more info.
	If L is *not* given, the string is decoded with an "auto-length" scheme, i.e. read an integer from the bytearray,
	and use that integer's value as the number of bytes to read and interpret as a string.
	All VMD strings are manual-length, and all PMX strings are auto-length.

	:param data: bytearray being walked & unpacked
	:param L: optional integer length, number of bytes in the resulting bytearray
	:return: decoded string
	"""
	global _UNPACKER_FAILED_TRANSLATE_FLAG

	try:
		if L is None:
			# this mode exclusively used for PMX parsing
			# auto-length str: a text type is an int followed by that many bytes
			i = my_unpack("i", data)     # get an int that contains the length of the following string
			strfmt = str(i) + "s"            # build fmt string that includes # of bytes to read
			b = my_unpack(strfmt, data)  # unpack the actual string(bytearray)
		
		else:
			# this mode exclusively used for VMD parsing
			# manual-length str: if a number is provided, then just read that number of bytes
			strfmt = str(L) + "s"            # build fmt string that includes # of bytes to read
			b = my_unpack(strfmt, data)  # unpack the actual string(bytearray)
			
			# manual-text strings are null-terminated: everything after a null byte is invalid garbage to be discarded
			terminator_idx = b.find(b'\x00')  # look for a null terminator
			if terminator_idx != -1:          # if null is found...
				b = b[0:terminator_idx]       # ...preserve only the bytes before it, not including it
				
		# b is now a bytearray that should be mappable onto a string, unless it is cut off mid-multibyte-char
		s = decode_bytes_with_escape(b)
	except Exception as e:
		core.MY_PRINT_FUNC("error in my_string_unpack(data,L)")
		core.MY_PRINT_FUNC("data=","really big!","L=",L)
		core.MY_PRINT_FUNC(e.__class__.__name__, e)
		raise
	# translated string is now in s (maybe with the escape char tacked on)
	# did it need escaping? add it to the dict for reporting later!
	if _UNPACKER_FAILED_TRANSLATE_FLAG:
		_UNPACKER_FAILED_TRANSLATE_FLAG = False
		_UNPACKER_FAILED_TRANSLATE_DICT[s] += 1
	return s


