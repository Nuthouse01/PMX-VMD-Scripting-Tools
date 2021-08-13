from PIL import Image
import tkinter.filedialog as fdg
import mmd_scripting.core.nuthouse01_core as core

_SCRIPT_VERSION = "Script version:  Nuthouse01 - v1.07.04 - 8/12/2021"
"""
Delete the transparency information of an image. i.e. make all parts of the image be opaque.
"""


USE_GRAPHICAL_FILE_DIALOGUE = True


def main():
	print("delete_alpha_layer")
	if USE_GRAPHICAL_FILE_DIALOGUE:
		filepath = fdg.askopenfilename(initialdir=".",
									  title="Select image file",)
	else:
		filepath = input("enter path to image file:")
	print("reading")
	im = Image.open(filepath)
	
	print("format =", im.format)
	print("mode =", im.mode)
	
	# convert from RGBA to RGB
	im_new = im.convert('RGB')
	
	output_path = core.filepath_insert_suffix(filepath, "_noalpha")
	im_new.save(output_path)
	
	print("done!")
	return None

if __name__ == "__main__":
	print(_SCRIPT_VERSION)
	main()

