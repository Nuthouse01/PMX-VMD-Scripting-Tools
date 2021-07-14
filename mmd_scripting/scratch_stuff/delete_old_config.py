
import mmd_scripting.core.nuthouse01_core as core
import os
# find the persistent json
persist_path = core._get_persistent_storage_path("persist.txt")
# delete it
try:
	os.remove(persist_path)
except FileNotFoundError:
	pass
