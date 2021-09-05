from distutils.core import setup
import DataServer
setup(name='ASM-DataServer',
      version=DataServer.__version__,
      description="Aye-Aye Sleep Monitoring Data Server",
      author="UC San Diego Engineers for Exploration",
      author_email="e4e@eng.ucsd.edu",
      packages=['DataServer'],
      scripts=['runServer.py'],
      install_requires=[
          'PyYAML',
          'asm_protocol'
      ]
      )
