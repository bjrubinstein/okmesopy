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
    affiliation: 2
affiliations:
 - name: Illinois Institute of Technology, Department of Civil, Architectural, and Environmental Engineering
 - orcid: 0000-0002-1880-2330
 - equal-contrib: true
   index: 1
 - name: Oklahoma State University, School of Civil and Environmental Engineering
   index: 2
date: 23 August 2022
bibliography: paper.bib
---

# Summary
The Oklahoma Mesonet (Mesonet) is a environmental monitoring network operated by the University of Oklahoma, Oklahoma State University, and the Oklahoma Climatological Survey. It consists of 120 monitoring stations that collect and send environmental data to a central database every 5 minutes. The climate stations measure air temperature, barometric pressure, humidity, wind speed, wind direction, precipitation, solar radiation, and soil temperature [@McPherson:2007]. `OKMesoPy` is a Python package that seeks to make accessing and working with this dataset easier for researchers.

# Statement of need
Data files from the Mesonet website are available as either the complete dataset for a single station on a single day or a all variables for all active stations at a single point in time, however climate research often requires data from multiple stations over time periods of months or years. `OKMesoPy` automates the process of downloading data over a specified time period and collating it into a single Pandas DataFrame. Users can provide a bounding box or shapefile and `OKMesoPy` download data for the stations within that geographic area.

A number of Mesonet variables are collected on a longer time interval than 5 minutes and are missing data on the off intervals. Additionally data may be missing due to failing Mesonet's rigorous QA process, stations failing to report, or calibration issues [@McPherson:2007]. `OKMesoPy` provides methods for characterizing and handling missing data. It makes use of the Missingno library to visualize missing data [@Bilogur:2018]. `OKMesoPy` provides methods for simply replacing error codes with NaN, imputing missing values with simply linear interpolation, and copying missing data from the nearest reporting station.

`OKMesoPy` was originally written with the intention of creating time series for use in PyHSPF models and it provides methods for extracting PyHSPF formatted time series from the downloaded data [Lampert:2015]. However, `OKMesoPy` is generic enough to assist with any kind of research using the Mesonet dataset.

# References
