# Model card: GeoRevive gold prospectivity (prototype)

_Regenerated automatically after each model run. Last update: 2026-10-12 05:43 UTC._

> **Prototype targets for discussion. All targets require field verification by a qualified geologist. Not investment advice.**

## Purpose
GeoRevive ranks 250 m grid cells in the pilot area (Harare 1:100 000 sheet (ZGS Bulletin 94) - provisional extent) by how favourable they look for **orogenic gold in
Archaean greenstone belts**. The ranking supports discussion and planning of field checks. It is **not** a resource
estimate and not investment advice.

## Users
Geologists and analysts (main users), small-scale miners (through the plain-language claim check report), and
investors (shared results only).

## Models
1. **Knowledge-driven (default): fuzzy logic.** Each evidence layer becomes a 0-1 *membership* using a simple,
   published-style rule (table below). The score is the weighted mean of the memberships. The weights come from the
   Geoscience Lead, who can edit them in the app; every change is logged. This model is **not trained on known occurrences**.
2. **Data-driven: logistic regression.** Trained on known gold occurrence cells (USGS MRDS) against random background
   cells kept at least 1 km away from any occurrence. Inputs are standardised, and the coefficients explain the model directly.
3. **Data-driven: gradient boosting with SHAP explanations.** A non-linear comparison model.

**Known occurrences are never an input feature.** They are used only as training labels (models 2 and 3) and to
validate all three models.

## Evidence layers and memberships
| Evidence | Membership rule | Default weight |
|---|---|---|
| Distance to faults / shear zones | Closer to a fault or shear zone is more favourable (half-way at 1.5 km). | 0.25 |
| Distance to granite-greenstone contact | Closer to a granite-greenstone contact is more favourable (half-way at 3 km). | 0.15 |
| Favourable host rock (greenstone, mafic-ultramafic, BIF) | Greenstone / mafic-ultramafic = 1.0, granite-gneiss = 0.35, other/cover = 0.1. | 0.25 |
| Sentinel-2 iron-oxide index (percentile) | Higher iron-oxide index (top 20%) is favourable. | 0.10 |
| Sentinel-2 clay / hydroxyl index (percentile) | Higher clay/hydroxyl index (top 20%) is favourable. | 0.10 |
| Sentinel-2 ferrous-iron index (percentile) | Higher ferrous-iron index is favourable. | 0.05 |
| Slope | Moderate slopes (2-15°) slightly favoured; flat cover or steep scarps less so. | 0.05 |
| Terrain roughness (TRI) | Rougher ground (outcrop) slightly favoured. | 0.05 |

## Validation method
- **Spatial block cross-validation** for the data-driven models: cells are grouped into square blocks
  (5 km), and whole blocks are held out together, so a model is never scored on cells next to its training
  cells. This avoids the over-optimistic results of random splits.
- **AUC** = the probability that a random known-occurrence cell scores higher than a random background cell
  (0.5 = no skill, 1.0 = perfect).
- **Success-rate curve** = the share of known occurrences that fall inside the top X% of the area. For the data-driven
  models it is computed out-of-fold.

## Latest run (run 1, fuzzy, 2026-10-12 05:43 UTC)

- Known gold occurrences in the pilot area: **0** (0 grid cells)
- AUC: not available
- Validation: Knowledge-driven model (not trained on occurrences): validated directly against all known occurrences.
- Evidence used: Favourable host rock (greenstone, mafic-ultramafic, BIF), Distance to granite-greenstone contact, Distance to faults / shear zones, Sentinel-2 iron-oxide index (percentile), Sentinel-2 clay / hydroxyl index (percentile), Sentinel-2 ferrous-iron index (percentile), Slope, Terrain roughness (TRI)

Run-specific limitations:
- Known occurrences (USGS MRDS) are historical compilations with approximate locations; many deposits are missing and absence of a record does not mean absence of gold.
- Background points are a random sample of the area, not confirmed barren ground.
- host_rock: From the 1:10 million CGMW-BRGM regional map (coarse) because the BGS 1:100k geology is not yet available.
- dist_fault: No mapped faults available: uses 57 automatically interpreted DEM lineaments (unverified - may include roads, rivers or artefacts).
- 10.1% of cells are built-up or water (ESA WorldCover) and are excluded from alteration indices and targets.

## Limitations (read these first)
- **Labels are incomplete and biased.** MRDS is a historical compilation (no systematic updates since 2011). Many
  workings are missing, locations can be off by hundreds of metres, and recorded sites cluster near roads and old
  mining centres. Background cells are not confirmed barren.
- **Few positives.** One map sheet holds few recorded gold sites, so the data-driven models can learn local accidents
  of the data. Treat them as a second opinion to the knowledge-driven model.
- **Input quality limits the output.** If the BGS/ZGS 1:100k geology and fault layers are not available, the app falls
  back to a 1:10 million regional map and automatically interpreted DEM lineaments. Both are far too coarse for
  target-scale decisions, and the app says so in every explanation.
- **Satellite band ratios are indirect.** Iron-oxide and clay indices respond to soils, laterite, bare ground and
  burnt areas as well as to hydrothermal alteration. Cloud, water and dense vegetation are masked out.
- **Spatial autocorrelation.** Even with block cross-validation, the metrics describe this area and these labels.
  They do not transfer elsewhere.
- **Not field-verified.** No target has been checked on the ground.

## Ethical and safety considerations
- Results can influence where people dig. Claim reports therefore state in plain language that the score is a hint,
  not proof. They tell users to check claim status with the Provincial Mining Director and to get a geologist's
  site visit, and they warn against entering old workings.
- Explanations are shown for every target, so users can see *why* a cell scored high and challenge it.

## How to reproduce
```powershell
.\.venv\Scripts\python.exe -m georevive.ingest --all
# then in the app: Prospectivity > choose a method > Run model for gold
```
Every run stores its weights, its evidence-layer lineage, its metrics and a score GeoTIFF
(`data/processed/prospect/run_<id>.tif`).
