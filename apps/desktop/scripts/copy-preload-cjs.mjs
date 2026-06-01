#!/usr/bin/env node
import { copyFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const desktopRoot = path.resolve(__dirname, "..");
const outputDir = path.join(desktopRoot, "dist-electron", "main");

await mkdir(outputDir, { recursive: true });
await copyFile(path.join(desktopRoot, "src", "main", "preload.cjs"), path.join(outputDir, "preload.cjs"));
