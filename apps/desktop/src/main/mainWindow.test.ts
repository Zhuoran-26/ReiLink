import { createMainWindowOptions, createPackagedRendererUrl, restoreMainWindowForActivation } from "./mainWindow";

describe("main window", () => {
  it("keeps the ReiLink main window as a normal desktop app window", () => {
    const options = createMainWindowOptions("/tmp/preload.cjs");

    expect(options.skipTaskbar).toBeUndefined();
    expect(options.focusable).toBeUndefined();
    expect(options.alwaysOnTop).toBeUndefined();
    expect(options.show).toBeUndefined();
    expect(options.transparent).toBeUndefined();
    expect(options.frame).toBeUndefined();
    expect(options.webPreferences).toMatchObject({
      contextIsolation: true,
      nodeIntegration: false,
      preload: "/tmp/preload.cjs"
    });
  });

  it("cache-busts packaged renderer URLs so overwritten local builds do not show stale tabs", () => {
    expect(createPackagedRendererUrl("session-archive-tab")).toBe(
      "app://./index.html?renderer_cache_key=session-archive-tab"
    );
  });

  it("restores minimized windows without forcing focus when the app is activated", () => {
    const window = {
      focus: vi.fn(),
      isDestroyed: vi.fn(() => false),
      isMinimized: vi.fn(() => true),
      isVisible: vi.fn(() => false),
      restore: vi.fn(),
      showInactive: vi.fn()
    };

    expect(restoreMainWindowForActivation(window)).toBe(true);

    expect(window.restore).toHaveBeenCalledOnce();
    expect(window.showInactive).not.toHaveBeenCalled();
    expect(window.focus).not.toHaveBeenCalled();
  });

  it("shows hidden windows inactively during activation", () => {
    const window = {
      focus: vi.fn(),
      isDestroyed: vi.fn(() => false),
      isMinimized: vi.fn(() => false),
      isVisible: vi.fn(() => false),
      restore: vi.fn(),
      showInactive: vi.fn()
    };

    expect(restoreMainWindowForActivation(window)).toBe(true);

    expect(window.restore).not.toHaveBeenCalled();
    expect(window.showInactive).toHaveBeenCalledOnce();
    expect(window.focus).not.toHaveBeenCalled();
  });

  it("leaves already visible windows alone during activation", () => {
    const window = {
      focus: vi.fn(),
      isDestroyed: vi.fn(() => false),
      isMinimized: vi.fn(() => false),
      isVisible: vi.fn(() => true),
      restore: vi.fn(),
      showInactive: vi.fn()
    };

    expect(restoreMainWindowForActivation(window)).toBe(true);

    expect(window.restore).not.toHaveBeenCalled();
    expect(window.showInactive).not.toHaveBeenCalled();
    expect(window.focus).not.toHaveBeenCalled();
  });

  it("does not touch destroyed windows during activation", () => {
    const window = {
      focus: vi.fn(),
      isDestroyed: vi.fn(() => true),
      isMinimized: vi.fn(() => true),
      isVisible: vi.fn(() => false),
      restore: vi.fn(),
      showInactive: vi.fn()
    };

    expect(restoreMainWindowForActivation(window)).toBe(false);

    expect(window.restore).not.toHaveBeenCalled();
    expect(window.showInactive).not.toHaveBeenCalled();
    expect(window.focus).not.toHaveBeenCalled();
  });
});
