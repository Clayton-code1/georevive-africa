# GeoRevive Africa - Data Sources Report

_Generated automatically on 2026-10-12 05:41 UTC by `python -m georevive.ingest`. Do not edit by hand._

**Pilot area:** Harare 1:100 000 sheet (ZGS Bulletin 94) - provisional extent - bounding box (lon/lat) `[30.75, -18.05, 31.5, -17.55]`

Rules: only open or published data we are allowed to access; robots.txt, licences and rate limits are respected; nothing is invented. A failed source stays failed - no gap is filled with made-up records.

**Raw data is not redistributed.** The GeoRevive repository contains code, configuration, documentation and generated reports only. No downloaded dataset, derived data layer or scanned document is included. Each dataset stays under its publisher's licence (listed below). To reproduce the data, run `python -m georevive.ingest --all`, which downloads open data from the original publishers and records checksums so you can confirm you have the same files.

## Summary

**Downloaded:** 8 · **Failed:** 1 · **Needs credentials:** 2 · **Needs manual request:** 9

| Source | What was obtained | URL | Licence | Accessed (UTC) | Records / raster | Status |
|---|---|---|---|---|---|---|
| ASTER Global Emissivity Dataset (AG100 v003) / ASTER L1T | nothing | https://lpdaac.usgs.gov/products/ag100v003/ | NASA Earthdata: no restrictions on use, citation requested; requires free Earthdata login | 2026-10-10 20:22 | - | Needs credentials |
| BGS digital Harare 1:100k geological map (GeoPackage, ZGS Bulletin No. 94) | nothing | https://nora.nerc.ac.uk/id/eprint/541846/ | licence to confirm (not publicly released; terms to be agreed with BGS/ZGS) | 2026-10-10 20:14 | - | Needs manual request |
| BGS report OR/26/047 - Digitisation of the 1:100k geological map of Harare | nothing | https://nora.nerc.ac.uk/id/eprint/541846/ | NORA access policy: single copy for personal research/study, educational or not-for-profit use with full citation; no robot harvesting; no commercial sale. © UKRI | 2026-10-10 20:14 | - | Needs manual request |
| Zimbabwe Regional Geochemical Survey (1982-86) - BGS international geochemistry CD-ROM | nothing | https://www.bgs.ac.uk/geology-projects/applied-geochemistry/international-geochemistry-cd-rom/zimbabwe-regional-geochemical-survey/ | licence to confirm with BGS | 2026-10-10 20:39 | - | Needs manual request |
| Copernicus DEM GLO-30 (30 m digital surface model) | Elevation (m), Slope (degrees), Terrain roughness (TRI, m), Hillshade (base map) | https://copernicus-dem-30m.s3.amazonaws.com/readme.html | Copernicus DEM licence: free of charge, worldwide, for any lawful use, with attribution | 2026-10-10 20:41 | 2670 x 1872 px @ 30 m (1 band) | Downloaded |
| EarthChem Portal - rock geochemistry samples in the pilot area | nothing | https://www.earthchem.org/ | CC BY 4.0 for EarthChem Library data (per-dataset; licence to confirm per sample source) | 2026-10-10 20:39 | - | Failed |
| ESA WorldCover 2021 v200 (10 m land cover) | Land cover (ESA WorldCover 2021) | https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_S21E030_Map.tif | CC BY 4.0 | 2026-10-10 20:40 | 2670 x 1872 px @ 30 m (1 band) | Downloaded |
| geoBoundaries - Zimbabwe administrative boundaries (ADM0-ADM2) | Country boundary, Provinces, Districts | https://www.geoboundaries.org/api/current/gbOpen/ZWE/ADM2/ | Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO) | 2026-10-10 20:23 | 102 records | Downloaded |
| GEOROC - Geochemistry of Rocks of the Oceans and Continents | nothing | https://georoc.eu/ | CC BY-SA 4.0 for GEOROC compilations (licence to confirm) | 2026-10-10 20:39 | - | Needs credentials |
| HathiTrust Digital Library - Southern Rhodesia Geological Survey bulletins | nothing | https://catalog.hathitrust.org/Search/Home?lookfor=%22Southern%20Rhodesia%22%20%22Geological%20Survey%22&type=all | Per volume; full view only for public-domain volumes; automated bulk download not permitted | 2026-10-10 20:38 | - | Needs manual request |
| Historical geological publications on Internet Archive (public-domain items only) | 7 file(s) | https://archive.org/ | Per item: only items flagged public domain / not in copyright are downloaded (see details) | 2026-10-10 20:38 | 3 records; 1159 scanned pages | Downloaded |
| OneGeology Portal - geology web map services covering Zimbabwe | nothing | https://portal.onegeology.org/ | Per service (to confirm for any service found) | 2026-10-10 20:42 | - | Needs manual request |
| OpenStreetMap - roads, places, rivers and mapped mine features | Roads, Rivers and streams, Towns, villages and farms, Mapped quarries and mine shafts (OSM) | https://download.geofabrik.de/africa/zimbabwe-latest.osm.pbf | Open Database Licence (ODbL) 1.0 | 2026-10-10 22:06 | 4,382 records | Downloaded |
| Regional geology - CGMW-BRGM 1:10M Geological Map of Africa (via Macrostrat API) | Regional geology (1:10M, CGMW-BRGM) | https://macrostrat.org/api/v2/geologic_units/map | CC BY 4.0 as stated by the Macrostrat API; underlying CGMW-BRGM map - licence to confirm with CGMW | 2026-10-10 21:43 | 9 records | Downloaded |
| Copernicus Sentinel-2 Level-2A surface reflectance (dry season scene) | Iron-oxide index (Sentinel-2 B4/B2), Ferrous-iron index (B12/B8A + B3/B4), Clay / hydroxyl index (B11/B12), Vegetation (NDVI), Sentinel-2 true colour | https://earth-search.aws.element84.com/v1 | Copernicus Sentinel data terms: free, full and open access (attribution required) | 2026-10-10 22:06 | 1336 x 937 px @ 60 m (8 bands) | Downloaded |
| USGS Compilation of Geospatial Data for the Mineral Industries and Related Infrastructure of Africa | nothing | https://www.sciencebase.gov/catalog/item/607611a9d34e018b3201cbbf | Public domain (U.S. Government work); some layers compiled from third-party sources - check layer metadata | 2026-10-10 20:14 | - | Needs manual request |
| USGS Geology of Africa (geo7_2ag, Open-File Report 97-470A) | nothing | https://www.sciencebase.gov/catalog/item/60d0ff26d34e86b938aab404 | Public domain (USGS); coastline/boundaries contain ESRI proprietary data - licence to confirm | 2026-10-10 20:42 | - | Needs manual request |
| USGS Mineral Resources Data System (MRDS) - Zimbabwe | nothing | https://mrdata.usgs.gov/mrds/mrds-csv.zip | Public domain (U.S. Government work) | 2026-10-10 20:14 | - | Needs manual request |
| Zimbabwe Geological Survey Bulletin No. 94 and related short reports (paper) | nothing | https://www.bgs.ac.uk/ | © Zimbabwe Geological Survey - permission required | 2026-10-10 20:38 | - | Needs manual request |
| Manual inbox (data/inbox/) | nothing | data/inbox/ | Per file (entered on upload) | 2026-10-10 20:39 | 0 records | Downloaded |

## What failed and why

- **EarthChem Portal - rock geochemistry samples in the pilot area** (Failed): EarthChem REST search unreachable: ConnectionError: HTTPSConnectionPool(host='ecp.iedadata.org', port=443): Max retries exceeded with url: /restsearchservice?outputtype=json&searchtype=rowdata&standarditems=yes&westlongitude=30.75&eastlongitude=31.5&southlatitude=-18.05&northlatitude=-17.55 (Caused by NameResolutionError("HTTPSConnection(host='ecp.iedadata.org', port=443): Failed to resolve 'ecp.i
  - What to do: Use the EarthChem Portal web search (https://portal.earthchem.org/) with the pilot bounding box, export CSV, and drop it into data/inbox/ with the citation details.

## Needs a manual request or credentials - and how to get it

### ASTER Global Emissivity Dataset (AG100 v003) / ASTER L1T

- Status: **Needs credentials**
- Publisher: NASA / METI, distributed by NASA LP DAAC (Earthdata)
- Where: https://lpdaac.usgs.gov/products/ag100v003/
- Why: No Earthdata credentials in .env (EARTHDATA_USERNAME / EARTHDATA_PASSWORD).
- How to obtain:

    1. Create a free NASA Earthdata account at https://urs.earthdata.nasa.gov/users/new
    2. In Earthdata, approve the 'LP DAAC Data Pool' application (Profile > Applications > Authorized Apps).
    3. Add EARTHDATA_USERNAME and EARTHDATA_PASSWORD to the .env file in the GeoRevive folder.
    4. Re-run:  .\.venv\Scripts\python.exe -m georevive.ingest --source aster

### BGS digital Harare 1:100k geological map (GeoPackage, ZGS Bulletin No. 94)

- Status: **Needs manual request**
- Publisher: British Geological Survey / Zimbabwe Geological Survey
- Where: https://nora.nerc.ac.uk/id/eprint/541846/
- Why: The GeoPackage is not publicly downloadable (no download link on the NORA record).
- How to obtain:

    The digitised map (GeoPackage) is described in BGS report OR/26/047 but is not offered for public download.
    1. Email BGS Enquiries: enquiries@bgs.ac.uk (cc the report authors via BGS: M.N. Jansen, T. Reeves, M. Krabbendam, S. Piper, B. Brauns). Quote 'OR/26/047 Harare 1:100k GeoPackage'.
    2. The map was digitised for the Zimbabwe Geological Survey (ZGS), which owns the original map: ask ZGS (Ministry of Mines and Mining Development, Harare) for permission to use the digital version for this prototype.
    3. State the purpose (UNDP/timbuktoo pre-incubation prototype, non-commercial) and ask for the licence terms in writing.
    4. When received, save the .gpkg file into data/inbox/bgs/ and re-run: .\.venv\Scripts\python.exe -m georevive.ingest --source bgs_harare_map

### BGS report OR/26/047 - Digitisation of the 1:100k geological map of Harare

- Status: **Needs manual request**
- Publisher: British Geological Survey (UKRI), for the Zimbabwe Geological Survey
- Where: https://nora.nerc.ac.uk/id/eprint/541846/
- Why: Report PDF not fetched automatically: NORA forbids robot harvesting of full-text items.
- How to obtain:

    NORA's policy allows single copies for research/educational/not-for-profit use but forbids robot harvesting, so GeoRevive does not download the PDF automatically.
    1. Open https://nora.nerc.ac.uk/id/eprint/541846/ in a browser and download OR26047.pdf.
    2. Save it as data/inbox/bgs/OR26047.pdf
    3. Re-run: .\.venv\Scripts\python.exe -m georevive.ingest --source bgs_or26047_report

### Zimbabwe Regional Geochemical Survey (1982-86) - BGS international geochemistry CD-ROM

- Status: **Needs manual request**
- Publisher: British Geological Survey / Zimbabwe Geological Survey
- Where: https://www.bgs.ac.uk/geology-projects/applied-geochemistry/international-geochemistry-cd-rom/zimbabwe-regional-geochemical-survey/
- Why: Distributed by BGS on request (international geochemistry CD-ROM); no open download link found.
- How to obtain:

    1. See https://www.bgs.ac.uk/geology-projects/applied-geochemistry/international-geochemistry-cd-rom/zimbabwe-regional-geochemical-survey/
    2. Email enquiries@bgs.ac.uk asking for the Zimbabwe Regional Geochemical Survey data covering the Harare sheet, its licence terms and any charges.
    3. Save the files into data/inbox/ and enter the licence details when prompted.

### GEOROC - Geochemistry of Rocks of the Oceans and Continents

- Status: **Needs credentials**
- Publisher: DIGIS project, University of Göttingen
- Where: https://georoc.eu/
- Why: The GEOROC API requires an API key issued by the DIGIS GEOROC team.
- How to obtain:

    1. Request an API key from the DIGIS GEOROC team (contact via https://georoc.eu/).
    2. Or use the GEOROC web interface to search by coordinates (the pilot bounding box), download the CSV, and drop it into data/inbox/ with the citation details.

### HathiTrust Digital Library - Southern Rhodesia Geological Survey bulletins

- Status: **Needs manual request**
- Publisher: HathiTrust
- Where: https://catalog.hathitrust.org/Search/Home?lookfor=%22Southern%20Rhodesia%22%20%22Geological%20Survey%22&type=all
- Why: HathiTrust's acceptable-use policy does not allow automated bulk downloading; GeoRevive does not scrape it.
- How to obtain:

    1. Open https://catalog.hathitrust.org/Search/Home?lookfor=%22Southern%20Rhodesia%22%20%22Geological%20Survey%22&type=all and tick 'Full view only'.
    2. For each public-domain bulletin, use 'Download > This page (PDF)' for the pages you need (e.g. pages describing gold deposits, with assay tables).
    3. Save the PDFs into data/inbox/ and record the HathiTrust URL and rights statement when the app asks.
    4. Volumes in 'Limited (search only)' need a request to the holding library or the Zimbabwe Geological Survey.

### OneGeology Portal - geology web map services covering Zimbabwe

- Status: **Needs manual request**
- Publisher: OneGeology (Commission for the Geological Map of the World partnership)
- Where: https://portal.onegeology.org/
- Why: Portal unreachable (SSLError). OneGeology documents no machine-readable catalogue for automated discovery, so GeoRevive does not guess service URLs.
- How to obtain:

    1. Open https://portal.onegeology.org/ in a browser and search the layer catalogue for 'Zimbabwe'.
    2. If a Zimbabwe Geological Survey service is listed, note its WMS address and its terms of use.
    3. Ask the OneGeology team (https://onegeology.org/) or ZGS to confirm the licence before use.
    Meanwhile GeoRevive uses the CGMW-BRGM 1:10M regional map via Macrostrat for context.

### USGS Compilation of Geospatial Data for the Mineral Industries and Related Infrastructure of Africa

- Status: **Needs manual request**
- Publisher: U.S. Geological Survey, National Minerals Information Center
- Where: https://www.sciencebase.gov/catalog/item/607611a9d34e018b3201cbbf
- Why: ScienceBase answered HTTP 403 to an automated request (bot protection). GeoRevive does not bypass access controls.
- How to obtain:

    The data are public domain and free to download by a person:
    1. In a browser, open https://www.sciencebase.gov/catalog/item/607611a9d34e018b3201cbbf
    2. Download the geodatabase / shapefile .zip listed under 'Attached Files' (or in the child items).
    3. Save it into data\inbox\usgs\africa\ (inside the GeoRevive folder).
    4. Re-run: .\.venv\Scripts\python.exe -m georevive.ingest --source usgs_africa_minerals

### USGS Geology of Africa (geo7_2ag, Open-File Report 97-470A)

- Status: **Needs manual request**
- Publisher: U.S. Geological Survey (World Energy Project)
- Where: https://www.sciencebase.gov/catalog/item/60d0ff26d34e86b938aab404
- Why: ScienceBase answered HTTP 403 to an automated request (bot protection); not bypassed.
- How to obtain:

    Optional (regional context only). In a browser open https://www.sciencebase.gov/catalog/item/60d0ff26d34e86b938aab404, download the shapefile .zip, save it into data\inbox\usgs\geo7\ and re-run --source usgs_geo7_africa.

### USGS Mineral Resources Data System (MRDS) - Zimbabwe

- Status: **Needs manual request**
- Publisher: U.S. Geological Survey
- Where: https://mrdata.usgs.gov/mrds/mrds-csv.zip
- Why: mrdata.usgs.gov/robots.txt disallows all automated agents (User-agent: * / Disallow: /), so GeoRevive does not download MRDS by script.
- How to obtain:

    MRDS is public domain, but its website forbids automated downloads. A person can download it:
    1. In a browser, open https://mrdata.usgs.gov/mrds/ and, under Downloads, click 'mrds-csv.zip' (CSV, about 23 MB).
    2. Save the file as data\inbox\usgs\mrds-csv.zip (inside the GeoRevive folder).
    3. Re-run: .\.venv\Scripts\python.exe -m georevive.ingest --source usgs_mrds

### Zimbabwe Geological Survey Bulletin No. 94 and related short reports (paper)

- Status: **Needs manual request**
- Publisher: Zimbabwe Geological Survey
- Where: https://www.bgs.ac.uk/
- Why: No openly downloadable digital copy was found.
- How to obtain:

    1. Zimbabwe Geological Survey (Ministry of Mines and Mining Development, Harare): request a copy of Bulletin No. 94 and permission to scan selected pages for this prototype. Confirm current contact details through the Ministry.
    2. BGS library (enquiries@bgs.ac.uk) holds many ZGS bulletins and may advise on access.
    3. University of Zimbabwe Geology Department library may hold copies.
    4. Scan at 300-400 dpi, save into data/inbox/ and enter the source and permission details when uploading.

## Licence terms marked 'to confirm' (check by hand)

- **BGS digital Harare 1:100k geological map (GeoPackage, ZGS Bulletin No. 94)** - licence to confirm (not publicly released; terms to be agreed with BGS/ZGS)
- **Zimbabwe Regional Geochemical Survey (1982-86) - BGS international geochemistry CD-ROM** - licence to confirm with BGS
- **EarthChem Portal - rock geochemistry samples in the pilot area** - CC BY 4.0 for EarthChem Library data (per-dataset; licence to confirm per sample source)
- **GEOROC - Geochemistry of Rocks of the Oceans and Continents** - CC BY-SA 4.0 for GEOROC compilations (licence to confirm)
- **OneGeology Portal - geology web map services covering Zimbabwe** - Per service (to confirm for any service found)
- **Regional geology - CGMW-BRGM 1:10M Geological Map of Africa (via Macrostrat API)** - CC BY 4.0 as stated by the Macrostrat API; underlying CGMW-BRGM map - licence to confirm with CGMW
- **USGS Geology of Africa (geo7_2ag, Open-File Report 97-470A)** - Public domain (USGS); coastline/boundaries contain ESRI proprietary data - licence to confirm

## Details per source

### ASTER Global Emissivity Dataset (AG100 v003) / ASTER L1T

- **ID:** `aster` · **Status:** Needs credentials
- **Publisher:** NASA / METI, distributed by NASA LP DAAC (Earthdata)
- **URL:** https://lpdaac.usgs.gov/products/ag100v003/
- **Licence / terms:** NASA Earthdata: no restrictions on use, citation requested; requires free Earthdata login (https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance)
- **Attribution:** ASTER GED courtesy of NASA/METI/AIST/Japan Spacesystems and U.S./Japan ASTER Science Team
- **Accessed:** 2026-10-10T20:22:56.219858
- **Coverage (bbox):** -
- **Records / raster size:** -
- **What it is:** Optional. Thermal-infrared emissivity (silica, carbonate) and SWIR bands for improved mineral mapping.
- **How GeoRevive uses it:** Optional extra evidence layers (not required for the demo).
- **Problem:** No Earthdata credentials in .env (EARTHDATA_USERNAME / EARTHDATA_PASSWORD).
- **URLs tried:**
    - https://lpdaac.usgs.gov/products/ag100v003/ -> not attempted: needs Earthdata login

### BGS digital Harare 1:100k geological map (GeoPackage, ZGS Bulletin No. 94)

- **ID:** `bgs_harare_map` · **Status:** Needs manual request
- **Publisher:** British Geological Survey / Zimbabwe Geological Survey
- **URL:** https://nora.nerc.ac.uk/id/eprint/541846/
- **Licence / terms:** licence to confirm (not publicly released; terms to be agreed with BGS/ZGS)
- **Attribution:** Geology: Zimbabwe Geological Survey Bulletin 94 map, digitised by BGS (OR/26/047)
- **Accessed:** 2026-10-10T20:14:05.750034
- **Coverage (bbox):** -
- **Records / raster size:** -
- **What it is:** Bedrock geology polygons, boundaries and faults with LEX-RCS codes for the pilot sheet.
- **How GeoRevive uses it:** Primary geology for the pilot area: host-rock (greenstone, mafic-ultramafic) and granite-contact evidence layers; fault/shear-zone distance layer.
- **Problem:** The GeoPackage is not publicly downloadable (no download link on the NORA record).
- **URLs tried:**
    - https://nora.nerc.ac.uk/id/eprint/541846/ -> no public GeoPackage link

### BGS report OR/26/047 - Digitisation of the 1:100k geological map of Harare

- **ID:** `bgs_or26047_report` · **Status:** Needs manual request
- **Publisher:** British Geological Survey (UKRI), for the Zimbabwe Geological Survey
- **URL:** https://nora.nerc.ac.uk/id/eprint/541846/
- **Licence / terms:** NORA access policy: single copy for personal research/study, educational or not-for-profit use with full citation; no robot harvesting; no commercial sale. © UKRI (https://nora.nerc.ac.uk/policies.html)
- **Attribution:** Jansen, M.N.; Reeves, T.; Krabbendam, M.; Piper, S.; Brauns, B. 2026. Digitisation of the 1:100k scale geological map of Harare, Zimbabwe. Nottingham, UK, British Geological Survey, 23pp. (OR/26/047)
- **Accessed:** 2026-10-10T20:14:05.668971
- **Coverage (bbox):** -
- **Records / raster size:** -
- **What it is:** 23-page report describing the digitised Harare 1:100k map (ZGS Bulletin No. 94): GeoPackage layers for bedrock polygons, boundaries, faults and seed points, with LEX-RCS unit codes.
- **How GeoRevive uses it:** Documents the pilot-area map; used to confirm the sheet extent and unit codes. Not redistributed.
- **Problem:** Report PDF not fetched automatically: NORA forbids robot harvesting of full-text items.
- **URLs tried:**
    - https://nora.nerc.ac.uk/id/eprint/541846/ -> HTTP 200

### Zimbabwe Regional Geochemical Survey (1982-86) - BGS international geochemistry CD-ROM

- **ID:** `bgs_zimbabwe_geochem` · **Status:** Needs manual request
- **Publisher:** British Geological Survey / Zimbabwe Geological Survey
- **URL:** https://www.bgs.ac.uk/geology-projects/applied-geochemistry/international-geochemistry-cd-rom/zimbabwe-regional-geochemical-survey/
- **Licence / terms:** licence to confirm with BGS
- **Accessed:** 2026-10-10T20:39:13.057842
- **Coverage (bbox):** -
- **Records / raster size:** -
- **What it is:** Regional stream-sediment geochemistry survey covering parts of Zimbabwe including the Harare area.
- **How GeoRevive uses it:** Potential geochemical evidence layer (e.g. Au, As pathfinders) once obtained.
- **Problem:** Distributed by BGS on request (international geochemistry CD-ROM); no open download link found.
- **URLs tried:**
    - https://www.data.gov.uk/dataset/756d6426-d52d-492a-a263-599ad1caa123/zimbabwe-regional-geochemical-survey -> HTTP 200

### Copernicus DEM GLO-30 (30 m digital surface model)

- **ID:** `copernicus_dem_glo30` · **Status:** Downloaded
- **Publisher:** European Space Agency / Airbus (Copernicus programme), via AWS Open Data
- **URL:** https://copernicus-dem-30m.s3.amazonaws.com/readme.html
- **Licence / terms:** Copernicus DEM licence: free of charge, worldwide, for any lawful use, with attribution (https://spacedata.copernicus.eu/documents/20123/122407/GEO1988-CopernicusDEM-SPE-002_ProductHandbook_I5.0+%281%29.pdf)
- **Attribution:** Copernicus DEM © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the European Union and ESA
- **Accessed:** 2026-10-10T20:41:39.232117
- **Coverage (bbox):** [30.75, -18.05, 31.5, -17.55]
- **Records / raster size:** 2670 x 1872 px @ 30 m (1 band)
- **What it is:** Elevation (surface model) at ~30 m, reprojected to UTM 36S. Elevation range 1141-1649 m.
- **How GeoRevive uses it:** Hillshade base map (works offline); slope and terrain roughness evidence layers; lineament support.
- **Files (SHA-256):**
    - `data/raw/copernicus_dem_glo30/dem_30m.tif` (20,444,330 bytes) `bd360e633bc52888863c3510ba6198f21cfeb594c732ac7c1127bb54aa3cfd55`
    - `data/raw/copernicus_dem_glo30/manifest.json` (813 bytes) `5a58bd6009a9373564dbf501b57c30410a94adeff2b884688640d48bdcc1a562`
- **URLs tried:**
    - https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_S19_00_E030_00_DEM/Copernicus_DSM_COG_10_S19_00_E030_00_DEM.tif -> cached: dem_30m.tif

### EarthChem Portal - rock geochemistry samples in the pilot area

- **ID:** `earthchem` · **Status:** Failed
- **Publisher:** EarthChem / IEDA (Lamont-Doherty Earth Observatory)
- **URL:** https://www.earthchem.org/
- **Licence / terms:** CC BY 4.0 for EarthChem Library data (per-dataset; licence to confirm per sample source) (https://www.earthchem.org/about/policies/)
- **Attribution:** Geochemistry: EarthChem Portal (and original publications)
- **Accessed:** 2026-10-10T20:39:10.708478
- **Coverage (bbox):** -
- **Records / raster size:** -
- **What it is:** Published whole-rock and mineral analyses with coordinates.
- **How GeoRevive uses it:** Optional context layer (sample locations and Au/As/Cu values where reported).
- **Problem:** EarthChem REST search unreachable: ConnectionError: HTTPSConnectionPool(host='ecp.iedadata.org', port=443): Max retries exceeded with url: /restsearchservice?outputtype=json&searchtype=rowdata&standarditems=yes&westlongitude=30.75&eastlongitude=31.5&southlatitude=-18.05&northlatitude=-17.55 (Caused by NameResolutionError("HTTPSConnection(host='ecp.iedadata.org', port=443): Failed to resolve 'ecp.i
- **URLs tried:**
    - https://ecp.iedadata.org/restsearchservice?outputtype=json&searchtype=rowdata&standarditems=yes&westlongitude=30.75&eastlongitude=31.5&southlatitude=-18.05&northlatitude=-17.55 -> error: ConnectionError: HTTPSConnectionPool(host='ecp.iedadata.org', port=443): Max retries exceeded with url: /restsearchservice?outputtype=json&searchtype=rowdata&standarditems=yes&westlongitude=30.75&eastlongitude=31.5&southlatitude=-18.05&northlatitude=-17.55 (Caused by NameResolutionError("HTTP

### ESA WorldCover 2021 v200 (10 m land cover)

- **ID:** `esa_worldcover` · **Status:** Downloaded
- **Publisher:** European Space Agency (ESA WorldCover consortium), via AWS Open Data
- **URL:** https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_S21E030_Map.tif
- **Licence / terms:** CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
- **Attribution:** © ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021)
- **Accessed:** 2026-10-10T20:40:43.507572
- **Coverage (bbox):** [30.75, -18.05, 31.5, -17.55]
- **Records / raster size:** 2670 x 1872 px @ 30 m (1 band)
- **What it is:** Global land-cover classes (tree, shrub, grass, crop, built-up, bare, water...) at 10 m for 2021. Built-up 7.8% of the pilot area.
- **How GeoRevive uses it:** Masks built-up areas and water so that roofs, roads and bare urban soil are not mistaken for alteration, and so that no target is placed in a town.
- **Files (SHA-256):**
    - `data/raw/esa_worldcover/worldcover_30m.tif` (3,131,485 bytes) `105f124211dc278607ac184bc8476020395af62d90942f3eeaec1a2ff2062742`
    - `data/raw/esa_worldcover/manifest.json` (312 bytes) `7c2c09ad524a495dfc566bd10094b70d4a3262ad1ea4c926eef02159b647751d`
- **URLs tried:**
    - https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_S21E030_Map.tif -> read window
    - https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_S18E030_Map.tif -> read window

### geoBoundaries - Zimbabwe administrative boundaries (ADM0-ADM2)

- **ID:** `geoboundaries` · **Status:** Downloaded
- **Publisher:** geoBoundaries (William & Mary geoLab)
- **URL:** https://www.geoboundaries.org/api/current/gbOpen/ZWE/ADM2/
- **Licence / terms:** Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)
- **Attribution:** Boundaries: geoBoundaries (Runfola et al. 2020), source ZIMSTAT / OCHA ROSEA
- **Accessed:** 2026-10-10T20:23:43.312955
- **Coverage (bbox):** [25.2376, -22.421, 33.0672, -15.6071]
- **Records / raster size:** 102 records
- **What it is:** Country, province and district boundaries for Zimbabwe.
- **How GeoRevive uses it:** District names in claim reports; plain base map that works offline.
- **Files (SHA-256):**
    - `data/raw/geoboundaries/geoBoundaries-ZWE-ADM0.geojson` (1,780,141 bytes) `dd5c7bbee97029c84287471839bdee1e68b841d1c2977a5ce633eb7d4c271359`
    - `data/raw/geoboundaries/geoBoundaries-ZWE-ADM1.geojson` (7,243,657 bytes) `4a84368bb234ab67e4285c7f4f5d2e460332629b843ac480fa380f49d9753f11`
    - `data/raw/geoboundaries/geoBoundaries-ZWE-ADM2.geojson` (17,379,177 bytes) `074a3632634b9448bb4043580fe7199e0b2f64ec68bd2f98932a2c68b3795b88`
    - `data/raw/geoboundaries/api_metadata.json` (1,882 bytes) `2b710fe0ecff0ce8bb9b30c6d38b3be8a8f71dc45c64e653f66474d88171fcc7`
- **URLs tried:**
    - https://www.geoboundaries.org/api/current/gbOpen/ZWE/ADM0/ -> HTTP 200
    - https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/ZWE/ADM0/geoBoundaries-ZWE-ADM0.geojson -> HTTP 200
    - https://www.geoboundaries.org/api/current/gbOpen/ZWE/ADM1/ -> HTTP 200
    - https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/ZWE/ADM1/geoBoundaries-ZWE-ADM1.geojson -> HTTP 200
    - https://www.geoboundaries.org/api/current/gbOpen/ZWE/ADM2/ -> HTTP 200
    - https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/ZWE/ADM2/geoBoundaries-ZWE-ADM2.geojson -> HTTP 200

### GEOROC - Geochemistry of Rocks of the Oceans and Continents

- **ID:** `georoc` · **Status:** Needs credentials
- **Publisher:** DIGIS project, University of Göttingen
- **URL:** https://georoc.eu/
- **Licence / terms:** CC BY-SA 4.0 for GEOROC compilations (licence to confirm)
- **Accessed:** 2026-10-10T20:39:10.779559
- **Coverage (bbox):** -
- **Records / raster size:** -
- **What it is:** Global compilation of published rock geochemistry.
- **How GeoRevive uses it:** Optional context: published analyses of Harare greenstone belt rocks, if any.
- **Problem:** The GEOROC API requires an API key issued by the DIGIS GEOROC team.

### HathiTrust Digital Library - Southern Rhodesia Geological Survey bulletins

- **ID:** `hathitrust_scans` · **Status:** Needs manual request
- **Publisher:** HathiTrust
- **URL:** https://catalog.hathitrust.org/Search/Home?lookfor=%22Southern%20Rhodesia%22%20%22Geological%20Survey%22&type=all
- **Licence / terms:** Per volume; full view only for public-domain volumes; automated bulk download not permitted (https://www.hathitrust.org/the-collection/terms-conditions/acceptable-use-policy/)
- **Accessed:** 2026-10-10T20:38:55.737292
- **Coverage (bbox):** -
- **Records / raster size:** -
- **What it is:** Catalogue of digitised Southern Rhodesia / Rhodesia Geological Survey bulletins and short reports.
- **How GeoRevive uses it:** Candidate test documents for data rescue, to be downloaded manually page by page where full view.
- **Problem:** HathiTrust's acceptable-use policy does not allow automated bulk downloading; GeoRevive does not scrape it.

### Historical geological publications on Internet Archive (public-domain items only)

- **ID:** `internet_archive_scans` · **Status:** Downloaded
- **Publisher:** Internet Archive (digitised by contributing libraries)
- **URL:** https://archive.org/
- **Licence / terms:** Per item: only items flagged public domain / not in copyright are downloaded (see details) (https://archive.org/about/terms.php)
- **Attribution:** Scans courtesy of the Internet Archive and contributing libraries
- **Accessed:** 2026-10-10T20:38:55.188087
- **Coverage (bbox):** -
- **Records / raster size:** 3 records; 1159 scanned pages
- **What it is:** Scanned historical texts about Rhodesian/Zimbabwean geology, gold mines and mineral resources. Items: The gold mines of the world : written after an inspection of the mines (1902); The Mineral Industry of Rhodesia (1911); Prehistoric Rhodesia; an examination of the historical, ethnological a (1909)
- **How GeoRevive uses it:** Test documents for the data-rescue pipeline (enhancement, OCR, fact extraction, accuracy check).
- **Files (SHA-256):**
    - `data/raw/internet_archive_scans/goldminesworldd00curlgoog/goldminesworldd00curlgoog.pdf` (13,057,218 bytes) `6d0f0024eb5c25b8f4230b05ab9a4941ff0de8e8a7cdc01f09c59b73603894e3`
    - `data/raw/internet_archive_scans/goldminesworldd00curlgoog/item_metadata.json` (1,874 bytes) `36cb4c0630a3ed37b5d5b636fe45f942e18b20ac3989d38322f35937b4111074`
    - `data/raw/internet_archive_scans/paper-doi-10_1038_087511b0/paper-doi-10_1038_087511b0.pdf` (220,638 bytes) `0a420372e2ebdc43bc9d529e9b708d6dffe5309ada02f629a567d98b4a2d9e33`
    - `data/raw/internet_archive_scans/paper-doi-10_1038_087511b0/item_metadata.json` (1,461 bytes) `b5f614c49d39d272c9b555ef4ce1af5a24cdccdde4e3126ade47bd74995c4430`
    - `data/raw/internet_archive_scans/prehistoricrhode00hall/prehistoricrhode00hall.pdf` (57,332,974 bytes) `c7222cd83de615bc3bbbc905a8317547277497d9305710ad0d78041f95f11523`
    - `data/raw/internet_archive_scans/prehistoricrhode00hall/item_metadata.json` (2,507 bytes) `f422477481c5fec9311e447e22507830b0dece907883da0d06fac00bfd156a5b`
    - `data/raw/internet_archive_scans/manifest.json` (1,491 bytes) `ceb24d2e19983f84634f15ef9b567ba1fa90086259db01470a44022e210b0e0d`
- **URLs tried:**
    - https://archive.org/advancedsearch.php?q=%28title%3A%28Rhodesia%29%20AND%20%28title%3A%28geology%29%20OR%20title%3A%28geological%29%20OR%20title%3A%28gold%29%20OR%20title%3A%28mineral%29%20OR%20title%3A%28mines%29%20OR%20subject%3A%28geology%29%29%29%20AND%20mediatype%3Atexts&fl[]=identifier&fl[]=title&fl[]=date&fl[]=licenseurl&fl[]=possible-copyright-status&fl[]=rights&fl[]=collection&rows=100&output=json -> HTTP 200
    - https://archive.org/advancedsearch.php?q=%28%22Geological%20Survey%22%20AND%20%28Rhodesia%20OR%20Zimbabwe%20OR%20Mashonaland%29%29%20AND%20mediatype%3Atexts&fl[]=identifier&fl[]=title&fl[]=date&fl[]=licenseurl&fl[]=possible-copyright-status&fl[]=rights&fl[]=collection&rows=100&output=json -> HTTP 200
    - https://archive.org/advancedsearch.php?q=%28subject%3A%28%22Geology%20--%20Zimbabwe%22%29%20OR%20subject%3A%28%22Geology%20--%20Rhodesia%22%29%20OR%20subject%3A%28%22Mines%20and%20mineral%20resources%20--%20Zimbabwe%22%29%29%20AND%20mediatype%3Atexts&fl[]=identifier&fl[]=title&fl[]=date&fl[]=licenseurl&fl[]=possible-copyright-status&fl[]=rights&fl[]=collection&rows=100&output=json -> HTTP 200
    - https://archive.org/metadata/goldminesworldd00curlgoog -> HTTP 200
    - https://archive.org/download/goldminesworldd00curlgoog/goldminesworldd00curlgoog.pdf -> HTTP 200
    - https://archive.org/metadata/paper-doi-10_1038_087511b0 -> HTTP 200
    - https://archive.org/download/paper-doi-10_1038_087511b0/paper-doi-10_1038_087511b0.pdf -> HTTP 200
    - https://archive.org/metadata/prehistoricrhode00hall -> HTTP 200
    - https://archive.org/download/prehistoricrhode00hall/prehistoricrhode00hall.pdf -> HTTP 200

### OneGeology Portal - geology web map services covering Zimbabwe

- **ID:** `onegeology` · **Status:** Needs manual request
- **Publisher:** OneGeology (Commission for the Geological Map of the World partnership)
- **URL:** https://portal.onegeology.org/
- **Licence / terms:** Per service (to confirm for any service found)
- **Accessed:** 2026-10-10T20:42:11.709722
- **Coverage (bbox):** -
- **Records / raster size:** -
- **What it is:** The OneGeology Portal lists geological web map services registered by national surveys.
- **How GeoRevive uses it:** Regional geology context, only if an openly licensed Zimbabwe layer is available.
- **Problem:** Portal unreachable (SSLError). OneGeology documents no machine-readable catalogue for automated discovery, so GeoRevive does not guess service URLs.
- **URLs tried:**
    - https://portal.onegeology.org/ -> error: SSLError: HTTPSConnectionPool(host='portal.onegeology.org', port=443): Max retries exceeded with url: / (Caused by SSLError(SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: Hostname mismatch, certificate is not valid for 'portal.onegeology.org'. (_ssl.c

### OpenStreetMap - roads, places, rivers and mapped mine features

- **ID:** `osm` · **Status:** Downloaded
- **Publisher:** OpenStreetMap contributors (via Overpass API)
- **URL:** https://download.geofabrik.de/africa/zimbabwe-latest.osm.pbf
- **Licence / terms:** Open Database Licence (ODbL) 1.0 (https://www.openstreetmap.org/copyright)
- **Attribution:** © OpenStreetMap contributors (ODbL)
- **Accessed:** 2026-10-10T22:06:47.156760
- **Coverage (bbox):** [30.75, -18.05, 31.5, -17.55]
- **Records / raster size:** 4,382 records
- **What it is:** Roads, towns/villages/farms/localities, rivers and streams, and mapped quarries/mine shafts. Feature groups from: roads: https://download.geofabrik.de/africa/zimbabwe-latest.osm.pbf; waterways: https://download.geofabrik.de/africa/zimbabwe-latest.osm.pbf; places: https://download.geofabrik.de/africa/zimbabwe-latest.osm.pbf; mines: https://download.geofabrik.de/africa/zimbabwe-latest.osm.pbf
- **How GeoRevive uses it:** Access and context on the map and in claim reports; place and farm names for offline geocoding of rescued facts.
- **Files (SHA-256):**
    - `data/raw/osm/overpass.json` (4,565,898 bytes) `26301699e33361b3854f27b12a8e06c3911904ffbea91a2d2d77d7bb721bffce`
    - `data/raw/osm/query_mines.overpassql` (280 bytes) `9a815dea5bae0dccb9a4fb4675d3c5b716039a8ab4138d7b2aa787a9c559ceea`
    - `data/raw/osm/query_places.overpassql` (163 bytes) `111df563e4d887b2c5d66c57770115f05b3a185ec035a56f06f4e5d7ffc88f89`
    - `data/raw/osm/query_roads.overpassql` (193 bytes) `26b353e497bee8ac2c60d02777145ee35b9f7a2f23571a1366d349745339a8d6`
    - `data/raw/osm/query_waterways.overpassql` (114 bytes) `0e7e69cca68785a8ad9b30cced69910d604757610ba0571605274e4b3abe184a`
- **URLs tried:**
    - https://overpass.kumi.systems/api/interpreter -> cached: overpass.json

### Regional geology - CGMW-BRGM 1:10M Geological Map of Africa (via Macrostrat API)

- **ID:** `regional_geology` · **Status:** Downloaded
- **Publisher:** Macrostrat (University of Wisconsin-Madison); map source CGMW-BRGM (Thiéblemont ed.)
- **URL:** https://macrostrat.org/api/v2/geologic_units/map
- **Licence / terms:** CC BY 4.0 as stated by the Macrostrat API; underlying CGMW-BRGM map - licence to confirm with CGMW (https://macrostrat.org/)
- **Attribution:** Regional geology: Macrostrat (CC BY 4.0) / CGMW-BRGM 1:10M Geological Map of Africa
- **Accessed:** 2026-10-10T21:43:19.089815
- **Coverage (bbox):** [30.75, -18.05, 31.5, -17.55]
- **Records / raster size:** 9 records
- **What it is:** Very small-scale (1:10 million) lithology/age polygons; separates Archean volcano-sedimentary belts from granitoids.
- **How GeoRevive uses it:** Regional context outside the pilot sheet, and a coarse fallback host-rock layer if the BGS 1:100k geology is not available. Far too coarse for target-scale decisions.
- **Files (SHA-256):**
    - `data/raw/regional_geology/macrostrat_small.geojson` (85,292 bytes) `414abc975f899d58fff8416404c4fb3acf982fec52b2273229456ba96b8905d6`
- **URLs tried:**
    - https://macrostrat.org/api/v2/geologic_units/map -> cached: macrostrat_small.geojson

### Copernicus Sentinel-2 Level-2A surface reflectance (dry season scene)

- **ID:** `sentinel2_l2a` · **Status:** Downloaded
- **Publisher:** European Space Agency / European Commission (Copernicus), via open STAC catalogue
- **URL:** https://earth-search.aws.element84.com/v1
- **Licence / terms:** Copernicus Sentinel data terms: free, full and open access (attribution required) (https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice)
- **Attribution:** Contains modified Copernicus Sentinel data [year], processed by GeoRevive
- **Accessed:** 2026-10-10T22:06:43.741836
- **Coverage (bbox):** [30.75, -18.05, 31.5, -17.55]
- **Records / raster size:** 1336 x 937 px @ 60 m (8 bands)
- **What it is:** Bottom-of-atmosphere reflectance (bands B02-B12, SCL) for one low-cloud dry-season date over the pilot area. Scene date 2026-07-14; scenes: S2C_35KRV_20260714_0_L2A, S2C_35KRA_20260714_0_L2A, S2C_36KTF_20260714_0_L2A, S2C_36KUF_20260714_0_L2A; mean cloud 0.0%.
- **How GeoRevive uses it:** Band-ratio alteration indices (iron oxide B4/B2, ferrous iron B12/B8A+B3/B4, clay/hydroxyl B11/B12) with cloud, water and vegetation masks; evidence layers for prospectivity.
- **Files (SHA-256):**
    - `data/raw/sentinel2_l2a/s2_bands.tif` (43,345,055 bytes) `dae025807dcf0a6c30c20e45c8086bcc5a5d052a954fedf5fa84237f8ec893fa`
    - `data/raw/sentinel2_l2a/manifest.json` (4,821 bytes) `7d848f4f132bd1a1fe2eb887fb4525519008f15b11822dfbca50a268bfa86c48`
    - `data/raw/sentinel2_l2a/S2C_35KRV_20260714_0_L2A.json` (22,512 bytes) `f9f59dcce9d8923407e6d343201a527e815af696d2cadbefa87f2b653affc05f`
    - `data/raw/sentinel2_l2a/S2C_35KRA_20260714_0_L2A.json` (22,500 bytes) `b7dd416fb66b709c0089efb0fcc703b6077287cd31c35fbfc9a15710f2fb5163`
    - `data/raw/sentinel2_l2a/S2C_36KTF_20260714_0_L2A.json` (22,503 bytes) `91bdf5a7bc1840dff59768fb0e6811783aa7887edc068f02625e69d53d5f1fe2`
    - `data/raw/sentinel2_l2a/S2C_36KUF_20260714_0_L2A.json` (22,509 bytes) `5ccb80e1343c9103a2f80f65abcdb4d8c7e1c1b89435e649da053aad7273f8d2`
- **URLs tried:**
    - https://earth-search.aws.element84.com/v1 -> cached: s2_bands.tif
    - https://earth-search.aws.element84.com/v1 -> repaired cached stack: removed a doubly applied BOA offset

### USGS Compilation of Geospatial Data for the Mineral Industries and Related Infrastructure of Africa

- **ID:** `usgs_africa_minerals` · **Status:** Needs manual request
- **Publisher:** U.S. Geological Survey, National Minerals Information Center
- **URL:** https://www.sciencebase.gov/catalog/item/607611a9d34e018b3201cbbf
- **Licence / terms:** Public domain (U.S. Government work); some layers compiled from third-party sources - check layer metadata (https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits)
- **Attribution:** Mineral facilities: USGS NMIC Africa geospatial compilation (2021)
- **Accessed:** 2026-10-10T20:14:08.748962
- **Coverage (bbox):** -
- **Records / raster size:** -
- **What it is:** Mineral production/processing facilities and exploration/development sites in Africa (reference year 2018).
- **How GeoRevive uses it:** Additional known sites for validation and context; points inside the pilot area are shown on the map.
- **Problem:** ScienceBase answered HTTP 403 to an automated request (bot protection). GeoRevive does not bypass access controls.
- **URLs tried:**
    - https://www.sciencebase.gov/catalog/item/607611a9d34e018b3201cbbf?format=json -> HTTP 403

### USGS Geology of Africa (geo7_2ag, Open-File Report 97-470A)

- **ID:** `usgs_geo7_africa` · **Status:** Needs manual request
- **Publisher:** U.S. Geological Survey (World Energy Project)
- **URL:** https://www.sciencebase.gov/catalog/item/60d0ff26d34e86b938aab404
- **Licence / terms:** Public domain (USGS); coastline/boundaries contain ESRI proprietary data - licence to confirm
- **Attribution:** Geology of Africa: Persits et al., USGS OFR 97-470A
- **Accessed:** 2026-10-10T20:42:13.151597
- **Coverage (bbox):** -
- **Records / raster size:** -
- **What it is:** 1:5M surficial/bedrock geology of Africa by age.
- **How GeoRevive uses it:** Regional context only.
- **Problem:** ScienceBase answered HTTP 403 to an automated request (bot protection); not bypassed.
- **URLs tried:**
    - https://www.sciencebase.gov/catalog/item/60d0ff26d34e86b938aab404?format=json -> HTTP 403

### USGS Mineral Resources Data System (MRDS) - Zimbabwe

- **ID:** `usgs_mrds` · **Status:** Needs manual request
- **Publisher:** U.S. Geological Survey
- **URL:** https://mrdata.usgs.gov/mrds/mrds-csv.zip
- **Licence / terms:** Public domain (U.S. Government work) (https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits)
- **Attribution:** Mineral occurrences: USGS MRDS (Mason & Arndt 1996; McFaul et al. 2000)
- **Accessed:** 2026-10-10T20:14:07.117316
- **Coverage (bbox):** -
- **Records / raster size:** -
- **What it is:** Known mineral occurrences, prospects and mines (points). USGS stopped systematic updates in 2011, so records reflect historical compilations and locations can be approximate.
- **How GeoRevive uses it:** Known gold occurrences are the training positives for the data-driven model and the validation set for both models (never an input feature).
- **Problem:** mrdata.usgs.gov/robots.txt disallows all automated agents (User-agent: * / Disallow: /), so GeoRevive does not download MRDS by script.
- **URLs tried:**
    - https://mrdata.usgs.gov/mrds/mrds-csv.zip -> skipped: disallowed by robots.txt

### Zimbabwe Geological Survey Bulletin No. 94 and related short reports (paper)

- **ID:** `zgs_bulletins` · **Status:** Needs manual request
- **Publisher:** Zimbabwe Geological Survey
- **URL:** https://www.bgs.ac.uk/
- **Licence / terms:** © Zimbabwe Geological Survey - permission required
- **Accessed:** 2026-10-10T20:38:55.747394
- **Coverage (bbox):** -
- **Records / raster size:** -
- **What it is:** The explanatory bulletin for the Harare 1:100 000 sheet and older reports on the Harare greenstone belt.
- **How GeoRevive uses it:** Primary documents for data rescue of the pilot area once scanned with permission.
- **Problem:** No openly downloadable digital copy was found.

### Manual inbox (data/inbox/)

- **ID:** `inbox` · **Status:** Downloaded
- **Publisher:** GeoRevive team
- **URL:** data/inbox/
- **Licence / terms:** Per file (entered on upload)
- **Accessed:** 2026-10-10T20:39:13.075600
- **Coverage (bbox):** -
- **Records / raster size:** 0 records
- **What it is:** Documents and scans added by the team. 0 file(s) in the inbox; 0 still need source/licence details.
- **How GeoRevive uses it:** Data rescue.
