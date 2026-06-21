import { chmod, mkdir, mkdtemp, readdir, stat, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

type PackageLocalModule = {
  bundleStandaloneResources: (options: {
    repoRoot: string;
    resourcesRoot: string;
    platform?: string;
  }) => Promise<{ backendBinaryPath: string; knowledgeGamesPath: string; runtimeResourcesPath: string }>;
  validateStandaloneResources: (options: { resourcesRoot: string; platform?: string }) => Promise<void>;
  setPlistString: (plistText: string, key: string, value: string) => string;
  removePlistKey: (plistText: string, key: string) => string;
};

const loadPackageLocal = async () =>
  (await import(pathToFileURL(path.join(process.cwd(), "scripts", "package-local.mjs")).href)) as PackageLocalModule;

const createPackageSourceRepo = async (withBackendBinary = true) => {
  const repoRoot = await mkdtemp(path.join(os.tmpdir(), "reilink-package-src-"));
  const backendBinary = path.join(repoRoot, "services", "backend", "dist", "reilink-backend");
  const gamesDir = path.join(repoRoot, "data", "knowledge", "games");
  await mkdir(path.join(repoRoot, "data", "personas"), { recursive: true });
  await mkdir(path.join(repoRoot, "personas", "rei"), { recursive: true });
  await mkdir(path.join(repoRoot, "data", "persona"), { recursive: true });
  await mkdir(path.join(repoRoot, "data", "games"), { recursive: true });
  await mkdir(path.join(repoRoot, "data", "elden_ring"), { recursive: true });
  await mkdir(path.dirname(backendBinary), { recursive: true });
  await mkdir(path.join(gamesDir, "elden_ring"), { recursive: true });
  await mkdir(path.join(gamesDir, "hollow_knight"), { recursive: true });
  await writeFile(path.join(repoRoot, "data", "personas", "rei_like.json"), "{}\n", "utf8");
  await writeFile(
    path.join(repoRoot, "personas", "rei", "version.json"),
    JSON.stringify(
      {
        id: "rei",
        name: "Rei",
        version: "1.0.0",
        language: "zh-CN",
        description: "test persona pack",
        created_for: "ReiLink",
        original_character: true
      },
      null,
      2
    ) + "\n",
    "utf8"
  );
  await writeFile(path.join(repoRoot, "personas", "rei", "persona.md"), "# Persona\n\nTest Rei persona.\n", "utf8");
  await writeFile(
    path.join(repoRoot, "personas", "rei", "style_calibration.md"),
    "# 风格校准\n\n- 话多程度：1/5。\n",
    "utf8"
  );
  await writeFile(
    path.join(repoRoot, "personas", "rei", "response_patterns.md"),
    "# 回复模式\n\n- 玩家死亡多次：先承接，再给一个小建议。\n",
    "utf8"
  );
  await writeFile(path.join(repoRoot, "data", "persona", "rei_minimal_prompt.json"), "{}\n", "utf8");
  await writeFile(path.join(repoRoot, "data", "persona", "rei_golden_style.json"), "{}\n", "utf8");
  await writeFile(path.join(repoRoot, "data", "persona", "rei_style_examples.json"), "[]\n", "utf8");
  await writeFile(path.join(repoRoot, "data", "games", "game_registry.json"), "{}\n", "utf8");
  await writeFile(path.join(repoRoot, "data", "elden_ring", "bosses.json"), "[]\n", "utf8");
  await writeFile(path.join(gamesDir, "catalog.json"), "{\"games\":[]}\n", "utf8");
  await writeFile(path.join(gamesDir, "elden_ring", "manifest.json"), "{}\n", "utf8");
  await writeFile(path.join(gamesDir, "elden_ring", "snippets.json"), "[]\n", "utf8");
  await writeFile(path.join(gamesDir, "hollow_knight", "manifest.json"), "{}\n", "utf8");
  await writeFile(path.join(gamesDir, "hollow_knight", "snippets.json"), "[]\n", "utf8");
  await writeFile(path.join(repoRoot, "services", "backend", ".env"), "DEEPSEEK_API_KEY=secret\n", "utf8");
  await mkdir(path.join(repoRoot, "data", "memory"), { recursive: true });
  await mkdir(path.join(repoRoot, "data", "session"), { recursive: true });
  await writeFile(path.join(repoRoot, "data", "memory", "user_profile.json"), "{}\n", "utf8");
  await writeFile(path.join(repoRoot, "data", "session", "game_session_state.json"), "{}\n", "utf8");
  if (withBackendBinary) {
    await writeFile(backendBinary, "#!/bin/sh\n", "utf8");
    await chmod(backendBinary, 0o755);
  }
  return { backendBinary, gamesDir, repoRoot };
};

describe("package-local standalone resources", () => {
  it("bundles backend binary and read-only knowledge without local secrets or state", async () => {
    const { bundleStandaloneResources, validateStandaloneResources } = await loadPackageLocal();
    const { repoRoot } = await createPackageSourceRepo();
    const resourcesRoot = await mkdtemp(path.join(os.tmpdir(), "reilink-resources-"));

    const result = await bundleStandaloneResources({ repoRoot, resourcesRoot, platform: "darwin" });

    expect(result.backendBinaryPath).toBe(path.join(resourcesRoot, "backend", "reilink-backend"));
    expect(result.knowledgeGamesPath).toBe(path.join(resourcesRoot, "knowledge", "games"));
    expect(result.runtimeResourcesPath).toBe(resourcesRoot);
    expect((await stat(result.backendBinaryPath)).mode & 0o111).toBeTruthy();
    await expect(stat(path.join(resourcesRoot, "knowledge", "games", "catalog.json"))).resolves.toBeTruthy();
    await expect(stat(path.join(resourcesRoot, "knowledge", "games", "elden_ring", "snippets.json"))).resolves.toBeTruthy();
    await expect(stat(path.join(resourcesRoot, "knowledge", "games", "hollow_knight", "snippets.json"))).resolves.toBeTruthy();
    await expect(stat(path.join(resourcesRoot, "personas", "rei_like.json"))).resolves.toBeTruthy();
    await expect(stat(path.join(resourcesRoot, "personas", "rei", "version.json"))).resolves.toBeTruthy();
    await expect(stat(path.join(resourcesRoot, "personas", "rei", "persona.md"))).resolves.toBeTruthy();
    await expect(stat(path.join(resourcesRoot, "personas", "rei", "style_calibration.md"))).resolves.toBeTruthy();
    await expect(stat(path.join(resourcesRoot, "personas", "rei", "response_patterns.md"))).resolves.toBeTruthy();
    await expect(stat(path.join(resourcesRoot, "persona", "rei_minimal_prompt.json"))).resolves.toBeTruthy();
    await expect(stat(path.join(resourcesRoot, "persona", "rei_golden_style.json"))).resolves.toBeTruthy();
    await expect(stat(path.join(resourcesRoot, "persona", "rei_style_examples.json"))).resolves.toBeTruthy();
    await expect(stat(path.join(resourcesRoot, "games", "game_registry.json"))).resolves.toBeTruthy();
    await expect(stat(path.join(resourcesRoot, "backend", ".env"))).rejects.toThrow();
    await expect(stat(path.join(resourcesRoot, ".env"))).rejects.toThrow();
    await expect(stat(path.join(resourcesRoot, "data", "memory"))).rejects.toThrow();
    await expect(stat(path.join(resourcesRoot, "data", "session"))).rejects.toThrow();
    expect(await readdir(path.join(resourcesRoot, "knowledge", "games"))).toEqual(
      expect.arrayContaining(["catalog.json", "elden_ring", "hollow_knight"])
    );
    await expect(validateStandaloneResources({ resourcesRoot, platform: "darwin" })).resolves.toBeUndefined();
  });

  it("fails clearly when backend binary is missing", async () => {
    const { bundleStandaloneResources } = await loadPackageLocal();
    const { repoRoot } = await createPackageSourceRepo(false);
    const resourcesRoot = await mkdtemp(path.join(os.tmpdir(), "reilink-resources-"));

    await expect(bundleStandaloneResources({ repoRoot, resourcesRoot, platform: "darwin" })).rejects.toThrow(
      "Run `make package-backend` before `make package-desktop`"
    );
  });

  it("validates required bundled resources", async () => {
    const { validateStandaloneResources } = await loadPackageLocal();
    const resourcesRoot = await mkdtemp(path.join(os.tmpdir(), "reilink-resources-"));
    await mkdir(path.join(resourcesRoot, "backend"), { recursive: true });
    await writeFile(path.join(resourcesRoot, "backend", "reilink-backend"), "", "utf8");

    await expect(validateStandaloneResources({ resourcesRoot, platform: "darwin" })).rejects.toThrow(
      "Packaged standalone resource is missing"
    );
  });

  it("adds Chinese audio permission descriptions to packaged app metadata", async () => {
    const { setPlistString } = await loadPackageLocal();
    const plist = "<plist><dict></dict></plist>";

    const microphoneResult = setPlistString(
      plist,
      "NSMicrophoneUsageDescription",
      "ReiLink 需要麦克风权限用于用户主动触发的语音输入测试。"
    );
    const audioCaptureResult = setPlistString(
      plist,
      "NSAudioCaptureUsageDescription",
      "ReiLink 需要麦克风权限用于用户主动触发的语音输入测试。"
    );

    expect(microphoneResult).toContain("<key>NSMicrophoneUsageDescription</key>");
    expect(microphoneResult).toContain("用户主动触发的语音输入测试");
    expect(audioCaptureResult).toContain("<key>NSAudioCaptureUsageDescription</key>");
    expect(audioCaptureResult).toContain("用户主动触发的语音输入测试");
  });

  it("keeps packaged ReiLink visible in Dock and the macOS app switcher", async () => {
    const { removePlistKey, setPlistString } = await loadPackageLocal();
    const plist = [
      "<plist><dict>",
      "<key>CFBundleExecutable</key>",
      "<string>Electron</string>",
      "<key>LSUIElement</key>",
      "<true/>",
      "<key>LSBackgroundOnly</key>",
      "<false/>",
      "</dict></plist>"
    ].join("");

    const result = removePlistKey(
      removePlistKey(setPlistString(plist, "CFBundleExecutable", "ReiLink"), "LSUIElement"),
      "LSBackgroundOnly"
    );

    expect(result).toContain("<key>CFBundleExecutable</key>");
    expect(result).toContain("<string>ReiLink</string>");
    expect(result).not.toContain("LSUIElement");
    expect(result).not.toContain("LSBackgroundOnly");
  });
});
