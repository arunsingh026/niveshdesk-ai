import { initializeApp, getApps } from "firebase/app";
import { getMessaging, getToken, isSupported, onMessage, type MessagePayload } from "firebase/messaging";

const API = window.location.hostname === "localhost" ? "http://localhost:8000" : window.location.origin;

export type PushResult = { ok: boolean; reason?: "unsupported" | "install_required" | "not_configured" | "denied"; token?: string };

export async function enablePushNotifications(onForeground?: (payload: MessagePayload) => void): Promise<PushResult> {
  if (!("serviceWorker" in navigator) || !(await isSupported())) return { ok: false, reason: "unsupported" };
  const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const isStandalone = window.matchMedia("(display-mode: standalone)").matches || (navigator as Navigator & { standalone?: boolean }).standalone;
  if (isIos && !isStandalone) return { ok: false, reason: "install_required" };

  const config = await fetch(`${API}/api/notifications/firebase-config`).then(response => response.json());
  if (!config.configured) return { ok: false, reason: "not_configured" };
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return { ok: false, reason: "denied" };

  const registration = await navigator.serviceWorker.register("/firebase-messaging-sw.js", { scope: "/" });
  const app = getApps()[0] || initializeApp({
    apiKey: config.apiKey,
    authDomain: config.authDomain,
    projectId: config.projectId,
    storageBucket: config.storageBucket,
    messagingSenderId: config.messagingSenderId,
    appId: config.appId,
  });
  const messaging = getMessaging(app);
  const token = await getToken(messaging, { vapidKey: config.vapidKey, serviceWorkerRegistration: registration });
  if (!token) return { ok: false, reason: "denied" };
  await fetch(`${API}/api/notifications/devices`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, device_label: `${navigator.platform || "Mobile"} browser` }),
  });
  localStorage.setItem("niveshdesk_push_token", token);
  if (onForeground) onMessage(messaging, onForeground);
  return { ok: true, token };
}
