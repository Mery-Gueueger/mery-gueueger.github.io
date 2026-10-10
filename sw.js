// Offline-Unterstützung: Dateien der App zwischenspeichern.
// Bei jeder neuen Version VERSION erhöhen, damit alle Handys die neuen Dateien holen.
const VERSION = "v34";
// Verschlüsselte Aufnahmen ändern sich nie (neue Aufnahme = neuer Dateiname), darum eigener, dauerhafter Speicher
const DATEN = "mg-daten-1";
const FILES = ["./", "index.html", "abcjs-basic-min.js", "logo.png", "splash-logo-w.png", "manifest.webmanifest", "icon-192.png", "icon-512.png", "apple-touch-icon.png", "favicon.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(VERSION).then(c => c.addAll(FILES)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSION && k !== DATEN).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;
  // Aufnahmen: zuerst aus dem Speicher (spart Daten), sonst laden und merken
  if (url.pathname.includes("/daten/") && url.pathname.endsWith(".bin") && !url.pathname.endsWith("lieder.bin")) {
    e.respondWith(caches.open(DATEN).then(c => c.match(e.request).then(m => m || fetch(e.request).then(r => { if (r.ok) c.put(e.request, r.clone()); return r; }))));
    return;
  }
  // Alles andere: zuerst das Netz (damit Änderungen sofort ankommen), ohne Netz aus dem Speicher
  e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(VERSION).then(c => c.put(e.request, copy)); return r; }).catch(() => caches.match(e.request).then(m => m || caches.match("index.html"))));
});
