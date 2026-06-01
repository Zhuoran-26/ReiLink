import { mkdir } from "node:fs/promises";
import path from "node:path";

export type ShellOpenPath = {
  openPath: (target: string) => Promise<string>;
};

export type OpenLocalDataDirResult = {
  ok: boolean;
  path: string;
  error: string | null;
};

export async function openLocalDataDir(
  appUserDataPath: string,
  shell: ShellOpenPath
): Promise<OpenLocalDataDirResult> {
  const dataDir = path.join(appUserDataPath, "data");
  try {
    await mkdir(dataDir, { recursive: true });
    const error = await shell.openPath(dataDir);
    return {
      ok: error === "",
      path: dataDir,
      error: error || null
    };
  } catch (error) {
    return {
      ok: false,
      path: dataDir,
      error: error instanceof Error ? error.message : String(error)
    };
  }
}
