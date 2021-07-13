import io
import os
import re
import time

import requests
from PIL import Image

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v0.6.01 - 7/12/2021"
# This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause.
#####################

def getFilename_fromCd(r):
	"""
	Get filename from content-disposition. Doesn't always work tho.
	"""
	cd = r.headers.get('content-disposition')
	if not cd:
		return None
	fname = re.findall('filename=(.+)', cd)
	if len(fname) == 0:
		return None
	return fname[0]

def is_downloadable(url):
	"""
	Is the url live? Does the url contain a downloadable resource?
	"""
	print("testing", url)
	try:
		h = requests.head(url, allow_redirects=True, timeout=10)
		header = h.headers
		content_type = header.get('content-type')
		if 'text' in content_type.lower():
			return False
		if 'html' in content_type.lower():
			return False
		return True
	except Exception as eee:
		print(eee.__class__.__name__, eee)
		return False


def main():
	print("enter URL of first page to download:")
	print("replace page number with a number of pound-signs that equals the zero-pad width")
	print("1 -> #, 01 -> ##, 001 -> ###, 0001 -> ####")
	input_url = input("> ")
	
	# create "my_url_template" from the input
	match_obj = re.search('#+', input_url, )
	if match_obj is not None:
		L = len(match_obj.group())
		my_url_template = input_url.replace(match_obj.group(), "{:0%dd}" % L)
		single = False
	else:
		my_url_template = input_url
		single = True
	
	# create a new folder to hold the results of this download
	# append numbers until i find an unused folder name
	base_foldername = "newfolder"
	foldername = base_foldername
	for i in range(2, 1000):
		if not os.path.exists(foldername): break
		else:                              foldername = base_foldername + str(i)
	os.mkdir(foldername)
	print("folder = %s" % foldername)
	
	# get image format from image = Image.open(io.BytesIO(r.content))
	# get name-to-save-as from URL, maybe, or from CD thing, maybe? idk
	# VERY IMPORTANT: must add 5-sec delay between stuff cuz most servers dont like it when i download all their
	# stuff, they detect a downloader because the downloader is very fast, once the downloader is going at slow
	# human-ish speeds then its indistinguishable!
	i = 1
	while is_downloadable(my_url_template.format(i)):
		print("pass")
		time.sleep(5)
		try:
			# do the acutal download
			r = requests.get(my_url_template.format(i), allow_redirects=True, timeout=20)
		except Exception as eee:
			print(eee.__class__.__name__, eee)
			break
		
		print("content-type = %s" % str(r.headers.get('content-type')))
		print("content-disposition = %s" % str(r.headers.get('content-disposition')))
		# shove it into PIL and figure out what format it is, just cuz
		image = Image.open(io.BytesIO(r.content))
		ext = image.format.lower()
		print("format = %s, size = %s" % (str(ext), str(image.size)))
		
		# decide what name to save it as
		# filename1 = getFilename_fromCd(r)
		# filename2 = os.path.split(my_url_template.format(i))[1]
		filename3 = "{:03d}.{}".format(i, ext)
		# if filename1 is not None:
		# 	filename = filename1
		# elif filename2 != "" and "." in filename2:
		# 	filename = filename2
		filename = filename3
		print(filename)
		# filename = getFilename_fromCd(r)
		writeme = open(os.path.join(foldername, filename), 'wb')
		writeme.write(r.content)
		i += 1
		time.sleep(5)
		if single:
			break
	print("downloaded %d images" % (i-1))
	print("done!")
	

if __name__ == '__main__':
	main()
