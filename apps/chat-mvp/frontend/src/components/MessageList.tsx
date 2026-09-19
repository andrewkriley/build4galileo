import type { ChatMessage } from "../types";

interface MessageListProps {
  messages: ChatMessage[];
  pending: boolean;
}

export function MessageList({ messages, pending }: MessageListProps) {
  return (
    <div className="message-list">
      {messages.length === 0 && !pending && (
        <p className="message-list__empty">
          Ask about the host system, the sandboxed demo files, or whether a URL is reachable.
        </p>
      )}
      {messages.map((message, index) => (
        <div key={index} className={`message message--${message.role}`}>
          <span className="message__role">{message.role}</span>
          <p className="message__content">{message.content}</p>
        </div>
      ))}
      {pending && (
        <div className="message message--assistant message--pending">
          <span className="message__role">assistant</span>
          <p className="message__content">thinking…</p>
        </div>
      )}
    </div>
  );
}
