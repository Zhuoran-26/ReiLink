#!/usr/bin/env node
import { access, chmod, cp, mkdir, readFile, rename, rm, writeFile } from "node:fs/promises";
import { constants } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const desktopRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(desktopRoot, "..", "..");
const platform = process.platform;
const arch = os.arch();
const appName = "ReiLink";
const releaseRoot = path.join(desktopRoot, "release");
const outputDir = path.join(releaseRoot, `${appName}-${platform}-${arch}`);
const outputApp = path.join(outputDir, `${appName}.app`);
const electronApp = path.join(desktopRoot, "node_modules", "electron", "dist", "Electron.app");
const rendererDist = path.join(desktopRoot, "dist");
const electronDist = path.join(desktopRoot, "dist-electron");
const microphoneUsageDescription = "ReiLink 需要麦克风权限用于用户主动触发的语音输入测试。";

export async function packageLocal(options = {}) {
  const currentPlatform = options.platform ?? platform;
  if (currentPlatform !== "darwin") {
    throw new Error("ReiLink local packaging v1 currently supports macOS only.");
  }

  await requirePath(electronApp, "Electron runtime not found. Run `make install-desktop` first.");
  await requirePath(path.join(rendererDist, "index.html"), "Renderer build not found. Run `npm run build` first.");
  await requirePath(path.join(electronDist, "main.js"), "Electron main build not found. Run `npm run build` first.");

  await rm(outputDir, { recursive: true, force: true });
  await mkdir(outputDir, { recursive: true });
  await cp(electronApp, outputApp, { recursive: true, dereference: true });

  const resourcesRoot = path.join(outputApp, "Contents", "Resources");
  const resourcesApp = path.join(resourcesRoot, "app");
  await rm(resourcesApp, { recursive: true, force: true });
  await mkdir(resourcesApp, { recursive: true });
  await cp(rendererDist, path.join(resourcesApp, "dist"), { recursive: true });
  await cp(electronDist, path.join(resourcesApp, "dist-electron"), { recursive: true });
  await preparePackagedRendererIndex(path.join(resourcesApp, "dist", "index.html"));
  await validateRendererIndex(path.join(resourcesApp, "dist", "index.html"));
  await bundleStandaloneResources({ repoRoot, resourcesRoot });

  const sourcePackage = JSON.parse(await readFile(path.join(desktopRoot, "package.json"), "utf8"));
  const packagedPackage = {
    name: sourcePackage.name,
    productName: appName,
    version: sourcePackage.version,
    private: true,
    type: sourcePackage.type,
    main: sourcePackage.main
  };
  await writeFile(
    path.join(resourcesApp, "package.json"),
    `${JSON.stringify(packagedPackage, null, 2)}\n`,
    "utf8"
  );
  await requirePath(path.join(resourcesApp, packagedPackage.main), "Packaged Electron main entry is missing.");
  await requirePath(path.join(resourcesApp, "dist-electron", "main", "preload.cjs"), "Packaged Electron preload entry is missing.");

  const plistPath = path.join(outputApp, "Contents", "Info.plist");
  let plist = await readFile(plistPath, "utf8");
  plist = setPlistString(plist, "CFBundleName", appName);
  plist = setPlistString(plist, "CFBundleDisplayName", appName);
  plist = setPlistString(plist, "CFBundleExecutable", appName);
  plist = setPlistString(plist, "CFBundleIdentifier", "com.reilink.desktop");
  plist = removePlistKey(plist, "LSUIElement");
  plist = removePlistKey(plist, "LSBackgroundOnly");
  plist = setPlistString(plist, "NSMicrophoneUsageDescription", microphoneUsageDescription);
  plist = setPlistString(plist, "NSAudioCaptureUsageDescription", microphoneUsageDescription);
  await writeFile(plistPath, plist, "utf8");

  const macOSDir = path.join(outputApp, "Contents", "MacOS");
  const electronExecutable = path.join(macOSDir, "Electron");
  const reilinkExecutable = path.join(macOSDir, appName);
  await rename(electronExecutable, reilinkExecutable).catch(async (error) => {
    if (error?.code !== "ENOENT") throw error;
    await requirePath(reilinkExecutable, "Packaged ReiLink executable is missing.");
  });
  await chmod(reilinkExecutable, 0o755).catch(() => undefined);

  return {
    backendBinaryPath: path.join(resourcesRoot, "backend", backendBinaryNameForPlatform(currentPlatform)),
    knowledgeGamesPath: path.join(resourcesRoot, "knowledge", "games"),
    outputApp,
    runtimeResourcesPath: resourcesRoot
  };
}

export async function bundleStandaloneResources({ repoRoot: sourceRepoRoot, resourcesRoot, platform: targetPlatform = platform }) {
  const binaryName = backendBinaryNameForPlatform(targetPlatform);
  const backendBinarySource = path.join(sourceRepoRoot, "services", "backend", "dist", binaryName);
  const knowledgeGamesSource = path.join(sourceRepoRoot, "data", "knowledge", "games");
  const readOnlyResourceSources = [
    { name: "personas", source: path.join(sourceRepoRoot, "data", "personas") },
    { name: "persona", source: path.join(sourceRepoRoot, "data", "persona") },
    { name: "games", source: path.join(sourceRepoRoot, "data", "games") },
    { name: "elden_ring", source: path.join(sourceRepoRoot, "data", "elden_ring") }
  ];
  const backendResourcesDir = path.join(resourcesRoot, "backend");
  const backendBinaryDest = path.join(backendResourcesDir, binaryName);
  const knowledgeDest = path.join(resourcesRoot, "knowledge", "games");

  await requirePath(
    backendBinarySource,
    `Backend binary not found at ${backendBinarySource}. Run \`make package-backend\` before \`make package-desktop\`.`
  );
  await requirePath(
    path.join(knowledgeGamesSource, "catalog.json"),
    `Knowledge catalog not found at ${knowledgeGamesSource}.`
  );

  await rm(backendResourcesDir, { recursive: true, force: true });
  await mkdir(backendResourcesDir, { recursive: true });
  await cp(backendBinarySource, backendBinaryDest);
  await chmod(backendBinaryDest, 0o755);

  await rm(path.join(resourcesRoot, "knowledge"), { recursive: true, force: true });
  await mkdir(path.dirname(knowledgeDest), { recursive: true });
  await cp(knowledgeGamesSource, knowledgeDest, { recursive: true });

  for (const item of readOnlyResourceSources) {
    await requirePath(item.source, `Required runtime resource not found at ${item.source}.`);
    await rm(path.join(resourcesRoot, item.name), { recursive: true, force: true });
    await cp(item.source, path.join(resourcesRoot, item.name), { recursive: true });
  }

  await validateStandaloneResources({ resourcesRoot, platform: targetPlatform });
  return { backendBinaryPath: backendBinaryDest, knowledgeGamesPath: knowledgeDest, runtimeResourcesPath: resourcesRoot };
}

export async function validateStandaloneResources({ resourcesRoot, platform: targetPlatform = platform }) {
  const binaryName = backendBinaryNameForPlatform(targetPlatform);
  const requiredPaths = [
    path.join(resourcesRoot, "backend", binaryName),
    path.join(resourcesRoot, "knowledge", "games", "catalog.json"),
    path.join(resourcesRoot, "knowledge", "games", "elden_ring", "snippets.json"),
    path.join(resourcesRoot, "knowledge", "games", "hollow_knight", "snippets.json"),
    path.join(resourcesRoot, "personas", "rei_like.json"),
    path.join(resourcesRoot, "persona", "rei_minimal_prompt.json"),
    path.join(resourcesRoot, "games", "game_registry.json")
  ];
  for (const requiredPath of requiredPaths) {
    await requirePath(requiredPath, `Packaged standalone resource is missing: ${requiredPath}`);
  }

  const forbiddenPaths = [
    path.join(resourcesRoot, "backend", ".env"),
    path.join(resourcesRoot, ".env"),
    path.join(resourcesRoot, "knowledge", ".env"),
    path.join(resourcesRoot, "data", "memory"),
    path.join(resourcesRoot, "data", "session"),
    path.join(resourcesRoot, "memory"),
    path.join(resourcesRoot, "session")
  ];
  for (const forbiddenPath of forbiddenPaths) {
    if (await pathExists(forbiddenPath)) {
      throw new Error(`Forbidden local state was copied into the app bundle: ${forbiddenPath}`);
    }
  }
}

export async function requirePath(target, message) {
  try {
    await access(target, constants.F_OK);
  } catch {
    throw new Error(message);
  }
}

export function backendBinaryNameForPlatform(targetPlatform = platform) {
  return targetPlatform === "win32" ? "reilink-backend.exe" : "reilink-backend";
}

export function setPlistString(plistText, key, value) {
  const pattern = new RegExp(`(<key>${key}</key>\\s*<string>)([^<]*)(</string>)`);
  if (!pattern.test(plistText)) {
    return plistText.replace("</dict>", `\t<key>${key}</key>\n\t<string>${value}</string>\n</dict>`);
  }
  return plistText.replace(pattern, `$1${value}$3`);
}

export function removePlistKey(plistText, key) {
  return plistText.replace(
    new RegExp(`\\s*<key>${key}</key>\\s*(?:<(?:true|false)\\/>|<string>[^<]*</string>|<integer>[^<]*</integer>)`, "g"),
    ""
  );
}

async function validateRendererIndex(indexPath) {
  await requirePath(indexPath, "Packaged renderer index.html is missing.");
  const html = await readFile(indexPath, "utf8");
  if (!html.includes("./assets/")) {
    throw new Error("Packaged renderer assets must use relative ./assets/ paths for file:// loading.");
  }
  if (/src="\/assets\//.test(html) || /href="\/assets\//.test(html)) {
    throw new Error("Packaged renderer index.html still contains absolute /assets/ paths.");
  }
  if (/\s+crossorigin(?:=(?:"[^"]*"|'[^']*'))?/.test(html)) {
    throw new Error("Packaged renderer index.html still contains crossorigin attributes.");
  }
}

async function preparePackagedRendererIndex(indexPath) {
  const html = await readFile(indexPath, "utf8");
  await writeFile(indexPath, html.replace(/\s+crossorigin(?:=(?:"[^"]*"|'[^']*'))?/g, ""), "utf8");
}

async function pathExists(target) {
  try {
    await access(target, constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  packageLocal()
    .then(({ backendBinaryPath, knowledgeGamesPath, outputApp: packagedApp }) => {
      console.log(`✅ ReiLink desktop app packaged: ${path.relative(process.cwd(), packagedApp)}`);
      console.log("Note: this is an unsigned local development build.");
      console.log(`Bundled backend: ${path.relative(process.cwd(), backendBinaryPath)}`);
      console.log(`Bundled knowledge: ${path.relative(process.cwd(), knowledgeGamesPath)}`);
      console.log(`Bundled runtime resources: ${path.relative(process.cwd(), packagedApp)}/Contents/Resources`);
      console.log("Backend auto-start uses external, configured, bundled, then repo-local fallback.");
    })
    .catch((error) => {
      console.error(error instanceof Error ? error.message : String(error));
      process.exit(1);
    });
}
