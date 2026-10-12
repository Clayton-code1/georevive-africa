# GeoRevive Africa: 4-minute Demo Script

**Before the pitch (5 minutes, the night before is better)**

1. Run ingestion once with internet, then build the samples and the fallback scenario (see README §2).
2. Double-click `Start GeoRevive.bat`. On the projector (1366×768), set Edge zoom to 100% and press F11 for full screen.
3. Press **Presenter**, then **R** to reset to the clean state. Press **→** to start.
4. Turn Wi-Fi **off**. The demo runs offline.
5. If anything fails live, press **Load complete** in the presenter panel. It jumps to the finished state, so you can keep talking and clicking.

Presenter keys: **→** next step · **←** back · **R** reset · **Esc** minimise the guide.

**Know these before you present (current data state):**
- **Rescued facts reach the map only when they have a location.** Mine names are located automatically through the USGS MRDS gazetteer, which must be downloaded by hand first (see the Data Report). Until then, the geologist uses **Edit** on a fact and enters its coordinates from a reliable source. Never type invented coordinates.
- **No known occurrences are loaded until MRDS is downloaded,** so the Validation tab shows no AUC yet and the data-driven models will refuse to run (too few positives). The knowledge-driven model works now.
- Geology is the coarse 1:10M regional map, and faults are automatic DEM lineaments, until the BGS/ZGS 1:100k GeoPackage arrives. Every explanation says so.

---

| Time | Screen (presenter step) | Do | Say |
|---|---|---|---|
| 0:00 | Data Sources (1) | Point at the status boxes. Click one *Needs manual request* row. | "Africa's geological knowledge is locked in paper bulletins and maps. GeoRevive starts with honest data: every dataset here is open or published, with its licence, date and checksum. What we could not get is listed, with who to ask. Nothing is invented." |
| 0:30 | Data Rescue (2) | Click **Rescue this page** on *Prehistoric Rhodesia (1909) p.76* (the first sample: aged paper, gutter shadow). Toggle *Before / after*. Point at quality 92 → 97 and evenness 0.83 → 0.96. Takes about 20 s, so keep talking. | "This is a page from a historical publication: faded, stained, unevenly lit. We straighten it, remove stains, correct the lighting and read it. Every step is saved, so the result can be reproduced." |
| 1:15 | Same page (3) | Click a fact so it lights up on the page. **Approve** one, **Edit** one, **Reject** one. | "Each fact (rock unit, mine name, assay grade, location) has a confidence score and points to its exact place on the page. Old units like pennyweights per ton are converted. Only facts our geologist approves enter the database." |
| 1:45 | Map Explorer (4) | Tick geology, Sentinel-2 iron oxide and land cover. If a rescued fact is on the map, click it, then **Open the original scanned page** (see the note below). | "Rescued facts join free satellite data, terrain and known occurrences. Click anything: you see its source and licence, and one click takes you back to the original page." |
| 2:15 | Prospectivity (5) | **Run model for gold**. Click target 1 and read the explanation. Open **Validation**. | "Ten ranked targets, each with a reason a geologist can check: distance to structures, host rock, alteration. We show the validation honestly, with its limits. These are prototype targets for discussion: every one needs field verification." |
| 3:00 | Claim Check (6) | **Enter coordinates** (or click target 1's *Claim check report here*), then **Generate PDF report**, then open it. | "For a small-scale miner: a low-cost, plain-language report on their claim. Rocks, nearby gold, satellite hints, the score and why, the sources, and a clear disclaimer." |
| 3:30 | Data Room, admin (7) | **Share with…** the demo investor (prospectivity layer). The app asks you to confirm, because one input (the regional map) still has a licence "to confirm". Say so: that is the licence guard working. | "Explorers and investors get a secure data room." |
| 3:40 | Data Room, investor (8) | Show that only the shared dataset is listed. Download it and open `WATERMARK.txt`. | "The investor sees only what we share. Every download carries their name and the time." |
| 3:50 | Audit Log (9) | Point at the investor's view and download at the top. | "And every view, download, approval and model run is logged. GeoRevive: rescue the records, rank the targets, and show the evidence." |

---

## Likely judge questions and answers

**Is the data real?**
Yes. Every dataset is in the Source Registry with its URL, licence, access date and SHA-256 checksum, and the Data Sources page and `reports/DATA_SOURCES.md` show which ones we could not obtain. Synthetic data is used only inside automated tests, and the app never displays it.

**How accurate is the extraction?**
We measured precision and recall on hand-labelled pages from openly available documents (`docs/extraction-accuracy.md`). The test set is small, so we quote the page count with the figure. This is also why a geologist approves every fact before it is used.

**How good are the targets?**
We report AUC and a success-rate curve, using spatial block cross-validation for the data-driven models so the scores are not inflated by neighbouring cells. The known-occurrence database is incomplete and historical, and the pilot sheet has few recorded sites, so the targets are for discussion and field checking, not investment decisions. All of this is in `docs/model-card.md`.

**Why not just use a deep-learning model?**
Users need to trust and challenge the result. The default model is knowledge-driven, with weights our geologist can see and edit. The data-driven models are explained with coefficients or SHAP values, and every target comes with a plain-language reason.

**Do known occurrences leak into the model?**
No. They are never an input feature. They are used only as training labels and to validate the models, and the explanations mark them "context only".

**What about the BGS 1:100k map of Harare?**
BGS digitised it for the Zimbabwe Geological Survey in 2026 (report OR/26/047), but the GeoPackage is not publicly released, so we have requested it through the proper channel. The app is built to ingest it the moment we have permission. Until then it uses coarse regional geology and says so in every explanation.

**Who owns the data? Data sovereignty?**
Rescued data stays with its owners (e.g. ZGS), under their terms. Production hosting is planned in Zimbabwe, in line with the Cyber and Data Protection Act [Chapter 12:07]: access control, an audit trail and watermarking are already built in (`docs/security-and-data-governance.md`).

**How does it help small-scale miners?**
They get a low-cost claim check report in plain language, with safety advice and a pointer to proper registration. It turns public data they could not otherwise use into something actionable, with a clear warning that it is a desk study.

**Business model?**
Claim reports for small-scale miners at low cost. Data rescue and prospectivity services for explorers and survey agencies. Subscription data-room access for investors.

**What does it need to scale?**
Access to scanned archives (ZGS, BGS, university libraries), a labelled set to keep improving the extraction, the 1:100k digital geology across Zimbabwe's greenstone belts, and field partners to verify targets.

**Does it work without internet?**
Yes. After the first download, the whole demo runs on the laptop: local base map, cached layers, and offline OCR and extraction.
