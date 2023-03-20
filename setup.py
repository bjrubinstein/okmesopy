from setuptools import setup

setup(name='okmesopy',
      version='1.1.1',
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
                        'missingno',
                        ],
      keywords=['Mesonet','climatology','meteorology','hydrology'],
      zip_safe=False)
