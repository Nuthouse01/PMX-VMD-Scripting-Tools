# PMX-VMD-Scripting-Tools

PMX/VMD Scripting Tools README  
Created by Nuthouse01 - v1.07.02 - 7/13/2021

If you appreciate my work, consider sending me a [donation via Paypal](https://paypal.me/nuthouse01)!  
If you would like to contact me (questions or feedback), my email domain is yahoo.com and my username is brian.henson1 (screw those bots)  
If you want to contribute a script or bugfix you've made, please make a Git Pull Request that merges onto the "develop" branch. Any pull requests onto "master" branch will be rejected.

###### Legal:
This code is free to use and re-distribute, but I cannot be held responsible for damages that it may or may not cause. You are permitted to examine and modify the code as you see fit, but I make no guarantees about the safety or quality of the result.  
I take no responsibility for how you use this code: any damages, or copyright violations or other illegal activity are completely the fault of the user. These tools only gives you "the ability to read/edit", what you do with that ability is not my business and not my fault.  
You are free to use this for any commercial or non-commercial applications.  
Don't try to claim this work as yours. That would be a profoundly dick move.

###### Installation:
Click the green button above, select "Download ZIP", save it, and unzip it somewhere.  
If you want to run the EXE version, that's it! You're ready to go! If you want, you can delete everything except for the EXE.  
If you want to run the PY version or modify the code:  
1. [Install Python](https://www.google.com/search?q=how+to+install+python) version 3.6 or higher.
2. Double-click "_RUN_THIS_TO_INSTALL.bat" to download "googletrans" and to locally install the "mmd_scripting" package you just downloaded.
   1. This will create a folder "mmd_scripting.egg-info", don't delete it, just ignore it.

###### Usage:
1. Just double-click "graphic_user_interface.exe" or "graphic_user_interface.py"
    1. If you get a popup saying "Windows protected your PC", you can click "More Info" and then "Run Anyway". This does not mean that it detected a virus (that is a different popup), this happens whenever you run an EXE from an unknown publisher, like me.
2. Use the dropdown menu at the top to select which script you want to run. You can press the "Help" button to print out a detailed explanation of what the currently selected script does, how it does it, and what output files it creates.
3. Click the large "RUN" button to the left to execute the selected script. This will begin by prompting you for input file(s), and will then run to completion. Outputs and info will be printed in the large space at the bottom of the window.
    1. If the "print extra info" checkbox is checked when the "RUN" button is clicked, more detailed info will be printed as the script runs.
4. Read all information that is printed to the screen (such as whether it succeeded or failed), then leave the window open. You can click "RUN" again to run the same script (it will prompt you again for input file(s)) or you can switch to a different script with the dropdown menu and run something else instead. You can click "Clear" to clear the printout space if it gets too messy.
5. Enjoy!

![Screenshot of console](https://raw.githubusercontent.com/Nuthouse01/PMX-VMD-Scripting-Tools/master/img/screenshot1.png)

### Descriptions:
I've got more than 20 different runnable scripts in this package, but here are some of the most useful ones:
##### model_overall_cleanup.py
This will perform a series of first-pass cleanup operations to generally improve any PMX model. This includes: translating missing english names (via Google Translate!), correcting alphamorphs, normalizing vertex weights, pruning invalid faces & orphan vertices, removing bones that serve no purpose, pruning imperceptible vertex morphs, cleaning up display frames, and detecting issues that might cause MMD to crash. These operations will reduce file size (sometimes massively!) and improve overall model health & usability.

##### file_sort_textures.py
This script is for organizing the texture imports used in a PMX model, to eliminate "top-level" clutter and sort Tex/Toon/SPH files into folders based on how they are used. This script will also report any files it finds that are not used by the PMX, and it will also report any files the PMX tries to reference which do not exist in the file system.

##### file_translate_filenames.py
This is for translating JP names of files to English. Unlike the "file_sort_textures" script, this will attempt to rename ALL files within the tree, it will not restrict itself to only certain filetypes.

##### check_model_compatability.py
This script is to check if the model you are using is compatible with the VMD/VPD you wish to use. This will display a summary that lists all the bones/morphs in the VMD/VPD file that are not supported by the model. If you are loading a motion designed for some different model (usually the case), and it seems to be playing wrong, it is very likely that there is a name mismatch.

(For example, if a model's eye-smile morph is named "笑い" and the motion uses "笑顔" for eye-smile, that morph will not be applied to the model and it will look wrong when played.)

This script will reveal what exactly is mismatched; but to fix the issue, you must either change the PMX to match the VMD/VPD (using PMXEditor or a similar tool) or you must change the VMD/VPD to match the PMX (use script "vmd_rename_bones_morphs" to do find-and-replace within the VMD!).

##### bone_make_semistandard_auto_armtwist.py
This will generate "automatic armtwist rigging" that will fix pinching at shoulders/elbows.  
**This only works on models that already have semistandard armtwist/腕捩 and wristtwist/手捩 bone rigs.** Install the "Semi-Standard Bone Plugin" in PMXE to create these bones if they do not exist.  
It creates a clever IK bone setup that hijacks the semistandard bones and moves them as needed to reach whatever pose you make with the arm/腕 or elbow/ひじ bones. You do not need to manually move the armtwist bones at all, you can animate all 3 axes of rotation on the arm bone and the twisting axis will be automatically extracted and transferred to the armtwist bone as needed!

##### morph_hide.py
This script simply sets the specified morphs within a model to group "0" so they do not show up in the eye/lip/brow/other menus. This is handy for components of group morphs that you don't want to be used independently.

##### morph_invert.py
This will "invert" a vertex or UV morph by permanently applying it to the model's mesh, then reversing the values inside that morph.

##### morph_scale.py
This will scale the strength/magnitude of a vertex, UV, or bone morph by a specified factor such as 2.9 or 0.75.

##### convert_vmd_to_txt.py
This tool is for converting VMD (Vocaloid Motion Data) files from their packed binary form to a human-readable and human-editable text form, and vice versa. This can allow 3rd-party scripts to perform procedural edits on the VMD data while it is in text format, such as (for example) constraining certain bones to a desired max range of motion, and then converting it back to VMD form for use in MikuMikuDance. Or it can be used to modify the names of the bones/morphs that the VMD is trying to control, to customize it to work better with a specific model.

##### convert_vpd_to_vmd.py
This script will convert VPD (Vocaloid Pose Data) files to or from VMD (Vocaloid Motion Data) files. The motion files will be only a single frame long, with all bones/morphs framed at time=0.

### Notes:
Note: if you want to run the Python version rather than the EXE version, you will need have Python 3.6 or higher and need to install the "googletrans" library (pip install googletrans). This is the only non-standard library used in my codebase.

Note: the EXE file is so much larger than all the Python scripts because it was bundled with PyInstaller, and contains an entire portable Python installation. Technically, when it runs it unpacks & installs Python to a temporary location, executes all of my Python scripts, and when the window is closed it deletes that temporary location.

Note: Bones and morphs are stored in the VMD format by their JAPANESE NAME. It is not possible to get any english name info from the VMD.

Note: The following data can be controlled by keyframes and stored within an MMD project, but cannot be stored in or restored by a VMD file:
* gravity data
* outside parent settings
* accessory data

Note: "morph" is a synonym for "facial"

Note: If using an English-translated version of MikuMikuDance, you will not be able to directly see the Japanese names of bones/morphs in your model. To see the Japanese names, either use PMXEditor or use the script "pmx_list_bone_morph_names.py" to create files that link each JP name with its corresponding EN name.

Note: if you want to examine/modify VPD (Vocaloid Pose Data) files, they are already stored as plain-text. Right-click the file and attempt to open it with whatever text editor you prefer.

Note: the VMD structure allocates a specific number of bytes to hold the name of each bone/morph, but sometimes these names are too long to be stored and get truncated down to that maximum size. Also, sometimes it takes 2 bytes to represent a single kanji: if the truncate point is in the middle of a kanji, it loses the 2nd byte and I cannot decode that kanji for printing or displaying. To prevent data loss, I use an escape character "‡" with two hex digits to represent the final dangling byte while it is in string form. (If you don't understand anything I just said then don't worry about it.)

### VMD text-file structure:

This is formatted in CSV (comma-separated value) format. You can theoretically change the file extension from .txt to .csv and open it with Microsoft Excel or whatever, but Excel isn't capable of properly displaying the Japanese characters so that isn't recommended.

The text file is encoded with "utf-8" scheme, and should be displayable by any text editor.

Bone-rotation angles are converted from quaternion format and outputted as euler or "real" angles in degrees, the same values that are displayed in MMD. Camera-rotation angles have no limits and are shown in degrees.

<details>
  <summary>Click to expand!</summary>

```
:file start:
version:, <versionnum>
modelname:, <modelname>
boneframe_ct:, <#>
    if the count is nonzero, then there will be a keystring here which labels the fields.
    then there will be a line for each boneframe.
morphframe_ct:, <#>
    if the count is nonzero, then there will be a keystring here which labels the fields.
    then there will be a line for each morphframe.
camframe_ct:, <#>
    if the count is nonzero, then there will be a keystring here which labels the fields.
    then there will be a line for each camframe.
lightframe_ct:, <#>
    if the count is nonzero, then there will be a keystring here which labels the fields.
    then there will be a line for each lightframe.
shadowframe_ct:, <#>
    if the count is nonzero, then there will be a keystring here which labels the fields.
    then there will be a line for each shadowframe.
ik/dispframe_ct:, <#>
    if the count is nonzero, then there will be a keystring here which labels the fields.
    then there will be a line for each ik/dispframe.
:file end:
```
</details>

### VMD binary structure:

This is only included because I don't have permissions to update the MikuMikuDance Fandom page with all the info I discovered. It would be a shame if it just vanished forever, so I'll post it here.

The binary file is encoded with "shift_jis" scheme.

Some really old motions that don't contain camframe/lightframe/shadowframe/ikdispframe may just end the bitstream early rather than specifying that there are 0 of each of these frame types. This early-end is supported but will cause warnings to be printed.

<details>
  <summary>Click to expand!</summary>

```
:file start:
30b char-string, header signature: either "Vocaloid Motion Data file" if old MMD or "Vocaloid Motion Data 0002" if new MMD
10b (if old MMD) OR 20b (if new MMD) char-string, model name
4b unsigned int, number of bone keyframes
for each keyframe:
    15b char-string, name of the bone
    4b unsigned int, frame number
    4b float, x-coordinate position
    4b float, y-coordinate position
    4b float, z-coordinate position
    4b float, x-coordinate rotation (quaternion)
    4b float, y-coordinate rotation (quaternion)
    4b float, z-coordinate rotation (quaternion)
    4b float, w-coordinate rotation (quaternion)
    64b, interpolation curve data
    *    actually 16 1-byte ints, range 0-127, 4 for each of the 4 layers
    *    point A is bottom-left, point B is top-right, 0,0 is bottom-left corner
    *    order is (ax for each layer) (ay for each layer) (bx for each layer) (by for each layer)
    *    the remaining 48 bytes are just copies shifted left 1/2/3 bytes, uses shift without wrap, meaning it loses the ax data and shifts in garbage
    *    !!!! EXCEPT that for some reason ax for z-layer and rot-layer (3rd and 4th bytes) are overwritten on the 1st line, so they need to be read from the 2nd line
    *    !!!! these bytes are (usually) overwritten with the physics indicator! if 99/15 = disable physics, if 0/0 or if they match ax_z & ax_r = don't disable, other values are unknown
4b unsigned int, number of facial/morph keyframes
for each keyframe:
    15b char-string, name of the facial/morph
    4b unsigned int, frame number
    4b float, value/weight
4b unsigned int, number of camera keyframes
for each keyframe:
    4b unsigned int, frame number
    4b float, dist from target to camera
    4b float, x-coordinate target position
    4b float, y-coordinate target position
    4b float, z-coordinate target position
    4b float, x-coordinate rotation (radians)
    4b float, y-coordinate rotation (radians)
    4b float, z-coordinate rotation (radians)
    24b, interpolation curve data
    *    actually 24 1-byte ints, range 0-127, 4 for each of the 6 layers
    *    (ax, bx, ay, by) then repeat for each layer. yes i know this is grouped differently than the bone interpolation data, i dont understand either
    *    point A is bottom-left, point B is top-right, 0,0 is bottom-left corner
    4b unsigned int, camera FOV angle
    1b bool, perspective on/off
4b unsigned int, =#lightframes
for each lightframe:
    4b unsigned int, =frame#
    4b float, = red value, stored as a float [0.0-1.0) to represent 0-255
    4b float, = green value, stored as a float [0.0-1.0) to represent 0-255
    4b float, = blue value, stored as a float [0.0-1.0) to represent 0-255
    4b float, = x-position
    4b float, = y-position
    4b float, = z-position
4b unsigned int, =#shadowframes
for each shadowframe:
    4b unsigned int, =frame#
    1b unsigned int, = mode (0=off, 1=mode1, 2=mode2)
    4b float, = shadow range value, stored as 0.0 to 0.1 and also range-inverted: [0,9999] -> [0.1, 0.0]
4b unsigned int, =#ikframes
for each ikdisp frame:
    4b unsigned int, =frame#
    1b boolean, =display, on=1/off=0
    4b unsigned int, =#ofikbones
    for each ikbone:
        20b char-string, = bone name
        1b boolean, = ik on=1/off=0
:file end:
```
</details>

Note: When doing conversion from txt->VMD, I append a signature string "Nuthouse01" to prove that this file was created by my conversion tool.
This does not affect MikuMikuDance, MikuMikuMoving, PMXE, or MMDTools (Blender plugin) from successfully reading the motion.

Technically, the VMD binary file structure allows having both model data (bones, morphs, ikdisp) and cam data (cam, light, shadow) in the same file at the same time. However, MikuMikuDance will ignore model data and read only the cam data if the modelname is exactly "カメラ・照明" (TL: Camera / Lighting), and will ignore cam data and read only the model data if the modelname is anything else.

###### Thanks:
Massive thanks and credit to "Isometric" for helping me discover the quaternion transformation method used by MMD!!!! The script wouldn't be completable without him :)

Thank you to whoever made [this VMD documentation page](https://mikumikudance.fandom.com/wiki/VMD_file_format), their documentation is incomplete but their work is the only reason I was able to even begin this project!

Also thanks to [FelixJones on Github](https://gist.github.com/felixjones/f8a06bd48f9da9a4539f) for already exploring & documenting the PMX file structure!

Big thanks to "Quappa-El" for inventing the automatic armtwist bone structure that my "bone_auto_armtwist" script copies. Once I had a working example in front of me, it took only 2 days to put together the script that lets me apply it onto any model.

Thanks to the people who made PyInstaller for making a super easy way to build an .exe from a bunch of Python scripts, its a really neat tool you should check it out. The EXE files are so large because it contains the entire Python kernel + all needed libraries for that script. "pyinstaller --onefile --noconsole whatever.py"

###### Files:
The following files should be included with this README:
* img/screenshot1.png
* mmd_scripting/core/*.py
* mmd_scripting/kaitai/*.py
* mmd_scripting/overall_cleanup/*.py
* mmd_scripting/scratch_stuff/*.py
* mmd_scripting/scripts_for_gui/*.py
* mmd_scripting/scripts_not_for_gui/*.py
* mmd_scripting/wip/*.py
* .gitignore
* _RUN_THIS_TO_INSTALL.bat
* graphic_user_interface.exe
* graphic_user_interface.py
* LICENSE
* README.md
* README.txt
* README_command_line_support.txt
* setup.cfg
* setup.py
* todo_list.txt

#### Changelog:
<details>
  <summary>Click to expand!</summary>

```
v1.07.02:
several minor changes to reduce the "boilerplate" code, no functional changes
   new func "RUN_WITH_TRACEBACK" to simplify direct-run code
   new func "filepath_insert_suffix" for creating output file name
   tweak how core files are imported
split the file I/O functions into a separate file, nuthouse01_io.py
add proper traceback display to GUI
improve exceptions in validation, file I/O
change "get_unused_filename" numbering template (very minor change)
file write will check for & remove "read-only" status from wherever it wants to write

v1.07.01:
"morph invert" script now supports material morphs & group morphs
NEW: minor improvements in the GUI!
    GUI will automatically find/load all scripts within "scripts_for_gui" folder, so if you write your own & stick it in there it will just work
    GUI will select the "last used script" when launched
    file input dialogue remembers different locations for each filetype
add "_SCRIPT_TEMPLATE"

v1.07.00:
overhaul the structure and imports to make it more like a proper package
bugfix in the new "bone_set_arm_localaxis" script
other than that, it should be functionally identical!

v6.01:
add todo_list.txt, you can track what i'm planning to do next!
NEW: add 'bone_set_arm_localaxis.py' to quickly set the localaxis params of arm bones
NEW: add 'vmd_rename_bones_morphs.py' for simple find-and-replace names within VMD
NEW: add "image set downloader" in handy tools
NEW: "bone auto armtwist" FIX HANDTWIST PINCHING WOOOOOO
NEW: add "bone sdef twist hand adapter" that will fix handtwist pinching on SDEF-autotwist models
overhaul "make ik from vmd" to make it more object-based and more readable
bugfixes in "reweight blender fragments", remove fancy optimizations
change persistent storage method to use one json-formatted file

v6.00:
BIG: overhaul several parts of my PMX/VMD classes to make things more intuitive and more readable
   overhaul how vertex weights are stored, now all weight types use same structure of [index,value] pairs
   overhaul how rigidbody nocollide groups are stored, now it's a set object containing ints
   overhaul material flags to use proper "flags" object and not a list-of-bools
   overhaul several fields to use "enum" objects, replace "magic numbers" with named constants
      vertex WeightMode, material SphMode, MorphPanel, MorphType, RigidBodyShape, RigidBodyPhysMode, JointType, VMD shadow frame ShadowMode
   remove stupid system where each texture is referred to by index, now each material just includes the filepath for tex/toon/sph
create "validate()" member function to rigorously enforce type/structure requirements before writing to file
new: if a float NaN value is found while reading PMX/VMD, replace it with a 0
change how each script stores its version number

v5.08:
new: list_all_pmx_with_missing_tex.py
new: reweight_blender_fragments.py
new: WIP_vmd_animation_smoothing.py
add kaitai struct definition file, just as a curiosity, don't really plan to use it
add base class for all morph items
bugfix: fix crash when material morph is broken 
bugfix: fix prettyprint to support negative filesizes
bugfix? remove the "rotate all faces" behavior, decided it was a bad idea after all
new: if vert weight is extremely near zero, eliminate it
new: check absolute filepath & model name for non-shift-jis symbols

v5.07:
minor update to make file_recompress_images more stable and have better error messages

v5.06:
NEW: "file_recompress_images.py" for converting TGA or DDS crap into nicely compressed PNG to save disk space
removed image-type detection stuff from file_sort_textures and put it into file_recompress_images
added README explaining how command-line support (doesn't) work
added README explaining how "handy_tools" stuff works
bugfix: change how translate grabs prefix/suffix, so it stops eating leading or trailing minus symbols

v5.05:
bugfix: fix file_sort_textures breaking when texture names end in whitespace
add more stuff to "handy_tools"

v5.04:
bugfix: fix a thing in file_sort_textures that needs to always be in sorted order
recompile EXE with updated version of googletrans (4.0.0-rc1)
"file_sort_textures" now can also verify image format matches image extension (if PIL is installed)(this is optional)
add more stuff to "handy_tools"

v5.03:
bugfix: in "bone auto armtwist", fixed bones hanging off of armtwist# bones not having deform level updated
bugfix: in "dispframe fix", fixed bug that would crash if root group is or becomes empty
"check model compatability" now also check bones for trans/rot support
"prune unused bones" now added "edge adjust" bone to list of exceptions

v5.02:
NEW: "bone_auto_armtwist.py" for creating rigging to automatically control existing armtwist bones

v5.01:
NEW: "translate_source_bone.py" for translating SFM names to MMD names
    added by "khanghugo"
bugfix: converted all angles in PMX structs to always use degrees, not radians
add 3 more useful scripts to "handy tools"

v5.00:
more words, always more words, so many words, words words words words
add new PMX structs so everything uses named fields & becomes more readable
    all scripts updated to use new PMX class
    probably introduced a few bugs with this, i'll find them eventually
increase required version to 3.6 so i can use variable type annotation
rename "pmx overall cleanup" -> "model overall cleanup"
rename "pmx armik addremove" -> "bone armik addremove"
rename "model compatability check" -> "check model compatability"
NEW: "model_shift" script to replace the buggy & broken PMXE plugin
NEW: "model_scale" script because why not
NEW: "bone_endpoint_addremove" to toggle between bonelink and offset modes
add new folder "handy tools", this will contain scripts and script fragments that come in handy for various tasks.
    these will not be documented or incorporated into the GUI because they are too specific or too minor,
    or require CSV files (from PMXE) as their inputs. use them only after inspecting them and learning what they do!
bugfix: printout bug in translate_to_english when PREFER_EXISTING_ENGLISH_NAME = False
bugfix: fix symmetry issue in add/remove arm IK script
bugfix: finally made "remove unused verts" script properly support softbodies
add half-katakana to full-katakana piecewise translation dict
    (no plans to actually use it however)
moved vmd structs to separate file because the pmx structs are in a separate file

v4.63:
tweak printouts in a couple places
more commenting & typechecking stuff
translation: force translation when english names are just "en" or "D"
translation: tighten criteria for "good" english names to highlight any funny unicode symbols and junk
    this means more names will be marked as "untranslateable" since google doesn't know how to deal with the symbols either
pmx cleanup: fix false warnings in jointless rigidbody detection
display frame cleanup: will now make "center" group follow semistandard conventions

v4.62:
bugfix: fixed incorrect behavior in new bezier code
replace VMD list-of-lists structure with simple custom classes, now things are accessed via named fields instead of indexes
    probably introduced a few bugs with this, i'll find them eventually
made "specify morph" popups more intelligent in morph_hide, morph_invert, morph_scale scripts
even more type-checking stuff

v4.61:
bugfix: in "model_compatability_check", catch errors due to bad chars in names instead of crashing outright
loads of documentation & type-checking to make stuff more maintainable & readable

v4.60:
rename "vmd_convert_tool" to "convert_vmd_to_txt"
rename "vmd_model_compatability_check" to "model_compatability_check"
NEW: "convert_vpd_to_vmd", lets you convert between pose and motion file
update model_compatability_check to allow comparing against VPD pose files as well as VMDs
extra safety net for file_translate_names, remove characters that are forbidden in windows file paths
change how translate_to_english handles stuff that Google was unable to translate
tweak binary pack/unpack functions for greater cleanliness & efficiency
more comments & documentation

v4.50:
rename "texture_file_sort" to "file_sort_textures"
NEW! "file_translate_names" halfway between "translate-to-english" and "file-sort-textures"
restructure file_sort_textures for better functionalization and overall cleanliness/clarity
massive overhaul structure of translate_to_english for better functionalization and overall cleanliness/clarity
    use regular expressions to handle common grammar stuff like L/R/parent/end prefix/suffix, indents, padding, etc
    new stage to look for exact matches in special dicts before trying to do piecewise local translation with general dict
    new approach to google translation: identify translateable islands/chunks and only translate those, assuming they will be used many times
        this should reduce google traffic in extreme cases and guarantee consistient translations
    force "words dict" to be sorted by size to prevent future "undershadowing" problems
    add new struct for holding the translation data as I am running, for better organization than just a list-of-lists
    fewer printouts when using "moreinfo": skip the exact-match and copy-JP entries cuz they're uninteresting
restructure "weight_cleanup" slightly, now compresses weight vect to lowest possible version
added WIP scripts "pmx_magic_armtwist" and "bone_merge_helpers", they're not ready yet please don't use them :) i just needed them out of the way
added smart gui-wise justifying to make things line up more nicely

v4.08:
bugfix: "delete duplicate faces" was conflating faces with opposite vertex order, now fixed
bugfix: bonedeform now handles bones with invalid partial inherit, though this should never be needed in a good model
re-order stages in pmx_overall_cleanup and improved printing
overhaul identify_unused_bones with new recursive strategy, cleaner & easier to understand & gives better results
more accurate progress estimate when reading PMX/VMD

v4.07:
bugfix: alphamorph feature "fix edging on default hidden materials" forgot to check that add-morphs were modifying the relevant material, oops
bugfix: armtwist, model compat, others were failing file-write when file path contained spaces, oops
add better err checking to separate "file doesn't exist" from other kinds of errors
translation shows error message if googletrans is not installed
tex file sort will ask for what unused files it should move

v4.06:
new: morph_hide
new: morph_invert
new: morph_scale
modified "prune invalid faces" to also detect & remove duplicate faces within material units
more words in translation dictionary
disable translation of model comments since the model info popup in MMD can display JP characters just fine
slight changes to printouts in most scripts

4.05:
bone deform check: bugfixes, better IK understanding
more translation words
warn about bone/morph names that can't be stored in SHIFT-JIS
prune unused bones: actually check that IK bones are used instead of just assuming
refine boneless rigidbody checks & warnings
automatically fix edging on default hidden materials with "show" morphs
weight cleanup: also normalize normals, including 0,0,0 "invalid" normals

4.04:
bugfix: weight_cleanup was incorrectly counting the number of changes it made (was actually operating correctly tho)
new: pmx_overall_cleanup finds "shadowy materials" i.e. hidden materials with visible edging
new: pmx_overall_cleanup finds physics bodies that aren't constrained by any joints
new: pmx_overall_cleanup fixes bone deform order issues, or causes a warning if it finds a circular relationship

4.03:
bugfix: did imports wrong oops
new script: "pmx_arm_ik_addremove" for adding arm IK rigs

4.02:
bugfix: texture_file_sort wasn't overwriting the original files as I had intended
limit # of longbones/longmorphs/noboneRBs that can be printed by pmx_overall_cleanup to 20
texture_file_sort: if all the files in a folder are unused, display that folder name with *** instead of each individual file
changed progress_print_oneline approach
fixed imports to work whether imported or standalone
"more info" checkbox now controls whether VMD/PMX breakdown is shown or not

4.01:
learned that VMD does not handle long bone/morphs, changed model-compatability to only use exact match checking
moved "graphic_user_interface" up a level to make it more important

4.00:
add "texture_file_sort" script to organize file references within a PMX file
rebuilt GUI and combined all scripts into one package, The Perfect Unified GUI
removed "load" button, removed ability to load once and run multiple times
added "clear" button to GUI
bugfix PMX parser because online file spec was incorrect
MASSIVE upgrades to local translation ability
modify how # of unique bones/morphs is printed when parsing VMD
create more overrideable function pointers MY_FILEPROMPT_FUNC, MY_SIMPLECHOICE_FUNC just the same as MY_PRINT_FUNC

3.61:
added threading module to GUI to allow moving/resizing/scrolling while the script is running
added a few more name maps to the local translation file

v3.6:
various bugfixes and improvements to the "pmx overall cleanup" pipeline
added a GUI frontend that better displays JP chars and includes a file selection dialoge
made "morph winnow" just use hardcoded 0.0003 threshold instead of prompting
revised error reporting method across all scripts to rely more on raising/catching errors instead of "pause and quit" thing
from translate script, removed MyMemory provider and pretty-printing to reduce final executable size
from translate script, removed confirmation of translations to make gui integration cleaner
for all(?) scripts, made a "moreinfo" argument to control what used to be debug print statements

v3.51:
added prune_unused_bones, dispframe_fix, find_crashing_joints into the "pmx_overall_cleanup" pipeline

v3.5:
added "pmx_overall_cleanup.py" which runs through all scripts whose names start with underscores
    good for first-pass cleanup of models

v3.02:
added PMX WRITE ability
    various restructuring and improvment of my custom pack/unpack functions, now both use the same recursive approach
print statement changes: binary/text file read/write print full absolute file path, read/write pmx/vmd print only basename

v3.01:
"prompt_user_filename" now prints the full file path when given a non-existant file
added .exe versions of all 5 scripts, generated with PyInstaller

v3.00:
removed scripts for PMX editing, left only scripts for VMD manipulation and tools to help with that
massive refactoring of "vmd_convert_tool":
    move funcs for reading/writing binary files into core
    move funcs for unpacking structs into core
    move funcs for parsing/writing VMDs into new file "vmd_parser"
        further refactored these funcs for stronger encapsulation & readability
    massive refactoring of funcs for parsing/writing VMD-as-text for stronger encapsulation & readability
    end-user experience is unchanged except for print statement differences
slightly changed the "nicelist" format for internally representing a VMD
completely redid my binary unpacker function, changed to a recursive approach
    now supports symbol "t" to indicate actual strings (packer also changed to support this)
    now creates escape character(‡) & writes the actual byte when unable to translate the final byte of a string (packer also changed to support this)
    discovered some more quirks of encoding/decoding shift_jis, listed in core file
added new file "pmx_parser", thanks to FelixJones on Github for already exporing & documenting the PMX file structure!!!
    only for reading PMX files, no plans to make a writer. If you wanna modify a PMX use PMXE, not my scripts!
    uses core funcs for reading binary files
    uses core funcs for unpacking binary structs (same function as VMD parser)
updated "vmd_armtwist_convert" to use this new PMX parser, and to work with VMD parsing changes
    now able to infer axis of rotation on armtwist bones even if it doesn't have its axis locked
updated "vmd_compatability_check" to use this new PMX parser, and to work with VMD parsing changes
    also changed comparison method to handle new escape char strategy and bones/morphs >= 15 bytes
updated "make_ik_from_vmd" to use this new PMX parser, and to work with VMD parsing changes
improved handling of user input file names to account for odd corner cases
improved error handling when reading vmd-as-text files
change how "read_txt_to_rawlist" detects if a thing is an int, so it can support negative ints
add ability for "read_txt_to_rawlist" to parse None objects (but there shouldn't ever be any None objects in the file so w/e)
add new script "pmx_list_bone_morph_names.py" so EN users can discover the JP names of a model without using PMXE
decided to release this script under the name Nuthouse01, changed all uses accordingly

v2.09:
fixed a logical bug in "bone_endpoint_create_remove"
stopped using default, built custom csv writer to preserve leading spaces of things
bugfix in "vmd_convert_tool" to handle strings exactly 15 bytes long that end with a multibyte char
speculative bugfix to handle multibyte chars that get cut off by 15-byte limit (is that even possible?)

2.08:
fixed a bug in "identify_unused_bones" due to not actually testing my code
changed encoding from "shift_jisx0213" to "shift_jis" to properly handle backslashes, in core and in VMD
New scripts:
+bone_geometry_isolate
+vmd_armtwist_convert
+bone_endpoint_create_remove
+texture_file_sort
moved more functions into the 'core' file

2.07:
fixed a bug in "weight_cleanup" due to not actually testing my code

2.06:
created new script "vmd_model_compatability_check"
in "vmd_convert_tool", disabled the writing of bonedict/morphdict because vmd_model_compatability_check overshadows that feature

2.05:
moved some code to "nuthouse01_core"
decided to distribute all scripts as a bundle
added several simple scripts
enforced standard templating for all scripts

2.04:
vmd_convert_tool:
    quaternion transform fix
    bonedict/morphdict sorting
    added "choose from options" function
    added selftest

2.03:
vmd_convert_tool:
    better functionalization
    better support for old motions (early end)
    moved when the sorting happens
```
</details>

