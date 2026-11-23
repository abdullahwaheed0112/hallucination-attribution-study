/* The two views. "console" = View A, "visual" = View B. Both use the shared task block, find box, agent filter,
   step body renderer and confirmation step from core.js. */
(function () {
  const el = DAV.el;
  const NS = "http://www.w3.org/2000/svg";
  function svg(tag, attrs, kids) {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs || {}) e.setAttribute(k, attrs[k]);
    (kids || []).forEach((c) => c && e.appendChild(c));
    return e;
  }
  const LAYOUT = { labelW: 200, dx: 42, laneH: 50, top: 22, r: 12 };

  /* opts: { suggestion: step number or null, log(type, detail), onSubmit(step) } */
  DAV.makeView = function (kind, item, opts) {
    const S = DAV.newState(item, { log: opts.log, suggestion: opts.suggestion });
    const root = el("div", { class: "view view-" + kind });
    root.appendChild(DAV.renderTask(item));
    root.appendChild(DAV.renderControls(item, S));
    const content = el("div", { class: "content" });
    root.appendChild(content);
    let scrollToCur = false;

    function submitClick(st) {
      S.log("select_click", { step: st.step });
      DAV.confirmStep(st, () => opts.onSubmit(st.step));
    }
    function selectButton(st) {
      return el("button", { type: "button", class: "ctl select", "data-step": st.step, text: "Select this step", onclick: () => submitClick(st) });
    }
    function headerBar(st, tag) {
      return el(tag, { class: "hdr" }, [
        el("span", { class: "title", text: DAV.headerText(st) }),
        S.suggestion === st.step ? DAV.badge() : null,
        selectButton(st),
      ]);
    }

    S.focusMatch = function (m, first) {
      scrollToCur = !first;
      if (kind === "visual") { S.selected = m.step; }
    };

    /* ---------- console ---------- */
    function renderConsole() {
      content.textContent = "";
      const list = el("div", { class: "steps" });
      item.steps.forEach((st) => {
        const a = el("article", { class: "step" + (S.hidden.has(st.agent) ? " is-filtered" : ""), id: "step-" + st.step, "data-step": st.step });
        a.appendChild(headerBar(st, "div"));
        a.appendChild(DAV.renderBody(st, S));
        list.appendChild(a);
      });
      content.appendChild(list);
    }

    /* ---------- visual ---------- */
    function renderVisual() {
      content.textContent = "";
      const L = LAYOUT, n = item.steps.length, lanes = item.agents;
      const W = L.labelW + n * L.dx + 20, H = L.top + lanes.length * L.laneH + 8;
      const g = svg("svg", { width: W, height: H, viewBox: "0 0 " + W + " " + H, role: "group", "aria-label": "Swimlane: one row per agent, steps left to right in order", class: "swim" });
      g.appendChild(svg("defs", {}, [svg("marker", { id: "arr", viewBox: "0 0 10 10", refX: "9", refY: "5", markerWidth: "7", markerHeight: "7", orient: "auto-start-reverse" }, [svg("path", { d: "M 0 0 L 10 5 L 0 10 z", fill: "#555" })])]));
      const cy = (a) => L.top + lanes.indexOf(a) * L.laneH + L.laneH / 2;
      const cx = (k) => L.labelW + (k - 0.5) * L.dx;
      lanes.forEach((a, i) => {
        g.appendChild(svg("rect", { x: 0, y: L.top + i * L.laneH, width: W, height: L.laneH, class: "lane" + (i % 2 ? " alt" : "") + (S.hidden.has(a) ? " dim" : "") }));
        const t = svg("text", { x: 8, y: cy(a) + 4, class: "lane-label" + (S.hidden.has(a) ? " dim" : "") });
        t.textContent = a;
        g.appendChild(t);
      });
      // arrows where the speaker changes (derived from order only)
      for (let k = 1; k < n; k++) {
        const s1 = item.steps[k - 1], s2 = item.steps[k];
        if (s1.agent === s2.agent) continue;
        const x1 = cx(k), y1 = cy(s1.agent), x2 = cx(k + 1), y2 = cy(s2.agent);
        const len = Math.hypot(x2 - x1, y2 - y1), ux = (x2 - x1) / len, uy = (y2 - y1) / len, pad = L.r + 3;
        g.appendChild(svg("line", { x1: x1 + ux * pad, y1: y1 + uy * pad, x2: x2 - ux * pad, y2: y2 - uy * pad, class: "handoff", "marker-end": "url(#arr)", "data-from": k, "data-to": k + 1 }));
      }
      const matched = new Set(S.matches.map((m) => m.step));
      const curStep = S.cur >= 0 ? S.matches[S.cur].step : null;
      item.steps.forEach((st) => {
        const tool = DAV.isToolStep(st), x = cx(st.step), y = cy(st.agent);
        const grp = svg("g", { class: "mark" + (S.hidden.has(st.agent) ? " dim" : "") + (S.selected === st.step ? " sel" : ""), tabindex: "0", role: "button", "data-step": st.step, "data-type": tool ? "tool" : "message", "data-lane": st.agent, "aria-label": DAV.headerText(st) });
        if (matched.has(st.step)) grp.appendChild(svg("circle", { cx: x, cy: y, r: L.r + 5, class: "ring" + (curStep === st.step ? " curring" : ""), "data-match": "1" }));
        if (S.selected === st.step) grp.appendChild(svg("circle", { cx: x, cy: y, r: L.r + 2, class: "selring" }));
        grp.appendChild(tool
          ? svg("rect", { x: x - L.r + 1, y: y - L.r + 1, width: 2 * L.r - 2, height: 2 * L.r - 2, class: "fill-tool" })
          : svg("circle", { cx: x, cy: y, r: L.r, class: "fill-msg" }));
        const num = svg("text", { x: x, y: y + 4, class: "mark-num " + (tool ? "on-tool" : "on-msg") });
        num.textContent = st.step;
        grp.appendChild(num);
        if (S.suggestion === st.step) {
          const f = svg("text", { x: x, y: y - L.r - 4, class: "flag" });
          f.textContent = "AI";
          f.appendChild(svg("title", {}, [])).textContent = DAV.AI_TEXT;
          grp.appendChild(f);
        }
        const pick = () => { S.selected = st.step; S.log("details_open", { step: st.step }); S.refresh(); };
        grp.addEventListener("click", pick);
        grp.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
        g.appendChild(grp);
      });
      const wrap = el("div", { class: "svgwrap" }, []);
      wrap.appendChild(g);
      content.appendChild(wrap);
      content.appendChild(el("div", { class: "legend", "aria-hidden": "true" }, [
        el("span", { class: "sw sw-msg" }), " message  ·  ", el("span", { class: "sw sw-tool" }), " tool call with output  ·  ",
        "arrow: the speaker changes  ·  dashed ring: search match  ·  heavy outline: selected",
      ]));
      const panel = el("div", { class: "panel", id: "panel" });
      if (S.selected == null) {
        panel.appendChild(el("p", { class: "placeholder", text: "Select a step on the timeline to read it." }));
      } else {
        const st = item.steps[S.selected - 1];
        panel.appendChild(headerBar(st, "div"));
        panel.appendChild(DAV.renderBody(st, S));
      }
      content.appendChild(panel);
    }

    S.refresh = function () {
      (kind === "console" ? renderConsole : renderVisual)();
      S.updateCount();
      if (scrollToCur) {
        scrollToCur = false;
        const mk = root.querySelector("mark.cur");
        if (mk) mk.scrollIntoView({ block: "center" });
      }
    };
    S.refresh();
    return { root: root, S: S, kind: kind };
  };
})();
