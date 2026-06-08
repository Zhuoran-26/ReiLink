import path from "node:path";

import {
  createLocalFilePickerOptions,
  normalizeLocalFilePickerKind,
  selectLocalFile,
  type LocalFilePickerDialog
} from "./localFilePicker";

const dependencies = (overrides: Partial<Parameters<typeof selectLocalFile>[1]> = {}) => ({
  appUserDataPath: "/Users/aragoto/Library/Application Support/ReiLink",
  dialog: { showOpenDialog: vi.fn(async () => ({ canceled: true, filePaths: [] })) },
  homeDir: "/Users/aragoto",
  pathExists: vi.fn(async () => false),
  ...overrides
});

describe("local file picker", () => {
  it("accepts only whitelisted Local ASR file picker kinds", () => {
    expect(normalizeLocalFilePickerKind("asr_binary")).toBe("asr_binary");
    expect(normalizeLocalFilePickerKind("asr_model")).toBe("asr_model");
    expect(normalizeLocalFilePickerKind("asr_converter")).toBe("asr_converter");
    expect(() => normalizeLocalFilePickerKind("../../../.env")).toThrow("unsupported local file picker kind");
  });

  it("does not open the dialog for unsupported picker kinds", async () => {
    const dialog: LocalFilePickerDialog = { showOpenDialog: vi.fn() };

    await expect(selectLocalFile({ kind: "secret" }, dependencies({ dialog }))).rejects.toThrow(
      "unsupported local file picker kind"
    );

    expect(dialog.showOpenDialog).not.toHaveBeenCalled();
  });

  it("returns a canceled result without a selected path", async () => {
    const dialog = { showOpenDialog: vi.fn(async () => ({ canceled: true, filePaths: [] })) };

    await expect(selectLocalFile({ kind: "asr_binary" }, dependencies({ dialog }))).resolves.toEqual({
      canceled: true,
      path: null
    });
  });

  it("returns only the selected local file path", async () => {
    const dialog = { showOpenDialog: vi.fn(async () => ({ canceled: false, filePaths: ["/opt/homebrew/bin/whisper-cli"] })) };

    await expect(selectLocalFile({ kind: "asr_binary" }, dependencies({ dialog }))).resolves.toEqual({
      canceled: false,
      path: "/opt/homebrew/bin/whisper-cli"
    });
  });

  it("prefers the existing current path directory for defaultPath", async () => {
    const currentDir = "/Users/aragoto/tools";
    const pathExists = vi.fn(async (target: string) => target === currentDir);

    const options = await createLocalFilePickerOptions(
      { kind: "asr_converter", currentPath: path.join(currentDir, "ffmpeg") },
      dependencies({ pathExists })
    );

    expect(options.defaultPath).toBe(currentDir);
    expect(options.properties).toEqual(["openFile"]);
    expect(options.filters).toEqual([{ name: "All files", extensions: ["*"] }]);
  });

  it("uses a model-friendly defaultPath and filter when available", async () => {
    const modelDir = "/Users/aragoto/Library/Application Support/ReiLink/models";
    const pathExists = vi.fn(async (target: string) => target === modelDir);

    const options = await createLocalFilePickerOptions(
      { kind: "asr_model" },
      dependencies({ pathExists })
    );

    expect(options.defaultPath).toBe(modelDir);
    expect(options.filters).toEqual([
      { name: "Model files", extensions: ["bin"] },
      { name: "All files", extensions: ["*"] }
    ]);
  });
});
