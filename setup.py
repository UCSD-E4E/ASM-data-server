'''ASM Data Server Setup file
'''
from setuptools import setup, find_packages

import DataServer

setup(
	name='ASM-DataServer',
	version=DataServer.__version__,
	description="Aye-Aye Sleep Monitoring Data Server",
	author="UC San Diego Engineers for Exploration",
	author_email="e4e@eng.ucsd.edu",
	packages=find_packages(),
	entry_points={
		'console_scripts': [
			'runServer = DataServer.runServer:main'
		]
	},
	install_requires=[
		'PyYAML',
		'asm_protocol @ git+https://github.com/UCSD-E4E/ASM_protocol.git',
		'appdirs',
		'pytest'],
	extras_require={
		'dev': [
			'pytest',
			'coverage',
			'pylint',
			'wheel',
		]
	},
)
