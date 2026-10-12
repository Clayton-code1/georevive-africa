# GeoRevive Africa: Security and Data Governance

This document has two parts. The first describes how the prototype protects data today. The second sets out what a production deployment must add to align with Zimbabwe's **Cyber and Data Protection Act [Chapter 12:07]** (2021). Points marked *(confirm with counsel)* are our understanding of the law. A qualified Zimbabwean data-protection lawyer must check them before going live.

## 1. What data GeoRevive holds

| Category | Examples | Personal data? | Sensitivity |
|---|---|---|---|
| Open geoscience data | USGS MRDS, Sentinel-2, Copernicus DEM, OpenStreetMap, geoBoundaries | No | Public; licences require attribution |
| Rescued records | Scans of bulletins and reports; facts extracted from them | Rarely (old reports may name prospectors or farm owners) | Varies; some documents are under copyright or permission terms |
| Restricted datasets | BGS/ZGS 1:100k map (when supplied), survey data under permission | No | Use only within the agreed terms |
| Derived products | Prospectivity scores, targets, claim reports | No, but claim polygons can reveal a person's or company's business interest | Commercially sensitive |
| Platform users | Username, display name, organisation, role, hashed password | **Yes** | Personal data |
| Audit log | Who viewed, downloaded, approved or ran what, and when | **Yes** (links actions to people) | Personal data, security record |

## 2. Controls in the prototype

- **Roles and least privilege.** There are five roles: Admin, Geologist, Analyst, Investor and Miner. A single permission matrix (`backend/georevive/security.py`) drives the API, the UI and the tests. An investor sees only the datasets shared with them. A miner can only create claim reports, and their map shows only base and context layers.
- **Authentication.** Passwords are hashed with Argon2. Sessions use signed tokens (JWT, HS256) that expire after 12 hours. The signing key lives only in `.env`.
- **One-click demo sign-in** (`security.demo_quick_login` in `config.yaml`) is accepted only from the local machine (127.0.0.1). It **must be set to `false`** on any shared or production server.
- **Secrets.** API keys, the Earthdata login, the signing key and the demo passwords live in `.env` only. That file is excluded from version control (`.gitignore`), and `setup.ps1` generates random values.
- **Audit trail.** Every sign-in, view, download, upload, fact approval, edit and rejection, weight change, model run, share, report and demo reset is written to the `audit_log` table. Fact edits also keep before/after values (`fact_reviews`). The Admin sees the log in the app.
- **Watermarked downloads.** Every data-room download is a zip containing `WATERMARK.txt` (user, organisation, UTC time) and a licence/source note. Each GeoJSON feature carries a `_watermark` property, CSVs carry a header line, GeoTIFFs carry a `WATERMARK` tag, and PNGs carry a visible watermark. Claim-report PDFs are stamped on every page.
- **Licence guard on sharing.** Sharing a dataset whose licence is unclear or restricted needs an explicit, logged acknowledgement.
- **Provenance.** Every dataset, file (SHA-256), layer, fact, model run and report records where it came from (the Source Registry and its lineage).
- **Original documents are never modified.** Uploaded originals are stored read-only, and enhancement steps are saved separately.
- **Local by default.** The API listens on 127.0.0.1 only. Once ingestion has run, nothing is sent to external services. The optional LLM extraction mode, which is off by default, would send page text to the Anthropic API.

## 3. Production requirements under the Cyber and Data Protection Act [Chapter 12:07]

1. **Data controller registration.** Register GeoRevive (or the operating company) as a data controller with the Data Protection Authority (POTRAZ) before processing personal data in production *(confirm with counsel)*.
2. **Data Protection Officer.** Appoint a DPO and publish a contact point for data subjects *(confirm with counsel)*.
3. **Lawful basis and purpose limitation.** Process user data only to run the service (accounts, access control, audit). Do not reuse claim polygons or download logs for other purposes without consent.
4. **Data minimisation.** Collect only name, organisation, role and e-mail. Do not store national ID numbers. Redact personal names in rescued documents unless they are needed and lawful to keep.
5. **Data subject rights.** Provide access, correction and deletion of user accounts. Note that audit records may need to be kept for security and legal reasons.
6. **Cross-border transfers and data sovereignty.** Host production data, especially personal data and permission-restricted survey data, **in Zimbabwe** or in a jurisdiction the Authority accepts as adequate. Avoid sending personal data to foreign cloud AI services. The LLM extraction mode stays off for restricted documents, and is used only with pages that hold no personal data *(confirm transfer rules with counsel)*.
7. **Security safeguards.** Use HTTPS/TLS, encrypt data at rest, require MFA for Admin and Geologist accounts, rotate the signing key, take regular encrypted backups, run vulnerability patching, and add rate limiting on sign-in.
8. **Breach notification.** Keep an incident response plan, and notify the Authority and affected users within the deadline the Act sets *(confirm current deadline with counsel)*.
9. **Contracts.** Put data-sharing agreements in place with the Zimbabwe Geological Survey, BGS and other providers. Data-room users accept terms of use that forbid redistribution.

## 4. Retention

| Data | Prototype | Proposed production policy |
|---|---|---|
| Raw open datasets | Kept in `data/raw/` with checksums | Keep while used; re-download to refresh |
| Uploaded scans | Kept (read-only) | Keep for the agreed term with the provider; delete on request |
| Extracted facts and reviews | Kept | Keep with lineage for as long as the source document is kept |
| User accounts | Demo accounts | Delete 12 months after an account closes |
| Audit log | Kept | Keep 24 months, then archive or delete *(confirm legal minimum)* |
| Claim reports | Kept in `reports/generated/` | User's own data: delete on request, otherwise after 24 months |
| Data-room downloads | Not stored (generated on demand) | Same |

## 5. Access matrix (from `security.py`)

| Permission | Admin | Geologist | Analyst | Investor | Miner |
|---|:-:|:-:|:-:|:-:|:-:|
| View Source Registry | ✓ | ✓ | ✓ | | |
| View all map layers | ✓ | ✓ | ✓ | shared only | base map only |
| Upload scans | ✓ | ✓ | ✓ | | |
| Review facts | ✓ | ✓ | | | |
| Run models | ✓ | ✓ | ✓ | | |
| Edit model weights | ✓ | ✓ | | | |
| Claim reports | ✓ | ✓ | ✓ | | ✓ |
| Data room: view/download | ✓ | ✓ | ✓ | shared only | |
| Data room: share | ✓ | | | | |
| Audit log | ✓ | | | | |
| Demo reset | ✓ | | | | |
