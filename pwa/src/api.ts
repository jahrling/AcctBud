const BASE = import.meta.env.BASE_URL.replace(/\/$/, "");

export async function getVapidPublicKey(): Promise<string> {
  const res = await fetch(`${BASE}/api/push/vapid-public-key`);
  const data = await res.json();
  return data.publicKey;
}

export async function registerSubscription(subscription: PushSubscription): Promise<void> {
  const sub = subscription.toJSON();
  await fetch(`${BASE}/api/push/subscriptions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      endpoint: sub.endpoint,
      keys: sub.keys,
      expirationTime: sub.expirationTime ?? null,
    }),
  });
}

export async function removeSubscription(endpoint: string): Promise<void> {
  await fetch(`${BASE}/api/push/subscriptions`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ endpoint }),
  });
}

export async function sendTestPush(): Promise<{ results: string[]; count: number }> {
  const res = await fetch(`${BASE}/api/push/test`, { method: "POST" });
  return res.json();
}

export async function getHealth(): Promise<{ version: string; server_time: string; timezone: string }> {
  const res = await fetch(`${BASE}/api/health`);
  return res.json();
}

// Tasks

export interface Task {
  id: number;
  title: string;
  note: string | null;
  category: "work" | "personal";
  status: "active" | "paused" | "archived";
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface TaskListResponse {
  tasks: Task[];
  active_count: number;
}

export async function getTasks(status = "active"): Promise<TaskListResponse> {
  const res = await fetch(`${BASE}/api/tasks?status=${status}`);
  return res.json();
}

export async function createTask(
  title: string,
  category: "work" | "personal",
  note?: string,
): Promise<Task> {
  const res = await fetch(`${BASE}/api/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, category, note: note ?? null }),
  });
  if (!res.ok) throw new Error("Failed to create task");
  return res.json();
}

export async function updateTask(
  id: number,
  data: Partial<Pick<Task, "title" | "note" | "category" | "status" | "sort_order">>,
): Promise<Task> {
  const res = await fetch(`${BASE}/api/tasks/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update task");
  return res.json();
}
