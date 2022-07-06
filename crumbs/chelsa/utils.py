"""
Module declaring utility functions for downloading CHELSA datasets.
"""

import glob
import os
import re
from optparse import OptionParser
from os import walk
from os.path import exists
from pathlib import Path
from typing import Dict, List, Set, Tuple

import fiona
import rasterio
import requests
from osgeo import gdal
from rasterio import mask as msk
from shapely.geometry import Point, Polygon, shape
from tqdm import tqdm


def tryfloat(s):
    try:
        return float(s)
    except:
        return s


def alphanum_key(s):
    """
    Turn a string into a list of string and number chunks. "z23a" -> ["z", 23, "a"].
    Useful for sorting filenames nicely.
    """
    return [tryfloat(c) for c in re.split(r"_(-*\d+)_", s)]


def sort_nicely(l):
    """
    Sort the given list in the way that humans expect.
    """
    l.sort(key=alphanum_key)
    return l


def implemented_variables():
    """
    Defines the list of bioclimatic variables accessible from crumbs
    """
    return ["dem", "glz", *["bio" + str(i).zfill(2) for i in range(1, 19, 1)]]


def retrieve_variable_names_from(urls):
    """
    Identify the name of the bioclimatic variables from the download urls
    """
    matched = []
    for variable in implemented_variables():
        if any(variable in s for s in urls):
            matched.append(variable)
    return matched


def bounds_to_polygon(shapefile, margin):
    """
    Computes a bounding box around points in the shapefile, adding a margin.
    Returns a spatial polygon.
    """
    import fiona
    import numpy as np

    with fiona.open(shapefile) as file:
        shapes = list(file)
        coords = [p["geometry"]["coordinates"] for p in shapes]
        bot_left_x, bot_left_y, top_right_x, top_right_y = bounding_box_naive(coords)
        bbox = to_polygon(bot_left_x, bot_left_y, top_right_x, top_right_y, margin)
        return bbox


def bounding_box_naive(points):
    """
    Returns a list containing the bottom left and the top right points in the sequence.
    Here, we use min and max four times over the collection of points.
    """
    bot_left_x = min(point[0] for point in points)
    bot_left_y = min(point[1] for point in points)
    top_right_x = max(point[0] for point in points)
    top_right_y = max(point[1] for point in points)

    return bot_left_x, bot_left_y, top_right_x, top_right_y


def to_polygon(long0, lat0, long1, lat1, margin=0.0):
    """
    Convert the given points into a polygon, adding a margin.
    """
    return Polygon(
        [
            [long0 - margin, lat0 - margin],
            [long1 + margin, lat0 - margin],
            [long1 + margin, lat1 + margin],
            [long0 - margin, lat1 + margin],
        ]
    )


def clip(inputFile: Path, shape, outputFile: Path) -> None:
    """
    Clip the input file by the shape given, saving the output file.
    """
    import numpy as np

    with rasterio.open(inputFile) as source:
        out_image, out_transform = msk.mask(source, [shape], crop=True)
        out_meta = source.meta
        # update metadata
        out_meta.update(
            {
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform,
            }
        )

        #  The meta property of a dataset is a copy of some of its important metadata.
        # Modifying that object has no effect on the dataset.
        with rasterio.open(outputFile, "w", **out_meta) as dest:
            dest.write(out_image)
            # Avoids warnings in pyimpute: "Setting nodata to -999; specify nodata explicitly"
            if source.nodata is None:
                dest.nodata = np.nan
            else:
                dest.nodata = source.nodata

    return None


def resume_download(fileurl, resume_byte_pos):
    """
    Resume the download of the file given its url
    """
    resume_header = {"Range": "bytes=%d-" % resume_byte_pos}
    return requests.get(
        fileurl, headers=resume_header, stream=True, verify=True, allow_redirects=True
    )


def expand_bio(variables: List[str]) -> List[str]:
    bioset = set(variables) - set(["dem", "glz"])

    if len(bioset) > 0:
        if bioset == set(["bio"]):
            bioset = set(["bio" + str(i).zfill(2) for i in range(1, 19, 1)])

    return list(bioset.union(set(variables)) - set(["bio"]))


def generate_urls(variables: List[str], timesID: List[int]) -> List[str]:
    """Generate the expected CHELSA TraCE21k urls given the variables and the time IDS to retrieve."""
    assert len(variables) > 0, "Unable to generate URL fom an empty variables list"
    assert len(timesID) > 0, "Unable to generate URL from an empty timesID list"

    urls = []
    implemented = implemented_variables()

    if set(variables).issubset(set(implemented)) or set(variables) - set(
        ["dem", "glz"]
    ) == set(["bio"]):

        if set(["dem"]).issubset(set(variables)):
            for timeID in timesID:
                url = (
                    "https://os.zhdk.cloud.switch.ch/envicloud/chelsa/chelsa_V1/chelsa_trace/orog/CHELSA_TraCE21k_dem_"
                    + str(timeID)
                    + "_V1.0.tif"
                )
                urls.append(url)

        if set(["glz"]).issubset(set(variables)):
            for timeID in timesID:
                url = (
                    "https://os.zhdk.cloud.switch.ch/envicloud/chelsa/chelsa_V1/chelsa_trace/orog/CHELSA_TraCE21k_glz_"
                    + str(timeID)
                    + "_V1.0.tif"
                )
                urls.append(url)

        bioset = set(variables) - set(["dem", "glz"])
        if len(bioset) > 0:
            if bioset == set(["bio"]):
                bioset = set(["bio" + str(i).zfill(2) for i in range(1, 19, 1)])
            for bio in bioset:
                for timeID in timesID:
                    url = (
                        "https://os.zhdk.cloud.switch.ch/envicloud/chelsa/chelsa_V1/chelsa_trace/bio/CHELSA_TraCE21k_"
                        + bio
                        + "_"
                        + str(timeID)
                        + "_V1.0.tif"
                    )
                    urls.append(url)

    else:
        not_implemented = set(variables) - set(variables).intersection(set(implemented))
        raise ValueError(
            " ".join([str(i) for i in not_implemented])
            + " not implemented. Implemented CHELSA variables are: "
            + " ".join([str(i) for i in implemented])
        )

    # Post condition: at least one workable URL
    assert len(urls) > 0, "Unable to generate URL."

    return urls


def to_vrt(inputFiles: List[str], outputFile: str) -> str:
    """
    Converts the list of input files into an output VRT file, that can be converted to geoTiff
    """

    print("    ... Converting bands to VRT file:", outputFile)

    gdal.BuildVRT(
        outputFile,
        inputFiles,
        # callback=gdal.TermProgress_nocb,
        separate=True,
    )

    vrt_options = gdal.BuildVRTOptions(
        separate=True,
        # callback=gdal.TermProgress_nocb,
        resampleAlg="average",
    )

    my_vrt = gdal.BuildVRT(outputFile, inputFiles, options=vrt_options)

    # free C resource ...
    my_vrt = None

    return outputFile


def to_geotiff(vrt: str, outputFile: str) -> str:
    """
    Converts the VRT files to a geotiff file
    """
    assert vrt is not None
    print("    ... Converting", vrt, "to GeoTiff file:", outputFile)
    ds = gdal.Open(str(vrt))
    ds = gdal.Translate(str(outputFile), ds)
    # free C resource
    ds = None
    return outputFile


def read_urls(inputFile: Path) -> List[str]:
    """
    Read the URLs in the Chelsa input file
    """
    with open(inputFile, "r") as input:
        urls = input.readlines()
        return [url.strip() for url in urls]


def get_filename(url):
    """
    Split the url into a list, starting from the right and get last element
    """
    filename = url.rsplit("/", 1)[-1].strip()
    return filename
