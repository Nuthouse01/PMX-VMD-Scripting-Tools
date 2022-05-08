@echo off

echo +++++++++++++++++++++++++++++++++++++++++++++++++++
echo First, ensure the "pip" tool is up to date.
echo +++++++++++++++++++++++++++++++++++++++++++++++++++
py -m pip install --upgrade pip

echo +++++++++++++++++++++++++++++++++++++++++++++++++++
echo Second, install the "googletrans" library, an API to let my code run text thru Google Translate service.
echo +++++++++++++++++++++++++++++++++++++++++++++++++++
py -m pip install googletrans==4.0.0-rc1

echo +++++++++++++++++++++++++++++++++++++++++++++++++++
echo Last, locally install the "mmd_scripting" package you just downloaded, necessary for the imports to properly work when running from several different entry points.
echo +++++++++++++++++++++++++++++++++++++++++++++++++++
py -m pip install -e .

echo +++++++++++++++++++++++++++++++++++++++++++++++++++
echo Last, ensure that any old config files are deleted
echo +++++++++++++++++++++++++++++++++++++++++++++++++++
py mmd_scripting/scratch_stuff/delete_old_config.py

echo +++++++++++++++++++++++++++++++++++++++++++++++++++
echo Done!
echo +++++++++++++++++++++++++++++++++++++++++++++++++++
pause
