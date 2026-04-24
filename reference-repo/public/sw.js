// No-op service worker to suppress 404 errors from browser/extension probes
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
