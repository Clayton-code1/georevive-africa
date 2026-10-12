# Extraction accuracy (rule-based, offline mode)

_Generated 2026-10-10 21:58 UTC by `python -m georevive.rescue.accuracy`._

> **Honest figure - held-out page(s) only (1 page, 15 labelled facts, first run, before any fix it prompted; never used to tune): precision 83%, recall 33%, F1 48%.** Quote this one, with the page count. The overall table below mixes in pages that were used to improve the rules, so it is optimistic.

**Overall on 4 labelled page(s), 65 labelled facts:** precision **100%**, recall **58%**, F1 **74%** (OCR engine: rapidocr).

| Fact type | Correct | Spurious | Missed | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| commodity | 13 | 0 | 4 | 100% | 76% | 87% |
| farm | 1 | 0 | 0 | 100% | 100% | 100% |
| lithology | 12 | 0 | 1 | 100% | 92% | 96% |
| mine | 10 | 0 | 22 | 100% | 31% | 48% |
| mineral | 2 | 0 | 0 | 100% | 100% | 100% |

## Important: these pages were also used to improve the rules
Before any rule changes, the first run on the same pages gave precision **96%**, recall **44%**, F1 **60%** (`reports/extraction_accuracy_baseline.json`). The misses showed generic gaps (lower-case 'mine', 'farm <Name>', lists of mine names, missing common rock and mineral words), which were then fixed. Because the same pages informed the fixes, the figure above is **optimistic**. The honest figure to quote is the baseline, until a fresh, held-out set of labelled pages (ideally ZGS bulletin pages) has been evaluated.

## How to read this honestly
- The test set is **small** (a handful of pages), so these numbers have wide uncertainty. Quote them as 'on our first labelled pages' and give the page count.
- Facts are compared as unique facts per page (a rock unit mentioned five times counts once). A fact counts as correct only if the type and the normalised value match a label (e.g. assay value and unit, mine name without 'Mine', canonical rock unit).
- **Precision** = share of extracted facts that are correct; **recall** = share of labelled facts that were found.
- Labels marked 'verified by geologist: no' were prepared by the build assistant from the page text and **must be checked by the Geoscience Lead** before the figure is used in the pitch.
- The pages are old public-domain publications; ZGS bulletins of the Harare sheet may behave differently (different typography, maps, tables).

## Pages

| Label file | Page | Source | Labelled by | Verified by geologist | Result |
|---|---|---|---|---|---|
| gmw_1902_p115.json | The Gold Mines of the World (1902), p.115 | internet_archive_scans | Claude (build assistant), read from the page image | no | 5 labels, 4 extracted |
| gmw_1902_p116.json | The Gold Mines of the World (1902), p.116 | internet_archive_scans | Claude (build assistant), read from the page image | no | 15 labels, 7 extracted |
| hall_1909_p76.json | Prehistoric Rhodesia (Hall, 1909), p.76 | internet_archive_scans | Claude (build assistant), read from the page image | no | 15 labels, 5 extracted |
| nature_1911_p512.json | Nature 87, p.512 (1911), review of 'The Mineral Industry of Rhodesia' | internet_archive_scans | Claude (build assistant), read from the page image | no | 30 labels, 22 extracted |

**gmw_1902_p115.json** - missed: commodity:arsenic; spurious: none

**gmw_1902_p116.json** - missed: mine:alice proprietary, mine:beatrice, mine:mozambique, mine:penhalonga, mine:premier tati monarch, mine:quagga, mine:sabi ophir, mine:vaughan williams; spurious: none

**hall_1909_p76.json** - missed: mine:alliance, mine:celtic, mine:early morn, mine:geelong, mine:hard times, mine:kameel, mine:minx, mine:oceolo, mine:susannah, mine:thornhill; spurious: none

**nature_1911_p512.json** - missed: commodity:bismuth, commodity:cobalt, commodity:nickel, lithology:alluvium, mine:alaska, mine:bwana m kubwe, mine:kansanshe, mine:umkondo; spurious: none
