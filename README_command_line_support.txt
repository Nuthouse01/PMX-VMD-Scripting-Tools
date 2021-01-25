====================
COMMAND-LINE SUPPORT
aka
BATCH FILE SUPPORT
====================

If you need to run these scripts on tens or hundreds of files, you may want to 
automate the process by using batch file scripts or other command-line-based 
automation. I do not plan to natively support this, mostly because I am lazy,
but also because many of the scripts require additional inputs/interaction/confirmation
beyond just one input file name. Some require a variable number of inputs depending
on what it encounters while processing. I don't want to figure out how to handle 
all that.

However, all of my scripts are open source and you are free to edit them as you
wish to use for your own purposes. Python is especially flexible and easy to tweak.
To modify a script to accept command-line arguments, use the following steps:

1. make a copy of the script you want to modify, and only modify the copy (because
these changes will make a script unable to be used with the GUI)
2. add the line "import sys" somewhere near the top of the file, if it is not
already present in the file
3. delete the two lines that have "core.pause_and_quit" near the bottom of the file
4. find all usages of "core.MY_SIMPLECHOICE_FUNC(...)", "core.MY_GENERAL_INPUT_FUNC(...)", 
and "core.MY_FILEPROMPT_FUNC(...)" throughout the file. These are the functions that 
pause script execution and wait for user input. They respectively return as an 
integer, a string, and an absolute filepath, and then store that value into some
kind of variable.
5. replace "core.MY_GENERAL_INPUT_FUNC(...)" and "core.MY_FILEPROMPT_FUNC(...)"
with "sys.argv[?]", and replace "core.MY_SIMPLECHOICE_FUNC(...)" with "int(sys.argv[?])",
where ? is the order of the argument on the command line. The first argument is 1.


Note: run with the syntax "python model_overall_cleanup.py thisistheinput". 
Don't forget the word "python" in there.
Note: if sys.argv[2] appears anywhere in the script, and the script is run with 0
or 1 arguments, the script will crash and raise an IndexError.




