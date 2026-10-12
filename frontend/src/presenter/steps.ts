export interface PresenterStep {
  title: string;
  path: string;
  role: string;
  minutes: string;
  do: string[];
  say: string;
}

// The 4-minute master demonstration path (see DEMO_SCRIPT.md for the full script).
export const STEPS: PresenterStep[] = [
  {
    title: "1 · Data Sources",
    path: "/sources",
    role: "admin",
    minutes: "0:00-0:30",
    do: ["Point at the status counts.", "Click a 'Needs manual request' row to show how to obtain it."],
    say: "Everything here is real, open or published data. Each dataset has its licence, access date, checksums and status. Nothing is invented: what we could not get is listed with who to ask.",
  },
  {
    title: "2 · Data rescue: upload and enhance",
    path: "/rescue",
    role: "geologist",
    minutes: "0:30-1:15",
    do: ["Click 'Rescue this page' on the sample (or upload a scan).", "Show Before / after; point at the quality and OCR-confidence scores."],
    say: "This is a page from a historical publication. We remove stains, straighten it, correct the uneven lighting and read it - every step is saved so the result can be reproduced.",
  },
  {
    title: "3 · Review extracted facts",
    path: "",
    role: "geologist",
    minutes: "1:15-1:45",
    do: ["Click a fact: its location lights up on the page.", "Approve one, edit one, reject one."],
    say: "Each fact has a confidence score and links back to its exact place on the page. Only facts our geologist approves enter the geodatabase.",
  },
  {
    title: "4 · Map explorer",
    path: "/map?layer=rescued_facts",
    role: "geologist",
    minutes: "1:45-2:15",
    do: ["Toggle geology, occurrences and the Sentinel-2 iron-oxide layer.", "Click a rescued fact: open its original page."],
    say: "Rescued facts sit with satellite indicators, terrain and known occurrences. Every feature shows its source and licence - one click back to the original.",
  },
  {
    title: "5 · Prospectivity",
    path: "/prospectivity",
    role: "geologist",
    minutes: "2:15-3:00",
    do: ["Press 'Run model for gold'.", "Click target 1: read the explanation.", "Open the Validation tab."],
    say: "Each target says why it scored: distance to structures, host rock, alteration. We show honest validation and its limits. These are prototype targets for discussion and need field checks.",
  },
  {
    title: "6 · Claim check report",
    path: "/claims",
    role: "miner",
    minutes: "3:00-3:30",
    do: ["Enter coordinates or draw a claim.", "Generate the PDF and open it."],
    say: "A small-scale miner gets a plain-language report: where the claim is, the rocks, nearby gold, satellite hints, the score and its explanation - with sources and a clear disclaimer.",
  },
  {
    title: "7 · Secure data room (admin)",
    path: "/dataroom",
    role: "admin",
    minutes: "3:30-3:40",
    do: ["Share the prospectivity layer with the demo investor."],
    say: "Explorers and investors get access control.",
  },
  {
    title: "8 · Data room as the investor",
    path: "/dataroom",
    role: "investor",
    minutes: "3:40-3:50",
    do: ["The investor sees only shared datasets.", "Download one - it is watermarked."],
    say: "They see only what we share, and every download carries their name and the time.",
  },
  {
    title: "9 · Audit trail",
    path: "/audit",
    role: "admin",
    minutes: "3:50-4:00",
    do: ["Show the investor's view and download at the top of the log."],
    say: "Every view, download, approval and model run is logged: who, what and when.",
  },
];
