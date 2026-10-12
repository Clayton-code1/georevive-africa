"""One connector per source. Order matters only for the terminal report."""

from __future__ import annotations

from .aster import AsterConnector
from .bgs_harare import BgsHarareMapConnector, BgsHarareReportConnector
from .cop_dem import CopDemConnector
from .geoboundaries import GeoBoundariesConnector
from .geochem import BgsZimGeochemConnector, EarthChemConnector, GeorocConnector
from .historical_scans import HathiTrustConnector, InternetArchiveConnector, ZgsBulletinsConnector
from .inbox import InboxConnector
from .osm import OsmConnector
from .regional_geology import OneGeologyConnector, RegionalGeologyConnector, UsgsGeo7Connector
from .sentinel2 import Sentinel2Connector
from .usgs_africa import UsgsAfricaMineralsConnector
from .usgs_mrds import UsgsMrdsConnector
from .worldcover import WorldCoverConnector

ALL_CONNECTORS = [
    BgsHarareReportConnector,
    BgsHarareMapConnector,
    UsgsMrdsConnector,
    UsgsAfricaMineralsConnector,
    Sentinel2Connector,
    CopDemConnector,
    WorldCoverConnector,
    AsterConnector,
    GeoBoundariesConnector,
    OsmConnector,
    RegionalGeologyConnector,
    UsgsGeo7Connector,
    OneGeologyConnector,
    InternetArchiveConnector,
    HathiTrustConnector,
    ZgsBulletinsConnector,
    EarthChemConnector,
    GeorocConnector,
    BgsZimGeochemConnector,
    InboxConnector,
]

BY_ID = {c.id: c for c in ALL_CONNECTORS}
