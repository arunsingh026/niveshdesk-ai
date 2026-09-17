import { initializeApp, getApps } from "firebase/app";
import { getMessaging, getToken, isSupported, onMessage, type MessagePayload } from "firebase/messaging";

const API = window.location.hostname === "localhost" ? "http://localhost:8000" : window.location.origin;

export type PushResult = { ok: boolean; reason?: "unsupported" | "install_required" | "not_configured" | "denied" | "registration_failed"; token?: string };
export type PushDeviceStatus = {
  supported: boolean;
  permission: NotificationPermission | "unsupported";
  installed: boolean;
  ios: boolean;
  tokenPresent: boolean;
};

export async function getPushDeviceStatus(): Promise<PushDeviceStatus> {
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const installed = window.matchMedia("(display-mode: standalone)").matches || Boolean((navigator as Navigator & { standalone?: boolean }).standalone);
  const supported = "Notification" in window && "serviceWorker" in navigator && await isSupported().catch(() => false);
  const storedToken = localStorage.getItem("niveshdesk_push_token");
  let tokenPresent = false;
  if (storedToken) {
    try {
      const response = await fetch(`${API}/api/notifications/devices/status`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: storedToken, device_label: `${navigator.platform || "Mobile"} browser` }),
      });
      tokenPresent = response.ok && Boolean((await response.json()).registered);
    } catch { tokenPresent = false; }
  }
  return {
    supported,
    permission: supported ? Notification.permission : "unsupported",
    installed,
    ios,
    tokenPresent,
  };
}

async function connectPush(requestPermission: boolean, onForeground?: (payload: MessagePayload) => void): Promise<PushResult> {
  if (!("serviceWorker" in navigator) || !(await isSupported())) return { ok: false, reason: "unsupported" };
  const isIos = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const isStandalone = window.matchMedia("(display-mode: standalone)").matches || (navigator as Navigator & { standalone?: boolean }).standalone;
  if (isIos && !isStandalone) return { ok: false, reason: "install_required" };

  const config = await fetch(`${API}/api/notifications/firebase-config`).then(response => response.json());
  if (!config.configured) return { ok: false, reason: "not_configured" };
  const permission = Notification.permission === "granted" ? "granted" : requestPermission ? await Notification.requestPermission() : Notification.permission;
  if (permission !== "granted") return { ok: false, reason: "denied" };

  await navigator.serviceWorker.register("/firebase-messaging-sw.js", { scope: "/" });
  const registration = await navigator.serviceWorker.ready;
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
  const registrationResponse = await fetch(`${API}/api/notifications/devices`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, device_label: `${navigator.platform || "Mobile"} browser` }),
  });
  if (!registrationResponse.ok || !(await registrationResponse.json()).registered) {
    return { ok: false, reason: "registration_failed" };
  }
  localStorage.setItem("niveshdesk_push_token", token);
  if (onForeground) onMessage(messaging, onForeground);
  return { ok: true, token };
}

export async function enablePushNotifications(onForeground?: (payload: MessagePayload) => void): Promise<PushResult> {
  return connectPush(true, onForeground);
}

export async function repairPushRegistration(onForeground?: (payload: MessagePayload) => void): Promise<PushResult> {
  return connectPush(false, onForeground);
}
