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
date: 25 September 2022
bibliography: paper.bib
---

# Summary
The Oklahoma Mesonet (Mesonet) is an environmental monitoring network operated by the University of Oklahoma, Oklahoma State University, and the Oklahoma Climatological Survey. It consists of 120 monitoring stations that collect and send in-situ environmental data to a central database every 5 minutes. Each of Oklahoma's 77 counties are covered by at least one Mesonet station. The climate stations measure air temperature, barometric pressure, humidity, wind speed, wind direction, precipitation, solar radiation, and soil temperature. `OKMesoPy` is a Python package that seeks to make accessing and working with this dataset easier for researchers.

# Statement of need
Data files from the Mesonet website are available as either a complete dataset for a single station on a single day or a set of all variables for all active stations at a single point in time through a web interface. However, climate research often requires specific data from multiple stations over time periods of months or years. `OKMesoPy` automates the process of downloading data over a specified time period, collating it into a single Pandas DataFrame, and extracting time series for specific variables from that data. Users can provide a bounding box or shapefile and `OKMesoPy` will download data for the stations within that geographic area. Mesonet data are recorded in UTC time. `OKMesoPy` returns DataFrames with timezone aware timestamps, simplifying conversion to local Oklahoma time.

Several Mesonet variables are collected on a longer time interval than 5 minutes that results in missing data between observations. Additional data may be missing when the observations fail Mesonet's rigorous QA process, stations fail to report measurements, or calibration issues occur [@Brock:1995] [@McPherson:2007]. `OKMesoPy` provides a method for characterizing missing data and uses the `Missingno` library for visualization [@Bilogur:2018]. `OKMesoPy` provides methods for simply replacing error codes with NaN, imputing missing values with simple linear interpolation, and copying missing data from the nearest reporting station.

Similar software exists for several other climate databases including `MesoPy` for the MesoWest database [@MesoWest:2017] and `PyHSPF` for the GSOD, GHCND, NCDC hourly precipication, NHDPlus, and NSRDB databases [@Lampert:2015] [@Lampert:2018]. No such software exists for the Oklahoma Mesonet and `OKMesoPy` aims to fill this gap.

# Target audience
`OKMesoPy` was originally written with the intention of creating time series for use in hydrologic models with `PyHSPF`, and it provides methods for generating `PyHSPF` formatted time series [@Lampert:2015] [@Lampert:2018]. However, `OKMesoPy` is generic enough to assist with any kind of data-intensive research using the Mesonet database. Weather data from Mesonet can be converted to climate data products based on mathematical operations. `OKMesoPy` allows climatologists to automate raw data acquisition and integrate it into existing Python code or save it to a CSV file for use outside of Python.

Another use case is performing geospatial analysis of environmental variables. When working with sets of stations, `OKMesoPy` can do simple areal averaging using the arithmetic mean, which can be adequate for a number of use cases [@Singh:1975]. When more complex methods are required, being able to easily generate data grouped by bounding boxes or shapefiles and having access to station's location makes it easy to implement other averaging methods such as Thiessen polygons or the reciprocal distance squared method [@Chow:1988].

Mesonet data can also be used by municipalities to make decisions for town planning, water management, energy needs, extreme weather events, and maintaining civil infrastructure. Farmers can use climate data from Mesonet to grow different crops while efficiently managing water. For all these use cases, `OKMesoPy` can help ease the data acquisition process.

# Example usage

`OKMesoPy` contains an example Jupyter notebook that illustrates sample code for every function in the module. The features of `OKMesoPy` are demonstrated using sample code. The examples below use make use of the 10 days of data from the "Acme" station from the first example in the Jupyter notebook.

With a single line of code, `OKMesoPy` generates a table showing the number of each kind of error in each column of the dataset shown in \autoref{tab:error}, as well as a graphical representation of the missing data using the `Missingno` library shown in \autoref{fig:missingno} [@Bilogur:2018].

\begin{table}[!h]
    \centering
    \begin{tabular}{|l|c|c|c|c|c|c|c|c}
    \hline
        & -994 & -995 & -996 & -997 & -998 & -999 & TOTAL \\
        \hline
        RELH & 0.0 & 0.0 & 0.0 & 0.0 & 0.0 & 0.0 & 0.0 \\
        TAIR & 0.0 & 0.0 & 0.0 & 0.0 & 0.0 & 0.0 & 0.0 \\
        WSPD & 0.0 & 0.0 & 0.0 & 0.0 & 0.0 & 534.0 & 534.0 \\
        WVEC & 0.0 & 0.0 & 0.0 & 0.0 & 0.0 & 534.0 & 534.0 \\
        WDIR & 0.0 & 0.0 & 0.0 & 0.0 & 0.0 & 534.0 & 534.0 \\
        WDSD & 0.0 & 0.0 & 0.0 & 0.0 & 0.0 & 534.0 & 534.0 \\
        WSSD & 0.0 & 0.0 & 0.0 & 0.0 & 0.0 & 534.0 & 534.0 \\
        WMAX & 0.0 & 0.0 & 0.0 & 0.0 & 0.0 & 534.0 & 534.0 \\
    \hline
    \end{tabular}
    \caption{Truncated error summary table.}
    \label{tab:error}
\end{table}

\begin{figure}[h!]\centering
  {\includegraphics[width=\textwidth]{errorsummary.png}}
  \caption{Missingno matrix.}
  \label{fig:missingno}
\end{figure}

\autoref{fig:missingno} shows that there is a period of missing wind speed data with -999 error codes. The -999 code is used for data that fails quality control checks [@McPherson:2007]. `OKMesoPy` can impute this data using linear interpolation or copy it from the nearest neighboring station. \autoref{fig:windspeed} shows a comparison of both methods.

\begin{figure}[h!]\centering
  {\includegraphics[width=\textwidth]{imputeddata.png}}
  \caption{Comparison of OKMesoPy imputation methods.}
  \label{fig:windspeed}
\end{figure}

Finally, the data can be exported as a time series or CSV for use in other research.

# Acknowledgements
This study is based upon the work supported by U.S. Department of the Interior, Geological Survey under Grant #2021OK006G. The authors would like to thank the taxpayers of the State of Oklahoma for providing continuous financial support to the Oklahoma Mesonet network.

# References
