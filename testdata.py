# -*- coding: utf-8 -*-
"""
Module to prepare test data for benchmarking geo operations.
"""

import enum
import logging
from pathlib import Path
import pprint
import shutil
import tempfile
from typing import Optional
import urllib.request
import zipfile

import geofileops as gfo

################################################################################
# Some inits
################################################################################

logger = logging.getLogger(__name__)

################################################################################
# The real work
################################################################################


class TestFile(enum.Enum):
    AGRIPRC_2018 = (
        0,
        "https://downloadagiv.blob.core.windows.net/landbouwgebruikspercelen/2018/Landbouwgebruikspercelen_LV_2018_GewVLA_Shape.zip",
        ".zip",
        "agriprc_2018.gpkg",
    )
    AGRIPRC_2019 = (
        1,
        "https://downloadagiv.blob.core.windows.net/landbouwgebruikspercelen/2019/Landbouwgebruikspercelen_LV_2019_GewVLA_Shapefile.zip",
        ".zip",
        "agriprc_2019.gpkg",
    )
    S2_NDVI_2020 = (
        2,
        "https://www.landbouwvlaanderen.be/bestanden/gis/Droogte%202020%20Sentinel2_NDVI_Periodiek_31370_rgb.zip",
        ".zip",
        "s2_ndvi_2020.tif",
    )

    def __init__(self, value, download_url, download_suffix, dst_name):
        self._value_ = value
        self.download_url = download_url
        self.download_suffix = download_suffix
        self.dst_name = dst_name

    def get_file(self, tmp_dir: Path) -> Path:
        testfile_path = download_samplefile(
            download_url=self.download_url,
            download_suffix=self.download_suffix,
            dst_name=self.dst_name,
            dst_dir=tmp_dir,
        )

        if gfo.is_geofile(testfile_path):
            testfile_info = gfo.get_layerinfo(testfile_path)
            logger.debug(
                f"TestFile {self.name} contains {testfile_info.featurecount} rows."
            )

        return testfile_path


def download_samplefile(
    download_url: str,
    download_suffix: str,
    dst_name: str,
    dst_dir: Optional[Path] = None,
) -> Path:
    """
    Download a sample file to dest_path.

    If it is zipped, it will be unzipped. If needed, it will be converted to
    the file type as determined by the suffix of dst_name.

    Args:
        url (str): the url of the file to download.
        download_name (str): the file name to download to.
        dst_name (str): the file name to save final file to.
        dst_dir (Path): the dir to downloaded the sample file to.
            If it is None, a dir in the default tmp location will be
            used. Defaults to None.

    Returns:
        Path: the path to the downloaded sample file.
    """
    # If the destination path is a directory, use the default file name
    dst_path = prepare_dst_path(dst_name, dst_dir)
    # If the sample file already exists, return
    if dst_path.exists():
        return dst_path
    # Make sure the destination directory exists
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    # If the url points to a file with the same suffix as the dst_path,
    # just download
    if download_suffix.lower() == dst_path.suffix.lower():
        logger.info(f"Download to {dst_path}")
        urllib.request.urlretrieve(download_url, dst_path)
        return dst_path

    # The file downloaded is of a different type than the destination wanted, so some
    # unpacking and/or converting will be needed.
    tmp_dir = dst_path.parent / "tmp"
    try:
        # Remove tmp dir if it exists already
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True, exist_ok=True)

        # Download file
        tmp_path = tmp_dir / f"{dst_path.stem}{download_suffix.lower()}"
        logger.info(f"Download tmp data to {tmp_path}")
        urllib.request.urlretrieve(download_url, tmp_path)

        # If the temp file is a .zip file, unzip to dir
        if tmp_path.suffix == ".zip":
            # Unzip
            unzippedzip_dir = dst_path.parent / tmp_path.stem
            logger.info(f"Unzip to {unzippedzip_dir}")
            with zipfile.ZipFile(tmp_path, "r") as zip_ref:
                zip_ref.extractall(unzippedzip_dir)

            # Look for the file
            tmp_paths = []
            for suffix in [".shp", ".gpkg", ".tif"]:
                tmp_paths.extend(list(unzippedzip_dir.rglob(f"*{suffix}")))
            if len(tmp_paths) in [1, 2]:
                tmp_path = tmp_paths[0]
            else:
                raise Exception(
                    f"Should find 1 geofile, found {len(tmp_paths)}: \n"
                    f"{pprint.pformat(tmp_paths)}"
                )

        if str(dst_path) != str(tmp_path):
            if dst_path.suffix == tmp_path.suffix:
                if dst_path.suffix == ".tif":
                    shutil.move(tmp_path, dst_path)
                else:
                    gfo.move(tmp_path, dst_path)
            else:
                logger.info(f"Convert tmp file to {dst_path}")
                gfo.makevalid(tmp_path, dst_path)
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)

    return dst_path


def prepare_dst_path(dst_name: str, dst_dir: Optional[Path] = None):
    if dst_dir is None:
        return Path(tempfile.gettempdir()) / "geofileops_sampledata" / dst_name
    else:
        return dst_dir / dst_name
