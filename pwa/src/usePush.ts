import { useCallback, useEffect, useState } from "react";
import { getVapidPublicKey, registerSubscription, removeSubscription } from "./api";

type PushState = "loading" | "unsupported" | "prompt" | "denied" | "subscribed" | "error";

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const array = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) array[i] = raw.charCodeAt(i);
  return array;
}

export function usePush() {
  const [state, setState] = useState<PushState>("loading");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    async function check() {
      if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
        setState("unsupported");
        return;
      }

      const perm = Notification.permission;
      if (perm === "denied") {
        setState("denied");
        return;
      }

      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      setState(sub ? "subscribed" : "prompt");
    }
    check();
  }, []);

  const subscribe = useCallback(async () => {
    try {
      const vapidKey = await getVapidPublicKey();
      const reg = await navigator.serviceWorker.ready;

      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setState("denied");
        return;
      }

      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidKey).buffer as ArrayBuffer,
      });

      await registerSubscription(sub);
      setState("subscribed");
    } catch (e) {
      setError(String(e));
      setState("error");
    }
  }, []);

  const unsubscribe = useCallback(async () => {
    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      if (sub) {
        await removeSubscription(sub.endpoint);
        await sub.unsubscribe();
      }
      setState("prompt");
    } catch (e) {
      setError(String(e));
      setState("error");
    }
  }, []);

  return { state, error, subscribe, unsubscribe };
}
