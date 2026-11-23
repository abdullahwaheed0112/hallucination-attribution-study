/* Logging. Records are kept in localStorage (key dav_records_v1) with an in-memory fallback if storage is blocked.
   One record per trial (type "trial"), plus tlx, background, final and screen records. See SCHEMA.md. */
(function () {
  const KEY = "dav_records_v1";
  let mem = [];
  let useMem = false;
  function read() {
    if (useMem) return mem;
    try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch (e) { useMem = true; return mem; }
  }
  function write(a) {
    if (useMem) { mem = a; return; }
    try { localStorage.setItem(KEY, JSON.stringify(a)); } catch (e) { useMem = true; mem = a; }
  }
  const store = (DAV.store = {});
  store.all = read;
  store.add = function (rec) { const a = read(); a.push(rec); write(a); mem = a; };
  store.clear = function () { write([]); mem = []; };
  store.usingMemory = () => useMem;

  function csvCell(v) {
    if (v === null || v === undefined) return "";
    const s = typeof v === "object" ? JSON.stringify(v) : String(v);
    return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }
  function toCsv(rows, cols) {
    return [cols.join(",")].concat(rows.map((r) => cols.map((c) => csvCell(r[c])).join(","))).join("\r\n") + "\r\n";
  }
  store.TRIAL_COLS = ["participant", "data_label", "session_id", "list", "view_order", "block", "trial_index", "item", "view", "chosen_step", "timed_out", "time_ms",
    "confidence", "suggestion_key", "suggestion_step", "suggestion_shown", "suggestion_accepted", "n_search", "n_details", "n_filter", "n_scroll", "n_expand", "events", "app_version", "timestamp"];
  store.TLX_COLS = ["participant", "data_label", "session_id", "view", "block", "mental", "physical", "temporal", "performance", "effort", "frustration", "raw_tlx", "timestamp"];
  store.SCREEN_COLS = ["screener", "item", "index", "reserve", "practice_item", "chosen_step", "no_step_found", "time_ms", "confidence", "final_answer_correct", "offensive_or_personal", "ambiguous", "comment", "app_version", "timestamp"];
  store.csv = function (type) {
    const rows = read().filter((r) => r.type === type);
    if (type === "trial") return toCsv(rows, store.TRIAL_COLS);
    if (type === "tlx") return toCsv(rows.map((r) => Object.assign({}, r, r.scores, { raw_tlx: r.raw_tlx })), store.TLX_COLS);
    if (type === "screen") return toCsv(rows, store.SCREEN_COLS);
    throw new Error("unknown type");
  };
  store.json = () => JSON.stringify({ app_version: DAV.VERSION, exported: new Date().toISOString(), records: read() }, null, 1);
  store.download = function (name, text, mime) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: mime || "text/plain" }));
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  };
  store.counts = function () {
    const c = {};
    read().forEach((r) => { c[r.type] = (c[r.type] || 0) + 1; });
    return c;
  };
})();
