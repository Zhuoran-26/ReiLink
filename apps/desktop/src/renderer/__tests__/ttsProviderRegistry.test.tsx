import { describe, expect, it } from "vitest";

import {
  buildTtsProviderRegistry,
  getEnabledTtsProviders,
  getSelectableTtsProviders,
  resolveTtsProvider,
  SYSTEM_TTS_PROVIDER_ID
} from "../ttsProviderRegistry";

describe("ttsProviderRegistry", () => {
  it("returns System Speech Synthesis as the current provider", () => {
    const registry = buildTtsProviderRegistry(true);
    const systemProvider = registry.find((provider) => provider.id === SYSTEM_TTS_PROVIDER_ID);

    expect(systemProvider).toMatchObject({
      id: "system_speech_synthesis",
      label: "System Speech Synthesis",
      status: "available",
      enabled: true,
      selectable: true,
      privacySummary: expect.stringContaining("ReiLink 不接外部 TTS API")
    });
    expect(systemProvider?.capability).toMatchObject({
      streaming: false,
      customVoice: false,
      localOnly: true,
      requiresNetwork: false,
      requiresApiKey: false,
      supportsInterrupt: true
    });
  });

  it("keeps only the system provider enabled and selectable", () => {
    const registry = buildTtsProviderRegistry(true);

    expect(getEnabledTtsProviders(registry).map((provider) => provider.id)).toEqual(["system_speech_synthesis"]);
    expect(getSelectableTtsProviders(registry).map((provider) => provider.id)).toEqual(["system_speech_synthesis"]);
  });

  it("reserves local and external providers as disabled future metadata", () => {
    const registry = buildTtsProviderRegistry(true);

    expect(registry.find((provider) => provider.id === "local_tts")).toMatchObject({
      status: "not_implemented",
      enabled: false,
      selectable: false
    });
    expect(registry.find((provider) => provider.id === "external_tts")).toMatchObject({
      status: "not_configured",
      enabled: false,
      selectable: false,
      capability: expect.objectContaining({
        requiresNetwork: true,
        requiresApiKey: true
      })
    });
  });

  it("falls back safely when an illegal provider id is requested", () => {
    const resolution = resolveTtsProvider("unknown_tts", buildTtsProviderRegistry(true));

    expect(resolution).toMatchObject({
      requestedProviderId: "unknown_tts",
      fallbackUsed: true,
      fallbackReason: "unknown_provider"
    });
    expect(resolution.provider.id).toBe("system_speech_synthesis");
  });

  it("marks the system provider unavailable without enabling future providers", () => {
    const registry = buildTtsProviderRegistry(false);

    expect(registry.find((provider) => provider.id === "system_speech_synthesis")).toMatchObject({
      status: "unavailable",
      enabled: true,
      selectable: true
    });
    expect(getEnabledTtsProviders(registry).map((provider) => provider.id)).toEqual(["system_speech_synthesis"]);
  });
});
