import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  type ReflectionMessage,
  getReflection,
  streamReflectionChat,
  finishReflection,
} from "../api";

function ReflectionPage() {
  const { checkinId } = useParams<{ checkinId: string }>();
  const id = Number(checkinId);

  const [messages, setMessages] = useState<ReflectionMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [input, setInput] = useState("");
  const [finished, setFinished] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const started = useRef(false);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(scrollToBottom, [messages, streamingContent, scrollToBottom]);

  const sendMessage = useCallback(
    async (userMessage: string | null) => {
      setStreaming(true);
      setStreamingContent("");
      setError(null);

      await streamReflectionChat(
        id,
        userMessage,
        (token) => setStreamingContent((prev) => prev + token),
        () => {
          setStreamingContent((content) => {
            if (content) {
              setMessages((prev) => [
                ...prev,
                { id: Date.now(), role: "assistant", content, created_at: new Date().toISOString() },
              ]);
            }
            return "";
          });
          setStreaming(false);
        },
        (err) => {
          setError(err);
          setStreaming(false);
          setStreamingContent("");
        },
      );
    },
    [id],
  );

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    (async () => {
      try {
        const data = await getReflection(id);
        setMessages(data.messages);
        setFinished(data.finished);
        if (!data.finished && data.messages.length === 0) {
          setLoading(false);
          sendMessage(null);
          return;
        }
      } catch {
        setError("Could not load reflection");
      }
      setLoading(false);
    })();
  }, [id, sendMessage]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || streaming) return;
    setMessages((prev) => [
      ...prev,
      { id: Date.now(), role: "user", content: text, created_at: new Date().toISOString() },
    ]);
    setInput("");
    sendMessage(text);
  };

  const handleFinish = async () => {
    setFinishing(true);
    try {
      await finishReflection(id);
      setFinished(true);
    } catch {
      setError("Failed to save reflection");
    } finally {
      setFinishing(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "1.5rem", maxWidth: "480px", margin: "0 auto" }}>
        <p style={{ color: "var(--text-muted)" }}>Loading...</p>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: "1.5rem",
        maxWidth: "480px",
        margin: "0 auto",
        display: "flex",
        flexDirection: "column",
        minHeight: "100dvh",
        boxSizing: "border-box",
      }}
    >
      <header style={{ display: "flex", alignItems: "center", marginBottom: "1rem" }}>
        <Link
          to="/checkin/today"
          style={{ color: "var(--text-muted)", textDecoration: "none", marginRight: "0.75rem" }}
        >
          &larr;
        </Link>
        <h1 style={{ fontSize: "1.5rem" }}>Reflection</h1>
      </header>

      {finished && (
        <div
          style={{
            background: "rgba(78, 204, 163, 0.15)",
            border: "1px solid var(--success)",
            borderRadius: "var(--radius)",
            padding: "0.75rem 1rem",
            marginBottom: "1rem",
            color: "var(--success)",
            fontSize: "0.9rem",
          }}
        >
          Reflection saved to journal.
        </div>
      )}

      <div style={{ flex: 1, overflowY: "auto", marginBottom: "1rem" }}>
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: "flex",
              justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
              marginBottom: "0.75rem",
            }}
          >
            <div
              style={{
                maxWidth: msg.role === "user" ? "80%" : "100%",
                background: msg.role === "user" ? "var(--accent)" : "var(--bg-card)",
                borderRadius: "var(--radius)",
                padding: "0.75rem 1rem",
                fontSize: "0.9rem",
                lineHeight: 1.5,
              }}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {streaming && streamingContent && (
          <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: "0.75rem" }}>
            <div
              style={{
                background: "var(--bg-card)",
                borderRadius: "var(--radius)",
                padding: "0.75rem 1rem",
                fontSize: "0.9rem",
                lineHeight: 1.5,
              }}
            >
              {streamingContent}
              <span
                style={{
                  display: "inline-block",
                  width: "2px",
                  height: "1em",
                  background: "var(--text-muted)",
                  marginLeft: "2px",
                  verticalAlign: "text-bottom",
                  animation: "blink 1s step-end infinite",
                }}
              />
            </div>
          </div>
        )}

        {streaming && !streamingContent && (
          <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: "0.75rem" }}>
            <div
              style={{
                background: "var(--bg-card)",
                borderRadius: "var(--radius)",
                padding: "0.75rem 1rem",
                fontSize: "0.9rem",
                color: "var(--text-muted)",
              }}
            >
              Thinking...
            </div>
          </div>
        )}

        {error && (
          <p style={{ color: "var(--accent-bright)", fontSize: "0.85rem", textAlign: "center" }}>
            {error}
          </p>
        )}

        <div ref={messagesEndRef} />
      </div>

      {!finished && (
        <div>
          <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.75rem" }}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Reply..."
              disabled={streaming}
              style={{
                flex: 1,
                padding: "10px 14px",
                borderRadius: "var(--radius)",
                border: "1px solid var(--accent)",
                background: "var(--bg-card)",
                color: "var(--text)",
                fontSize: "0.9rem",
              }}
            />
            <button
              className="btn-primary"
              onClick={handleSend}
              disabled={streaming || !input.trim()}
              style={{ padding: "10px 20px" }}
            >
              Send
            </button>
          </div>

          {messages.length > 0 && !streaming && (
            <button
              className="btn-secondary"
              onClick={handleFinish}
              disabled={finishing}
              style={{ width: "100%", marginBottom: "0.5rem" }}
            >
              {finishing ? "Saving..." : "Finish reflection"}
            </button>
          )}
        </div>
      )}

      <div style={{ textAlign: "center", paddingTop: "0.5rem" }}>
        <Link to="/" style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
          Home
        </Link>
      </div>
    </div>
  );
}

export default ReflectionPage;
