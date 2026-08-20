import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { type CheckIn, getTodayCheckIn, completeCheckIn } from "../api";

function CheckInPage() {
  const [checkIn, setCheckIn] = useState<CheckIn | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await getTodayCheckIn();
      setCheckIn(data);
      if (data.status === "completed") {
        const doneIds = new Set(data.items.filter((i) => i.done).map((i) => i.task_id));
        setSelected(doneIds);
        setNote(data.note ?? "");
      }
    } catch {
      setError("Could not load check-in");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggle = (taskId: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) next.delete(taskId);
      else next.add(taskId);
      return next;
    });
  };

  const handleSubmit = async () => {
    if (!checkIn) return;
    setSubmitting(true);
    try {
      const result = await completeCheckIn(
        checkIn.id,
        Array.from(selected),
        note.trim() || undefined,
      );
      setCheckIn(result);
      const doneCount = result.items.filter((i) => i.done).length;
      const total = result.items.length;
      const time = new Date(result.completed_at!).toLocaleTimeString([], {
        hour: "numeric",
        minute: "2-digit",
      });
      setConfirmation(`Recorded ${doneCount} of ${total}, ${time}`);
    } catch {
      setError("Failed to submit check-in");
    } finally {
      setSubmitting(false);
    }
  };

  if (error) {
    return (
      <div style={{ padding: "1.5rem", maxWidth: "480px", margin: "0 auto" }}>
        <p style={{ color: "var(--accent-bright)" }}>{error}</p>
        <Link to="/" style={{ color: "var(--text-muted)" }}>&larr; Home</Link>
      </div>
    );
  }

  if (!checkIn) {
    return (
      <div style={{ padding: "1.5rem", maxWidth: "480px", margin: "0 auto" }}>
        <p style={{ color: "var(--text-muted)" }}>Loading...</p>
      </div>
    );
  }

  const isCompleted = checkIn.status === "completed";

  return (
    <div style={{ padding: "1.5rem", maxWidth: "480px", margin: "0 auto" }}>
      <header style={{ display: "flex", alignItems: "center", marginBottom: "1.5rem" }}>
        <Link
          to="/"
          style={{ color: "var(--text-muted)", textDecoration: "none", marginRight: "0.75rem" }}
        >
          &larr;
        </Link>
        <h1 style={{ fontSize: "1.5rem" }}>Evening check-in</h1>
      </header>

      {confirmation && (
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
          {confirmation}
        </div>
      )}

      {checkIn.items.length === 0 ? (
        <p style={{ color: "var(--text-muted)", padding: "2rem 0", textAlign: "center" }}>
          No active tasks for today.
        </p>
      ) : (
        <>
          <p
            style={{
              color: "var(--text-muted)",
              fontSize: "0.9rem",
              marginBottom: "1rem",
            }}
          >
            {isCompleted
              ? "Check-in recorded. You can update it."
              : "Tap the tasks you completed today."}
          </p>

          <div
            style={{
              background: "var(--bg-card)",
              borderRadius: "var(--radius)",
              overflow: "hidden",
              marginBottom: "1rem",
            }}
          >
            {checkIn.items.map((item) => {
              const isSelected = selected.has(item.task_id);
              return (
                <button
                  key={item.id}
                  onClick={() => toggle(item.task_id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    width: "100%",
                    padding: "0.875rem 1rem",
                    background: isSelected ? "rgba(78, 204, 163, 0.1)" : "transparent",
                    border: "none",
                    borderBottom: "1px solid rgba(255,255,255,0.05)",
                    borderRadius: 0,
                    color: "var(--text)",
                    fontSize: "0.95rem",
                    textAlign: "left",
                    cursor: "pointer",
                    gap: "0.75rem",
                    fontWeight: 400,
                  }}
                >
                  <span
                    style={{
                      width: "24px",
                      height: "24px",
                      borderRadius: "6px",
                      border: isSelected
                        ? "2px solid var(--success)"
                        : "2px solid var(--text-muted)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      background: isSelected ? "var(--success)" : "transparent",
                      color: isSelected ? "var(--bg)" : "transparent",
                      fontSize: "0.8rem",
                      fontWeight: 700,
                    }}
                  >
                    {isSelected ? "✓" : ""}
                  </span>
                  <span style={{ flex: 1 }}>{item.task_title}</span>
                  <span
                    style={{
                      fontSize: "0.75rem",
                      color: "var(--text-muted)",
                      textTransform: "uppercase",
                    }}
                  >
                    {item.task_category}
                  </span>
                </button>
              );
            })}
          </div>

          {selected.size === 0 && (
            <p
              style={{
                color: "var(--text-muted)",
                fontSize: "0.85rem",
                textAlign: "center",
                marginBottom: "1rem",
              }}
            >
              Nothing selected — that's an honest answer.
            </p>
          )}
        </>
      )}

      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Optional note..."
        maxLength={500}
        rows={2}
        style={{
          width: "100%",
          padding: "10px 14px",
          borderRadius: "var(--radius)",
          border: "1px solid var(--accent)",
          background: "var(--bg-card)",
          color: "var(--text)",
          fontSize: "0.9rem",
          resize: "vertical",
          marginBottom: "1rem",
        }}
      />

      <button
        className="btn-primary"
        onClick={handleSubmit}
        disabled={submitting}
        style={{ width: "100%", marginBottom: "1.5rem" }}
      >
        {submitting
          ? "Saving..."
          : isCompleted
            ? "Update check-in"
            : selected.size === 0
              ? "Submit — nothing today"
              : `Submit ${selected.size} of ${checkIn.items.length}`}
      </button>

      {checkIn.status === "completed" && (
        <Link
          to={`/reflect/${checkIn.id}`}
          style={{
            display: "block",
            textAlign: "center",
            background: checkIn.reflection_finished
              ? "var(--bg-card)"
              : "var(--accent)",
            color: "var(--text)",
            borderRadius: "var(--radius)",
            padding: "12px 24px",
            fontWeight: 600,
            textDecoration: "none",
            marginBottom: "1rem",
          }}
        >
          {checkIn.reflection_finished ? "View reflection" : "Start reflection"}
        </Link>
      )}

      <div style={{ textAlign: "center" }}>
        <Link
          to="/history"
          style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}
        >
          View history
        </Link>
      </div>
    </div>
  );
}

export default CheckInPage;
