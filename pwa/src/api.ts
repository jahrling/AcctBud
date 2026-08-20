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
  if (!res.ok) throw new Error("Failed to fetch tasks");
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

// Check-ins

export interface CheckInItem {
  id: number;
  task_id: number;
  task_title: string;
  task_category: string;
  done: boolean;
}

export interface CheckIn {
  id: number;
  for_date: string;
  created_at: string;
  notified_at: string | null;
  completed_at: string | null;
  status: "pending" | "completed" | "missed";
  note: string | null;
  items: CheckInItem[];
  reflection_finished: boolean;
  reflection_journal_written: boolean;
}

export async function getTodayCheckIn(): Promise<CheckIn> {
  const res = await fetch(`${BASE}/api/checkins/today`);
  if (!res.ok) throw new Error("Failed to fetch today's check-in");
  return res.json();
}

export async function completeCheckIn(
  id: number,
  doneTaskIds: number[],
  note?: string,
): Promise<CheckIn> {
  const res = await fetch(`${BASE}/api/checkins/${id}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ done_task_ids: doneTaskIds, note: note ?? null }),
  });
  if (!res.ok) throw new Error("Failed to complete check-in");
  return res.json();
}

export async function getCheckIns(limit = 30): Promise<{ checkins: CheckIn[] }> {
  const res = await fetch(`${BASE}/api/checkins?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to fetch check-ins");
  return res.json();
}

// Reflections

export interface ReflectionMessage {
  id: number;
  role: "assistant" | "user";
  content: string;
  created_at: string;
}

export interface ReflectionData {
  messages: ReflectionMessage[];
  finished: boolean;
}

export async function getReflection(checkinId: number): Promise<ReflectionData> {
  const res = await fetch(`${BASE}/api/reflections/${checkinId}`);
  if (!res.ok) throw new Error("Failed to fetch reflection");
  return res.json();
}

export async function streamReflectionChat(
  checkinId: number,
  message: string | null,
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (error: string) => void,
): Promise<void> {
  const res = await fetch(`${BASE}/api/reflections/${checkinId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  if (!res.ok) {
    onError("Failed to start reflection chat");
    return;
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop()!;

    for (const block of parts) {
      const eventMatch = block.match(/^event: (\w+)/m);
      const dataMatch = block.match(/^data: (.+)$/m);
      if (!eventMatch || !dataMatch) continue;

      const eventType = eventMatch[1];
      const data = JSON.parse(dataMatch[1]);

      if (eventType === "token") {
        onToken(data.content);
      } else if (eventType === "done") {
        onDone();
        return;
      } else if (eventType === "error") {
        onError(data.detail || "LLM error");
        return;
      }
    }
  }

  // Process any remaining buffer after stream ends
  if (buffer.trim()) {
    const eventMatch = buffer.match(/^event: (\w+)/m);
    const dataMatch = buffer.match(/^data: (.+)$/m);
    if (eventMatch && dataMatch) {
      const eventType = eventMatch[1];
      const data = JSON.parse(dataMatch[1]);
      if (eventType === "token") {
        onToken(data.content);
      } else if (eventType === "done") {
        onDone();
        return;
      } else if (eventType === "error") {
        onError(data.detail || "LLM error");
        return;
      }
    }
  }
  onDone();
}

export async function finishReflection(
  checkinId: number,
): Promise<{ journal_written: boolean }> {
  const res = await fetch(`${BASE}/api/reflections/${checkinId}/finish`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to finish reflection");
  return res.json();
}
