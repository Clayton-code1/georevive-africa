import { describe, expect, it } from "vitest";
import { STATUS_STYLES } from "./components/ui";
import { NAV, navFor } from "./nav";
import { STEPS } from "./presenter/steps";

describe("navigation", () => {
  it("maps paths to their nav item", () => {
    expect(navFor("/")?.label).toBe("Overview");
    expect(navFor("/rescue/doc_123")?.label).toBe("Data Rescue");
    expect(navFor("/map")?.label).toBe("Map Explorer");
  });

  it("has a page for every master-path step", () => {
    const paths = new Set(NAV.map((n) => n.path));
    for (const s of STEPS) {
      const base = s.path.split("?")[0];
      if (base) expect(paths.has(base)).toBe(true);
    }
  });
});

describe("source statuses", () => {
  it("explains every registry status", () => {
    for (const s of ["downloaded", "partial", "failed", "needs_manual_request", "needs_credentials"]) {
      expect(STATUS_STYLES[s].help.length).toBeGreaterThan(10);
    }
  });
});
