/* Independent re-implementation of the expected text; compares it with what each view puts in the DOM.
   Does not call DAV.sections or DAV.findMatches to build its expectations. */
(function () {
  const stage = document.getElementById("stage");
  const tally = {}, fails = [];
  function ok(test, cond, msg) {
    const t = (tally[test] = tally[test] || { n: 0, bad: 0 });
    t.n++;
    if (!cond) { t.bad++; if (fails.length < 25) fails.push(test + ": " + msg); }
  }
  const wc = (s) => s.trim().split(/\s+/).filter(Boolean).length;

  function expectedBody(st, expandAll) {
    let out = "";
    if (st.text.trim() !== "") out += "Message" + st.text;
    if (st.tool_calls.length) out += "Tool call" + st.tool_calls.join("\n");
    if (st.tool_output.length) {
      const txt = st.tool_output.join("\n\n"), w = wc(txt), coll = w > 150 && !expandAll;
      out += "Tool output (" + w + " words" + (coll ? ", collapsed" : "") + ")" + (coll ? "" : txt);
    }
    if (st.text.trim() === "" && !st.tool_calls.length && !st.tool_output.length) out += "(no content)";
    return out;
  }
  function bodyText(node) { const c = node.cloneNode(true); c.querySelectorAll(".ctl").forEach((x) => x.remove()); return c.textContent; }
  function expectedHits(item, q, hidden) {
    const per = {}; let total = 0; const ql = q.toLowerCase();
    item.steps.forEach((st) => {
      if (hidden.has(st.agent)) return;
      const secs = [];
      if (st.text.trim() !== "") secs.push(st.text);
      if (st.tool_calls.length) secs.push(st.tool_calls.join("\n"));
      if (st.tool_output.length) secs.push(st.tool_output.join("\n\n"));
      secs.forEach((s) => { const sl = s.toLowerCase(); let i = 0; while ((i = sl.indexOf(ql, i)) >= 0) { per[st.step] = (per[st.step] || 0) + 1; total++; i += q.length; } });
    });
    return { per, total };
  }
  const mk = (kind, item, sugg) => { const v = DAV.makeView(kind, item, { suggestion: sugg || null, log: () => {}, onSubmit: () => {} }); stage.textContent = ""; stage.appendChild(v.root); return v; };
  function setQuery(v, q) { const i = v.root.querySelector("#findbox"); i.value = q; i.dispatchEvent(new Event("input")); }
  function expandAllIn(root) { let g = 0; while (g++ < 60) { const b = Array.from(root.querySelectorAll("button.expand")).find((x) => x.textContent === "Expand"); if (!b) break; b.click(); } }
  const clickMark = (v, k) => v.root.querySelector('g.mark[data-step="' + k + '"]').dispatchEvent(new Event("click"));
  const countText = (n) => (n ? "1 of " + n : "0 matches");

  const items = Object.values(window.ITEMS);
  let collapsedSteps = 0, steps = 0;
  items.forEach((item) => {
    const id = item.id;
    const cTask = mk("console", item).root.querySelector(".task").textContent;
    const vTask = mk("visual", item).root.querySelector(".task").textContent;
    ok("T9 task block: identical text in both views", cTask === vTask, id);
    ok("T9 task block: contains question, final answer, reference answer", cTask.indexOf(item.question) >= 0 && cTask.indexOf(item.agent_answer) >= 0 && cTask.indexOf(item.true_answer) >= 0, id);
    const c = mk("console", item);
    item.steps.forEach((st) => {
      steps++;
      const art = c.root.querySelector("#step-" + st.step);
      ok("T4 console header text", art.querySelector(".title").textContent === "[Step " + st.step + "] " + st.agent, id + " step " + st.step);
      const exp0 = expectedBody(st, false);
      if (exp0 !== expectedBody(st, true)) collapsedSteps++;
      ok("T1 console body, collapsed state", bodyText(art.querySelector(".step-body")) === exp0, id + " step " + st.step);
    });
    expandAllIn(c.root);
    item.steps.forEach((st) => ok("T2 console body, expanded", bodyText(c.root.querySelector("#step-" + st.step + " .step-body")) === expectedBody(st, true), id + " step " + st.step));
    ok("T8 console: one Select button per step", c.root.querySelectorAll("button.select").length === item.steps.length, id);

    let v = mk("visual", item);
    ok("T5 visual: one mark per step", v.root.querySelectorAll("g.mark").length === item.steps.length, id);
    const lanes = Array.from(v.root.querySelectorAll("text.lane-label")).map((x) => x.textContent);
    const expLanes = []; item.steps.forEach((s) => { if (expLanes.indexOf(s.agent) < 0) expLanes.push(s.agent); });
    ok("T5 visual: lane labels = agents in order of first appearance", JSON.stringify(lanes) === JSON.stringify(expLanes), id);
    let changes = 0;
    item.steps.forEach((st, k) => {
      const m = v.root.querySelector('g.mark[data-step="' + st.step + '"]');
      ok("T5 visual: mark lane = step agent", m.getAttribute("data-lane") === st.agent, id + " step " + st.step);
      const tool = st.tool_calls.length > 0 || st.tool_output.length > 0;
      ok("T5 visual: mark type = message vs tool call", m.getAttribute("data-type") === (tool ? "tool" : "message"), id + " step " + st.step);
      if (k > 0 && item.steps[k - 1].agent !== st.agent) { changes++; ok("T5 visual: arrow at each speaker change", !!v.root.querySelector('line.handoff[data-from="' + k + '"][data-to="' + (k + 1) + '"]'), id + " " + k); }
    });
    ok("T5 visual: arrows only at speaker changes", v.root.querySelectorAll("line.handoff").length === changes, id);
    ok("T8 visual: no Select button before a step is chosen", v.root.querySelectorAll("button.select").length === 0, id);
    item.steps.forEach((st) => {
      v = mk("visual", item);
      clickMark(v, st.step);
      const p = v.root.querySelector("#panel");
      ok("T4 visual panel header = console header", p.querySelector(".title").textContent === "[Step " + st.step + "] " + st.agent, id + " step " + st.step);
      ok("T3 visual panel body, collapsed state", bodyText(p.querySelector(".step-body")) === expectedBody(st, false), id + " step " + st.step);
      ok("T8 visual: exactly one Select button, in the panel", p.querySelectorAll("button.select").length === 1 && v.root.querySelectorAll("button.select").length === 1, id + " step " + st.step);
      expandAllIn(v.root);
      ok("T3 visual panel body, expanded", bodyText(v.root.querySelector("#panel .step-body")) === expectedBody(st, true), id + " step " + st.step);
    });
  });

  items.forEach((item) => {
    const id = item.id;
    const qs = ["the", "(", item.true_answer.slice(0, 12), (item.question.split(/\s+/).find((w) => w.length > 5) || "x"), "zzzqqq"];
    qs.forEach((q) => {
      if (!q.trim()) return;
      const e = expectedHits(item, q, new Set());
      const c = mk("console", item); setQuery(c, q);
      ok("T6 search count, console = independent count", c.root.querySelector(".count").textContent === countText(e.total), id + " q=" + q);
      expandAllIn(c.root);
      ok("T6 search: highlights in console = count", c.root.querySelectorAll("mark.hit").length === e.total, id + " q=" + q);
      const v = mk("visual", item); setQuery(v, q);
      ok("T6 search count, visual = independent count", v.root.querySelector(".count").textContent === countText(e.total), id + " q=" + q);
      ok("T6 search: lane marks ringed = steps with a match", v.root.querySelectorAll("g.mark circle.ring").length === Object.keys(e.per).length, id + " q=" + q);
      Object.keys(e.per).forEach((k) => {
        const v2 = mk("visual", item); setQuery(v2, q);
        clickMark(v2, k);
        expandAllIn(v2.root);
        ok("T6 search: highlights in the details panel = matches in that step", v2.root.querySelectorAll("#panel mark.hit").length === e.per[k], id + " q=" + q + " step " + k);
      });
      if (e.total > 1) {
        c.root.querySelector("#nextbtn").click(); v.root.querySelector("#nextbtn").click();
        ok("T6 next: both views report the same position", c.root.querySelector(".count").textContent === v.root.querySelector(".count").textContent && /^2 of /.test(c.root.querySelector(".count").textContent), id + " q=" + q);
      }
    });
    if (item.agents.length > 1) {
      const a = item.agents[0], hid = new Set([a]);
      // (checkbox change events fire only on elements that are in the document, so mount each view before using it)
      const c = mk("console", item);
      c.root.querySelector('input[data-agent="' + a + '"]').click();
      item.steps.forEach((st) => {
        const t = c.root.querySelector("#step-" + st.step + " .step-body").textContent;
        ok("T7 filter: hidden agent's bodies are hidden in console", (t === "Hidden by agent filter") === (st.agent === a), id + " step " + st.step);
      });
      const e = expectedHits(item, "the", hid);
      setQuery(c, "the");
      ok("T7 filter: search ignores hidden agents (console)", c.root.querySelector(".count").textContent === countText(e.total), id);
      const v = mk("visual", item);
      v.root.querySelector('input[data-agent="' + a + '"]').click();
      setQuery(v, "the");
      ok("T7 filter: search ignores hidden agents (visual)", v.root.querySelector(".count").textContent === countText(e.total), id);
      const hs = item.steps.find((s) => s.agent === a);
      clickMark(v, hs.step);
      ok("T7 filter: hidden step in visual panel shows the same note", v.root.querySelector("#panel .step-body").textContent === "Hidden by agent filter", id);
    }
    const st = item.steps[Math.min(1, item.steps.length - 1)];
    const c = mk("console", item, st.step);
    c.root.querySelector("#step-" + st.step + " button.select").click();
    const m1 = document.querySelector(".modal p").textContent; document.querySelector("#confirm-no").click();
    const v = mk("visual", item, st.step);
    clickMark(v, st.step);
    v.root.querySelector("#panel button.select").click();
    const m2 = document.querySelector(".modal p").textContent; document.querySelector("#confirm-no").click();
    ok("T8 confirmation text identical and names the step", m1 === m2 && m1 === "Submit [Step " + st.step + "] " + st.agent + " as your answer?", id);
    ok("T11 badge: console shows exactly one, text exact", c.root.querySelectorAll(".badge").length === 1 && c.root.querySelector("#step-" + st.step + " .badge").textContent === "AI suggests this step", id);
    ok("T11 badge: visual panel badge text exact", v.root.querySelectorAll("#panel .badge").length === 1 && v.root.querySelector("#panel .badge").textContent === "AI suggests this step", id);
    const fl = v.root.querySelectorAll("g.mark text.flag");
    ok("T11 badge: one flag on the suggested mark, same wording in its title", fl.length === 1 && fl[0].parentNode.getAttribute("data-step") === String(st.step) && fl[0].querySelector("title").textContent === "AI suggests this step", id);
    ok("T11 no badge when no suggestion", mk("console", item).root.querySelectorAll(".badge").length === 0 && mk("visual", item).root.querySelectorAll("text.flag").length === 0, id);
  });

  const lines = ["items: " + items.length + "; steps: " + steps + "; steps with collapsed tool output (> 150 words): " + collapsedSteps, "", "test".padEnd(72) + "checks".padStart(7) + "failed".padStart(8)];
  let bad = 0, n = 0;
  Object.keys(tally).sort().forEach((k) => { lines.push(k.padEnd(72) + String(tally[k].n).padStart(7) + String(tally[k].bad).padStart(8)); bad += tally[k].bad; n += tally[k].n; });
  lines.push("", "TOTAL checks: " + n + "   failed: " + bad, bad ? "RESULT: FAIL" : "RESULT: PASS");
  if (fails.length) { lines.push("", "First failures:"); fails.forEach((f) => lines.push("  " + f)); }
  document.getElementById("out").textContent = lines.join("\n");
  document.title = (bad ? "FAIL" : "PASS") + " self-test";
  document.body.setAttribute("data-done", bad ? "fail" : "pass");
})();
