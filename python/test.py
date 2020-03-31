
''' tk_scrolledtext101.py
explore Tkinter's ScrolledText widget
inside the edit_space use
ctrl+c to copy, ctrl+x to cut selected text,
ctrl+v to paste, and ctrl+a to select all
uses the same methods as the Text() widget
'''
try:
	# for Python2
	import Tkinter as tk
	import ScrolledText as tkst
except ImportError:
	# for Python3
	import tkinter as tk
	import tkinter.scrolledtext as tkst
import tkinter.filedialog as fdg

root = tk.Tk()
root.title("ScrolledText")
frame = tk.Frame(root, bg='brown')
frame.pack(fill='both', expand='yes')
edit_space = tkst.ScrolledText(
	master = frame,
	wrap   = 'word',  # wrap text at full words only
	width  = 25,      # characters
	height = 10,      # text lines
	bg='beige'        # background color of edit area
)
# the padx/pady space will form a frame
edit_space.pack(fill='both', expand=True, padx=8, pady=8)
mytext = '''\
Man who drive like hell, bound to get there.
Man who run in front of car, get tired.
Man who run behind car, get exhausted. 全ての親
The Internet: where men are men, women are men, and children are FBI agents.
'''
edit_space.insert('insert', mytext)
root.mainloop()
# optiona info
# help(tkst.ScrolledText)


d = fdg.askopenfilename(initialdir=".", filetypes=(("PMX files", "*.pmx"),))
print(d)
