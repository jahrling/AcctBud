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
