import os

import mmd_scripting.core.nhio as nhio

# find the persistent json
persist_path = nhio._get_persistent_storage_path("persist.txt")
# delete it
try:
	os.remove(persist_path)
except FileNotFoundError:
	pass
