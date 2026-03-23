/* ── Element refs ───────────────────────────────────────────────────── */
const essayTextEl         = document.getElementById("essayText");
const targetScoreEl       = document.getElementById("targetScore");
const timerMinutesEl      = document.getElementById("timerMinutes");
const startTimerBtn       = document.getElementById("startTimerBtn");
const timerDisplayEl      = document.getElementById("timerDisplay");
const detectBadgeEl       = document.getElementById("detectBadge");
const wordStatEl          = document.getElementById("wordStat");
const sentenceStatEl      = document.getElementById("sentenceStat");
const targetHintEl        = document.getElementById("targetHint");
const draftStatusEl       = document.getElementById("draftStatus");
const checkRiskBtn        = document.getElementById("checkRiskBtn");
const evaluateBtn         = document.getElementById("evaluateBtn");
const insertTemplateBtn   = document.getElementById("insertTemplateBtn");
const autoReevalBtn       = document.getElementById("autoReevalBtn");
const clearDraftBtn       = document.getElementById("clearDraftBtn");
const downloadPdfBtn      = document.getElementById("downloadPdfBtn");
const statusText          = document.getElementById("statusText");
const resultSection       = document.getElementById("resultSection");
const riskPanel           = document.getElementById("riskPanel");
const riskLevelEl         = document.getElementById("riskLevel");
const riskWarningsEl      = document.getElementById("riskWarnings");
const scoreArcEl          = document.getElementById("scoreArc");
const score05El           = document.getElementById("score05");
const score30El           = document.getElementById("score30");
const writingRangeEl      = document.getElementById("writingRange");
const totalRangeEl        = document.getElementById("totalRange");
const aiModeBadgeEl       = document.getElementById("aiModeBadge");
const grammarCapBadgeEl   = document.getElementById("grammarCapBadge");
const grammarCapReasonEl  = document.getElementById("grammarCapReason");
const confidenceEl        = document.getElementById("confidence");
const confidenceReasonEl  = document.getElementById("confidenceReason");
const dimensionBarsEl     = document.getElementById("dimensionBars");
const taskTagEl           = document.getElementById("taskTag");
const grammarStatsEl      = document.getElementById("grammarStats");
const grammarCorrectionsEl= document.getElementById("grammarCorrections");
const essayHighlightPreviewEl = document.getElementById("essayHighlightPreview");
const grammarImpactEl     = document.getElementById("grammarImpact");
const beforeAfterProjectionEl = document.getElementById("beforeAfterProjection");
const templateOpeningEl       = document.getElementById("templateOpening");
const templateBodyEl          = document.getElementById("templateBody");
const templateTransitionsEl   = document.getElementById("templateTransitions");
const templateClosingEl       = document.getElementById("templateClosing");
const scoreHighlightsEl   = document.getElementById("scoreHighlights");
const strengthsEl         = document.getElementById("strengths");
const weaknessesEl        = document.getElementById("weaknesses");
const actionPlanEl        = document.getElementById("actionPlan");
const sentenceEditsEl     = document.getElementById("sentenceEdits");
const claimMapEl          = document.getElementById("claimMap");
const weaknessDictionaryEl= document.getElementById("weaknessDictionary");
const rewriteMinimalEl    = document.getElementById("rewriteMinimal");
const rewriteAggressiveEl = document.getElementById("rewriteAggressive");
const paraphraseSuggestionsEl = document.getElementById("paraphraseSuggestions");
const checklistTotalEl    = document.getElementById("checklistTotal");
const checklistItemsEl    = document.getElementById("checklistItems");
const grammarDrillsEl     = document.getElementById("grammarDrills");
const scoreSimulatorEl    = document.getElementById("scoreSimulator");
const smartRecommendationsEl = document.getElementById("smartRecommendations");
const topPriorityActionsEl = document.getElementById("topPriorityActions");
const targetEtaEl         = document.getElementById("targetEta");
const sentenceVarietyEl   = document.getElementById("sentenceVariety");
const revisionDiffEl      = document.getElementById("revisionDiff");
const targetBandStrategyEl = document.getElementById("targetBandStrategy");
const repetitionTrainingEl = document.getElementById("repetitionTraining");
const examinerFeedbackEl   = document.getElementById("examinerFeedback");
const boosterListEl       = document.getElementById("boosterList");
const weaknessRankingEl   = document.getElementById("weaknessRanking");
const weeklyPlanEl        = document.getElementById("weeklyPlan");
const sampleOverlapEl     = document.getElementById("sampleOverlap");
const sampleMatchedEl     = document.getElementById("sampleMatched");
const sampleMissingEl     = document.getElementById("sampleMissing");
const summaryKoEl         = document.getElementById("summaryKo");
const summaryEnEl         = document.getElementById("summaryEn");
const personalToneEl      = document.getElementById("personalTone");
const personalIssuesEl    = document.getElementById("personalIssues");
const personalNextEl      = document.getElementById("personalNext");
const sampleParagraphEl   = document.getElementById("sampleParagraph");
const historyEl           = document.getElementById("history");
const dashAttemptEl       = document.getElementById("dashAttempt");
const dashAvgScoreEl      = document.getElementById("dashAvgScore");
const dashAvgPromptFitEl  = document.getElementById("dashAvgPromptFit");
const dashTrendEl         = document.getElementById("dashTrend");
const dashGrammarEl       = document.getElementById("dashGrammar");
const dashFocusEl         = document.getElementById("dashFocus");
const trendScoreBtn       = document.getElementById("trendScoreBtn");
const trendGrammarBtn     = document.getElementById("trendGrammarBtn");
const trendCaptionEl      = document.getElementById("trendCaption");
const trendLineEl         = document.getElementById("trendLine");

let timerId = null;
let pendingAutoSubmitId = null;
let pendingAutoSubmit = false;
let dashboardCache = null;
let activeTrend = "score";
let lastResult = null;

/* ── Draft helpers ───────────────────────────────────────────────────── */
const DRAFT_KEY = "toefl_draft_text";

function sentenceCount(text) {
  const m = text.match(/[^.!?]+[.!?]?/g) || [];
  return m.map(function(x) { return x.trim(); }).filter(Boolean).length;
}

function updateLiveStats() {
  const essay = essayTextEl.value.trim();
  const words = essay ? essay.split(/\s+/).filter(Boolean).length : 0;
  const sentences = essay ? sentenceCount(essay) : 0;
  const detectedType = detectType(essay);
  const target = detectedType === "email" ? 100 : 120;
  setText(wordStatEl, "단어 " + words);
  setText(sentenceStatEl, "문장 " + sentences);
  setText(targetHintEl, "권장 " + target + "+");
}

function saveDraft() {
  localStorage.setItem(DRAFT_KEY, essayTextEl.value);
  setText(draftStatusEl, "자동저장 완료");
}

function loadDraft() {
  const draft = localStorage.getItem(DRAFT_KEY);
  if (!draft) return;
  essayTextEl.value = draft;
  setText(draftStatusEl, "자동저장 불러옴");
}

function insertTemplate() {
  const type = detectType(essayTextEl.value.trim());
  const emailTemplate = [
    "Dear Professor Lee,",
    "I am writing to request a short extension for my assignment.",
    "First, I completed the outline and collected sources, but I need one more day to revise grammar and evidence details.",
    "For example, I plan to strengthen topic sentences and correct article and tense issues.",
    "Therefore, I would appreciate submitting it by tomorrow evening.",
    "Thank you for your understanding.",
    "Sincerely,",
    "[Your Name]",
  ].join(" ");
  const discussionTemplate = [
    "I agree that schools should expand project-based learning.",
    "First, team tasks improve communication because students must explain and defend ideas with evidence.",
    "For example, when students divide roles and review each other's drafts, they practice both clarity and collaboration.",
    "Second, this method mirrors real workplaces, so students build practical skills before graduation.",
    "Therefore, project-based learning can improve both academic performance and long-term readiness.",
  ].join(" ");

  essayTextEl.value = type === "email" ? emailTemplate : discussionTemplate;
  updateDetectBadge(essayTextEl.value);
  updateLiveStats();
  saveDraft();
}

/* ── Client-side type detection ─────────────────────────────────────── */
function detectType(essay) {
  const t = essay.trim();
  let score = 0;
  if (/^\s*(dear\b|hi\b|hello\b|good morning\b|good afternoon\b|to whom it may concern)/im.test(t)) score += 2;
  if (/(sincerely|best regards|kind regards|yours truly)/i.test(t)) score += 2;
  if (/(i am writing to|i would like to (?:request|inform|ask|apply|invite)|i am contacting|please find|please let me know)/i.test(t)) score += 1;
  return score >= 2 ? "email" : "academic_discussion";
}

function updateDetectBadge(essay) {
  if (essay.trim().length < 30) {
    detectBadgeEl.className = "detect-badge detect-none";
    detectBadgeEl.textContent = "유형 감지 대기 중…";
    return null;
  }
  const type = detectType(essay);
  if (type === "email") {
    detectBadgeEl.className = "detect-badge detect-email";
    detectBadgeEl.textContent = "✉️  Task 2 — 이메일 감지됨";
  } else {
    detectBadgeEl.className = "detect-badge detect-disc";
    detectBadgeEl.textContent = "💬  Task 3 — 학술 토론 감지됨";
  }
  return type;
}

essayTextEl.addEventListener("input", function() {
  updateDetectBadge(essayTextEl.value);
  updateLiveStats();
  saveDraft();
});

/* ── Helpers ─────────────────────────────────────────────────────────── */
function setText(el, val) { if (el) el.textContent = val != null ? val : "-"; }

function renderList(target, items) {
  target.innerHTML = "";
  (items && items.length ? items : ["항목이 없습니다."]).forEach(function(item) {
    const li = document.createElement("li");
    li.textContent = item;
    target.appendChild(li);
  });
}

function renderDimensionBars(dimensions) {
  dimensionBarsEl.innerHTML = "";
  dimensions.forEach(function(d) {
    const pct = (d.score / 5) * 100;
    const band = Math.max(1, Math.min(6, d.score + 1));
    const row = document.createElement("div");
    row.className = "rubric-row";
    row.innerHTML =
      '<span class="rubric-name">' + d.name + '</span>' +
      '<div class="rubric-track"><div class="rubric-fill" style="width:0%" data-pct="' + pct + '"></div></div>' +
      '<span class="rubric-val">' + band.toFixed(1) + ' / 6</span>';
    dimensionBarsEl.appendChild(row);
  });
  requestAnimationFrame(function() {
    dimensionBarsEl.querySelectorAll(".rubric-fill").forEach(function(el) {
      el.style.width = el.dataset.pct + "%";
    });
  });
}

function animateScoreRing(score) {
  const circumference = 213.6;
  scoreArcEl.style.strokeDashoffset = circumference - (score / 6) * circumference;
}

function renderSentenceEdits(items) {
  sentenceEditsEl.innerHTML = "";
  items.forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML =
      "<p><strong>원문</strong>: " + item.original + "</p>" +
      "<p><strong>개선</strong>: " + item.improved + "</p>" +
      "<p><strong>포인트</strong>: " + item.note + "</p>";
    sentenceEditsEl.appendChild(box);
  });
}

function renderGrammarStats(stats) {
  const labels = [
    ["시제", stats.tense], ["관사", stats.article], ["전치사", stats.preposition],
    ["Run-on", stats.run_on], ["수일치", stats.subject_verb],
    ["문장부호", stats.punctuation], ["총합", stats.total],
  ];
  grammarStatsEl.innerHTML = "";
  labels.forEach(function(pair) {
    const li = document.createElement("li");
    li.textContent = pair[0] + ": " + pair[1];
    grammarStatsEl.appendChild(li);
  });
}

function renderClaimMap(items) {
  claimMapEl.innerHTML = "";
  items.forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML =
      '<p><span class="tag tag-' + item.tag + '">' + item.tag + '</span>' + item.sentence + '</p>' +
      "<p><strong>설명</strong>: " + item.note + "</p>";
    claimMapEl.appendChild(box);
  });
}

function renderScoreHighlights(items) {
  scoreHighlightsEl.innerHTML = "";
  items.forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML =
      '<p><span class="tag tag-' + item.impact + '">' + item.impact + '</span>' + item.sentence + '</p>' +
      "<p><strong>근거</strong>: " + item.reason + "</p>";
    scoreHighlightsEl.appendChild(box);
  });
}

function renderWeaknessDictionary(items) {
  weaknessDictionaryEl.innerHTML = "";
  items.forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML =
      "<p><strong>분류</strong>: " + item.category + "</p>" +
      "<p><strong>잘못된 패턴</strong>: " + item.wrong_pattern + "</p>" +
      "<p><strong>교정 패턴</strong>: " + item.fix_pattern + "</p>" +
      "<p><strong>팁</strong>: " + item.tip + "</p>";
    weaknessDictionaryEl.appendChild(box);
  });
}

function renderParaphraseSuggestions(items) {
  paraphraseSuggestionsEl.innerHTML = "";
  (items && items.length ? items : []).forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML =
      "<p><strong>원표현</strong>: " + item.original + "</p>" +
      "<p><strong>추천표현</strong>: " + item.improved + "</p>" +
      "<p><strong>이유</strong>: " + item.reason + "</p>";
    paraphraseSuggestionsEl.appendChild(box);
  });
}

function renderChecklist(checklist) {
  if (!checklist) return;
  setText(checklistTotalEl, checklist.total_score + " / 100");
  checklistItemsEl.innerHTML = "";
  (checklist.items || []).forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML =
      "<p><strong>항목</strong>: " + item.label + "</p>" +
      "<p><strong>점수</strong>: " + item.score + "</p>" +
      "<p><strong>상태</strong>: " + (item.status === "good" ? "양호" : "주의") + "</p>";
    checklistItemsEl.appendChild(box);
  });
}

function renderGrammarDrills(items) {
  grammarDrillsEl.innerHTML = "";
  (items || []).forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML =
      "<p><strong>이슈</strong>: " + item.issue + "</p>" +
      "<p><strong>오답</strong>: " + item.wrong + "</p>" +
      "<p><strong>정답</strong>: " + item.correct + "</p>" +
      "<p><strong>팁</strong>: " + item.tip + "</p>";
    grammarDrillsEl.appendChild(box);
  });
}

function renderGrammarCorrections(items) {
  grammarCorrectionsEl.innerHTML = "";
  if (!items || !items.length) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.textContent = "탐지된 문법 오류가 적습니다. 현재 문장 정확도가 양호합니다.";
    grammarCorrectionsEl.appendChild(box);
    return;
  }

  items.forEach(function(item, idx) {
    const box = document.createElement("div");
    box.className = "edit-item correction-item severity-" + item.severity;
    box.id = "corr-" + idx;
    box.innerHTML =
      '<p><span class="tag">' + item.error_type + '</span><span class="badge small-badge">' + item.severity + '</span></p>' +
      "<p><strong>원문</strong>: " + item.sentence + "</p>" +
      "<p><strong>교정</strong>: " + item.corrected + "</p>" +
      "<p><strong>근거</strong>: " + item.explanation + "</p>";
    grammarCorrectionsEl.appendChild(box);
  });
}

function renderEssayHighlightPreview(essay, corrections) {
  if (!essayHighlightPreviewEl) return;
  function esc(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  const spans = (corrections || []).map(function(c, idx) {
    return {
      idx: idx,
      start: Number(c.focus_start),
      end: Number(c.focus_end),
      severity: c.severity || "medium",
    };
  }).filter(function(x) {
    return Number.isFinite(x.start) && Number.isFinite(x.end) && x.start >= 0 && x.end > x.start;
  }).sort(function(a, b) {
    if (a.start !== b.start) return a.start - b.start;
    return a.end - b.end;
  });

  if (!spans.length) {
    essayHighlightPreviewEl.innerHTML = esc(essay);
    return;
  }

  let html = "";
  let cursor = 0;
  spans.forEach(function(s) {
    if (s.start < cursor) return;
    html += esc(essay.slice(cursor, s.start));
    html += '<mark class="hl-' + s.severity + '" data-corr-index="' + s.idx + '">' + esc(essay.slice(s.start, s.end)) + "</mark>";
    cursor = s.end;
  });
  html += esc(essay.slice(cursor));
  essayHighlightPreviewEl.innerHTML = html;
}

function renderGrammarImpact(items) {
  grammarImpactEl.innerHTML = "";
  (items || []).forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML =
      "<p><strong>이슈</strong>: " + item.issue + "</p>" +
      "<p><strong>횟수</strong>: " + item.count + "</p>" +
      "<p><strong>예상 감점 영향</strong>: -" + item.estimated_penalty_0_5 + "점</p>";
    grammarImpactEl.appendChild(box);
  });
}

function renderBeforeAfterProjection(p) {
  beforeAfterProjectionEl.innerHTML = "";
  if (!p) return;
  const box = document.createElement("div");
  box.className = "edit-item";
  box.innerHTML =
    "<p><strong>현재 예상 밴드</strong>: " + p.current_band_1_6.toFixed(1) + " / 6</p>" +
    "<p><strong>교정 후 예상 밴드</strong>: " + p.projected_band_1_6.toFixed(1) + " / 6</p>" +
    "<p><strong>예상 상승</strong>: +" + p.expected_gain_0_5.toFixed(2) + "점</p>";
  beforeAfterProjectionEl.appendChild(box);
}

function renderScoreSimulator(items) {
  scoreSimulatorEl.innerHTML = "";
  (items || []).forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML =
      "<p><strong>액션</strong>: " + item.action + "</p>" +
      "<p><strong>예상 상승</strong>: +" + item.expected_delta_0_5 + "점</p>" +
      "<p><strong>예상 밴드</strong>: " + item.projected_band_1_6 + " / 6</p>";
    scoreSimulatorEl.appendChild(box);
  });
}

function renderSmartRecommendations(items) {
  smartRecommendationsEl.innerHTML = "";
  (items || []).forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML =
      "<p><strong>액션</strong>: " + item.title + "</p>" +
      "<p><strong>기대효과</strong>: " + item.impact + "</p>" +
      "<p><strong>신뢰도</strong>: " + (item.confidence || "medium") + "</p>" +
      "<p><strong>이유</strong>: " + item.why + "</p>" +
      "<p><strong>실행법</strong>: " + item.how_to + "</p>";
    smartRecommendationsEl.appendChild(box);
  });
}

function renderTopPriorityActions(items) {
  topPriorityActionsEl.innerHTML = "";
  (items || []).forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML =
      "<p><strong>우선 액션</strong>: " + item.title + "</p>" +
      "<p><strong>기대효과</strong>: " + item.impact + "</p>" +
      "<p><strong>신뢰도</strong>: " + (item.confidence || "medium") + "</p>";
    topPriorityActionsEl.appendChild(box);
  });
}

function renderTargetEta(eta) {
  targetEtaEl.innerHTML = "";
  if (!eta) return;
  const box = document.createElement("div");
  box.className = "edit-item";
  box.innerHTML =
    "<p><strong>예상 제출 횟수</strong>: " + eta.estimated_attempts + "회</p>" +
    "<p><strong>페이스</strong>: " + eta.pace_label + "</p>" +
    "<p><strong>메시지</strong>: " + eta.message + "</p>";
  targetEtaEl.appendChild(box);
}

function renderSentenceVariety(v) {
  sentenceVarietyEl.innerHTML = "";
  if (!v) return;
  const box = document.createElement("div");
  box.className = "edit-item";
  box.innerHTML =
    "<p><strong>Short</strong>: " + Math.round((v.short_ratio || 0) * 100) + "%</p>" +
    "<p><strong>Medium</strong>: " + Math.round((v.medium_ratio || 0) * 100) + "%</p>" +
    "<p><strong>Long</strong>: " + Math.round((v.long_ratio || 0) * 100) + "%</p>" +
    "<p><strong>코치</strong>: " + (v.recommendation || "") + "</p>";
  sentenceVarietyEl.appendChild(box);
}

function renderRevisionDiff(lines) {
  revisionDiffEl.innerHTML = "";
  const shown = (lines || []).slice(0, 20);
  if (!shown.length) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.textContent = "변경 내용이 거의 없거나 자동 교정 적용 전입니다.";
    revisionDiffEl.appendChild(box);
    return;
  }
  shown.forEach(function(line) {
    const box = document.createElement("div");
    box.className = "edit-item";
    if (line.startsWith("+ ")) box.classList.add("diff-add");
    if (line.startsWith("- ")) box.classList.add("diff-del");
    box.textContent = line;
    revisionDiffEl.appendChild(box);
  });
}

function renderTargetBandStrategy(items) {
  targetBandStrategyEl.innerHTML = "";
  (items || []).forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML = "<p><strong>전략</strong>: " + item.title + "</p><p>" + item.detail + "</p>";
    targetBandStrategyEl.appendChild(box);
  });
}

function renderRepetitionTraining(items) {
  repetitionTrainingEl.innerHTML = "";
  (items || []).forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML =
      "<p><strong>반복어</strong>: " + item.word + " (" + item.count + "회)</p>" +
      "<p><strong>대체어</strong>: " + (item.alternatives || []).join(", ") + "</p>";
    repetitionTrainingEl.appendChild(box);
  });
}

function renderExaminerFeedback(payload) {
  renderList(examinerFeedbackEl, payload && payload.comments ? payload.comments : ["코멘트 없음"]);
}

function renderBoosterList(result) {
  const items = [];
  if (result.grammar_stats && result.grammar_stats.total >= 4) {
    items.push("문법 오류 총합을 4개 이하로 줄이면 밴드 상한이 크게 완화됩니다.");
  }
  if (result.prompt_fit && result.prompt_fit.score < 3.5) {
    items.push("프롬프트 키워드 반영률을 올리면 Content 점수 안정성이 개선됩니다.");
  }
  if (result.sample_comparison && result.sample_comparison.missing_points && result.sample_comparison.missing_points.length) {
    items.push("누락된 샘플 포인트를 보완하면 구조 점수 상승이 쉽습니다.");
  }
  if (!items.length) {
    items.push("현재 밸런스가 좋아서 문법 정밀도와 어휘 치환만 다듬으면 상위 밴드 진입이 가능합니다.");
  }
  renderList(boosterListEl, items);
}

function renderTrendLine(points, kind) {
  if (!points || !points.length) {
    trendLineEl.setAttribute("points", "");
    return;
  }
  const xs = points.map(function(_, i) { return 10 + (280 * i) / Math.max(1, points.length - 1); });
  const values = points.map(function(p) {
    return kind === "score" ? (p.score_0_5 + 1.0) : p.total_errors;
  });
  const maxY = Math.max.apply(null, values) || 1;
  const coords = points.map(function(p, i) {
    const val = kind === "score" ? (p.score_0_5 + 1.0) : p.total_errors;
    const y = 80 - (70 * val / maxY);
    return xs[i].toFixed(1) + "," + y.toFixed(1);
  });
  trendLineEl.setAttribute("points", coords.join(" "));
  trendLineEl.setAttribute("stroke", kind === "score" ? "#00838f" : "#d95f02");
}

function renderActiveTrend() {
  if (!dashboardCache) return;
  if (activeTrend === "score") {
    trendCaptionEl.textContent = "점수 추세(높을수록 좋음)";
    trendScoreBtn.classList.add("active");
    trendGrammarBtn.classList.remove("active");
    renderTrendLine(dashboardCache.score_trend || [], "score");
  } else {
    trendCaptionEl.textContent = "문법 오류 추세(낮을수록 좋음)";
    trendGrammarBtn.classList.add("active");
    trendScoreBtn.classList.remove("active");
    renderTrendLine(dashboardCache.grammar_error_trend || [], "grammar");
  }
}

function startTimer() {
  if (pendingAutoSubmit) {
    pendingAutoSubmit = false;
    if (pendingAutoSubmitId) clearInterval(pendingAutoSubmitId);
    pendingAutoSubmitId = null;
    startTimerBtn.textContent = "타이머 시작";
    statusText.textContent = "자동 제출이 취소되었습니다.";
    return;
  }
  const mins = Number(timerMinutesEl.value || 30);
  let remain = Math.max(1, mins) * 60;
  if (timerId) clearInterval(timerId);
  timerDisplayEl.textContent = String(mins).padStart(2, "0") + ":00";

  timerId = setInterval(function() {
    remain -= 1;
    const m = Math.floor(remain / 60);
    const s = remain % 60;
    timerDisplayEl.textContent = String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
    if (remain <= 0) {
      clearInterval(timerId);
      timerId = null;
      timerDisplayEl.textContent = "00:00";
      let grace = 5;
      pendingAutoSubmit = true;
      startTimerBtn.textContent = "자동제출 취소";
      statusText.textContent = grace + "초 후 자동 제출됩니다. 취소하려면 버튼을 누르세요.";
      pendingAutoSubmitId = setInterval(function() {
        grace -= 1;
        if (!pendingAutoSubmit) return;
        if (grace <= 0) {
          clearInterval(pendingAutoSubmitId);
          pendingAutoSubmitId = null;
          pendingAutoSubmit = false;
          startTimerBtn.textContent = "타이머 시작";
          evaluateEssay(true);
          return;
        }
        statusText.textContent = grace + "초 후 자동 제출됩니다. 취소하려면 버튼을 누르세요.";
      }, 1000);
    }
  }, 1000);
}

function renderRisk(risk) {
  riskPanel.classList.remove("hidden");
  riskLevelEl.textContent = risk.risk_level;
  renderList(riskWarningsEl, risk.warnings.length ? risk.warnings : ["현재 제출 위험 요소 없음 ✅"]);
  if (risk.checklist) renderChecklist(risk.checklist);
}

function renderDashboard(data) {
  dashboardCache = data;
  setText(dashAttemptEl, data.attempt_count);
  setText(dashAvgScoreEl, (data.avg_score_0_5 + 1.0).toFixed(2));
  setText(dashAvgPromptFitEl, data.avg_prompt_fit.toFixed(2));
  setText(dashTrendEl, data.score_trend.length
    ? data.score_trend.map(function(p) { return "#" + p.submission_id + ":" + (p.score_0_5 + 1.0).toFixed(1); }).join(" › ")
    : "데이터 없음");
  setText(dashGrammarEl, data.top_grammar_issues.length
    ? data.top_grammar_issues.map(function(x) { return x.type + "(" + x.count + ")"; }).join(", ")
    : "데이터 없음");
  renderActiveTrend();
  renderList(dashFocusEl, data.recommended_focus);
}

/* ── API calls ───────────────────────────────────────────────────────── */
async function fetchDashboard() {
  try {
    const res = await fetch("/api/dashboard?limit=200");
    if (!res.ok) throw new Error();
    renderDashboard(await res.json());
  } catch(e) {
    dashFocusEl.innerHTML = "<li>대시보드를 불러오지 못했습니다.</li>";
  }
}

async function fetchHistory() {
  try {
    const res = await fetch("/api/history?limit=10");
    const data = await res.json();
    historyEl.innerHTML = "";
    if (!data.items || !data.items.length) {
      historyEl.textContent = "아직 제출 이력이 없습니다.";
      return;
    }
    data.items.forEach(function(row) {
      const div = document.createElement("div");
      div.className = "history-row";
      const typeLabel = row.prompt_type === "email" ? "이메일" : "학술토론";
      div.innerHTML =
        "<span>#" + row.id + " · " + typeLabel + " · " + new Date(row.created_at).toLocaleString() + "</span>" +
        "<strong>Band " + row.score_band_1_6.toFixed(1) + " / 6</strong>";
      historyEl.appendChild(div);
    });
  } catch(e) {
    historyEl.textContent = "이력 로드에 실패했습니다.";
  }
}

async function checkRisk() {
  const essay = essayTextEl.value.trim();
  if (essay.length < 80) {
    statusText.textContent = "에세이를 80자 이상 입력해 주세요.";
    return;
  }
  try {
    const res = await fetch("/api/precheck", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ essay_text: essay }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error("위험 체크 실패");
    renderRisk(data);
    statusText.textContent = data.ready ? "제출 준비 완료 ✅" : "제출 전 보완 권장";
  } catch(err) {
    statusText.textContent = "오류: " + err.message;
  }
}

async function evaluateEssay(isExamMode) {
  const essay = essayTextEl.value.trim();
  if (essay.length < 80) {
    statusText.textContent = "에세이를 80자 이상 입력해 주세요.";
    return;
  }
  const payload = {
    essay_text: essay,
    target_score_0_5: Math.max(0, Math.min(5, Number(targetScoreEl.value || 5.0) - 1.0)),
    exam_mode: Boolean(isExamMode),
  };

  evaluateBtn.disabled = true;
  statusText.textContent = "채점 중…";

  try {
    const res = await fetch("/api/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "채점 실패");

    const result = data.result;
    lastResult = result;

    const s = result.score_band_1_6;
    const lo = Math.floor(s * 2) / 2;
    const hi = Math.min(6, lo + 0.5);
    setText(score05El, lo.toFixed(1) + "~" + hi.toFixed(1));
    setText(score30El, result.estimated_score_30);
    setText(writingRangeEl, result.score_profile.writing);
    setText(totalRangeEl, result.score_profile.total);
    setText(aiModeBadgeEl, result.ai_mode === "ai" ? "AI 고급" : "로컬");
    if (result.grammar_cap_applied) {
      setText(grammarCapBadgeEl, "적용됨");
      grammarCapBadgeEl.classList.add("warn");
      setText(grammarCapReasonEl, result.grammar_cap_reason || "문법 상한이 적용되었습니다.");
    } else {
      setText(grammarCapBadgeEl, "없음");
      grammarCapBadgeEl.classList.remove("warn");
      setText(grammarCapReasonEl, "");
    }
    setText(confidenceEl, result.confidence);
    setText(confidenceReasonEl, result.confidence_reason);
    animateScoreRing(s);

    const detectedType = detectType(essay);
    setText(taskTagEl, detectedType === "email" ? "Task 2 · 이메일" : "Task 3 · 학술 토론");
    renderDimensionBars(result.dimensions);

    setText(summaryKoEl, result.bilingual_feedback.summary_ko);
    setText(summaryEnEl, result.bilingual_feedback.summary_en);
    setText(personalToneEl, result.personalization.coaching_tone);
    setText(personalNextEl, result.personalization.next_focus);
    setText(personalIssuesEl, result.personalization.repeated_issues.join(", "));

    renderList(strengthsEl, result.strengths);
    renderList(weaknessesEl, result.weaknesses);
    renderList(actionPlanEl, result.action_plan);
    renderSentenceEdits(result.sentence_edits);

    setText(templateOpeningEl, result.template_coach.opening_templates.join("  /  "));
    setText(templateBodyEl, result.template_coach.body_templates.join("  /  "));
    setText(templateTransitionsEl, result.template_coach.transition_bank.join(", "));
    setText(templateClosingEl, result.template_coach.closing_templates.join("  /  "));

    renderGrammarStats(result.grammar_stats);
    renderWeaknessDictionary(result.weakness_dictionary);
    renderParaphraseSuggestions(result.paraphrase_recommendations);
    renderChecklist(result.checklist);
    renderGrammarDrills(result.grammar_drills);
    renderGrammarCorrections(result.grammar_corrections);
    renderEssayHighlightPreview(essay, result.grammar_corrections || []);
    renderGrammarImpact(result.grammar_impact || []);
    renderBeforeAfterProjection(result.before_after_projection || null);
    renderScoreSimulator(result.score_simulator);
    renderSmartRecommendations(result.smart_recommendations || []);
    renderTopPriorityActions(result.top_priority_actions || []);
    renderTargetEta(result.target_eta || null);
    renderSentenceVariety(result.sentence_variety || null);
    renderRevisionDiff(result.revision_diff || []);
    renderTargetBandStrategy(result.target_band_strategy || []);
    renderRepetitionTraining(result.repetition_training || []);
    renderExaminerFeedback(result.examiner_feedback || null);
    renderList(weaknessRankingEl, result.personal_weakness_ranking || []);
    renderBoosterList(result);
    renderList(weeklyPlanEl, result.weekly_plan);
    renderScoreHighlights(result.score_highlights);
    renderClaimMap(result.claim_evidence_map);

    setText(rewriteMinimalEl, result.target_rewrite.minimal);
    setText(rewriteAggressiveEl, result.target_rewrite.aggressive);
    setText(sampleOverlapEl, result.sample_comparison.overlap_score.toFixed(1));
    setText(sampleMatchedEl, result.sample_comparison.matched_points.join(", ") || "없음");
    setText(sampleMissingEl, result.sample_comparison.missing_points.join(", ") || "없음");
    setText(sampleParagraphEl, result.upgraded_sample_paragraph);

    resultSection.classList.remove("hidden");
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    downloadPdfBtn.disabled = false;
    autoReevalBtn.disabled = !(result.auto_rewrite_essay && result.auto_rewrite_essay.trim());
    downloadPdfBtn.dataset.submissionId = String(data.submission_id);
    statusText.textContent = "채점 완료 (ID: " + data.submission_id + ")";
    await Promise.all([fetchHistory(), fetchDashboard()]);
  } catch(err) {
    statusText.textContent = "오류: " + err.message;
  } finally {
    evaluateBtn.disabled = false;
  }
}

/* ── Event Listeners ─────────────────────────────────────────────────── */
checkRiskBtn.addEventListener("click", checkRisk);
evaluateBtn.addEventListener("click", function() { evaluateEssay(false); });
startTimerBtn.addEventListener("click", startTimer);
insertTemplateBtn.addEventListener("click", insertTemplate);
clearDraftBtn.addEventListener("click", function() {
  essayTextEl.value = "";
  localStorage.removeItem(DRAFT_KEY);
  setText(draftStatusEl, "초안 비움");
  updateDetectBadge(essayTextEl.value);
  updateLiveStats();
});
autoReevalBtn.addEventListener("click", function() {
  if (!lastResult || !lastResult.auto_rewrite_essay) {
    statusText.textContent = "자동 재채점용 교정본이 없습니다.";
    return;
  }
  essayTextEl.value = lastResult.auto_rewrite_essay;
  updateDetectBadge(essayTextEl.value);
  updateLiveStats();
  saveDraft();
  statusText.textContent = "교정 반영본으로 재채점합니다...";
  evaluateEssay(false);
});
essayHighlightPreviewEl.addEventListener("click", function(ev) {
  const mark = ev.target.closest("mark[data-corr-index]");
  if (!mark) return;
  const idx = mark.getAttribute("data-corr-index");
  const target = document.getElementById("corr-" + idx);
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "center" });
  target.classList.add("corr-focus");
  setTimeout(function() { target.classList.remove("corr-focus"); }, 1200);
});
trendScoreBtn.addEventListener("click", function() { activeTrend = "score"; renderActiveTrend(); });
trendGrammarBtn.addEventListener("click", function() { activeTrend = "grammar"; renderActiveTrend(); });
downloadPdfBtn.addEventListener("click", function() {
  const id = downloadPdfBtn.dataset.submissionId;
  if (!id) { statusText.textContent = "먼저 채점을 실행해 주세요."; return; }
  window.open("/api/report/" + id + ".pdf", "_blank");
});
document.getElementById("refreshHistory").addEventListener("click", fetchHistory);
document.getElementById("refreshDashboard").addEventListener("click", fetchDashboard);

fetchHistory();
fetchDashboard();
loadDraft();
updateDetectBadge(essayTextEl.value);
updateLiveStats();
