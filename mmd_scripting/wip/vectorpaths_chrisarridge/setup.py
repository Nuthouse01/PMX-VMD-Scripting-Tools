import setuptools

setuptools.setup(
	name = 'vectorpaths',
	version = '0.2',
	package_dir = {'': 'source'},
	packages = ['vectorpaths'],
	author = 'Chris Arridge',
	description = 'Vector path fitting and plotting',
	install_requires = ['numpy', 'matplotlib']
)
