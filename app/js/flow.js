/* Session flow: start screen, study sequence (practice, Block A in two view blocks with TLX and a break, Block B, final),
   and screening mode. Plain DOM, no framework. */
(function () {
  const el = DAV.el;
  const root = () => document.getElementById("app");
  const VIEW_LABEL = { console: "View A", visual: "View B" };   // neutral names; A = console, B = visual for everyone
  let P = null;   // participant / session info
  let live = null; // trial in progress (for cleanup)

  function show(nodes) { cleanup(); document.querySelectorAll(".modal-back").forEach((m) => m.remove()); const r = root(); r.textContent = ""; (Array.isArray(nodes) ? nodes : [nodes]).forEach((n) => r.appendChild(n)); window.scrollTo(0, 0); }
  function cleanup() { if (live) { live.stop(); live = null; } }
  function nowIso() { return new Date().toISOString(); }
  function base() { return { participant: P.code, data_label: P.dataLabel, session_id: P.sessionId, list: P.list, view_order: P.order === "console" ? "A_first" : "B_first" }; }

  /* ---------------- assignment ---------------- */
  DAV.assign = function (code) {
    const m = /(\d+)/.exec(code);
    if (!m) return null;
    const n = parseInt(m[1], 10);
    if (n < 1) return null;
    const cell = (n - 1) % 8;
    return { n: n, cell: cell, list: Math.floor(cell / 2) + 1, order: cell % 2 === 0 ? "console" : "visual" };
  };
  const other = (v) => (v === "console" ? "visual" : "console");

  /* ---------------- start screen ---------------- */
  function startScreen() {
    const code = el("input", { type: "text", id: "pcode", value: "", placeholder: "P01", size: "8" });
    const label = el("select", { id: "dlabel" }, [el("option", { value: "TEST", text: "TEST: app test, excluded from analysis (default)" }), el("option", { value: "PILOT", text: "PILOT (n = 2): real team-member session, choose deliberately" })]);
    const info = el("div", { class: "small", id: "assigninfo" });
    const listSel = el("select", { id: "listsel" }, [1, 2, 3, 4].map((n) => el("option", { value: n, text: "List " + n })));
    const ordSel = el("select", { id: "ordsel" }, [el("option", { value: "console", text: "View A first" }), el("option", { value: "visual", text: "View B first" })]);
    function upd() {
      const a = DAV.assign(code.value);
      info.textContent = a ? "Participant number " + a.n + " gives list " + a.list + ", " + (a.order === "console" ? "View A" : "View B") + " first. Override below only for testing." : "Enter a code containing a number, for example P01.";
      if (a) { listSel.value = a.list; ordSel.value = a.order; }
    }
    code.addEventListener("input", upd);
    const modeStudy = el("input", { type: "radio", name: "mode", value: "study", checked: "checked", id: "mode-study" });
    const modeScreen = el("input", { type: "radio", name: "mode", value: "screening", id: "mode-screen" });
    const go = el("button", { type: "button", class: "primary", id: "startbtn", text: "Start", onclick: () => {
      const mode = modeScreen.checked ? "screening" : "study";
      const c = code.value.trim();
      if (!c) { alert("Enter a code."); return; }
      if (mode === "study" && !DAV.assign(c)) { alert("The code needs a number, for example P01."); return; }
      P = { code: c, dataLabel: label.value, sessionId: "S" + Date.now().toString(36), list: parseInt(listSel.value, 10), order: ordSel.value, mode: mode };
      if (mode === "screening") screening(); else background();
    } });
    show([
      el("h1", { text: "Trace study app" }),
      el("p", { class: "warn", text: "Researcher use only. No data from anyone outside the two team members may be collected (ethics review is unresolved)." }),
      el("div", { class: "card" }, [
        el("div", { class: "row" }, [el("label", { for: "pcode", text: "Participant code (or screener initials) " }), code, label]),
        el("div", { class: "row" }, [modeStudy, el("label", { for: "mode-study", text: "Study session" }), modeScreen, el("label", { for: "mode-screen", text: "Screening mode (blind labelling of the first hallucinated step)" })]),
        el("div", { class: "row" }, [listSel, ordSel]), info, go,
      ]),
      dataCard(),
    ]);
    upd();
  }

  function dataCard() {
    const c = DAV.store.counts();
    const dl = (name, text, mime) => () => DAV.store.download(name, text(), mime);
    return el("div", { class: "card", id: "datacard" }, [
      el("h2", { text: "Saved data" }),
      el("p", { class: "small", id: "counts", text: "In this browser: " + (Object.keys(c).length ? Object.keys(c).map((k) => c[k] + " " + k).join(", ") : "nothing yet") + (DAV.store.usingMemory() ? " (browser storage blocked: data is kept in memory only, download before closing)" : "") }),
      el("div", { class: "row" }, [
        el("button", { type: "button", id: "dl-json", text: "Download JSON (all)", onclick: dl("trace_study_all.json", DAV.store.json, "application/json") }),
        el("button", { type: "button", id: "dl-trials", text: "Trials CSV", onclick: dl("trials.csv", () => DAV.store.csv("trial"), "text/csv") }),
        el("button", { type: "button", id: "dl-tlx", text: "TLX CSV", onclick: dl("tlx.csv", () => DAV.store.csv("tlx"), "text/csv") }),
        el("button", { type: "button", id: "dl-screen", text: "Screening CSV", onclick: dl("screening.csv", () => DAV.store.csv("screen"), "text/csv") }),
        el("button", { type: "button", id: "clearbtn", text: "Delete saved data", onclick: () => { if (confirm("Delete all saved records in this browser? Download first.")) { DAV.store.clear(); startScreen(); } } }),
      ]),
    ]);
  }

  /* ---------------- generic screens ---------------- */
  function info(title, paras, btnText, next, id) {
    show(el("div", { class: "card" }, [el("h1", { text: title })].concat(paras.map((t) => el("p", { text: t }))).concat([el("button", { type: "button", class: "primary", id: id || "continue", text: btnText || "Continue", onclick: next })])));
  }
  function likert(name, text) {
    const w = el("div", { class: "likert" }, [el("p", { text: text })]);
    [1, 2, 3, 4, 5].forEach((v) => w.appendChild(el("label", {}, [el("input", { type: "radio", name: name, value: v }), " " + v])));
    return w;
  }
  const picked = (name) => { const x = document.querySelector('input[name="' + name + '"]:checked'); return x ? parseInt(x.value, 10) : null; };

  function background() {
    show(el("div", { class: "card" }, [
      el("h1", { text: "A few questions about you" }),
      likert("prog", "How much programming experience do you have? (1 = none, 5 = a lot)"),
      likert("agents", "How much experience do you have with LLM-based agents? (1 = none, 5 = a lot)"),
      el("button", { type: "button", class: "primary", id: "bg-next", text: "Continue", onclick: () => {
        if (picked("prog") === null || picked("agents") === null) { alert("Answer both questions."); return; }
        DAV.store.add(Object.assign({ type: "background", programming: picked("prog"), llm_agents: picked("agents"), timestamp: nowIso() }, base()));
        instructions();
      } }),
    ]));
  }

  function instructions() {
    info("Task", [
      "You will read records of several AI agents working together on a question. Each record is a numbered list of steps.",
      DAV.TASK_TEXT,
      "The agent who wrote that step is treated as the responsible agent, so choosing a step answers both who and when.",
      "You will use two ways of showing the same record, called View A and View B. Both contain the same text. Each trial has a 4-minute limit, shown on screen.",
      "First there are two practice trials with feedback.",
    ], "Start practice", () => runPractice(0), "start-practice");
  }

  /* ---------------- trials ---------------- */
  /* spec: {item, view, block, index, total, suggestionKey, suggestionStep, cap(ms|null), onDone(rec), screeningMode} */
  function trial(spec) {
    const item = window.ITEMS[spec.item];
    const intro = el("div", { class: "card" }, [
      el("h1", { text: (spec.block === "screening" ? "Item " : "Trial ") + spec.index + " of " + spec.total }),
      el("p", { text: spec.block === "screening" ? "Console view. Take the time you need." : VIEW_LABEL[spec.view] + (spec.cap ? ". You have 4 minutes. The timer starts when the record appears." : ".") }),
      el("button", { type: "button", class: "primary", id: "trial-start", text: "Show the record", onclick: begin }),
    ]);
    show(intro);
    function begin() {
      let t0 = performance.now(); const events = [];
      let done = false, timer = null, lastScroll = 0;
      const log = (type, detail) => events.push({ t: Math.round(performance.now() - t0), type: type, detail: detail || null });
      const timerEl = el("span", { class: "timer", id: "timer", text: "" });
      const view = DAV.makeView(spec.view, item, { suggestion: spec.suggestionStep || null, log: log, onSubmit: (step) => finish(step, false) });
      const bar = el("div", { class: "topbar" }, [el("strong", { text: spec.block === "screening" ? "Screening" : VIEW_LABEL[spec.view] }), el("span", { text: (spec.block === "screening" ? "Item " : "Trial ") + spec.index + " of " + spec.total }), timerEl]);
      if (spec.block === "screening") bar.insertBefore(el("button", { type: "button", id: "nostep", text: "I cannot find one / cannot decide", onclick: () => finish(null, false, true) }), timerEl);
      function tick() {
        const left = spec.cap ? Math.max(0, spec.cap - (performance.now() - t0)) : null;
        if (left === null) { timerEl.textContent = Math.floor((performance.now() - t0) / 1000) + " s"; return; }
        const s = Math.ceil(left / 1000);
        timerEl.textContent = Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
        timerEl.classList.toggle("low", s <= 60);
        if (left <= 0) finish(null, true);
      }
      function onScroll() { const n = performance.now(); if (n - lastScroll > 1000) { lastScroll = n; log("scroll", { y: Math.round(window.scrollY) }); } }
      function stop() { clearInterval(timer); document.removeEventListener("scroll", onScroll, true); }
      function finish(step, timedOut, noStep) {
        if (done) return; done = true; stop();
        const ms = Math.round(performance.now() - t0);
        const count = (t) => events.filter((e) => e.type === t).length;
        const rec = Object.assign({
          type: "trial", block: spec.block, trial_index: spec.index, item: spec.item, view: spec.view, chosen_step: step, timed_out: !!timedOut, time_ms: ms, confidence: null,
          suggestion_key: spec.suggestionKey || null, suggestion_step: spec.suggestionStep || null, suggestion_shown: !!spec.suggestionStep,
          suggestion_accepted: spec.suggestionStep ? (step === null ? null : step === spec.suggestionStep) : null,
          n_search: count("search"), n_details: count("details_open"), n_filter: count("filter"), n_scroll: count("scroll"), n_expand: events.filter((e) => e.type === "expand" && e.detail && e.detail.open).length,
          events: events, app_version: DAV.VERSION, timestamp: nowIso(),
        }, base());
        spec.onDone(rec, { timedOut: timedOut, noStep: noStep });
      }
      show([bar, view.root]);          // show() first: it stops the previous trial
      t0 = performance.now();          // timer starts when the record is on screen
      live = { stop: stop };
      document.addEventListener("scroll", onScroll, true);
      timer = setInterval(tick, 250); tick();
    }
  }

  function askConfidence(step, ok) {
    const box = el("div", { class: "card" }, [
      el("h1", { text: "How confident are you?" }),
      el("p", { text: "How confident are you that Step " + step + " is the first step where an agent stated something unsupported? (1 = not at all, 5 = completely)" }),
      el("div", { class: "row" }, [1, 2, 3, 4, 5].map((v) => el("button", { type: "button", class: "conf", "data-v": v, text: String(v), onclick: () => ok(v) }))),
    ]);
    show(box);
  }

  function endTrial(rec, flags, after, feedbackStep) {
    const finishRec = (conf) => {
      rec.confidence = conf;
      DAV.store.add(rec);
      if (feedbackStep) {
        info("Feedback (practice only)", [flags.timedOut ? "Time ran out." : "You chose Step " + rec.chosen_step + ".", "In this record the first hallucinated step is Step " + feedbackStep + ". Real trials give no feedback."], "Continue", after, "fb-continue");
      } else after();
    };
    if (flags.timedOut) info("Time is up", ["The 4 minutes are over. This trial is recorded as unanswered."], "Continue", () => finishRec(null), "timeout-continue");
    else askConfidence(rec.chosen_step, finishRec);
  }

  /* ---------------- study sequence ---------------- */
  function runPractice(i) {
    const D = window.DESIGN;
    if (i >= D.practice.length) return blockA(0);
    const view = i === 0 ? P.order : other(P.order);
    trial({ item: D.practice[i], view: view, block: "practice", index: i + 1, total: D.practice.length, cap: DAV.TRIAL_MS,
      onDone: (rec, fl) => endTrial(rec, fl, () => runPractice(i + 1), D.practice_feedback_step[D.practice[i]]) });
  }

  function blockA(k) {   // k = 0 first view block, 1 second
    const D = window.DESIGN, view = k === 0 ? P.order : other(P.order);
    const items = DAV.shuffle(D.block_a_lists[String(P.list)][view], DAV.rng(DAV.hash(P.code + "|A|" + view)));
    info(k === 0 ? "Main trials: first set" : "Main trials: second set", ["You will now see " + items.length + " records in " + VIEW_LABEL[view] + ". No feedback is given."], "Start", () => {
      const run = (i) => {
        if (i >= items.length) return tlx(view, () => (k === 0 ? breakScreen(other(P.order)) : blockB()));
        trial({ item: items[i], view: view, block: "A", index: i + 1 + (k === 0 ? 0 : 6), total: 12, cap: DAV.TRIAL_MS, onDone: (rec, fl) => endTrial(rec, fl, () => run(i + 1)) });
      };
      run(0);
    }, "start-block");
  }

  function breakScreen(nextView) {
    info("Break", ["Take a short break. Continue when you are ready.", "Next you will use " + VIEW_LABEL[nextView] + "."], "Continue", () => blockA(1), "break-continue");
  }

  const TLX = [
    ["mental", "Mental demand", "How mentally demanding was the task?", "Very low", "Very high"],
    ["physical", "Physical demand", "How physically demanding was the task?", "Very low", "Very high"],
    ["temporal", "Temporal demand", "How hurried or rushed was the pace of the task?", "Very low", "Very high"],
    ["performance", "Performance", "How successful were you in accomplishing what you were asked to do?", "Perfect", "Failure"],
    ["effort", "Effort", "How hard did you have to work to accomplish your level of performance?", "Very low", "Very high"],
    ["frustration", "Frustration", "How insecure, discouraged, irritated, stressed and annoyed were you?", "Very low", "Very high"],
  ];
  function tlx(view, after) {
    const vals = {}, box = el("div", { class: "card tlx" }, [el("h1", { text: "Workload: " + VIEW_LABEL[view] }), el("p", { class: "small", text: "Move each slider to your answer (0 to 100). The button unlocks when you have moved all six." })]);
    const submit = el("button", { type: "button", class: "primary", id: "tlx-submit", text: "Submit", disabled: "disabled" });
    TLX.forEach((d) => {
      const out = el("span", { class: "small", id: "tlx-" + d[0] + "-v", text: "" });
      const r = el("input", { type: "range", min: "0", max: "100", step: "5", value: "50", id: "tlx-" + d[0], "aria-label": d[1] });
      const set = () => { vals[d[0]] = parseInt(r.value, 10); out.textContent = " " + r.value; if (Object.keys(vals).length === 6) submit.removeAttribute("disabled"); };
      r.addEventListener("input", set); r.addEventListener("change", set);
      box.appendChild(el("label", { for: "tlx-" + d[0], text: d[1] + ": " + d[2] }));
      box.appendChild(r);
      box.appendChild(el("div", { class: "anch" }, [el("span", { text: d[3] }), out, el("span", { text: d[4] })]));
    });
    submit.addEventListener("click", () => {
      const raw = Object.keys(vals).reduce((s, k) => s + vals[k], 0) / 6;
      DAV.store.add(Object.assign({ type: "tlx", view: view, block: "A", scores: vals, raw_tlx: raw, timestamp: nowIso() }, base()));
      after();
    });
    box.appendChild(submit);
    show(box);
  }

  function blockB() {
    if (!DAV.FEATURES.blockB) return final();
    const D = window.DESIGN, rows = D.block_b_lists[String(P.list)];
    const rnd = DAV.rng(DAV.hash(P.code + "|B"));
    const first = DAV.shuffle(rows.filter((r) => r.view === P.order), rnd), second = DAV.shuffle(rows.filter((r) => r.view !== P.order), rnd);
    const seq = first.concat(second);
    info("Last set: suggestions", ["In these " + seq.length + " records one step is marked \"" + DAV.AI_TEXT + "\". The suggestion is sometimes wrong. The decision is yours.", "Same task, same 4-minute limit, no feedback."], "Start", () => {
      const run = (i) => {
        if (i >= seq.length) return final();
        const r = seq[i];
        trial({ item: r.item, view: r.view, block: "B", index: i + 1, total: seq.length, cap: DAV.TRIAL_MS, suggestionKey: r.sugg, suggestionStep: D.block_b_candidates[r.item][r.sugg],
          onDone: (rec, fl) => endTrial(rec, fl, () => run(i + 1)) });
      };
      run(0);
    }, "start-blockb");
  }

  function final() {
    const pref = el("select", { id: "pref" }, [el("option", { value: "", text: "Choose" }), el("option", { value: "A", text: "View A" }), el("option", { value: "B", text: "View B" }), el("option", { value: "none", text: "No preference" })]);
    const com = el("textarea", { id: "comments", rows: "4", cols: "60" });
    show(el("div", { class: "card" }, [
      el("h1", { text: "Last questions" }),
      el("div", { class: "row" }, [el("label", { for: "pref", text: "Which view did you prefer? " }), pref]),
      el("p", { text: "Comments (anything confusing or missing):" }), com,
      el("div", {}, [el("button", { type: "button", class: "primary", id: "final-submit", text: "Finish", onclick: () => {
        if (!pref.value) { alert("Choose an option."); return; }
        DAV.store.add(Object.assign({ type: "final", preference: pref.value, comments: com.value, timestamp: nowIso() }, base()));
        show([el("div", { class: "card" }, [el("h1", { text: "Finished" }), el("p", { text: "Thank you. Download the data below before closing this page." })]), dataCard(), el("button", { type: "button", id: "restart", text: "Back to start", onclick: startScreen })]);
      } })]),
    ]));
  }

  /* ---------------- screening mode ---------------- */
  function screening() {
    const D = window.DESIGN;
    const done = new Set(DAV.store.all().filter((r) => r.type === "screen" && r.screener === P.code).map((r) => r.item));
    const order = D.screening_order, nPrimary = D.screening_primary_count;
    const queue = order.map((id, i) => ({ id: id, index: i + 1, reserve: i >= nPrimary })).filter((q) => !done.has(q.id));
    info("Screening", ["Label the first hallucinated step in each record, blind: the labels are not available to you here. Console view, no suggestions, no time limit.",
      "The first " + nPrimary + " items are the selected set. " + (order.length - nPrimary) + " reserves follow and are optional.",
      done.size ? done.size + " items already done by " + P.code + "; the rest follow." : "Do not open results/labels_PRIVATE.json until both of you have finished."], "Start", () => runScreen(queue, 0), "start-screening");
  }
  function runScreen(q, i) {
    if (i >= q.length) return info("Screening finished", ["Download the screening CSV on the start screen."], "Back to start", startScreen);
    const it = q[i];
    if (it.reserve && (i === 0 || !q[i - 1].reserve)) {
      return info("Selected items done", ["The reserves are optional. Continue only if time allows."], "Continue with reserves", () => { q[i] = Object.assign({}, it, { reserve: true, shown: true }); runScreen2(q, i); }, "reserves-continue");
    }
    runScreen2(q, i);
  }
  function runScreen2(q, i) {
    const it = q[i];
    trial({ item: it.id, view: "console", block: "screening", index: it.index, total: window.DESIGN.screening_order.length, cap: null,
      onDone: (rec, fl) => {
        const item = window.ITEMS[it.id];
        const cb = (id, t) => el("label", { class: "fchk" }, [el("input", { type: "checkbox", id: id }), " " + t]);
        const conf = el("select", { id: "sc-conf" }, [el("option", { value: "", text: "Confidence" })].concat([1, 2, 3, 4, 5].map((v) => el("option", { value: v, text: String(v) }))));
        const com = el("input", { type: "text", id: "sc-comment", size: "60", placeholder: "Comment (optional)" });
        show(el("div", { class: "card" }, [
          el("h1", { text: "Item " + it.index + (fl.noStep ? ": no step chosen" : ": you chose Step " + rec.chosen_step) }),
          el("p", { class: "small", text: "Reference answer: " + item.true_answer }),
          el("div", { class: "row" }, [cb("sc-correct", "The system's final answer appears correct (matches the reference)"), cb("sc-off", "Offensive or personal content"), cb("sc-amb", "Ambiguous: more than one step could count")]),
          el("div", { class: "row" }, [conf, com]),
          el("button", { type: "button", class: "primary", id: "sc-next", text: "Save and continue", onclick: () => {
            DAV.store.add({ type: "screen", screener: P.code, item: it.id, index: it.index, reserve: it.reserve, practice_item: window.DESIGN.screening_practice_items.indexOf(it.id) >= 0, chosen_step: rec.chosen_step, no_step_found: !!fl.noStep, time_ms: rec.time_ms,
              confidence: conf.value ? parseInt(conf.value, 10) : null, final_answer_correct: document.getElementById("sc-correct").checked, offensive_or_personal: document.getElementById("sc-off").checked,
              ambiguous: document.getElementById("sc-amb").checked, comment: com.value, events: rec.events, app_version: DAV.VERSION, timestamp: nowIso() });
            runScreen(q, i + 1);
          } }),
        ]));
      } });
  }

  window.addEventListener("DOMContentLoaded", startScreen);
})();
