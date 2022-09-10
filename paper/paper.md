---
title: 'OKMesoPy: A Python package for working with the Oklahoma Mesonet climate dataset'
tags:
  - Python
  - Oklahoma Mesonet
  - climatology
  - meteorology
  - hydrology
authors:
  - name: Benjamin J. Rubinstein
    orcid: 0000-0001-5852-2555
    equal-contrib: true
    affiliation: 1
  - name: Abhiram S.P. Pamula
  - orcid: 0000-0002-1880-2330
    equal-contrib: true
    affiliation: 2
  - name: David J. Lampert
    orcid: 0000-0001-7357-1873
    affiliation: 1 
affiliations:
 - name: Illinois Institute of Technology, Department of Civil, Architectural, and Environmental Engineering
   index: 1
 - name: Oklahoma State University, School of Civil and Environmental Engineering
   index: 2
date: 09 September 2022
bibliography: paper.bib
---

# Summary
The Oklahoma Mesonet (Mesonet) is a environmental monitoring network operated by the University of Oklahoma, Oklahoma State University, and the Oklahoma Climatological Survey. It consists of 120 monitoring stations that collect and send environmental data to a central database every 5 minutes. Each of Oklahoma's 77 counties are covered by at least one Mesonet station. The climate stations measure air temperature, barometric pressure, humidity, wind speed, wind direction, precipitation, solar radiation, and soil temperature [@McPherson:2007]. `OKMesoPy` is a Python package that seeks to make accessing and working with this dataset easier for researchers.

# Statement of need
Data files from the Mesonet website are available as either the complete dataset for a single station on a single day or a all variables for all active stations at a single point in time, however climate research often requires data from multiple stations over time periods of months or years. `OKMesoPy` automates the process of downloading data over a specified time period and collating it into a single Pandas DataFrame. Users can provide a bounding box or shapefile and `OKMesoPy` download data for the stations within that geographic area. Mesonet data is provided in UTC time and `OKMesoPy` can automate conversion into local Oklahoma time.

A number of Mesonet variables are collected on a longer time interval than 5 minutes and are missing data on the off intervals. Additionally data may be missing due to failing Mesonet's rigorous QA process, stations failing to report, or calibration issues [@McPherson:2007]. `OKMesoPy` provides methods for characterizing and handling missing data. It makes use of the `Missingno` library to visualize missing data [@Bilogur:2018]. `OKMesoPy` provides methods for simply replacing error codes with NaN, imputing missing values with simple linear interpolation, and copying missing data from the nearest reporting station.

# Target audience
`OKMesoPy` was originally written with the intention of creating time series for use in `PyHSPF` models and it provides methods for extracting PyHSPF formatted time series from the downloaded data [@Lampert:2015]. However, `OKMesoPy` is generic enough to assist with any kind of research using the Mesonet dataset. Weather data from Mesonet can be converted to climate data products based on mathematical operations. `OKMesoPy` allows climatologists to automate raw data acquisition and integrate it into existing Python code.

Another use case is performing geospatial analysis of environmental variables. When working with sets of stations `OKMesoPy` can do simple areal averaging using the arithmetic mean which can be adequate for a number of use cases [@Singh:1975]. When more complex methods are required being able to easily generate data grouped by bounding boxes or shapefiles and having access to station location data makes it easy to implement other methods such as Thiessen polygons or the reciprocal distance squared method.

Mesonet data can also be used by municipalities to make decisions for town planning, water management, energy needs, extreme weather events, and maintaining civil infrastructure. Farmers can use climate data from Mesonet to grow different crops while efficiently managing water. For all these use cases, `OKMesoPy` can help ease the data acquisition process.

# Acknowledgements
This study is based upon the work supported by U.S. Department of the Interior, Geological Survey under Grant #2021OK006G. The authors would like to thank the taxpayers of the state of Oklahoma for providing continuous financial support to the Oklahoma mesonet network.

# References
