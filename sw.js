// Offline-Unterstützung: Dateien der App zwischenspeichern.
// Bei jeder neuen Version VERSION erhöhen, damit alle Handys die neuen Dateien holen.
const VERSION = "v106";
// Verschlüsselte Aufnahmen ändern sich nie (neue Aufnahme = neuer Dateiname), darum eigener, dauerhafter Speicher
const DATEN = "mg-daten-1";
// Entschlüsselte Aufnahmen für die laufende Sitzung (die App legt sie hier ab). Das iPhone springt in Aufnahmen
// nur zuverlässig, wenn sie wie eine echte Datei mit Teilstücken (Range) geliefert werden, nicht als Blob.
const HOER = "mg-hoeren";
const HB = new Map();
async function hoeren(req) {
  const key = req.url.split("?")[0];
  let buf = HB.get(key);
  if (!buf) { const m = await (await caches.open(HOER)).match(key); if (!m) return new Response("", { status: 404 }); buf = await m.arrayBuffer(); HB.clear(); HB.set(key, buf); }
  const n = buf.byteLength, h = req.headers.get("range"), base = { "Content-Type": "audio/mpeg", "Accept-Ranges": "bytes", "Cache-Control": "no-store" };
  const mm = h && /bytes=(\d*)-(\d*)/.exec(h);
  if (!mm) return new Response(buf, { status: 200, headers: Object.assign({ "Content-Length": String(n) }, base) });
  let a, b;
  if (mm[1] === "") { a = Math.max(0, n - Number(mm[2])); b = n - 1; } else { a = Number(mm[1]); b = mm[2] === "" ? n - 1 : Math.min(Number(mm[2]), n - 1); }
  if (a >= n || a > b) return new Response("", { status: 416, headers: { "Content-Range": `bytes */${n}` } });
  return new Response(buf.slice(a, b + 1), { status: 206, headers: Object.assign({ "Content-Length": String(b - a + 1), "Content-Range": `bytes ${a}-${b}/${n}` }, base) });
}
const FILES = ["./", "index.html", "abcjs-basic-min.js", "logo.png", "splash-logo-w.png", "manifest.webmanifest", "icon-192.png", "icon-512.png", "apple-touch-icon.png", "favicon.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(VERSION).then(c => c.addAll(FILES)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== VERSION && k !== DATEN && k !== HOER).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.includes("/hoeren/")) { e.respondWith(hoeren(e.request)); return; }
  // Aufnahmen: zuerst aus dem Speicher (spart Daten), sonst laden und merken
  if (url.pathname.includes("/daten/") && url.pathname.endsWith(".bin") && !url.pathname.endsWith("lieder.bin") && !url.pathname.endsWith("archiv.bin") && !url.pathname.endsWith("termine.bin")) {
    e.respondWith(caches.open(DATEN).then(c => c.match(e.request).then(m => m || fetch(e.request).then(r => { if (r.ok) c.put(e.request, r.clone()); return r; }))));
    return;
  }
  // Alles andere: zuerst das Netz (damit Änderungen sofort ankommen), ohne Netz aus dem Speicher
  e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(VERSION).then(c => c.put(e.request, copy)); return r; }).catch(() => caches.match(e.request).then(m => m || caches.match("index.html"))));
});
