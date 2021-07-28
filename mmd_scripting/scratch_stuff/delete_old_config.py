import os

import mmd_scripting.core.nuthouse01_io as io

# find the persistent json
persist_path = io._get_persistent_storage_path(io.MY_JSON_NAME)
# delete it
try:
	os.remove(persist_path)
except FileNotFoundError:
	pass
