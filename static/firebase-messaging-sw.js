/* Firebase Messaging service worker. Firebase web config is public and loaded from the app. */
importScripts("https://www.gstatic.com/firebasejs/12.2.1/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/12.2.1/firebase-messaging-compat.js");

fetch("/api/notifications/firebase-config")
  .then((response) => response.json())
  .then((config) => {
    if (!config.configured) return;
    firebase.initializeApp({
      apiKey: config.apiKey,
      authDomain: config.authDomain,
      projectId: config.projectId,
      storageBucket: config.storageBucket,
      messagingSenderId: config.messagingSenderId,
      appId: config.appId,
    });
    firebase.messaging();
  });

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
    const existing = windows.find((client) => client.url.includes("/notifications"));
    return existing ? existing.focus() : clients.openWindow("/notifications");
  }));
});
