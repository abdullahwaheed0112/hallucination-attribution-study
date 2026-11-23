/* Shared helpers. Both views are built from these functions, so text, collapse rule, search and answer action are
   identical by construction; selftest.html checks that this holds in the rendered DOM. */
(function () {
  const DAV = (window.DAV = {});
  DAV.VERSION = "0.1.0";
  DAV.COLLAPSE_WORDS = 150;           // tool output longer than this is collapsed behind "Expand"
  DAV.TRIAL_MS = 4 * 60 * 1000;       // per-trial cap
  DAV.AI_TEXT = "AI suggests this step";
  DAV.TASK_TEXT = "This run ended with a wrong answer. Select the first step where an agent stated something not supported by the task, the earlier steps or a tool's output.";
  DAV.FEATURES = { filter: true, blockB: true };   // cut line: set either to false to drop it

  DAV.el = function (tag, attrs, kids) {
    const e = document.createElement(tag);
    for (const k in attrs || {}) {
      if (k === "class") e.className = attrs[k];
      else if (k === "text") e.textContent = attrs[k];
      else if (k.slice(0, 2) === "on") e.addEventListener(k.slice(2), attrs[k]);
      else e.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach((c) => c && e.appendChild(typeof c === "string" ? document.createTextNode(c) : c));
    return e;
  };

  DAV.countWords = function (s) { s = String(s).trim(); return s ? s.split(/\s+/).length : 0; };

  /* Seeded RNG (mulberry32) and string hash, used for the per-participant trial order. */
  DAV.hash = function (s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; };
  DAV.rng = function (seed) { let a = seed >>> 0; return function () { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; };
  DAV.shuffle = function (arr, rnd) { const a = arr.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };

  /* A step is shown as up to three sections. Same function for both views. */
  DAV.sections = function (st) {
    const s = [];
    if (st.text.trim() !== "") s.push({ kind: "message", label: "Message", text: st.text });
    if (st.tool_calls.length) s.push({ kind: "call", label: "Tool call", text: st.tool_calls.join("\n") });
    if (st.tool_output.length) {
      const text = st.tool_output.join("\n\n");
      const w = DAV.countWords(text);
      s.push({ kind: "output", label: "Tool output", text: text, words: w, collapsible: w > DAV.COLLAPSE_WORDS });
    }
    if (!s.length) s.push({ kind: "empty", label: "", text: "(no content)" });
    return s;
  };
  DAV.isToolStep = (st) => st.tool_calls.length > 0 || st.tool_output.length > 0;
  DAV.headerText = (st) => "[Step " + st.step + "] " + st.agent;

  /* Search: case-insensitive, over section texts only (not headers or labels), steps hidden by the agent filter excluded. */
  DAV.findMatches = function (item, q, hiddenAgents) {
    const res = [];
    if (!q) return res;
    const re = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
    item.steps.forEach((st) => {
      if (hiddenAgents && hiddenAgents.has(st.agent)) return;
      DAV.sections(st).forEach((sec, si) => {
        if (sec.kind === "empty") return;
        re.lastIndex = 0;
        let m;
        while ((m = re.exec(sec.text)) !== null) res.push({ step: st.step, sec: si, start: m.index, len: m[0].length });
      });
    });
    return res;
  };

  /* Put text into a node with <mark> around matches. textContent stays equal to the text. */
  DAV.fillHighlighted = function (node, text, matches, curMatch) {
    let pos = 0;
    matches.forEach((m) => {
      if (m.start > pos) node.appendChild(document.createTextNode(text.slice(pos, m.start)));
      const mk = DAV.el("mark", { class: m === curMatch ? "hit cur" : "hit" });
      mk.textContent = text.slice(m.start, m.start + m.len);
      node.appendChild(mk);
      pos = m.start + m.len;
    });
    if (pos < text.length) node.appendChild(document.createTextNode(text.slice(pos)));
  };

  /* The body of one step. st: step; S: view state (expanded set, hidden agents, matches, cur). */
  DAV.renderBody = function (st, S) {
    if (S.hidden.has(st.agent)) return DAV.el("div", { class: "step-body filtered", text: "Hidden by agent filter" });
    const body = DAV.el("div", { class: "step-body" });
    DAV.sections(st).forEach((sec, si) => {
      const open = !(sec.kind === "output" && sec.collapsible && !S.expanded.has(st.step));
      const lbl = sec.kind === "output"
        ? "Tool output (" + sec.words + " words" + (open ? "" : ", collapsed") + ")"
        : sec.label;
      const wrap = DAV.el("div", { class: "sec sec-" + sec.kind });
      if (lbl) wrap.appendChild(DAV.el("div", { class: "lbl", text: lbl }));
      if (open) {
        const pre = DAV.el("pre", { class: "txt" });
        const mine = S.matches.filter((m) => m.step === st.step && m.sec === si);
        DAV.fillHighlighted(pre, sec.text, mine, S.matches[S.cur]);
        wrap.appendChild(pre);
      }
      if (sec.kind === "output" && sec.collapsible) {
        wrap.appendChild(DAV.el("button", {
          class: "ctl expand", type: "button", text: open ? "Collapse" : "Expand",
          onclick: () => { if (open) S.expanded.delete(st.step); else S.expanded.add(st.step); S.log("expand", { step: st.step, open: !open }); S.refresh(); },
        }));
      }
      body.appendChild(wrap);
    });
    return body;
  };

  DAV.badge = () => DAV.el("span", { class: "badge", text: DAV.AI_TEXT });

  /* Shared task block, find box and agent filter. Rendered once per trial, identical in both views. */
  DAV.renderTask = function (item) {
    return DAV.el("section", { class: "task" }, [
      DAV.el("p", { class: "task-q", text: DAV.TASK_TEXT }),
      DAV.el("details", { open: "open" }, [DAV.el("summary", { text: "Question" }), DAV.el("pre", { class: "txt", text: item.question })]),
      DAV.el("details", { open: "open" }, [DAV.el("summary", { text: "System's final answer" }), DAV.el("pre", { class: "txt", text: item.agent_answer })]),
      DAV.el("div", { class: "ref" }, [DAV.el("strong", { text: "Reference answer: " }), DAV.el("span", { class: "refans", text: item.true_answer })]),
    ]);
  };

  DAV.renderControls = function (item, S) {
    const count = DAV.el("span", { class: "count", "aria-live": "polite", text: "" });
    const input = DAV.el("input", { type: "search", id: "findbox", placeholder: "Find in trace", "aria-label": "Find in trace" });
    function updateCount() {
      count.textContent = S.query ? (S.matches.length ? (S.cur + 1) + " of " + S.matches.length : "0 matches") : "";
    }
    S.updateCount = updateCount;
    function recompute() { S.matches = DAV.findMatches(item, S.query, S.hidden); S.cur = S.matches.length ? 0 : -1; }
    S.recompute = recompute;
    function go(d) {
      if (!S.matches.length) return;
      S.cur = (S.cur + d + S.matches.length) % S.matches.length;
      const m = S.matches[S.cur];
      const st = item.steps[m.step - 1], sec = DAV.sections(st)[m.sec];
      if (sec.kind === "output" && sec.collapsible) S.expanded.add(st.step);
      S.log("search_nav", { index: S.cur, step: m.step });
      S.focusMatch(m);
      S.refresh();
    }
    let t = null;
    input.addEventListener("input", () => {
      S.query = input.value;
      recompute();
      clearTimeout(t);
      t = setTimeout(() => S.log("search", { query: S.query, matches: S.matches.length }), 600);
      if (S.matches.length) S.focusMatch(S.matches[0], true);
      S.refresh();
    });
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); go(e.shiftKey ? -1 : 1); } });
    const bar = DAV.el("div", { class: "controls" }, [
      DAV.el("label", { for: "findbox", text: "Find: " }), input, count,
      DAV.el("button", { type: "button", class: "ctl", id: "prevbtn", text: "Previous", onclick: () => go(-1) }),
      DAV.el("button", { type: "button", class: "ctl", id: "nextbtn", text: "Next", onclick: () => go(1) }),
    ]);
    if (DAV.FEATURES.filter && item.agents.length > 1) {
      const f = DAV.el("div", { class: "filter" }, [DAV.el("span", { text: "Show agents: " })]);
      item.agents.forEach((a) => {
        const cb = DAV.el("input", { type: "checkbox", checked: "checked", "data-agent": a });
        cb.addEventListener("change", () => {
          if (cb.checked) S.hidden.delete(a); else S.hidden.add(a);
          recompute(); S.log("filter", { agent: a, shown: cb.checked });
          S.refresh();
        });
        f.appendChild(DAV.el("label", { class: "fchk" }, [cb, " " + a]));
      });
      bar.appendChild(f);
    }
    return bar;
  };

  DAV.newState = function (item, opts) {
    return Object.assign({
      query: "", matches: [], cur: -1, expanded: new Set(), hidden: new Set(), selected: null,
      suggestion: null, log: function () {}, refresh: function () {}, onSelect: function () {}, updateCount: function () {},
    }, opts || {});
  };

  /* Same confirmation step for both views. */
  DAV.confirmStep = function (st, ok) {
    const back = DAV.el("div", { class: "modal-back" });
    const box = DAV.el("div", { class: "modal", role: "dialog", "aria-modal": "true" }, [
      DAV.el("p", { text: "Submit " + DAV.headerText(st) + " as your answer?" }),
      DAV.el("button", { type: "button", id: "confirm-yes", class: "primary", text: "Confirm", onclick: () => { back.remove(); ok(); } }),
      DAV.el("button", { type: "button", id: "confirm-no", text: "Cancel", onclick: () => back.remove() }),
    ]);
    back.appendChild(box);
    document.body.appendChild(back);
    box.querySelector("#confirm-yes").focus();
  };
})();
