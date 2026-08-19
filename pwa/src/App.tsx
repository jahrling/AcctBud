import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { usePush } from "./usePush";
import { sendTestPush, getHealth, getTasks } from "./api";

function App() {
  const { state, error, subscribe, unsubscribe } = usePush();
  const [health, setHealth] = useState<{ version: string; server_time: string; timezone: string } | null>(null);
  const [testResult, setTestResult] = useState<string>("");
  const [activeCount, setActiveCount] = useState<number | null>(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => {});
    getTasks("active").then((r) => setActiveCount(r.active_count)).catch(() => {});
  }, []);

  const handleTest = async () => {
    setTestResult("Sending...");
    try {
      const res = await sendTestPush();
      setTestResult(`Sent to ${res.count} device(s): ${res.results.join(", ")}`);
    } catch {
      setTestResult("Failed to send test push");
    }
  };

  return (
    <div style={{ padding: "1.5rem", maxWidth: "480px", margin: "0 auto" }}>
      <header style={{ textAlign: "center", marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.75rem", marginBottom: "0.25rem" }}>AcctBud</h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
          Your accountability buddy
        </p>
      </header>

      {activeCount !== null && (
        <Link to="/tasks" style={{ textDecoration: "none" }}>
          <section
            style={{
              background: "var(--bg-card)",
              borderRadius: "var(--radius)",
              padding: "1.25rem",
              marginBottom: "1rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div>
              <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text)" }}>
                {activeCount}
              </div>
              <div style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>
                active task{activeCount !== 1 ? "s" : ""}
              </div>
            </div>
            <span style={{ color: "var(--text-muted)", fontSize: "1.25rem" }}>&rarr;</span>
          </section>
        </Link>
      )}

      <section
        style={{
          background: "var(--bg-card)",
          borderRadius: "var(--radius)",
          padding: "1.25rem",
          marginBottom: "1rem",
        }}
      >
        <h2 style={{ fontSize: "1.1rem", marginBottom: "1rem" }}>Notifications</h2>

        {state === "loading" && <p style={{ color: "var(--text-muted)" }}>Checking...</p>}

        {state === "unsupported" && (
          <p style={{ color: "var(--text-muted)" }}>
            Push notifications are not supported in this browser. On iOS, install this app to your
            home screen first: tap Share then "Add to Home Screen."
          </p>
        )}

        {state === "prompt" && (
          <>
            <p style={{ color: "var(--text-muted)", marginBottom: "1rem", fontSize: "0.9rem" }}>
              AcctBud sends morning and evening check-in reminders. Enable notifications so it can
              reach you.
            </p>
            <button className="btn-primary" onClick={subscribe} style={{ width: "100%" }}>
              Enable notifications
            </button>
          </>
        )}

        {state === "denied" && (
          <p style={{ color: "var(--text-muted)" }}>
            Notification permission was denied. To re-enable, update this site's permissions in your
            browser or device settings.
          </p>
        )}

        {state === "subscribed" && (
          <>
            <p style={{ color: "var(--success)", marginBottom: "1rem" }}>
              Notifications are enabled.
            </p>
            <div style={{ display: "flex", gap: "0.75rem" }}>
              <button className="btn-primary" onClick={handleTest} style={{ flex: 1 }}>
                Send test
              </button>
              <button className="btn-secondary" onClick={unsubscribe} style={{ flex: 1 }}>
                Disable
              </button>
            </div>
            {testResult && (
              <p style={{ color: "var(--text-muted)", marginTop: "0.75rem", fontSize: "0.85rem" }}>
                {testResult}
              </p>
            )}
          </>
        )}

        {state === "error" && (
          <p style={{ color: "var(--accent-bright)" }}>
            Something went wrong: {error}
          </p>
        )}
      </section>

      {health && (
        <section
          style={{
            background: "var(--bg-card)",
            borderRadius: "var(--radius)",
            padding: "1.25rem",
            fontSize: "0.85rem",
            color: "var(--text-muted)",
          }}
        >
          <p>Server v{health.version}</p>
          <p>{health.timezone} &mdash; {new Date(health.server_time).toLocaleString()}</p>
        </section>
      )}

      <footer
        style={{
          textAlign: "center",
          marginTop: "2rem",
          color: "var(--text-muted)",
          fontSize: "0.8rem",
        }}
      >
        <p>Install to your home screen for the full experience.</p>
      </footer>
    </div>
  );
}

export default App;
