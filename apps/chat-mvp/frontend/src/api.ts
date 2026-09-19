const API_BASE_URL = "http://localhost:8000";

export interface ConfigResponse {
  available_providers: string[];
  default_provider: string;
}

export interface ChatResponse {
  answer: string;
}

export async function fetchConfig(): Promise<ConfigResponse> {
  const response = await fetch(`${API_BASE_URL}/config`);
  if (!response.ok) {
    throw new Error(`GET /config failed: ${response.status}`);
  }
  return response.json() as Promise<ConfigResponse>;
}

export async function sendChatMessage(
  message: string,
  sessionId: string,
  provider: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, provider }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`POST /chat failed: ${response.status} ${detail}`);
  }
  return response.json() as Promise<ChatResponse>;
}
