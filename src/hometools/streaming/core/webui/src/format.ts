/** Format a duration in seconds as `m:ss` or `h:mm:ss`. */
export function fmtTime(s: number): string {
  if (!isFinite(s)) return "0:00";
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = String(Math.floor(s % 60)).padStart(2, "0");
  return h > 0 ? h + ":" + String(m).padStart(2, "0") + ":" + sec : m + ":" + sec;
}

/** Escape `&`, `<`, `>`, `"` for safe interpolation into `innerHTML`. */
export function escHtml(s: unknown): string {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Format a byte count as a human-readable size (`"12.3 MB"`). */
export function formatBytes(bytes: number): string {
  const value = Number(bytes || 0);
  if (value <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let v = value;
  let idx = 0;
  while (v >= 1024 && idx < units.length - 1) {
    v /= 1024;
    idx++;
  }
  return (idx === 0 ? String(v) : v.toFixed(1)) + " " + units[idx];
}
