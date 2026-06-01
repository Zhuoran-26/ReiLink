import { access, mkdtemp, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import { openLocalDataDir } from "./localData";

describe("openLocalDataDir", () => {
  it("creates and opens only the ReiLink data directory", async () => {
    const appUserDataPath = await mkdtemp(path.join(os.tmpdir(), "reilink-user-data-"));
    const openPath = vi.fn(async () => "");

    const result = await openLocalDataDir(appUserDataPath, { openPath });

    const expectedDataDir = path.join(appUserDataPath, "data");
    expect(result).toEqual({ ok: true, path: expectedDataDir, error: null });
    expect(openPath).toHaveBeenCalledWith(expectedDataDir);
    expect(openPath).not.toHaveBeenCalledWith(expect.stringContaining(".env"));
    await expect(access(expectedDataDir)).resolves.toBeUndefined();
  });

  it("does not open sensitive files even when they exist beside local data", async () => {
    const appUserDataPath = await mkdtemp(path.join(os.tmpdir(), "reilink-user-data-"));
    await writeFile(path.join(appUserDataPath, ".env"), "DEEPSEEK_API_KEY=secret\n", "utf8");
    const openPath = vi.fn(async () => "");

    await openLocalDataDir(appUserDataPath, { openPath });

    expect(openPath).toHaveBeenCalledTimes(1);
    expect(openPath.mock.calls[0][0]).toBe(path.join(appUserDataPath, "data"));
  });

  it("returns a clear error when the system file manager cannot open the directory", async () => {
    const appUserDataPath = await mkdtemp(path.join(os.tmpdir(), "reilink-user-data-"));
    const openPath = vi.fn(async () => "Finder is unavailable");

    const result = await openLocalDataDir(appUserDataPath, { openPath });

    expect(result.ok).toBe(false);
    expect(result.path).toBe(path.join(appUserDataPath, "data"));
    expect(result.error).toBe("Finder is unavailable");
  });
});
