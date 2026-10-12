# GeoRevive Africa: User Guide

This guide is for everyone on the team, not only programmers. Each task has numbered steps. To install and start the app, see [README.md](README.md). A shorter version of this guide is in the app under **How to use**.

> Prototype targets for discussion. All targets require field verification by a qualified geologist. Not investment advice.

## Contents
1. [Signing in and roles](#1-signing-in-and-roles)
2. [The Data Sources page and what each status means](#2-the-data-sources-page)
3. [Adding your own scans (data/inbox)](#3-adding-your-own-scans)
4. [Reviewing extracted facts (geologist)](#4-reviewing-extracted-facts-geologist)
5. [Using the Map Explorer](#5-using-the-map-explorer)
6. [Running and interpreting the prospectivity model](#6-running-and-interpreting-the-prospectivity-model)
7. [Producing a claim check report](#7-producing-a-claim-check-report)
8. [Sharing data in the data room and reading the audit log](#8-the-data-room-and-the-audit-log)
9. [Requesting missing data](#9-requesting-missing-data)
10. [Presenter Mode](#10-presenter-mode)

---

## 1. Signing in and roles

1. Start the app (double-click `Start GeoRevive.bat`). Edge opens the sign-in page.
2. On the laptop that runs GeoRevive, click one of the **demo accounts**. Anywhere else, type a username and password (the passwords are in `.env`).
3. The left sidebar shows only the pages your role may use. Click **Collapse** to make more room on a projector. Use the breadcrumbs and the **Back** arrow at the top to go back.

| Role | What it can do |
|---|---|
| **Admin** | Everything. Shares datasets in the data room, reads the audit log, resets the demo. |
| **Geologist** | Reviews extracted facts (approve, edit, reject) and edits the prospectivity model weights. Also uploads and runs models. |
| **Analyst** | Sees all data, uploads scans, runs models, makes claim reports. Cannot approve facts or edit weights. |
| **Investor** | Sees and downloads **only** the datasets shared with them. Every download is watermarked with their name and the time. |
| **Miner** | Makes claim check reports only. |

## 2. The Data Sources page

The Data Sources page is the **Source Registry**. It lists every dataset GeoRevive uses.

1. Open **Data Sources** in the sidebar.
2. The boxes at the top count datasets by status.
3. Each row shows the dataset and publisher, its **status**, its **licence**, when we **accessed** it, and how much we got (records or raster size).
4. Click a row to see more:
   - what the dataset is and how GeoRevive uses it
   - the source URL and the attribution to show
   - the **files we downloaded, with SHA-256 checksums**, which prove which exact file we used
   - every **URL we tried** and what happened
   - **what failed and why**, and **how to obtain** anything that is missing
5. Click **View on map** next to a layer to open it in the Map Explorer.
6. Click **Data report** (top right) to read the full report. The same report is saved as `reports/DATA_SOURCES.md`.

**What each status means**

| Status | Meaning | What to do |
|---|---|---|
| **Downloaded** | We obtained and checked the data. | Nothing; it is ready. |
| **Partial** | Some of it was obtained. | Read the note to see what is missing. |
| **Failed** | The download failed (server error, no matching data). The reason is recorded. Nothing was made up to fill the gap. | Try again later, or follow "How to obtain". |
| **Needs manual request** | Not openly downloadable, or the website forbids automated downloads. | Follow the steps in "How to obtain" (see section 9). |
| **Needs credentials** | Free, but needs a login (for example NASA Earthdata). | Add the login to `.env` and run that source again. |

Licences marked **"licence to confirm"** are shown in amber. Someone must check those terms before the data is shared outside the team.

## 3. Adding your own scans

Use this for PDFs and scans from the Geological Survey, libraries, or your own scanning. **Only add documents we are allowed to use.**

**Option A: upload in the app (recommended)**

1. Open **Data Rescue**.
2. Under **Upload a scan**, choose the file (PDF, PNG, JPG or TIFF, up to 60 MB).
3. Fill in the provenance. It goes into the Source Registry:
   - **Title of the document**, e.g. *ZGS Bulletin 94, page 37*
   - **Publisher / holder**, e.g. *Zimbabwe Geological Survey*
   - **Where it came from**: a URL, or a library reference such as *BGS Library, Keyworth, shelf ref …*
   - **Licence / terms**, e.g. *public domain*, *CC BY 4.0*, or *written permission from ZGS, e-mail of 1 Oct 2026*
   - **Pages to process**, e.g. `1` or `3-5` (up to 5 at a time)
4. Tick **"I confirm we are allowed to use this document"**. GeoRevive refuses uploads without this.
5. Press **Upload and rescue**. After 5–20 seconds per page, the page opens with its enhancement steps and extracted facts.

**Option B: the data/inbox folder**

1. Copy the files into `data\inbox\` inside the GeoRevive folder.
2. Run `.\.venv\Scripts\python.exe -m georevive.ingest --source inbox` in PowerShell.
3. For each new file, the program asks for the same details (title, publisher, where from, licence, permission). It saves them next to the file as `<file>.source.yaml`. Files without details are listed as **Needs manual request** until the details are entered.

**What happens to a page**

The **original is kept unchanged** (read-only). The app then runs these steps, each saved as an image so the result can be reproduced:

1. **Stain reduction:** yellow and brown foxing is lifted toward the paper tone.
2. **Deskew:** the page is straightened.
3. **Denoise:** speckle is removed.
4. **Illumination correction:** uneven lighting and fading are flattened.
5. **Contrast (CLAHE):** local contrast is improved.
6. **Binarise:** a black-and-white version is made for OCR.

The bar above the image shows the **quality score**, the **evenness of lighting** and the **OCR confidence**, before → after.

## 4. Reviewing extracted facts (geologist)

Only facts that a geologist **approves or edits** enter the geodatabase and appear on the map.

1. Open **Review Queue** to see every fact waiting for review, or open a document from **Data Rescue**.
2. Click a fact in the right-hand list. Its box **lights up on the page** and the line of text around it appears below the image. You can also click a box on the page.
3. Read the fact card:
   - **Type**, e.g. Rock unit, Mineral occurrence, Assay, Coordinates, Mine / claim, Farm, Location description, Drill hole, Fault / shear
   - **Value** and units. Old units are converted, e.g. *12 dwt per ton ≈ 20.6 g/t (assumes short ton)*.
   - **Confidence**: green above 75%, amber 50–75%, red below 50%. It combines how specific the rule is with how sure the OCR was.
   - **Location**: green if stated in the text or matched exactly; **⚠ amber "Location uncertain"** if it was estimated (e.g. "15 miles north-east of Salisbury") or copied from a nearby fact on the same line.
4. Decide:
   - **Approve** if the value is right.
   - **Edit** if it is nearly right. Correct the value or units, and add a latitude and longitude if you know the place (this clears the uncertainty flag). Add a comment and press **Save edit**.
   - **Reject** if it is wrong (OCR error, wrong meaning).
5. Every decision is stored with your name, the time and the before/after values. It appears under the fact and in the audit log.

Tips: historical place names are understood (Salisbury → Harare, Gatooma → Kadoma, Que Que → Kwekwe, and so on). Old grades in **dwt** (pennyweights) and **oz** per ton are converted to g/t, assuming short tons (2000 lb). Edit the fact if the report used long tons.

## 5. Using the Map Explorer

1. Open **Map Explorer**.
2. Tick layers in the left panel. They are grouped as:
   - **Rescued facts** (approved facts from documents)
   - **Known occurrences** (USGS MRDS)
   - **Geology** and **Faults & structure**
   - **Sentinel-2 indicators**: iron oxide, clay/hydroxyl, ferrous iron, vegetation, true colour
   - **Terrain (DEM)**: elevation, slope, roughness
   - **Roads, places, rivers** (OpenStreetMap)
   - **Base map**: hillshade and district boundaries
3. The **legend** (bottom left) explains the colours of every visible layer. The **attribution bar** (bottom right) credits every visible layer's source.
4. **Click a feature** to see its attributes and its **source** (publisher, licence, date accessed, link). For satellite and terrain layers, click anywhere to read the value at that point.
5. For a **rescued fact**, click **Open the original scanned page** to go straight to the page, with the fact highlighted.
6. The base map is made from local data (hillshade and boundaries), so the map works **without internet**.

## 6. Running and interpreting the prospectivity model

1. Open **Prospectivity**.
2. Choose a method:
   - **Knowledge-driven (fuzzy logic)** is the default. It uses the geologist's weights and is not trained on known occurrences.
   - **Logistic regression**: learns from known gold occurrences, and its weights are easy to read.
   - **Gradient boosting + SHAP**: a non-linear comparison model.
3. Press **Run model for gold**. In a few seconds the heat map appears (yellow = lower, red = higher), with numbered markers for the **top 10 targets** (at least 1.5 km apart).
4. Click a target or its marker. The card says **why** it scored highly in plain words, e.g. *"0.4 km from a mapped fault or shear zone; greenstone host rock; iron-oxide index in the top 8% of the area. 3 known gold occurrences within 5 km (context only - not used in the score)."* The bars show which factors raised (ochre) or lowered (blue) the score.
5. Click anywhere on the map to explain that cell.
6. Open the **Validation** tab:
   - **AUC**: 0.5 means no better than chance, 1.0 is perfect.
   - **Top 10% / 20% area**: the share of known occurrences that fall inside the highest-scoring 10% or 20% of the area.
   - **Success-rate curve**: the further it rises above the dashed "random" line, the better.
   - **Limitations**: read them before using any target.
7. **Evidence & weights** tab (geologist): move the sliders, give a reason and press **Save weights**, then run the knowledge-driven model again. "Not available" lists evidence we could not build from the data obtained.

**Limits of the model:**

- The output is only as good as its inputs. If the 1:100k geology and faults are not available, the app uses coarse regional geology and automatic DEM lineaments, and says so in every explanation.
- Known occurrences (MRDS) are incomplete and partly mislocated.
- With few occurrences on one sheet, the data-driven models are a second opinion only.
- Satellite indices also react to soils and bare ground.
- **No target has been checked in the field.**

## 7. Producing a claim check report

1. Open **Claim Check** (or click **Claim check report here** on a target).
2. Give the claim a name.
3. Define the claim in one of three ways:
   - **Draw on map**: click each corner, then press **Finish** (**Undo** removes the last corner).
   - **Enter coordinates**: latitude and longitude of the centre, and the side of a square claim in metres. You can also click the map to set the centre.
   - **Paste corners**: one `latitude, longitude` per line.
4. Leave **Include technical appendix** ticked if a geologist will read the report.
5. Press **Generate PDF report**, then **Open the PDF report**.

The PDF covers:

- location, district and province
- the rocks under the claim, and what they mean for gold
- the nearest fault
- known occurrences within 5 km
- satellite indicators compared with the whole area
- the prospectivity score and **why**
- next steps (claim registration with the Provincial Mining Director, a geologist's visit, safety)
- data sources with licences
- a clear disclaimer
- in the appendix, feature contributions and model limits

Each download is watermarked with your name and the time.

## 8. The data room and the audit log

**Sharing (Admin)**

1. Open **Data Room**. Every dataset is listed with its source, licence and a licence check.
2. In **Shared with**, choose a user from **Share with…**.
3. If the licence is unclear or restricted (amber note), the app asks you to confirm. The confirmation is logged. Do not share data marked "licence to confirm" outside the team until the terms are confirmed.
4. Click **remove** to stop sharing.

**What the investor sees**

1. The investor signs in and opens **Data Room**. They see **only** the datasets shared with them.
2. **View on map** shows those datasets, and nothing else, on the map.
3. Each download is a zip containing the data, `WATERMARK.txt` (their name, organisation and time) and `LICENCE_AND_SOURCE.txt`. GeoJSON features carry a `_watermark` field, and images carry a visible watermark.

**Reading the audit log (Admin)**

1. Open **Audit Log**. Newest entries are at the top.
2. Each line shows **when**, **who** (and their role), the **action** (login, view, download, upload, approve, edit, reject, model_run, weights_edit, share, unshare, claim_report, reset, scenario) and **what** (the object).
3. Filter by action or user. Example: choose user *investor* and action *download* to see everything the investor took.
4. The **Data Room** page also lists recent data-room activity.

## 9. Requesting missing data

The Data Report (`reports/DATA_SOURCES.md`, and the Data Sources page) lists every source with status **Needs manual request** or **Needs credentials**, together with the contacts and steps. The usual cases are:

1. **BGS digital Harare 1:100k map (GeoPackage).** E-mail **BGS Enquiries (enquiries@bgs.ac.uk)** quoting *OR/26/047*, and ask the Zimbabwe Geological Survey (the map owner) for permission. State the non-commercial prototype purpose and ask for the licence terms in writing. Save the `.gpkg` into `data\inbox\bgs\` and run:
   `.\.venv\Scripts\python.exe -m georevive.ingest --source bgs_harare_map`
2. **BGS report OR/26/047 (PDF).** NORA forbids robot downloads. Download it once in a browser from <https://nora.nerc.ac.uk/id/eprint/541846/>, save it as `data\inbox\bgs\OR26047.pdf`, then run `--source bgs_or26047_report`.
3. **USGS MRDS.** The website forbids automated downloads. Open <https://mrdata.usgs.gov/mrds/> in a browser, click **mrds-csv.zip**, save it as `data\inbox\usgs\mrds-csv.zip`, then run `--source usgs_mrds`.
4. **USGS Africa mineral facilities.** ScienceBase blocks automated clients. Open <https://www.sciencebase.gov/catalog/item/607611a9d34e018b3201cbbf> in a browser, download the data `.zip` into `data\inbox\usgs\africa\`, then run `--source usgs_africa_minerals`.
5. **ASTER (NASA).** Create a free account at <https://urs.earthdata.nasa.gov/users/new>, add `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD` to `.env`, then run `--source aster`.
6. **ZGS bulletins, HathiTrust volumes, BGS geochemistry.** Follow the steps shown for each source.

After adding any file, run the matching `--source`, or `--all` to refresh everything. Check the Data Sources page: the status should change to **Downloaded**.

## 10. Presenter Mode

1. Press **Presenter** in the top bar. Text becomes larger and the step guide appears (bottom right).
2. Press **→** (or **Next step**) to move through the master path. The app switches to the right demo account and page for each step.
3. Press **←** to go back, **R** to reset to the clean state after ingestion, and **Esc** to minimise the guide.
4. If something fails live, press **Load complete** to jump to the finished end state.
5. See [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for the words to say.
