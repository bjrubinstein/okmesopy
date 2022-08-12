from setuptools import setup

setup(name='okmesopy',
      version='0.7.0',
      description='Tools to download and manipulate data from OK Mesonet',
      url='https://github.com/bjrubinstein/okmesopy',
      author='Ben Rubinstein',
      author_email='brubinst@hawk.iit.edu',
      license='GNU',
      packages=['okmesopy'],
      install_requires=['numpy',
                        'pandas',
                        'pyshp',
                        'pyproj',
                        'geopy',
                        ],
      keywords=['Mesonet','climatology','meteorology','hydrology'],
      zip_safe=False)
