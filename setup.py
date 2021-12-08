from setuptools import setup

__title__ = 'dramatiq_livemonitor'
__version__ = '0.1'
__author__ = 'Artem Sovetnikov'

setup(name=__title__,
      version=__version__,
      description='Dramatiq tasks and workers monitor with API',
      url='',
      author=__author__,
      author_email='asovetnikov@gmail.com',
      packages=[__title__, ],
      platforms=['Any',],
      entry_points={},
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
      ],
      include_package_data=True,
      install_requires=[]
      )
