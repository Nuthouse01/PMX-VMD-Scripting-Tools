import pathlib
import setuptools

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
# fails when it hits JP characters i think? idgaf
#README = (HERE / "README.md").read_text()

setuptools.setup(
	name="mmd_scripting",
	version="1.07.00",
	packages=["mmd_scripting"],
)
