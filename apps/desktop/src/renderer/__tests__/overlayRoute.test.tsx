import { describe, expect, it } from "vitest";

import { isOverlayRendererLocation } from "../overlayRoute";

const locationFor = (href: string) => {
  const url = new URL(href);
  return {
    hash: url.hash,
    href: url.href,
    search: url.search
  };
};

describe("overlay renderer route", () => {
  it("recognizes query and hash overlay renderer markers", () => {
    expect(isOverlayRendererLocation(locationFor("http://127.0.0.1:5173/?overlay=1"))).toBe(true);
    expect(isOverlayRendererLocation(locationFor("http://127.0.0.1:5173/#overlay"))).toBe(true);
    expect(isOverlayRendererLocation(locationFor("app://./index.html?overlay=1#overlay"))).toBe(true);
  });

  it("does not classify the main ReiLink renderer as overlay", () => {
    expect(isOverlayRendererLocation(locationFor("http://127.0.0.1:5173/"))).toBe(false);
    expect(isOverlayRendererLocation(locationFor("app://./index.html"))).toBe(false);
  });
});
