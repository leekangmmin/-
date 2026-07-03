/* ── Element refs ───────────────────────────────────────────────────── */
const essayTextEl         = document.getElementById("essayText");
const promptTextEl        = document.getElementById("promptText");
const engineBadgeEl       = document.getElementById("engineBadge");
const engineInfoEl        = document.getElementById("engineInfo");
const grammarCapChipEl    = document.getElementById("grammarCapChip");
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
const savePromptBtn       = document.getElementById("savePromptBtn");
const loadPromptBtn       = document.getElementById("loadPromptBtn");
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
const copyMinimalBtn      = document.getElementById("copyMinimalBtn");
const copyAggressiveBtn   = document.getElementById("copyAggressiveBtn");
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

const aiProviderSelect    = document.getElementById("aiProviderSelect");
const aiEnabledCheckbox   = document.getElementById("aiEnabledCheckbox");
const openaiApiKeyInput   = document.getElementById("openaiApiKeyInput");
const openaiModelInput    = document.getElementById("openaiModelInput");
const anthropicApiKeyInput= document.getElementById("anthropicApiKeyInput");
const anthropicModelInput = document.getElementById("anthropicModelInput");
const geminiApiKeyInput   = document.getElementById("geminiApiKeyInput");
const geminiModelInput    = document.getElementById("geminiModelInput");
const saveAiConfigBtn     = document.getElementById("saveAiConfigBtn");
const testAiConfigBtn     = document.getElementById("testAiConfigBtn");
const aiConfigStatus      = document.getElementById("aiConfigStatus");

let timerId = null;
let pendingAutoSubmitId = null;
let pendingAutoSubmit = false;
let dashboardCache = null;
let activeTrend = "score";
let lastResult = null;

/* ── Draft helpers ───────────────────────────────────────────────────── */
const DRAFT_KEY = "toefl_draft_text";
const PROMPT_DRAFT_KEY = "toefl_prompt_draft_text";
const PROMPT_LIBRARY_KEY = "toefl_prompt_library";

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

// 서버측 draft 동기화 — localStorage와 별개로 DB에도 보존해서
// 웹뷰 저장소가 비워지거나 강제 종료돼도 작성 중 답안을 복구한다.
let serverDraftTimer = null;
function scheduleServerDraftSync() {
  if (serverDraftTimer) clearTimeout(serverDraftTimer);
  serverDraftTimer = setTimeout(async function() {
    try {
      await fetch("/api/draft", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          essay_text: essayTextEl.value,
          prompt_text: promptTextEl ? promptTextEl.value : "",
        }),
      });
      setText(draftStatusEl, "자동저장 완료");
    } catch (_) {
      setText(draftStatusEl, "임시 보관됨 (이 창에만)");
    }
  }, 800);
}

function saveDraft() {
  try {
    localStorage.setItem(DRAFT_KEY, essayTextEl.value);
    if (promptTextEl) localStorage.setItem(PROMPT_DRAFT_KEY, promptTextEl.value);
    setText(draftStatusEl, "저장 중…");
  } catch (_) {
    setText(draftStatusEl, "임시 보관됨 (이 창에만)");
  }
  scheduleServerDraftSync();
}

async function loadDraft() {
  // 서버 draft를 우선한다 — 강제 종료/저장소 초기화에도 살아남는 사본이다.
  let serverDraft = null;
  try {
    const res = await fetch("/api/draft");
    if (res.ok) serverDraft = (await res.json()).draft;
  } catch (_) { /* 서버 draft 조회 실패 시 localStorage로 폴백 */ }

  if (serverDraft && (serverDraft.essay_text || serverDraft.prompt_text)) {
    if (promptTextEl && serverDraft.prompt_text) promptTextEl.value = serverDraft.prompt_text;
    if (serverDraft.essay_text) essayTextEl.value = serverDraft.essay_text;
    setText(draftStatusEl, "작성하던 답안을 불러왔어요");
    updateDetectBadge(essayTextEl.value);
    updateLiveStats();
    return;
  }

  const draft = localStorage.getItem(DRAFT_KEY);
  const promptDraft = localStorage.getItem(PROMPT_DRAFT_KEY);
  if (promptTextEl && promptDraft) promptTextEl.value = promptDraft;
  if (!draft) return;
  essayTextEl.value = draft;
  setText(draftStatusEl, "작성하던 답안을 불러왔어요");
}

function savePromptLibrary() {
  const promptText = promptTextEl ? promptTextEl.value.trim() : "";
  const text = promptText || essayTextEl.value.trim();
  if (!text) {
    statusText.textContent = "저장할 문제 지문이 없습니다.";
    return;
  }
  const current = JSON.parse(localStorage.getItem(PROMPT_LIBRARY_KEY) || "[]");
  const item = { text: text, createdAt: new Date().toISOString() };
  const next = [item].concat(current).slice(0, 20);
  localStorage.setItem(PROMPT_LIBRARY_KEY, JSON.stringify(next));
  statusText.textContent = "문제 지문을 저장했습니다.";
}

function loadPromptLibrary() {
  const items = JSON.parse(localStorage.getItem(PROMPT_LIBRARY_KEY) || "[]");
  if (!items.length) {
    statusText.textContent = "저장된 문제 지문이 없습니다.";
    return;
  }
  const pick = items[0];
  if (promptTextEl) {
    promptTextEl.value = String(pick.text || "");
    const details = promptTextEl.closest("details");
    if (details) details.open = true;
  }
  saveDraft();
  statusText.textContent = "최근 저장한 문제 지문을 불러왔습니다.";
}

async function copyTextSafe(text, label) {
  if (!text || !text.trim()) {
    statusText.textContent = label + " 내용이 비어 있습니다.";
    return;
  }
  try {
    await navigator.clipboard.writeText(text);
    statusText.textContent = label + "을(를) 클립보드에 복사했습니다.";
  } catch(_) {
    statusText.textContent = "클립보드 복사에 실패했습니다.";
  }
}

function providerLabel(provider) {
  if (provider === "local") return "내장 AI";
  if (provider === "claude") return "Claude";
  if (provider === "gemini") return "Gemini";
  return "ChatGPT";
}

/* ── Build a Sentence (자체 제작 연습 문제, API/인터넷 불필요) ────────── */
const basItemSelect   = document.getElementById("basItemSelect");
const basStartBtn     = document.getElementById("basStartBtn");
const basRefreshBtn   = document.getElementById("basRefreshBtn");
const basPlayArea     = document.getElementById("basPlayArea");
const basAnswerListEl = document.getElementById("basAnswerList");
const basFragmentPoolEl = document.getElementById("basFragmentPool");
const basDirectInputEl  = document.getElementById("basDirectInput");
const basSubmitBtn    = document.getElementById("basSubmitBtn");
const basResetBtn     = document.getElementById("basResetBtn");
const basAttemptInfoEl = document.getElementById("basAttemptInfo");
const basFeedbackEl   = document.getElementById("basFeedback");

let basCurrentItemId = null;
let basPool = [];      // [{key, text}] 아직 배치하지 않은 조각
let basAnswer = [];    // [{key, text}] 사용자가 배열한 순서
let basStartedAt = 0;
let basKeyCounter = 0;

const basDifficultyLabel = { easy: "쉬움", medium: "보통", hard: "어려움" };
let basItemOrder = [];  // 문제 순서 (다음 문제 버튼용)

async function loadBasItemOptions() {
  if (!basItemSelect) return;
  try {
    const res = await fetch("/api/build-a-sentence/items");
    if (!res.ok) throw new Error();
    const data = await res.json();
    basItemSelect.innerHTML = "";
    basItemOrder = data.items.map(function(i) { return i.item_id; });
    data.items.forEach(function(item, idx) {
      const opt = document.createElement("option");
      opt.value = item.item_id;
      const diff = basDifficultyLabel[item.difficulty] || item.difficulty;
      const tag = item.grammar_tag ? " · " + item.grammar_tag : "";
      opt.textContent = (idx + 1) + "번 (" + diff + tag + ")";
      basItemSelect.appendChild(opt);
    });
    updateBasProgress();
  } catch (_) {
    if (basItemSelect) basItemSelect.innerHTML = "<option>문제를 불러오지 못했어요</option>";
  }
}

// 푼 문제(정답 처리된 item_id)를 localStorage로 추적해 진행 상황을 표시한다
const BAS_SOLVED_KEY = "toefl_bas_solved_v1";
function getBasSolved() {
  try { return new Set(JSON.parse(localStorage.getItem(BAS_SOLVED_KEY) || "[]")); }
  catch (_) { return new Set(); }
}
function markBasSolved(itemId) {
  const solved = getBasSolved();
  solved.add(itemId);
  try { localStorage.setItem(BAS_SOLVED_KEY, JSON.stringify(Array.from(solved))); } catch (_) {}
  updateBasProgress();
}
function updateBasProgress() {
  const el = document.getElementById("basProgress");
  if (!el || !basItemOrder.length) return;
  const solved = getBasSolved();
  const count = basItemOrder.filter(function(id) { return solved.has(id); }).length;
  el.textContent = "완료 " + count + " / " + basItemOrder.length;
}

function renderBasPool() {
  if (!basFragmentPoolEl) return;
  basFragmentPoolEl.innerHTML = "";
  for (const frag of basPool) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "bas-fragment-chip";
    btn.textContent = frag.text;
    btn.setAttribute("role", "listitem");
    btn.addEventListener("click", function() { moveFragmentToAnswer(frag.key); });
    basFragmentPoolEl.appendChild(btn);
  }
}

function renderBasAnswer() {
  if (!basAnswerListEl) return;
  basAnswerListEl.innerHTML = "";
  basAnswer.forEach(function(frag, idx) {
    const li = document.createElement("li");
    li.className = "bas-answer-item";

    const span = document.createElement("span");
    span.className = "bas-fragment-text";
    span.textContent = frag.text;
    li.appendChild(span);

    const upBtn = document.createElement("button");
    upBtn.type = "button";
    upBtn.className = "bas-icon-btn";
    upBtn.textContent = "▲";
    upBtn.setAttribute("aria-label", "위로 이동");
    upBtn.disabled = idx === 0;
    upBtn.addEventListener("click", function() { moveBasAnswerItem(idx, -1); });
    li.appendChild(upBtn);

    const downBtn = document.createElement("button");
    downBtn.type = "button";
    downBtn.className = "bas-icon-btn";
    downBtn.textContent = "▼";
    downBtn.setAttribute("aria-label", "아래로 이동");
    downBtn.disabled = idx === basAnswer.length - 1;
    downBtn.addEventListener("click", function() { moveBasAnswerItem(idx, 1); });
    li.appendChild(downBtn);

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "bas-icon-btn";
    removeBtn.textContent = "✕";
    removeBtn.setAttribute("aria-label", "제거");
    removeBtn.addEventListener("click", function() { moveFragmentToPool(frag.key); });
    li.appendChild(removeBtn);

    basAnswerListEl.appendChild(li);
  });
}

function moveFragmentToAnswer(key) {
  const idx = basPool.findIndex(function(f) { return f.key === key; });
  if (idx === -1) return;
  const [frag] = basPool.splice(idx, 1);
  basAnswer.push(frag);
  renderBasPool();
  renderBasAnswer();
}

function moveFragmentToPool(key) {
  const idx = basAnswer.findIndex(function(f) { return f.key === key; });
  if (idx === -1) return;
  const [frag] = basAnswer.splice(idx, 1);
  basPool.push(frag);
  renderBasPool();
  renderBasAnswer();
}

function moveBasAnswerItem(idx, direction) {
  const target = idx + direction;
  if (target < 0 || target >= basAnswer.length) return;
  const tmp = basAnswer[idx];
  basAnswer[idx] = basAnswer[target];
  basAnswer[target] = tmp;
  renderBasAnswer();
}

async function startBasItem() {
  if (!basItemSelect || !basItemSelect.value) return;
  const itemId = basItemSelect.value;
  try {
    const res = await fetch(`/api/build-a-sentence/items/${encodeURIComponent(itemId)}`);
    if (!res.ok) throw new Error();
    const data = await res.json();
    basCurrentItemId = data.item_id;
    basPool = data.source_fragments.map(function(text) { return { key: ++basKeyCounter, text: text }; });
    basAnswer = [];
    basStartedAt = Date.now();
    if (basDirectInputEl) basDirectInputEl.value = "";
    if (basAttemptInfoEl) basAttemptInfoEl.textContent = "";
    if (basFeedbackEl) { basFeedbackEl.className = "bas-feedback hidden"; basFeedbackEl.textContent = ""; }
    const explEl = document.getElementById("basExplanation");
    if (explEl) explEl.classList.add("hidden");
    const nextBtn = document.getElementById("basNextBtn");
    if (nextBtn) nextBtn.classList.add("hidden");
    if (basPlayArea) basPlayArea.classList.remove("hidden");
    renderBasPool();
    renderBasAnswer();
  } catch (_) {
    if (basFeedbackEl) {
      basFeedbackEl.className = "bas-feedback incorrect";
      basFeedbackEl.textContent = "문제를 불러오지 못했습니다. 다시 시도해 주세요.";
    }
  }
}

async function submitBasAnswer() {
  if (!basCurrentItemId) return;
  const directText = basDirectInputEl ? basDirectInputEl.value.trim() : "";
  const submissionText = directText || basAnswer.map(function(f) { return f.text; }).join(" ");
  if (!submissionText) {
    if (basFeedbackEl) {
      basFeedbackEl.className = "bas-feedback incorrect";
      basFeedbackEl.textContent = "조각을 배열하거나 직접 입력한 후 제출해 주세요.";
    }
    return;
  }
  const timeSpentMs = basStartedAt ? Date.now() - basStartedAt : null;
  try {
    const res = await fetch(`/api/build-a-sentence/items/${encodeURIComponent(basCurrentItemId)}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ submission_text: submissionText, time_spent_ms: timeSpentMs }),
    });
    if (!res.ok) throw new Error();
    const data = await res.json();
    if (basAttemptInfoEl) basAttemptInfoEl.textContent = `시도 ${data.attempt_number}회`;
    if (basFeedbackEl) {
      basFeedbackEl.className = "bas-feedback " + (data.is_correct ? "correct" : "incorrect");
      let text = data.feedback;
      if (!data.is_correct && data.correct_answer) {
        text += ` (정답 예시: ${data.correct_answer})`;
      }
      basFeedbackEl.textContent = text;
    }
    const explEl = document.getElementById("basExplanation");
    if (explEl) {
      if (data.explanation) {
        explEl.textContent = "💡 " + data.explanation;
        explEl.classList.remove("hidden");
      } else {
        explEl.classList.add("hidden");
      }
    }
    if (data.is_correct) {
      markBasSolved(basCurrentItemId);
      const nextBtn = document.getElementById("basNextBtn");
      if (nextBtn) nextBtn.classList.remove("hidden");
    }
  } catch (_) {
    if (basFeedbackEl) {
      basFeedbackEl.className = "bas-feedback incorrect";
      basFeedbackEl.textContent = "채점 요청에 실패했어요. 답안 배열은 그대로 남아 있으니 다시 제출해 보세요.";
    }
  }
}

function goToNextBasItem() {
  if (!basItemSelect || !basItemOrder.length || !basCurrentItemId) return;
  const idx = basItemOrder.indexOf(basCurrentItemId);
  const nextId = basItemOrder[(idx + 1) % basItemOrder.length];
  basItemSelect.value = nextId;
  const nextBtn = document.getElementById("basNextBtn");
  if (nextBtn) nextBtn.classList.add("hidden");
  startBasItem();
}

if (basStartBtn) basStartBtn.addEventListener("click", startBasItem);
if (basRefreshBtn) basRefreshBtn.addEventListener("click", loadBasItemOptions);
if (basSubmitBtn) basSubmitBtn.addEventListener("click", submitBasAnswer);
if (basResetBtn) basResetBtn.addEventListener("click", startBasItem);
const basNextBtnEl = document.getElementById("basNextBtn");
if (basNextBtnEl) basNextBtnEl.addEventListener("click", goToNextBasItem);

/* ── 온보딩 (최초 실행 안내) ─────────────────────────────────────────── */
async function initOnboarding() {
  const dialog = document.getElementById("onboardingDialog");
  if (!dialog || typeof dialog.showModal !== "function") return;
  try {
    const res = await fetch("/api/onboarding");
    if (!res.ok) return;
    const data = await res.json();
    if (!data.done) dialog.showModal();
  } catch (_) { /* 상태 조회 실패 시 온보딩을 강제하지 않는다 */ }

  const startBtn = document.getElementById("onboardingStartBtn");
  if (startBtn) {
    startBtn.addEventListener("click", async function() {
      dialog.close();
      try { await fetch("/api/onboarding/complete", { method: "POST" }); } catch (_) {}
    });
  }
  const replayBtn = document.getElementById("replayOnboardingBtn");
  if (replayBtn) {
    replayBtn.addEventListener("click", function() { dialog.showModal(); });
  }
}

/* ── 백업·복원·전체 삭제 ─────────────────────────────────────────────── */
function formatBytes(n) {
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  return (n / (1024 * 1024)).toFixed(1) + " MB";
}

async function refreshBackupList() {
  const listEl = document.getElementById("backupList");
  const dirEl = document.getElementById("backupsDirPath");
  if (!listEl) return;
  try {
    const res = await fetch("/api/backup/list");
    if (!res.ok) throw new Error();
    const data = await res.json();
    if (dirEl) dirEl.textContent = data.backups_dir || "-";
    listEl.innerHTML = "";
    if (!data.backups.length) {
      listEl.innerHTML = '<p class="muted small">아직 만든 백업이 없어요.</p>';
      return;
    }
    data.backups.forEach(function(b) {
      const row = document.createElement("div");
      row.className = "backup-row";
      const when = b.created_at ? new Date(b.created_at).toLocaleString() : "생성일 알 수 없음";
      const counts = b.record_counts ? " · 기록 " + b.record_counts.submissions + "건" : "";
      const info = document.createElement("span");
      info.textContent = when + counts + " · " + formatBytes(b.size_bytes) + (b.app_version ? " · v" + b.app_version : "");
      row.appendChild(info);

      const restoreBtn = document.createElement("button");
      restoreBtn.type = "button";
      restoreBtn.className = "btn ghost sm";
      restoreBtn.textContent = "복원";
      restoreBtn.disabled = !b.readable;
      restoreBtn.addEventListener("click", function() { restoreFromBackup(b.filename); });
      row.appendChild(restoreBtn);

      listEl.appendChild(row);
    });
  } catch (_) {
    listEl.innerHTML = '<p class="muted small">백업 목록을 불러오지 못했어요.</p>';
  }
}

async function createBackup() {
  const statusEl = document.getElementById("backupStatus");
  if (statusEl) statusEl.textContent = "백업을 만들고 있어요…";
  try {
    const res = await fetch("/api/backup", { method: "POST" });
    if (!res.ok) throw new Error();
    const meta = await res.json();
    if (statusEl) statusEl.textContent = "백업 완료 — 기록 " + meta.record_counts.submissions + "건이 담겼어요.";
    refreshBackupList();
  } catch (_) {
    if (statusEl) statusEl.textContent = "백업을 만들지 못했어요. 저장 공간을 확인하고 다시 시도해 주세요.";
  }
}

async function restoreFromBackup(filename) {
  const statusEl = document.getElementById("backupStatus");
  try {
    // 1) 미리보기 — 복원될 기록 수를 사용자에게 보여주고 확인받는다
    const inspectRes = await fetch("/api/backup/inspect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: filename }),
    });
    const inspect = await inspectRes.json();
    if (!inspectRes.ok) throw new Error(inspect.detail || "백업 파일을 확인하지 못했어요");

    const backupCount = inspect.backup.record_counts.submissions;
    const currentCount = inspect.current_record_counts.submissions;
    const ok = window.confirm(
      "이 백업으로 되돌릴까요?\n\n" +
      "백업 속 기록: " + backupCount + "건 (" + new Date(inspect.backup.created_at).toLocaleString() + ")\n" +
      "현재 기록: " + currentCount + "건\n\n" +
      "복원 전에 현재 데이터가 자동으로 백업되니 안심하세요."
    );
    if (!ok) return;

    if (statusEl) statusEl.textContent = "복원하고 있어요…";
    const res = await fetch("/api/backup/restore", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: filename }),
    });
    const body = await res.json();
    if (!res.ok) throw new Error(body.detail || "복원에 실패했어요");
    if (statusEl) statusEl.textContent = "복원 완료 — 기록 " + body.record_counts.submissions + "건. 화면을 새로고침해요.";
    await Promise.all([fetchHistory(), fetchDashboard()]);
    refreshBackupList();
  } catch (err) {
    if (statusEl) statusEl.textContent = "복원하지 못했어요: " + err.message + " — 기존 데이터는 그대로 안전해요.";
  }
}

function initDataManagement() {
  const createBtn = document.getElementById("createBackupBtn");
  if (createBtn) createBtn.addEventListener("click", createBackup);

  const deleteAllBtn = document.getElementById("deleteAllBtn");
  const confirmBox = document.getElementById("deleteAllConfirm");
  const execBtn = document.getElementById("deleteAllExecBtn");
  const cancelBtn = document.getElementById("deleteAllCancelBtn");
  const phraseInput = document.getElementById("deleteAllPhrase");
  const delStatusEl = document.getElementById("deleteAllStatus");

  if (deleteAllBtn && confirmBox) {
    deleteAllBtn.addEventListener("click", function() {
      confirmBox.classList.remove("hidden");
      if (phraseInput) phraseInput.focus();
    });
  }
  if (cancelBtn && confirmBox) {
    cancelBtn.addEventListener("click", function() {
      confirmBox.classList.add("hidden");
      if (phraseInput) phraseInput.value = "";
      if (delStatusEl) delStatusEl.textContent = "";
    });
  }
  if (execBtn) {
    execBtn.addEventListener("click", async function() {
      const phrase = phraseInput ? phraseInput.value.trim() : "";
      if (delStatusEl) delStatusEl.textContent = "삭제하고 있어요…";
      try {
        const res = await fetch("/api/data/delete-all", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ confirm: phrase }),
        });
        const body = await res.json();
        if (!res.ok) throw new Error(body.detail || "삭제하지 못했어요");
        if (delStatusEl) {
          delStatusEl.textContent = "삭제 완료. 되돌리려면 백업 목록에서 '" + body.safety_backup + "'을(를) 복원하세요.";
        }
        if (phraseInput) phraseInput.value = "";
        essayTextEl.value = "";
        await Promise.all([fetchHistory(), fetchDashboard()]);
        refreshBackupList();
      } catch (err) {
        if (delStatusEl) delStatusEl.textContent = err.message;
      }
    });
  }

  // 데이터 관리 섹션을 열 때 백업 목록을 로드한다
  const details = document.getElementById("dataManageDetails");
  if (details) {
    details.addEventListener("toggle", function() {
      if (details.open) refreshBackupList();
    });
  }
}

async function fetchAppStatus() {
  const modeEl = document.getElementById("statusAnalysisMode");
  const shadowEl = document.getElementById("statusShadowState");
  const versionEl = document.getElementById("statusAppVersion");
  const schemaEl = document.getElementById("statusSchemaVersion");
  const summaryEl = document.getElementById("statusSummaryLine");
  if (!modeEl && !versionEl) return;
  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error();
    const data = await res.json();
    if (versionEl) versionEl.textContent = data.app_version || "-";
    if (schemaEl) schemaEl.textContent = data.db_schema_version || "-";
    if (shadowEl) shadowEl.textContent = data.shadow_enabled ? "활성 (연구용, 점수 미반영)" : "비활성";
    if (modeEl) modeEl.textContent = "기본 분석 모드";
    if (summaryEl) {
      summaryEl.textContent = data.shadow_enabled
        ? "기본 분석 모드 · AI 심층 분석 활성(연구용)"
        : "기본 분석 모드";
    }
  } catch (_) {
    if (summaryEl) summaryEl.textContent = "기본 분석 모드 (상태 확인 실패)";
  }
}

async function loadAiConfig() {
  try {
    const res = await fetch("/api/ai/config");
    if (!res.ok) throw new Error();
    const cfg = await res.json();
    aiProviderSelect.value = cfg.provider;
    aiEnabledCheckbox.checked = Boolean(cfg.enabled);
    openaiModelInput.value = cfg.openai_model || "gpt-4.1-mini";
    anthropicModelInput.value = cfg.anthropic_model || "claude-3-5-sonnet-latest";
    geminiModelInput.value = cfg.gemini_model || "gemini-1.5-pro-latest";
    openaiApiKeyInput.placeholder = cfg.has_openai_key ? "저장됨 (재입력 시 갱신)" : "sk-...";
    anthropicApiKeyInput.placeholder = cfg.has_anthropic_key ? "저장됨 (재입력 시 갱신)" : "sk-ant-...";
    geminiApiKeyInput.placeholder = cfg.has_gemini_key ? "저장됨 (재입력 시 갱신)" : "AIza...";
    aiConfigStatus.textContent = "현재 설정을 불러왔습니다.";
  } catch (_) {
    aiConfigStatus.textContent = "AI 설정을 불러오지 못했습니다.";
  }
}

async function saveAiConfig() {
  const payload = {
    provider: aiProviderSelect.value,
    enabled: Boolean(aiEnabledCheckbox.checked),
    openai_api_key: openaiApiKeyInput.value.trim() || null,
    openai_model: openaiModelInput.value.trim() || null,
    anthropic_api_key: anthropicApiKeyInput.value.trim() || null,
    anthropic_model: anthropicModelInput.value.trim() || null,
    gemini_api_key: geminiApiKeyInput.value.trim() || null,
    gemini_model: geminiModelInput.value.trim() || null,
  };
  try {
    const res = await fetch("/api/ai/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error();
    openaiApiKeyInput.value = "";
    anthropicApiKeyInput.value = "";
    geminiApiKeyInput.value = "";
    await loadAiConfig();
    aiConfigStatus.textContent = "AI 설정이 저장되었습니다.";
  } catch (_) {
    aiConfigStatus.textContent = "AI 설정 저장에 실패했습니다.";
  }
}

async function testAiConfig() {
  aiConfigStatus.textContent = "연결 테스트 중...";
  try {
    const res = await fetch("/api/ai/test", { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error();
    aiConfigStatus.textContent = (data.ok ? "성공: " : "실패: ") + (data.message || "테스트 완료");
  } catch (_) {
    aiConfigStatus.textContent = "연결 테스트 요청에 실패했습니다.";
  }
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
  essayTextEl.focus();
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
    detectBadgeEl.textContent = "✉️ 이메일 (Write an Email)";
  } else {
    detectBadgeEl.className = "detect-badge detect-disc";
    detectBadgeEl.textContent = "💬 학술 토론 (Academic Discussion)";
  }
  return type;
}

essayTextEl.addEventListener("input", function() {
  updateDetectBadge(essayTextEl.value);
  updateLiveStats();
  saveDraft();
});

if (promptTextEl) {
  promptTextEl.addEventListener("input", saveDraft);
}

essayTextEl.addEventListener("keydown", function(ev) {
  if ((ev.metaKey || ev.ctrlKey) && ev.key === "Enter") {
    ev.preventDefault();
    evaluateEssay(false);
  }
});

/* ── Helpers ─────────────────────────────────────────────────────────── */
function setText(el, val) { if (el) el.textContent = val != null ? val : "-"; }

/* 사용자 답안 등 신뢰할 수 없는 텍스트는 innerHTML 삽입 전 반드시 이스케이프한다 */
function esc(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const SEVERITY_SAFE = { high: "high", medium: "medium", low: "low" };
function safeSeverity(value) { return SEVERITY_SAFE[value] || "medium"; }

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
      '<span class="rubric-name">' + esc(d.name) + '</span>' +
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
      "<p><strong>원문</strong>: " + esc(item.original) + "</p>" +
      "<p><strong>개선</strong>: " + esc(item.improved) + "</p>" +
      "<p><strong>포인트</strong>: " + esc(item.note) + "</p>";
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
      '<p><span class="tag tag-' + esc(item.tag) + '">' + esc(item.tag) + '</span>' + esc(item.sentence) + '</p>' +
      "<p><strong>설명</strong>: " + esc(item.note) + "</p>";
    claimMapEl.appendChild(box);
  });
}

function renderScoreHighlights(items) {
  scoreHighlightsEl.innerHTML = "";
  items.forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML =
      '<p><span class="tag tag-' + esc(item.impact) + '">' + esc(item.impact) + '</span>' + esc(item.sentence) + '</p>' +
      "<p><strong>근거</strong>: " + esc(item.reason) + "</p>";
    scoreHighlightsEl.appendChild(box);
  });
}

function renderWeaknessDictionary(items) {
  weaknessDictionaryEl.innerHTML = "";
  items.forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML =
      "<p><strong>분류</strong>: " + esc(item.category) + "</p>" +
      "<p><strong>잘못된 패턴</strong>: " + esc(item.wrong_pattern) + "</p>" +
      "<p><strong>교정 패턴</strong>: " + esc(item.fix_pattern) + "</p>" +
      "<p><strong>팁</strong>: " + esc(item.tip) + "</p>";
    weaknessDictionaryEl.appendChild(box);
  });
}

function renderParaphraseSuggestions(items) {
  paraphraseSuggestionsEl.innerHTML = "";
  (items && items.length ? items : []).forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML =
      "<p><strong>원표현</strong>: " + esc(item.original) + "</p>" +
      "<p><strong>추천표현</strong>: " + esc(item.improved) + "</p>" +
      "<p><strong>이유</strong>: " + esc(item.reason) + "</p>";
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
      "<p><strong>항목</strong>: " + esc(item.label) + "</p>" +
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
      "<p><strong>이슈</strong>: " + esc(item.issue) + "</p>" +
      "<p><strong>오답</strong>: " + esc(item.wrong) + "</p>" +
      "<p><strong>정답</strong>: " + esc(item.correct) + "</p>" +
      "<p><strong>팁</strong>: " + esc(item.tip) + "</p>";
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
    box.className = "edit-item correction-item severity-" + safeSeverity(item.severity);
    box.id = "corr-" + idx;
    box.innerHTML =
      '<p><span class="tag">' + esc(item.error_type) + '</span><span class="badge small-badge">' + esc(safeSeverity(item.severity)) + '</span></p>' +
      "<p><strong>원문</strong>: " + esc(item.sentence) + "</p>" +
      "<p><strong>교정</strong>: " + esc(item.corrected) + "</p>" +
      "<p><strong>근거</strong>: " + esc(item.explanation) + "</p>";
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
      "<p><strong>이슈</strong>: " + esc(item.issue) + "</p>" +
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
      "<p><strong>액션</strong>: " + esc(item.action) + "</p>" +
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
      "<p><strong>액션</strong>: " + esc(item.title) + "</p>" +
      "<p><strong>기대효과</strong>: " + esc(item.impact) + "</p>" +
      "<p><strong>신뢰도</strong>: " + esc(item.confidence || "medium") + "</p>" +
      "<p><strong>이유</strong>: " + esc(item.why) + "</p>" +
      "<p><strong>실행법</strong>: " + esc(item.how_to) + "</p>";
    smartRecommendationsEl.appendChild(box);
  });
}

function renderTopPriorityActions(items) {
  topPriorityActionsEl.innerHTML = "";
  (items || []).forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML =
      "<p><strong>우선 액션</strong>: " + esc(item.title) + "</p>" +
      "<p><strong>기대효과</strong>: " + esc(item.impact) + "</p>" +
      "<p><strong>신뢰도</strong>: " + esc(item.confidence || "medium") + "</p>";
    topPriorityActionsEl.appendChild(box);
  });
}

function renderTargetEta(eta) {
  targetEtaEl.innerHTML = "";
  if (!eta) return;
  const box = document.createElement("div");
  box.className = "edit-item";
  box.innerHTML =
    "<p><strong>예상 제출 횟수</strong>: " + esc(eta.estimated_attempts) + "회</p>" +
    "<p><strong>페이스</strong>: " + esc(eta.pace_label) + "</p>" +
    "<p><strong>메시지</strong>: " + esc(eta.message) + "</p>";
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
    "<p><strong>코치</strong>: " + esc(v.recommendation || "") + "</p>";
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
    box.innerHTML = "<p><strong>전략</strong>: " + esc(item.title) + "</p><p>" + esc(item.detail) + "</p>";
    targetBandStrategyEl.appendChild(box);
  });
}

function renderRepetitionTraining(items) {
  repetitionTrainingEl.innerHTML = "";
  (items || []).forEach(function(item) {
    const box = document.createElement("div");
    box.className = "edit-item";
    box.innerHTML =
      "<p><strong>반복어</strong>: " + esc(item.word) + " (" + esc(item.count) + "회)</p>" +
      "<p><strong>대체어</strong>: " + esc((item.alternatives || []).join(", ")) + "</p>";
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

function renderEngineInfo(engine) {
  if (!engineBadgeEl || !engineInfoEl) return;
  if (!engine) {
    engineBadgeEl.textContent = "레거시 기록 (버전 정보 없음)";
    engineInfoEl.innerHTML = "<p>이 결과는 버전 스탬프 도입 이전에 저장된 형식입니다.</p>";
    return;
  }
  engineBadgeEl.textContent = "v" + esc(engine.scoring_engine_version);
  const rows = [
    ["시험 사양", engine.exam_spec_version],
    ["루브릭", engine.rubric_version],
    ["문법 규칙", engine.grammar_rules_version],
    ["결과 스키마", engine.result_schema_version],
    ["채점 방식", engine.provider === "heuristic" ? "결정론적 휴리스틱 (AI 미개입)" : esc(engine.provider)],
    ["모델", engine.model === "not-applicable" ? "해당 없음" : esc(engine.model)],
    ["캘리브레이션", engine.calibration_version === "uncalibrated" ? "미적용 (전문가 데이터 확보 전)" : esc(engine.calibration_version)],
  ];
  engineInfoEl.innerHTML = rows.map(function(r) {
    return '<p class="kv"><span class="kv-key">' + esc(r[0]) + '</span><span>' + esc(r[1]) + '</span></p>';
  }).join("");
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
      const legacyTag = row.is_legacy ? ' <span class="badge small-badge" title="이전 버전 채점 기준 — 최신 결과와 직접 비교하면 부정확할 수 있어요">이전 기준</span>' : "";
      div.innerHTML =
        "<span>#" + esc(row.id) + " · " + esc(typeLabel) + " · " + esc(new Date(row.created_at).toLocaleString()) + legacyTag + "</span>" +
        "<strong>Band " + esc(row.score_band_1_6.toFixed(1)) + " / 6</strong>";

      const actions = document.createElement("span");
      actions.className = "history-actions";

      const pdfBtn = document.createElement("button");
      pdfBtn.type = "button";
      pdfBtn.className = "btn ghost sm";
      pdfBtn.textContent = "PDF";
      pdfBtn.setAttribute("aria-label", "#" + row.id + " 기록 PDF 열기");
      pdfBtn.addEventListener("click", function() {
        window.open("/api/report/" + row.id + ".pdf", "_blank");
      });
      actions.appendChild(pdfBtn);

      const delBtn = document.createElement("button");
      delBtn.type = "button";
      delBtn.className = "btn ghost sm";
      delBtn.textContent = "삭제";
      delBtn.setAttribute("aria-label", "#" + row.id + " 기록 삭제");
      delBtn.addEventListener("click", async function() {
        if (!window.confirm("#" + row.id + " 기록을 삭제할까요? 이 기록만 지워지고 다른 기록은 그대로 남아요.")) return;
        try {
          const delRes = await fetch("/api/history/" + row.id, { method: "DELETE" });
          if (!delRes.ok) throw new Error();
          fetchHistory();
          fetchDashboard();
        } catch (_) {
          statusText.textContent = "기록 삭제에 실패했어요. 잠시 후 다시 시도해 주세요.";
        }
      });
      actions.appendChild(delBtn);
      div.appendChild(actions);

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
      body: JSON.stringify({
        essay_text: essay,
        prompt_text: promptTextEl ? promptTextEl.value.trim() : "",
      }),
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
    prompt_text: promptTextEl ? promptTextEl.value.trim() : "",
    target_score_0_5: Math.max(0, Math.min(5, Number(targetScoreEl.value || 5.0) - 1.0)),
    exam_mode: Boolean(isExamMode),
  };

  evaluateBtn.disabled = true;
  // Offline Core의 실제 처리 순서에 맞춘 단계 문구 — 처리가 빨리 끝나면
  // 그대로 결과가 표시된다 (가짜 진행률/억지 대기 없음).
  const loadingStages = [
    "답안 구조를 확인하고 있어요…",
    "문법과 표현을 분석하고 있어요…",
    "점수와 개선 방향을 정리하고 있어요…",
  ];
  let stageIdx = 0;
  statusText.textContent = loadingStages[0];
  const stageTimer = setInterval(function() {
    stageIdx = Math.min(stageIdx + 1, loadingStages.length - 1);
    statusText.textContent = loadingStages[stageIdx];
  }, 700);

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
    setText(aiModeBadgeEl, result.ai_mode === "ai" ? (providerLabel(result.ai_provider) + " 연동") : "로컬");
    if (result.grammar_cap_applied) {
      if (grammarCapChipEl) grammarCapChipEl.hidden = false;
      setText(grammarCapBadgeEl, "적용됨");
      setText(grammarCapReasonEl, result.grammar_cap_reason || "문법 상한이 적용되었습니다.");
    } else {
      if (grammarCapChipEl) grammarCapChipEl.hidden = true;
      setText(grammarCapBadgeEl, "없음");
      setText(grammarCapReasonEl, "");
    }
    setText(confidenceEl, result.confidence);
    setText(confidenceReasonEl, result.confidence_reason);
    renderEngineInfo(result.engine || null);
    animateScoreRing(s);

    const detectedType = detectType(essay);
    setText(taskTagEl, detectedType === "email" ? "이메일" : "학술 토론");
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
    renderScoreHighlights(result.score_highlights);
    renderClaimMap(result.claim_evidence_map);

    setText(rewriteMinimalEl, result.target_rewrite.minimal);
    setText(rewriteAggressiveEl, result.target_rewrite.aggressive);
    const overlapBand = Math.max(1, Math.min(6, Number(result.sample_comparison.overlap_score || 0) + 1));
    setText(sampleOverlapEl, overlapBand.toFixed(1));
    setText(sampleMatchedEl, result.sample_comparison.matched_points.join(", ") || "없음");
    setText(sampleMissingEl, result.sample_comparison.missing_points.join(", ") || "없음");
    setText(sampleParagraphEl, result.upgraded_sample_paragraph);

    resultSection.classList.remove("hidden");
    resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    downloadPdfBtn.disabled = false;
    autoReevalBtn.disabled = !(result.auto_rewrite_essay && result.auto_rewrite_essay.trim());
    downloadPdfBtn.dataset.submissionId = String(data.submission_id);
    statusText.textContent = "채점 완료 (ID: " + data.submission_id + ")";
    // 채점 완료된 답안의 draft는 정리한다 — 단 화면의 텍스트는 그대로 유지되므로
    // 사용자가 제출 직전 내용을 잃지 않는다.
    fetch("/api/draft", { method: "DELETE" }).catch(function() {});
    await Promise.all([fetchHistory(), fetchDashboard()]);
  } catch(err) {
    statusText.textContent = "채점하지 못했어요: " + err.message + " — 작성한 답안은 그대로 남아 있어요. 다시 시도해 주세요.";
  } finally {
    clearInterval(stageTimer);
    evaluateBtn.disabled = false;
  }
}

/* ── Event Listeners ─────────────────────────────────────────────────── */
checkRiskBtn.addEventListener("click", checkRisk);
evaluateBtn.addEventListener("click", function() { evaluateEssay(false); });
startTimerBtn.addEventListener("click", startTimer);
insertTemplateBtn.addEventListener("click", insertTemplate);
savePromptBtn.addEventListener("click", savePromptLibrary);
loadPromptBtn.addEventListener("click", loadPromptLibrary);
clearDraftBtn.addEventListener("click", function() {
  essayTextEl.value = "";
  localStorage.removeItem(DRAFT_KEY);
  fetch("/api/draft", { method: "DELETE" }).catch(function() {});
  setText(draftStatusEl, "비웠어요");
  updateDetectBadge(essayTextEl.value);
  updateLiveStats();
  essayTextEl.focus();
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
  essayTextEl.focus();
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
saveAiConfigBtn.addEventListener("click", saveAiConfig);
testAiConfigBtn.addEventListener("click", testAiConfig);
copyMinimalBtn.addEventListener("click", function() { copyTextSafe(rewriteMinimalEl.textContent || "", "최소 수정문"); });
copyAggressiveBtn.addEventListener("click", function() { copyTextSafe(rewriteAggressiveEl.textContent || "", "적극 수정문"); });

fetchHistory();
fetchDashboard();
fetchAppStatus();
loadBasItemOptions();
loadAiConfig();
loadDraft();
initOnboarding();
initDataManagement();
updateDetectBadge(essayTextEl.value);
updateLiveStats();
window.addEventListener("load", function() {
  essayTextEl.focus();
  essayTextEl.setSelectionRange(essayTextEl.value.length, essayTextEl.value.length);
});
