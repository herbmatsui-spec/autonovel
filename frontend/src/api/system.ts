export interface ServerModelInfo {
  status: string;
  current_provider: string;
  server_defaults: {
    planning: string;
    plot_expansion: string;
    writing: string;
    audit: string;
    embedding: string;
  };
  configured_keys: {
    gemini: boolean;
    openai: boolean;
    anthropic: boolean;
    openrouter: boolean;
  };
  available_providers: string[];
}

export async function fetchServerModelInfo(): Promise<ServerModelInfo | null> {
  try {
    const res = await fetch("/api/system/models/info");
    if (!res.ok) {
      return null;
    }
    return await res.json();
  } catch (err) {
    console.warn("Failed to fetch server model info:", err);
    return null;
  }
}
