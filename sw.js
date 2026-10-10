// Offline-Unterstützung: Dateien der App zwischenspeichern.
// Bei jeder neuen Version VERSION erhöhen, damit alle Handys die neuen Dateien holen.
const VERSION = "v15";
const FILES = ["./", "index.html", "abcjs-basic-min.js", "logo.png", "splash-logo-w.png", "manifest.webmanifest", "icon-192.png", "icon-512.png", "apple-touch-icon.png", "favicon.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(VERSION).then(c => c.addAll(FILES)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSION).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
// Zuerst das Netz (damit Änderungen sofort ankommen), ohne Netz aus dem Speicher
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET" || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(VERSION).then(c => c.put(e.request, copy)); return r; }).catch(() => caches.match(e.request).then(m => m || caches.match("index.html"))));
});
