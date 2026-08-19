import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { usePush } from "./usePush";
import { getHealth, getTasks, getTodayCheckIn, type CheckIn } from "./api";

function App() {
  const { state, subscribe, unsubscribe } = usePush();
  const [health, setHealth] = useState<{ version: string; server_time: string; timezone: string } | null>(null);
  const [activeCount, setActiveCount] = useState<number | null>(null);
  const [todayCheckIn, setTodayCheckIn] = useState<CheckIn | null>(null);
  const [showPushSetup, setShowPushSetup] = useState(false);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => {});
    getTasks("active").then((r) => setActiveCount(r.active_count)).catch(() => {});
    getTodayCheckIn().then(setTodayCheckIn).catch(() => {});
  }, []);

  const pushLabel =
    state === "subscribed"
      ? "Notifications on"
      : state === "denied"
        ? "Notifications blocked"
        : state === "unsupported"
          ? "Notifications unavailable"
          : "Notifications off";

  return (
    <div style={{ padding: "1.5rem", maxWidth: "480px", margin: "0 auto" }}>
      <header style={{ textAlign: "center", marginBottom: "2rem" }}>
        <h1 style={{ fontSize: "1.75rem", marginBottom: "0.25rem" }}>AcctBud</h1>
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
          Your accountability buddy
        </p>
      </header>

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
            {activeCount !== null ? (
              <>
                <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "var(--text)" }}>
                  {activeCount}
                </div>
                <div style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>
                  active task{activeCount !== 1 ? "s" : ""}
                </div>
              </>
            ) : (
              <div style={{ fontSize: "0.95rem", color: "var(--text)" }}>Tasks</div>
            )}
          </div>
          <span style={{ color: "var(--text-muted)", fontSize: "1.25rem" }}>&rarr;</span>
        </section>
      </Link>

      {todayCheckIn && (
        <Link to="/checkin/today" style={{ textDecoration: "none" }}>
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
              {todayCheckIn.status === "completed" ? (
                <>
                  <div style={{ fontSize: "0.95rem", color: "var(--success)" }}>
                    Check-in complete
                  </div>
                  <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                    {todayCheckIn.items.filter((i) => i.done).length} of{" "}
                    {todayCheckIn.items.length} done
                  </div>
                </>
              ) : (
                <>
                  <div style={{ fontSize: "0.95rem", color: "var(--text)" }}>
                    Evening check-in
                  </div>
                  <div style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                    {todayCheckIn.items.length} task{todayCheckIn.items.length !== 1 ? "s" : ""} to
                    review
                  </div>
                </>
              )}
            </div>
            <span style={{ color: "var(--text-muted)", fontSize: "1.25rem" }}>&rarr;</span>
          </section>
        </Link>
      )}

      <Link to="/history" style={{ textDecoration: "none" }}>
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
          <div style={{ fontSize: "0.95rem", color: "var(--text)" }}>History</div>
          <span style={{ color: "var(--text-muted)", fontSize: "1.25rem" }}>&rarr;</span>
        </section>
      </Link>

      {health && (
        <section
          style={{
            background: "var(--bg-card)",
            borderRadius: "var(--radius)",
            padding: "1.25rem",
            fontSize: "0.85rem",
            color: "var(--text-muted)",
            marginBottom: "1rem",
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
        <p
          onClick={() => setShowPushSetup(!showPushSetup)}
          style={{ cursor: "pointer" }}
        >
          {pushLabel}
          {state !== "subscribed" && state !== "unsupported" && state !== "denied" && " — tap to set up"}
        </p>

        {showPushSetup && (
          <div style={{ marginTop: "0.75rem" }}>
            {state === "prompt" && (
              <button className="btn-primary" onClick={subscribe} style={{ fontSize: "0.85rem", padding: "8px 20px" }}>
                Enable notifications
              </button>
            )}
            {state === "subscribed" && (
              <button className="btn-secondary" onClick={unsubscribe} style={{ fontSize: "0.85rem", padding: "8px 20px" }}>
                Disable notifications
              </button>
            )}
            {state === "denied" && (
              <p>Update this site's permissions in browser settings to re-enable.</p>
            )}
            {state === "unsupported" && (
              <p>Install to home screen on iOS, or use a supported browser.</p>
            )}
          </div>
        )}
      </footer>
    </div>
  );
}

export default App;
