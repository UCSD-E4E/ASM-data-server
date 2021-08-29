from distutils.core import setup
import DataServer
setup(name='ASM-DataServer',
      version=DataServer.__version__,
      description="Aye-Aye Sleep Monitoring Data Server",
      author="UC San Diego Engineers for Exploration",
      author_email="e4e@eng.ucsd.edu",
      packeages=['DataServer'],
      install_requires=[
          'PyYAML'
      ]
      )
