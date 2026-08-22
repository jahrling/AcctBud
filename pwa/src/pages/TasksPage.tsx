import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { type Task, getTasks, createTask, updateTask } from "../api";

type Category = "work" | "personal";

function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [activeCount, setActiveCount] = useState(0);
  const [filter, setFilter] = useState<string>("active");
  const [newTitle, setNewTitle] = useState("");
  const [newCategory, setNewCategory] = useState<Category>("work");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editNote, setEditNote] = useState("");
  const [reordering, setReordering] = useState(false);
  const addRef = useRef<HTMLTextAreaElement>(null);

  const load = useCallback(async () => {
    const res = await getTasks(filter);
    setTasks(res.tasks);
    setActiveCount(res.active_count);
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const title = newTitle.trim();
    if (!title) return;
    await createTask(title, newCategory);
    setNewTitle("");
    if (addRef.current) addRef.current.style.height = "auto";
    load();
  };

  const handleStatusChange = async (task: Task, status: Task["status"]) => {
    await updateTask(task.id, { status });
    load();
  };

  const handleStartEdit = (task: Task) => {
    setEditingId(task.id);
    setEditTitle(task.title);
    setEditNote(task.note ?? "");
  };

  const handleSaveEdit = async () => {
    if (editingId === null) return;
    const trimmed = editTitle.trim();
    if (!trimmed) return;
    await updateTask(editingId, {
      title: trimmed,
      note: editNote.trim() || null,
    });
    setEditingId(null);
    load();
  };

  const handleMoveUp = async (task: Task, categoryTasks: Task[], indexInGroup: number) => {
    if (indexInGroup === 0) return;
    const prev = categoryTasks[indexInGroup - 1];
    await Promise.all([
      updateTask(task.id, { sort_order: prev.sort_order }),
      updateTask(prev.id, { sort_order: task.sort_order }),
    ]);
    load();
  };

  const handleMoveDown = async (task: Task, categoryTasks: Task[], indexInGroup: number) => {
    if (indexInGroup === categoryTasks.length - 1) return;
    const next = categoryTasks[indexInGroup + 1];
    await Promise.all([
      updateTask(task.id, { sort_order: next.sort_order }),
      updateTask(next.id, { sort_order: task.sort_order }),
    ]);
    load();
  };

  const workTasks = tasks.filter((t) => t.category === "work");
  const personalTasks = tasks.filter((t) => t.category === "personal");

  return (
    <div style={{ padding: "1.5rem", maxWidth: "480px", margin: "0 auto" }}>
      <header style={{ display: "flex", alignItems: "center", marginBottom: "1.5rem" }}>
        <Link to="/" style={{ color: "var(--text-muted)", textDecoration: "none", marginRight: "0.75rem" }}>
          &larr;
        </Link>
        <h1 style={{ fontSize: "1.5rem" }}>Tasks</h1>
      </header>

      {activeCount > 5 && (
        <div
          style={{
            background: "#3d2e00",
            border: "1px solid #665200",
            borderRadius: "var(--radius)",
            padding: "0.75rem 1rem",
            marginBottom: "1rem",
            fontSize: "0.85rem",
            color: "#ffd666",
          }}
        >
          More than 5 active tasks makes check-ins fatiguing — consider pausing some.
        </div>
      )}

      <form onSubmit={handleAdd} style={{ display: "flex", gap: "0.5rem", marginBottom: "1.25rem", alignItems: "flex-end" }}>
        <textarea
          ref={addRef}
          value={newTitle}
          onChange={(e) => {
            setNewTitle(e.target.value);
            e.target.style.height = "auto";
            e.target.style.height = e.target.scrollHeight + "px";
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleAdd(e);
            }
          }}
          placeholder="Add a task..."
          maxLength={120}
          rows={1}
          style={{
            flex: 1,
            minWidth: 0,
            padding: "10px 14px",
            borderRadius: "var(--radius)",
            border: "1px solid var(--accent)",
            background: "var(--bg-card)",
            color: "var(--text)",
            fontSize: "16px",
            resize: "none",
            lineHeight: 1.4,
            overflow: "hidden",
          }}
        />
        <button
          type="button"
          onClick={() => setNewCategory(newCategory === "work" ? "personal" : "work")}
          style={{
            padding: "10px 8px",
            borderRadius: "var(--radius)",
            background: "var(--accent)",
            color: "var(--text)",
            fontSize: "0.8rem",
            whiteSpace: "nowrap",
            flexShrink: 0,
          }}
        >
          {newCategory}
        </button>
        <button type="submit" className="btn-primary" style={{ padding: "10px 14px", flexShrink: 0 }}>
          +
        </button>
      </form>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.25rem", alignItems: "center" }}>
        {(["active", "paused", "archived", "all"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={{
              padding: "6px 12px",
              borderRadius: "var(--radius)",
              background: filter === f ? "var(--accent-bright)" : "var(--accent)",
              color: "var(--text)",
              fontSize: "0.8rem",
            }}
          >
            {f}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <button
          onClick={() => setReordering(!reordering)}
          style={{
            padding: "6px 12px",
            borderRadius: "var(--radius)",
            background: reordering ? "var(--accent-bright)" : "var(--accent)",
            color: "var(--text)",
            fontSize: "0.8rem",
          }}
        >
          {reordering ? "Done" : "Reorder"}
        </button>
      </div>

      {tasks.length === 0 && (
        <p style={{ color: "var(--text-muted)", textAlign: "center", padding: "2rem 0" }}>
          {filter === "active" ? "No active tasks. Add one above." : `No ${filter} tasks.`}
        </p>
      )}

      {workTasks.length > 0 && (
        <TaskGroup
          label="Work"
          tasks={workTasks}
          editingId={editingId}
          editTitle={editTitle}
          editNote={editNote}
          reordering={reordering}
          onEditTitle={setEditTitle}
          onEditNote={setEditNote}
          onStartEdit={handleStartEdit}
          onSaveEdit={handleSaveEdit}
          onCancelEdit={() => setEditingId(null)}
          onStatusChange={handleStatusChange}
          onMoveUp={handleMoveUp}
          onMoveDown={handleMoveDown}
        />
      )}

      {personalTasks.length > 0 && (
        <TaskGroup
          label="Personal"
          tasks={personalTasks}
          editingId={editingId}
          editTitle={editTitle}
          editNote={editNote}
          reordering={reordering}
          onEditTitle={setEditTitle}
          onEditNote={setEditNote}
          onStartEdit={handleStartEdit}
          onSaveEdit={handleSaveEdit}
          onCancelEdit={() => setEditingId(null)}
          onStatusChange={handleStatusChange}
          onMoveUp={handleMoveUp}
          onMoveDown={handleMoveDown}
        />
      )}
    </div>
  );
}

function TaskGroup({
  label,
  tasks,
  editingId,
  editTitle,
  editNote,
  reordering,
  onEditTitle,
  onEditNote,
  onStartEdit,
  onSaveEdit,
  onCancelEdit,
  onStatusChange,
  onMoveUp,
  onMoveDown,
}: {
  label: string;
  tasks: Task[];
  editingId: number | null;
  editTitle: string;
  editNote: string;
  reordering: boolean;
  onEditTitle: (v: string) => void;
  onEditNote: (v: string) => void;
  onStartEdit: (t: Task) => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onStatusChange: (t: Task, s: Task["status"]) => void;
  onMoveUp: (t: Task, categoryTasks: Task[], i: number) => void;
  onMoveDown: (t: Task, categoryTasks: Task[], i: number) => void;
}) {
  return (
    <section style={{ marginBottom: "1.25rem" }}>
      <h2
        style={{
          fontSize: "0.8rem",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          color: "var(--text-muted)",
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
        {tasks.map((task, index) => {
          const isEditing = editingId === task.id;

          return (
            <div
              key={task.id}
              style={{
                padding: "0.75rem 1rem",
                borderBottom: "1px solid rgba(255,255,255,0.05)",
                opacity: task.status !== "active" ? 0.6 : 1,
              }}
            >
              {isEditing ? (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => onEditTitle(e.target.value)}
                    maxLength={120}
                    style={{
                      padding: "8px 10px",
                      borderRadius: "8px",
                      border: "1px solid var(--accent)",
                      background: "var(--bg)",
                      color: "var(--text)",
                      fontSize: "0.9rem",
                    }}
                  />
                  <textarea
                    value={editNote}
                    onChange={(e) => onEditNote(e.target.value)}
                    placeholder="Note (optional)"
                    rows={2}
                    style={{
                      padding: "8px 10px",
                      borderRadius: "8px",
                      border: "1px solid var(--accent)",
                      background: "var(--bg)",
                      color: "var(--text)",
                      fontSize: "0.85rem",
                      resize: "vertical",
                    }}
                  />
                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    <button className="btn-primary" onClick={onSaveEdit} style={{ padding: "6px 14px", fontSize: "0.85rem" }}>
                      Save
                    </button>
                    <button className="btn-secondary" onClick={onCancelEdit} style={{ padding: "6px 14px", fontSize: "0.85rem" }}>
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <div style={{ flex: 1, cursor: "pointer" }} onClick={() => onStartEdit(task)}>
                    <div style={{ fontSize: "0.95rem" }}>{task.title}</div>
                    {task.note && (
                      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: "2px" }}>
                        {task.note}
                      </div>
                    )}
                  </div>
                  <div style={{ display: "flex", gap: "4px", flexShrink: 0 }}>
                    {reordering ? (
                      <>
                        <ActionBtn label="↑" onClick={() => onMoveUp(task, tasks, index)} disabled={index === 0} />
                        <ActionBtn label="↓" onClick={() => onMoveDown(task, tasks, index)} disabled={index === tasks.length - 1} />
                      </>
                    ) : (
                      <>
                        {task.status === "active" && (
                          <ActionBtn label="⏸" onClick={() => onStatusChange(task, "paused")} />
                        )}
                        {task.status === "paused" && (
                          <ActionBtn label="▶" onClick={() => onStatusChange(task, "active")} />
                        )}
                        {task.status !== "archived" && (
                          <ActionBtn label="✕" onClick={() => onStatusChange(task, "archived")} />
                        )}
                        {task.status === "archived" && (
                          <ActionBtn label="↩" onClick={() => onStatusChange(task, "active")} />
                        )}
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ActionBtn({ label, onClick, disabled }: { label: string; onClick: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: "4px 8px",
        borderRadius: "6px",
        background: "var(--accent)",
        color: "var(--text)",
        fontSize: "0.8rem",
        minWidth: "28px",
        opacity: disabled ? 0.3 : 1,
      }}
    >
      {label}
    </button>
  );
}

export default TasksPage;
