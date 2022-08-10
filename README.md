# OKMesoPy

NOTE: data from the Oklahoma Mesonet is copyrighted by the Oklahoma Climatological Survey and the Oklahoma Mesonet. It is the responsibility of the user of this package to ensure they follow the Mesonet Data Access Policy: https://www.mesonet.org/index.php/site/about/data_access_and_pricing

OKMesoPy is a package to aid in downloading and manipulating the Oklahoma Mesonet climate dataset. This tool was written for creating time series for use in HSPF models but the dataset can have many uses.

**Core Dependencies:**
- NumPy
- Pandas
- PyShp
- PyProj
- GeoPy

**Additional Dependencies:**
- MatPlotLib is required to run the examples

**Installation:** OKMesoPy can be installed from Python Package Index (PyPI) using pip: "pip install okmesopy." Alternatively, it can be installed from source by cloning the repo and running "python setup.py install" as administrator.

**Usage:** Import the package into your code using "from okmesopy import MesonetDownloader, MesonetTools." The package is well documented in docstrings which can be read by running "help(okmesopy)" after it has been imported. The "examples.ipynb" notebook in the "examples" folder demonstrates how to use this package.

**Contributing:** We welcome all contributions. Bugs reports and feature requests can be made by opening an issue on Github. Bug fixes, new features, documentation updates, or additional Jupyter notebooks examples can be submitted by creating a pull request on Github.
