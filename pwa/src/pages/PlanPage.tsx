import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  type Plan,
  type Task,
  getTodayPlan,
  streamPlanSuggestion,
  confirmPlan,
} from "../api";

const MAX_ITEMS = 5;

function PlanPage() {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [activeTasks, setActiveTasks] = useState<Task[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [keyItems, setKeyItems] = useState<{ work: number | null; personal: number | null }>({
    work: null,
    personal: null,
  });
  const [suggestion, setSuggestion] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const suggestFired = useRef(false);

  const load = useCallback(async () => {
    try {
      const data = await getTodayPlan();
      setPlan(data.plan);
      setActiveTasks(data.active_tasks);

      if (data.plan.status === "confirmed") {
        const sel = new Set(data.plan.items.map((i) => i.task_id));
        setSelected(sel);
        const keys = { work: null as number | null, personal: null as number | null };
        for (const item of data.plan.items) {
          if (item.is_key) {
            if (item.task_category === "work") keys.work = item.task_id;
            else if (item.task_category === "personal") keys.personal = item.task_id;
          }
        }
        setKeyItems(keys);
      }

      if (data.plan.llm_suggestion) {
        setSuggestion(data.plan.llm_suggestion);
      } else if (data.plan.status === "draft" && !suggestFired.current) {
        suggestFired.current = true;
        setStreaming(true);
        streamPlanSuggestion(
          data.plan.id,
          (token) => setSuggestion((prev) => prev + token),
          (full) => {
            if (full) setSuggestion(full);
            setStreaming(false);
          },
          (err) => {
            setStreaming(false);
            console.error("Suggestion error:", err);
          },
        );
      }
    } catch {
      setError("Could not load plan");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggle = (taskId: number, category: string) => {
    setValidationError(null);
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(taskId)) {
        next.delete(taskId);
        setKeyItems((k) => {
          const updated = { ...k };
          if (updated.work === taskId) updated.work = null;
          if (updated.personal === taskId) updated.personal = null;
          return updated;
        });
      } else {
        if (next.size >= MAX_ITEMS) return prev;
        next.add(taskId);
        setKeyItems((k) => {
          const updated = { ...k };
          if (category === "work" && updated.work === null) updated.work = taskId;
          if (category === "personal" && updated.personal === null) updated.personal = taskId;
          return updated;
        });
      }
      return next;
    });
  };

  const toggleKey = (taskId: number, category: string) => {
    setKeyItems((k) => {
      const updated = { ...k };
      if (category === "work") {
        updated.work = updated.work === taskId ? null : taskId;
      } else {
        updated.personal = updated.personal === taskId ? null : taskId;
      }
      return updated;
    });
  };

  const handleConfirm = async () => {
    if (!plan) return;

    const hasWork = activeTasks.some((t) => t.category === "work" && selected.has(t.id));
    const hasPersonal = activeTasks.some((t) => t.category === "personal" && selected.has(t.id));
    if (hasWork && !keyItems.work) {
      setValidationError("Pick at least 1 key work item.");
      return;
    }
    if (hasPersonal && !keyItems.personal) {
      setValidationError("Pick at least 1 key personal item.");
      return;
    }
    if (!keyItems.work && !keyItems.personal) {
      setValidationError("Pick at least 1 key item.");
      return;
    }

    setSubmitting(true);
    setValidationError(null);
    try {
      const items = Array.from(selected).map((task_id) => ({
        task_id,
        is_key: task_id === keyItems.work || task_id === keyItems.personal,
      }));
      const result = await confirmPlan(plan.id, items);
      setPlan(result);
    } catch (e) {
      setValidationError(e instanceof Error ? e.message : "Failed to confirm plan");
    } finally {
      setSubmitting(false);
    }
  };

  if (error) {
    return (
      <div style={{ padding: "1.5rem", maxWidth: "480px", margin: "0 auto" }}>
        <p style={{ color: "var(--accent-bright)" }}>{error}</p>
        <button
          className="btn-primary"
          onClick={() => { setError(null); suggestFired.current = false; load(); }}
          style={{ marginTop: "0.75rem", marginBottom: "0.75rem" }}
        >
          Retry
        </button>
        <br />
        <Link to="/" style={{ color: "var(--text-muted)" }}>&larr; Home</Link>
      </div>
    );
  }

  if (!plan) {
    return (
      <div style={{ padding: "1.5rem", maxWidth: "480px", margin: "0 auto" }}>
        <p style={{ color: "var(--text-muted)" }}>Loading...</p>
      </div>
    );
  }

  const isConfirmed = plan.status === "confirmed";

  const workTasks = activeTasks.filter((t) => t.category === "work");
  const personalTasks = activeTasks.filter((t) => t.category === "personal");

  return (
    <div style={{ padding: "1.5rem", maxWidth: "480px", margin: "0 auto" }}>
      <header style={{ display: "flex", alignItems: "center", marginBottom: "1.5rem" }}>
        <Link
          to="/"
          style={{ color: "var(--text-muted)", textDecoration: "none", marginRight: "0.75rem" }}
        >
          &larr;
        </Link>
        <h1 style={{ fontSize: "1.5rem" }}>Morning plan</h1>
      </header>

      {suggestion && (
        <div
          style={{
            background: "var(--bg-card)",
            borderRadius: "var(--radius)",
            padding: "1rem",
            marginBottom: "1rem",
            fontSize: "0.9rem",
            color: "var(--text)",
            lineHeight: 1.5,
            borderLeft: "3px solid var(--accent)",
          }}
        >
          {suggestion}
          {streaming && <span style={{ opacity: 0.5 }}> ...</span>}
        </div>
      )}

      {!suggestion && !streaming && !isConfirmed && (
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "1rem" }}>
          Pick your focus items for today.
        </p>
      )}

      {isConfirmed ? (
        <>
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
            Plan confirmed
          </div>

          <div
            style={{
              background: "var(--bg-card)",
              borderRadius: "var(--radius)",
              overflow: "hidden",
              marginBottom: "1.5rem",
            }}
          >
            {plan.items.map((item) => (
              <div
                key={item.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: "0.875rem 1rem",
                  borderBottom: "1px solid rgba(255,255,255,0.05)",
                  gap: "0.75rem",
                }}
              >
                {item.is_key && (
                  <span style={{ color: "var(--accent)", fontSize: "0.85rem" }}>&#9733;</span>
                )}
                <span style={{ flex: 1, color: "var(--text)", fontSize: "0.95rem" }}>
                  {item.task_title}
                </span>
                <span
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-muted)",
                    textTransform: "uppercase",
                  }}
                >
                  {item.task_category}
                </span>
              </div>
            ))}
          </div>

          <div style={{ textAlign: "center" }}>
            <Link to="/" style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
              &larr; Home
            </Link>
          </div>
        </>
      ) : (
        <>
          {!suggestion && streaming && (
            <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginBottom: "1rem" }}>
              Thinking...
            </p>
          )}

          {([
            { label: "Work", tasks: workTasks, category: "work" },
            { label: "Personal", tasks: personalTasks, category: "personal" },
          ] as const).map(({ label, tasks, category }) =>
            tasks.length > 0 ? (
              <div key={category} style={{ marginBottom: "1rem" }}>
                <h2
                  style={{
                    fontSize: "0.8rem",
                    color: "var(--text-muted)",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                    marginBottom: "0.5rem",
                  }}
                >
                  {label}
                </h2>
                <div
                  style={{
                    background: "var(--bg-card)",
                    borderRadius: "var(--radius)",
                    overflow: "hidden",
                  }}
                >
                  {tasks.map((task) => {
                    const isSelected = selected.has(task.id);
                    const isKey =
                      (category === "work" && keyItems.work === task.id) ||
                      (category === "personal" && keyItems.personal === task.id);
                    const atLimit = selected.size >= MAX_ITEMS && !isSelected;

                    return (
                      <div
                        key={task.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          borderBottom: "1px solid rgba(255,255,255,0.05)",
                        }}
                      >
                        <button
                          onClick={() => toggle(task.id, category)}
                          disabled={atLimit}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            flex: 1,
                            padding: "0.875rem 1rem",
                            background: isSelected ? "rgba(78, 204, 163, 0.1)" : "transparent",
                            border: "none",
                            borderRadius: 0,
                            color: atLimit ? "var(--text-muted)" : "var(--text)",
                            fontSize: "0.95rem",
                            textAlign: "left",
                            cursor: atLimit ? "default" : "pointer",
                            gap: "0.75rem",
                            fontWeight: 400,
                            opacity: atLimit ? 0.5 : 1,
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
                          <span style={{ flex: 1 }}>{task.title}</span>
                        </button>
                        {isSelected && (
                          <button
                            onClick={() => toggleKey(task.id, category)}
                            style={{
                              background: "none",
                              border: "none",
                              cursor: "pointer",
                              padding: "0.5rem 0.75rem",
                              fontSize: "1.1rem",
                              color: isKey ? "var(--accent)" : "var(--text-muted)",
                              opacity: isKey ? 1 : 0.4,
                            }}
                            title={isKey ? "Key item" : "Mark as key item"}
                          >
                            &#9733;
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : null,
          )}

          {selected.size >= MAX_ITEMS && (
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", textAlign: "center", marginBottom: "0.5rem" }}>
              {MAX_ITEMS} items max — deselect one to swap.
            </p>
          )}

          {validationError && (
            <p
              style={{
                color: "var(--accent-bright, #e94560)",
                fontSize: "0.85rem",
                textAlign: "center",
                marginBottom: "0.5rem",
              }}
            >
              {validationError}
            </p>
          )}

          <button
            className="btn-primary"
            onClick={handleConfirm}
            disabled={submitting || selected.size === 0}
            style={{ width: "100%", marginBottom: "1.5rem" }}
          >
            {submitting
              ? "Confirming..."
              : `Confirm plan (${selected.size} item${selected.size !== 1 ? "s" : ""})`}
          </button>

          <div style={{ textAlign: "center" }}>
            <Link to="/" style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
              Skip &mdash; plan later
            </Link>
          </div>
        </>
      )}
    </div>
  );
}

export default PlanPage;
