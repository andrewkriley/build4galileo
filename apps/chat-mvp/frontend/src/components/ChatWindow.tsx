import { useEffect, useState } from "react";

import { fetchConfig, sendChatMessage } from "../api";
import { getOrCreateSessionId } from "../session";
import type { ChatMessage } from "../types";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";
import { ModelSelector } from "./ModelSelector";
import { ProviderSelector } from "./ProviderSelector";

const sessionId = getOrCreateSessionId();

export function ChatWindow() {
  const [providers, setProviders] = useState<string[]>([]);
  const [provider, setProvider] = useState<string>("");
  const [modelsByProvider, setModelsByProvider] = useState<Record<string, string[]>>({});
  const [model, setModel] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchConfig()
      .then((config) => {
        setProviders(config.available_providers);
        setProvider(config.default_provider);
        setModelsByProvider(config.models);
        setModel(config.models[config.default_provider]?.[0] ?? "");
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "failed to load /config");
      });
  }, []);

  function handleProviderChange(nextProvider: string) {
    setProvider(nextProvider);
    setModel(modelsByProvider[nextProvider]?.[0] ?? "");
  }

  async function handleSend(message: string) {
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setPending(true);
    setError(null);
    try {
      const response = await sendChatMessage(message, sessionId, provider, model);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response.answer, timeline: response.timeline },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "chat request failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="chat-window">
      <header className="chat-window__header">
        <h1>build4galileo chat MVP</h1>
        <div className="chat-window__model-controls">
          <ProviderSelector providers={providers} selected={provider} onChange={handleProviderChange} />
          <ModelSelector
            models={modelsByProvider[provider] ?? []}
            selected={model}
            onChange={setModel}
          />
        </div>
      </header>
      <p className="chat-window__session-note">
        This browser tab is one Galileo <strong>session</strong> (<code>{sessionId}</code>). Every
        message you send below opens one <strong>trace</strong> inside it, made of nested{" "}
        <strong>spans</strong> — expand a reply's "Galileo trace" to see them.
      </p>
      {error && <p className="chat-window__error">{error}</p>}
      <MessageList messages={messages} pending={pending} />
      <MessageInput disabled={pending || providers.length === 0 || !model} onSend={handleSend} />
    </div>
  );
}
