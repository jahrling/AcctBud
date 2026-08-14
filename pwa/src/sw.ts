/// <reference lib="webworker" />
import { precacheAndRoute } from "workbox-precaching";

declare let self: ServiceWorkerGlobalScope;

precacheAndRoute(self.__WB_MANIFEST);

self.addEventListener("push", (event) => {
  if (!event.data) return;

  const payload = event.data.json() as { title: string; body: string; url?: string };
  const options: NotificationOptions = {
    body: payload.body,
    data: { url: payload.url || "/" },
    icon: "/icon-192.png",
    badge: "/icon-192.png",
  };

  event.waitUntil(self.registration.showNotification(payload.title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data?.url as string) || "/";

  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if (client.url.includes(self.location.origin) && "focus" in client) {
          client.navigate(url);
          return client.focus();
        }
      }
      return self.clients.openWindow(url);
    })
  );
});
