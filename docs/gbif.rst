Accessing the GBIF database with Quetzal-CRUMBS
=====================================================

The `Global Biodiversity Information Facility <https://www.gbif.org/>`_ is an international network
and data infrastructure that provides open access to around 2 billions of occurrence
records.

Why do we need to access GBIF ?
-------------------------------

The first step in IDDC modeling is to reconstruct a dynamic suitability map to inform every
generation (or year, or century) of the simulation of a meta-population.
This suitability map can be derived from a Species Distribution Model
(aka an Environmental Niche Model).

There are many models available out there, and in CRUMBS we use a model averaging over 4 classifiers:

* Random Forest (RF)
* Extra-Tree (ET)
* Extreme Gradient Boosting (XGB)
* Light Gradient Boosted Machine (LGBM)

These classifiers use spatial predictors (bioclimatic variables from CHELSA) and the following features:
* presence points (*retrieved from the Global Biodiversity Information Facility*)
* pseudo-absence points (*generated from the presence points and the CHELSA Digital Elevation Model*).

Why a scripted approach?
------------------------

To integrate GBIF occurrence records in an IDDC workflow, you need to:

1. download the observational data
2. restrict them to your area of interest (a bounding box around your genetic sample +/- an offset in km)
3. remove the duplicated obsevations
4. download the CHELSA-TraCE21k Digital Elevation Model for the present century
5. filter out the data points that fall in the ocean cells
6. export the remaining points as a shapefile

You could do that manually, but for reproducible science it's nice to have these
steps configured in a script and executed programmatically: this is in essence
what the ``crumbs-get-gbif`` utility does.

Usage
-------
