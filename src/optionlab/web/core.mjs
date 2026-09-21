// Presentation helpers only. The server remains authoritative for risk and fills.
export const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
export function date(value) {
  if (!value) return new Date(NaN);
  const s = String(value);
  return new Date(
    /Z$|[+-]\d\d:\d\d$/.test(s)
      ? s
      : s.length === 10
        ? s + "T00:00:00Z"
        : s + "Z",
  );
}
export const number = (value, digits = 2) =>
  value == null || !Number.isFinite(Number(value))
    ? "—"
    : new Intl.NumberFormat("en-IN", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      }).format(Number(value));
export const money = (value) =>
  value == null || !Number.isFinite(Number(value))
    ? "—"
    : new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 2,
      }).format(Number(value));
export const signed = (value) => (Number(value) > 0 ? "+" : "") + number(value);
export function when(value, withDate = true) {
  const d = date(value);
  return Number.isNaN(d.getTime())
    ? "—"
    : d.toLocaleString("en-IN", {
        timeZone: "Asia/Kolkata",
        ...(withDate ? { day: "2-digit", month: "short" } : {}),
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
}
export function age(value, now = Date.now()) {
  const seconds = Math.max(0, Math.floor((now - date(value).getTime()) / 1000));
  if (!Number.isFinite(seconds)) return "No data";
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}
export function isFresh(value, maxAge, now = Date.now()) {
  const seconds = (now - date(value).getTime()) / 1000;
  return Number.isFinite(seconds) && seconds >= -5 && seconds <= maxAge;
}
export const proposalStatus = (p, now = Date.now()) =>
  p.status === "PROPOSED"
    ? date(p.expires_at).getTime() <= now
      ? "expired"
      : "pending"
    : p.status.toLowerCase();
export function csv(rows) {
  return rows
    .map((row) =>
      row
        .map((value) => {
          let text = String(value ?? "");
          if (/^[=+@\-\t\r]/.test(text)) text = "'" + text;
          return '"' + text.replaceAll('"', '""') + '"';
        })
        .join(","),
    )
    .join("\r\n");
}
export const humanize = (value) =>
  String(value ?? "")
    .replaceAll("_", " ")
    .replaceAll(".", " · ")
    .replace(/^./, (c) => c.toUpperCase());
