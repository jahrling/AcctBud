import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { type CheckIn, getCheckIns } from "../api";

function HistoryPage() {
  const [checkins, setCheckins] = useState<CheckIn[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    getCheckIns(30)
      .then((r) => setCheckins(r.checkins))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ padding: "1.5rem", maxWidth: "480px", margin: "0 auto" }}>
      <header style={{ display: "flex", alignItems: "center", marginBottom: "1.5rem" }}>
        <Link
          to="/"
          style={{ color: "var(--text-muted)", textDecoration: "none", marginRight: "0.75rem" }}
        >
          &larr;
        </Link>
        <h1 style={{ fontSize: "1.5rem" }}>History</h1>
      </header>

      {loading && <p style={{ color: "var(--text-muted)" }}>Loading...</p>}

      {error && (
        <p style={{ color: "var(--accent-bright)", textAlign: "center", padding: "2rem 0" }}>
          Could not load history.
        </p>
      )}

      {!loading && checkins.length === 0 && (
        <p style={{ color: "var(--text-muted)", textAlign: "center", padding: "2rem 0" }}>
          No check-ins yet.
        </p>
      )}

      {checkins.map((ci) => {
        const doneCount = ci.items.filter((i) => i.done).length;
        const total = ci.items.length;
        const statusColor =
          ci.status === "completed"
            ? "var(--success)"
            : ci.status === "missed"
              ? "var(--accent-bright)"
              : "var(--text-muted)";

        return (
          <div
            key={ci.id}
            style={{
              background: "var(--bg-card)",
              borderRadius: "var(--radius)",
              padding: "0.875rem 1rem",
              marginBottom: "0.5rem",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: ci.note ? "0.5rem" : 0,
              }}
            >
              <div>
                <span style={{ fontSize: "0.95rem" }}>{ci.for_date}</span>
                {ci.status === "completed" && total > 0 && (
                  <span style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginLeft: "0.5rem" }}>
                    {doneCount} of {total}
                  </span>
                )}
              </div>
              <span
                style={{
                  fontSize: "0.75rem",
                  textTransform: "uppercase",
                  color: statusColor,
                  fontWeight: 600,
                }}
              >
                {ci.status}
              </span>
            </div>
            {ci.note && (
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", margin: 0 }}>
                {ci.note}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default HistoryPage;
