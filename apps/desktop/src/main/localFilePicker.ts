import { access } from "node:fs/promises";
import path from "node:path";

export const LOCAL_FILE_PICKER_KINDS = ["asr_binary", "asr_model", "asr_converter"] as const;

export type LocalFilePickerKind = typeof LOCAL_FILE_PICKER_KINDS[number];

export type LocalFilePickerRequest = {
  kind?: unknown;
  currentPath?: unknown;
};

export type LocalFilePickerResult = {
  canceled: boolean;
  path: string | null;
};

type OpenDialogOptions = {
  title: string;
  properties: ["openFile"];
  defaultPath?: string;
  filters: Array<{ name: string; extensions: string[] }>;
};

export type LocalFilePickerDialog = {
  showOpenDialog: (options: OpenDialogOptions) => Promise<{ canceled: boolean; filePaths: string[] }>;
};

type LocalFilePickerDependencies = {
  appUserDataPath: string;
  dialog: LocalFilePickerDialog;
  homeDir: string;
  pathExists?: (target: string) => Promise<boolean>;
};

export const normalizeLocalFilePickerKind = (kind: unknown): LocalFilePickerKind => {
  if (LOCAL_FILE_PICKER_KINDS.includes(kind as LocalFilePickerKind)) return kind as LocalFilePickerKind;
  throw new Error("unsupported local file picker kind");
};

const defaultExists = async (target: string) => {
  try {
    await access(target);
    return true;
  } catch {
    return false;
  }
};

const expandHomePath = (target: string, homeDir: string) => {
  if (target === "~") return homeDir;
  if (target.startsWith("~/")) return path.join(homeDir, target.slice(2));
  return target;
};

const currentPathDefaultCandidate = (currentPath: unknown, homeDir: string) => {
  if (typeof currentPath !== "string") return null;
  const trimmed = currentPath.trim();
  if (!trimmed) return null;
  return path.dirname(expandHomePath(trimmed, homeDir));
};

const fallbackDefaultCandidates = (kind: LocalFilePickerKind, appUserDataPath: string) => {
  if (kind === "asr_model") return [path.join(appUserDataPath, "models")];
  return ["/opt/homebrew/bin", "/usr/local/bin"];
};

export const localFilePickerFilters = (kind: LocalFilePickerKind) =>
  kind === "asr_model"
    ? [
        { name: "Model files", extensions: ["bin"] },
        { name: "All files", extensions: ["*"] }
      ]
    : [{ name: "All files", extensions: ["*"] }];

const localFilePickerTitle = (kind: LocalFilePickerKind) => {
  if (kind === "asr_model") return "选择本地 ASR 模型文件";
  if (kind === "asr_converter") return "选择音频转换工具";
  return "选择本地 ASR 识别程序";
};

const existingDefaultPath = async (
  candidates: string[],
  pathExists: (target: string) => Promise<boolean>
) => {
  for (const candidate of candidates) {
    if (await pathExists(candidate)) return candidate;
  }
  return undefined;
};

export const createLocalFilePickerOptions = async (
  request: LocalFilePickerRequest,
  dependencies: Omit<LocalFilePickerDependencies, "dialog">
): Promise<OpenDialogOptions> => {
  const kind = normalizeLocalFilePickerKind(request.kind);
  const pathExists = dependencies.pathExists ?? defaultExists;
  const candidates = [
    currentPathDefaultCandidate(request.currentPath, dependencies.homeDir),
    ...fallbackDefaultCandidates(kind, dependencies.appUserDataPath)
  ].filter((candidate): candidate is string => Boolean(candidate));
  const defaultPath = await existingDefaultPath(candidates, pathExists);

  return {
    title: localFilePickerTitle(kind),
    properties: ["openFile"],
    defaultPath,
    filters: localFilePickerFilters(kind)
  };
};

export const selectLocalFile = async (
  request: LocalFilePickerRequest,
  dependencies: LocalFilePickerDependencies
): Promise<LocalFilePickerResult> => {
  const options = await createLocalFilePickerOptions(request, dependencies);
  const result = await dependencies.dialog.showOpenDialog(options);
  const selectedPath = result.filePaths[0];
  if (result.canceled || !selectedPath) {
    return { canceled: true, path: null };
  }
  return { canceled: false, path: selectedPath };
};
