type OverlayLocation = Pick<Location, "hash" | "href" | "search">;

const OVERLAY_HASH = "overlay";

export const isOverlayRendererLocation = (location: OverlayLocation) => {
  const searchParams = new URLSearchParams(location.search);
  if (searchParams.get("overlay") === "1") return true;

  const normalizedHash = location.hash.replace(/^#\/?/, "");
  if (normalizedHash === OVERLAY_HASH) return true;

  try {
    const parsed = new URL(location.href);
    return parsed.searchParams.get("overlay") === "1" || parsed.hash.replace(/^#\/?/, "") === OVERLAY_HASH;
  } catch {
    return false;
  }
};
