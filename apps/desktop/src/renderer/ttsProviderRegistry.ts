export type TtsProviderId = "system_speech_synthesis" | "local_tts" | "external_tts";

export type TtsProviderStatus = "available" | "unavailable" | "not_configured" | "not_implemented";

export type TtsProviderCapability = {
  streaming: boolean;
  customVoice: boolean;
  localOnly: boolean;
  requiresNetwork: boolean;
  requiresApiKey: boolean;
  supportsInterrupt: boolean;
};

export type TtsProviderDescriptor = {
  id: TtsProviderId;
  label: string;
  status: TtsProviderStatus;
  enabled: boolean;
  selectable: boolean;
  description: string;
  privacySummary: string;
  fallbackSummary: string;
  capability: TtsProviderCapability;
};

export type TtsProviderResolution = {
  provider: TtsProviderDescriptor;
  requestedProviderId: string | null;
  fallbackUsed: boolean;
  fallbackReason: "unknown_provider" | "disabled_provider" | "provider_not_selectable" | null;
};

export const SYSTEM_TTS_PROVIDER_ID = "system_speech_synthesis" as const;

const SYSTEM_TTS_PROVIDER: TtsProviderDescriptor = {
  id: SYSTEM_TTS_PROVIDER_ID,
  label: "System Speech Synthesis",
  status: "available",
  enabled: true,
  selectable: true,
  description: "本机系统语音 fallback",
  privacySummary: "使用本机系统语音，不上传音频，不需要 API key。",
  fallbackSummary: "默认 provider；不可用时保留文字回复并安全 no-op。",
  capability: {
    streaming: false,
    customVoice: false,
    localOnly: true,
    requiresNetwork: false,
    requiresApiKey: false,
    supportsInterrupt: true
  }
};

const RESERVED_TTS_PROVIDERS: TtsProviderDescriptor[] = [
  {
    id: "local_tts",
    label: "Local TTS",
    status: "not_implemented",
    enabled: false,
    selectable: false,
    description: "未来本地 TTS provider 占位，当前未实现。",
    privacySummary: "当前不会读取本地模型路径，也不会调用本地 TTS runtime。",
    fallbackSummary: "不可选择；如被请求会回退到 System Speech Synthesis。",
    capability: {
      streaming: false,
      customVoice: false,
      localOnly: true,
      requiresNetwork: false,
      requiresApiKey: false,
      supportsInterrupt: false
    }
  },
  {
    id: "external_tts",
    label: "External TTS",
    status: "not_configured",
    enabled: false,
    selectable: false,
    description: "未来外部 TTS provider 占位，当前未实现也未配置。",
    privacySummary: "当前不会保存 API key，不上传文本或音频到外部 TTS。",
    fallbackSummary: "不可选择；如被请求会回退到 System Speech Synthesis。",
    capability: {
      streaming: false,
      customVoice: false,
      localOnly: false,
      requiresNetwork: true,
      requiresApiKey: true,
      supportsInterrupt: false
    }
  }
];

export const buildTtsProviderRegistry = (systemAvailable: boolean): TtsProviderDescriptor[] => [
  {
    ...SYSTEM_TTS_PROVIDER,
    status: systemAvailable ? "available" : "unavailable"
  },
  ...RESERVED_TTS_PROVIDERS.map((provider) => ({ ...provider }))
];

export const getSystemTtsProviderDescriptor = (systemAvailable = true) =>
  buildTtsProviderRegistry(systemAvailable)[0];

export const resolveTtsProvider = (
  requestedProviderId?: string | null,
  registry: TtsProviderDescriptor[] = buildTtsProviderRegistry(true)
): TtsProviderResolution => {
  const systemProvider = registry.find((provider) => provider.id === SYSTEM_TTS_PROVIDER_ID) ?? getSystemTtsProviderDescriptor();
  const requestedProvider = requestedProviderId
    ? registry.find((provider) => provider.id === requestedProviderId)
    : systemProvider;

  if (!requestedProvider) {
    return {
      provider: systemProvider,
      requestedProviderId: requestedProviderId ?? null,
      fallbackUsed: Boolean(requestedProviderId),
      fallbackReason: requestedProviderId ? "unknown_provider" : null
    };
  }

  if (!requestedProvider.enabled) {
    return {
      provider: systemProvider,
      requestedProviderId: requestedProviderId ?? null,
      fallbackUsed: requestedProvider.id !== systemProvider.id,
      fallbackReason: requestedProvider.id === systemProvider.id ? null : "disabled_provider"
    };
  }

  if (!requestedProvider.selectable) {
    return {
      provider: systemProvider,
      requestedProviderId: requestedProviderId ?? null,
      fallbackUsed: requestedProvider.id !== systemProvider.id,
      fallbackReason: requestedProvider.id === systemProvider.id ? null : "provider_not_selectable"
    };
  }

  return {
    provider: requestedProvider,
    requestedProviderId: requestedProviderId ?? requestedProvider.id,
    fallbackUsed: false,
    fallbackReason: null
  };
};

export const getEnabledTtsProviders = (registry: TtsProviderDescriptor[]) =>
  registry.filter((provider) => provider.enabled);

export const getSelectableTtsProviders = (registry: TtsProviderDescriptor[]) =>
  registry.filter((provider) => provider.selectable);
