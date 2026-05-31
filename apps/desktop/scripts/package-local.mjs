#!/usr/bin/env node
import { access, chmod, cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { constants } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const desktopRoot = path.resolve(__dirname, "..");
const platform = process.platform;
const arch = os.arch();
const appName = "ReiLink";
const releaseRoot = path.join(desktopRoot, "release");
const outputDir = path.join(releaseRoot, `${appName}-${platform}-${arch}`);
const outputApp = path.join(outputDir, `${appName}.app`);
const electronApp = path.join(desktopRoot, "node_modules", "electron", "dist", "Electron.app");
const rendererDist = path.join(desktopRoot, "dist");
const electronDist = path.join(desktopRoot, "dist-electron");

if (platform !== "darwin") {
  console.error("ReiLink local packaging v1 currently supports macOS only.");
  process.exit(1);
}

await requirePath(electronApp, "Electron runtime not found. Run `make install-desktop` first.");
await requirePath(path.join(rendererDist, "index.html"), "Renderer build not found. Run `npm run build` first.");
await requirePath(path.join(electronDist, "main.js"), "Electron main build not found. Run `npm run build` first.");

await rm(outputDir, { recursive: true, force: true });
await mkdir(outputDir, { recursive: true });
await cp(electronApp, outputApp, { recursive: true, dereference: true });

const resourcesApp = path.join(outputApp, "Contents", "Resources", "app");
await rm(resourcesApp, { recursive: true, force: true });
await mkdir(resourcesApp, { recursive: true });
await cp(rendererDist, path.join(resourcesApp, "dist"), { recursive: true });
await cp(electronDist, path.join(resourcesApp, "dist-electron"), { recursive: true });
await preparePackagedRendererIndex(path.join(resourcesApp, "dist", "index.html"));
await validateRendererIndex(path.join(resourcesApp, "dist", "index.html"));

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

const plistPath = path.join(outputApp, "Contents", "Info.plist");
let plist = await readFile(plistPath, "utf8");
plist = setPlistString(plist, "CFBundleName", appName);
plist = setPlistString(plist, "CFBundleDisplayName", appName);
plist = setPlistString(plist, "CFBundleIdentifier", "com.reilink.desktop");
await writeFile(plistPath, plist, "utf8");

await chmod(path.join(outputApp, "Contents", "MacOS", "Electron"), 0o755).catch(() => undefined);

console.log(`✅ ReiLink desktop app packaged: ${path.relative(process.cwd(), outputApp)}`);
console.log("Note: this is an unsigned local development build. Start the backend separately with `make dev-backend`.");

async function requirePath(target, message) {
  try {
    await access(target, constants.F_OK);
  } catch {
    console.error(message);
    process.exit(1);
  }
}

function setPlistString(plistText, key, value) {
  const pattern = new RegExp(`(<key>${key}</key>\\s*<string>)([^<]*)(</string>)`);
  if (!pattern.test(plistText)) {
    return plistText.replace("</dict>", `\t<key>${key}</key>\n\t<string>${value}</string>\n</dict>`);
  }
  return plistText.replace(pattern, `$1${value}$3`);
}

async function validateRendererIndex(indexPath) {
  await requirePath(indexPath, "Packaged renderer index.html is missing.");
  const html = await readFile(indexPath, "utf8");
  if (!html.includes("./assets/")) {
    console.error("Packaged renderer assets must use relative ./assets/ paths for file:// loading.");
    process.exit(1);
  }
  if (/src="\/assets\//.test(html) || /href="\/assets\//.test(html)) {
    console.error("Packaged renderer index.html still contains absolute /assets/ paths.");
    process.exit(1);
  }
  if (/\s+crossorigin(?:=(?:"[^"]*"|'[^']*'))?/.test(html)) {
    console.error("Packaged renderer index.html still contains crossorigin attributes.");
    process.exit(1);
  }
}

async function preparePackagedRendererIndex(indexPath) {
  const html = await readFile(indexPath, "utf8");
  await writeFile(indexPath, html.replace(/\s+crossorigin(?:=(?:"[^"]*"|'[^']*'))?/g, ""), "utf8");
}
