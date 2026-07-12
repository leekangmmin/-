"use strict";

const $ = (id) => document.getElementById(id);
const essay = $("essayText");
const prompt = $("promptText");
const storageKey = "toefl-web-draft-v1";

const LABELS = {
  greeting:"자연스러운 인사", purpose:"글을 쓰는 목적", situation:"구체적인 상황 설명", request:"정중하고 직접적인 요청", second:"두 번째 요청 또는 후속 조치", closing:"간단한 맺음말",
  stance:"명확한 입장", reason:"주장을 뒷받침하는 이유", example:"구체적인 예시", explanation:"예시의 영향 설명", other:"다른 학생 의견에 대한 반응", reinforcement:"입장 재강조"
};

const PATTERNS = {
  email: {
    greeting:/^\s*(dear|hello|hi|good (morning|afternoon)|to whom it may concern)\b/im,
    purpose:/\b(i am writing (to|concerning|regarding)|i would like to|i am contacting you)\b/i,
    situation:/\b(unfortunately|because|due to|the problem|the issue|specifically)\b/i,
    request:/\b(could you please|would you please|i would be grateful if|i would appreciate it if|please)\b/i,
    second:/\b(i would also|also appreciate|in addition|and let me know|as well)\b/i,
    closing:/\b(sincerely|best regards|kind regards|regards|yours truly)\b/i
  },
  academic_discussion: {
    stance:/\b(i (firmly |strongly )?(believe|agree|disagree|maintain|support)|in my view|my position)\b/i,
    reason:/\b(because|one reason|the reason|this is important)\b/i,
    example:/\b(for example|for instance|a clear example|in my experience|when students|when people)\b/i,
    explanation:/\b(as a result|therefore|consequently|this (means|allows|helps|would)|thus)\b/i,
    other:/\b(i (agree|disagree) with [A-Z][a-z]+|[A-Z][a-z]+('s|\s+raises|\s+argues|\s+points? out)|while [A-Z][a-z]+)\b/,
    reinforcement:/\b(for these reasons|overall|in conclusion|i maintain|should therefore)\b/i
  }
};

function words(text) { return text.match(/[A-Za-z']+/g) || []; }
function sentences(text) { return text.split(/(?<=[.!?])\s+/).filter(Boolean); }
function count(text, re) { return (text.match(re) || []).length; }
function clamp(n,min,max) { return Math.max(min,Math.min(max,n)); }
function quarter(n) { return Math.round(clamp(n,0,5)*4)/4; }
function half(n) { return Math.round(clamp(n,0,5)*2)/2; }

function detectType(text) {
  let signals = 0;
  if (/^\s*(dear|hello|hi|to whom)/im.test(text)) signals += 2;
  if (/\b(sincerely|best regards|kind regards|yours truly)\b/i.test(text)) signals += 2;
  if (/\bi am writing (to|regarding|concerning)\b/i.test(text)) signals += 1;
  return signals >= 2 ? "email" : "academic_discussion";
}

function analyzeStructure(text,type) {
  const detected = Object.entries(PATTERNS[type]).filter(([,re]) => re.test(text)).map(([key]) => key);
  const missing = Object.keys(PATTERNS[type]).filter((key) => !detected.includes(key));
  return {detected,missing};
}

function score(text,type) {
  const ws = words(text), ss = sentences(text), unique = new Set(ws.map(w=>w.toLowerCase()));
  const paragraphs = text.split(/\n\s*\n/).filter(x=>x.trim()).length;
  const transitions = count(text,/\b(however|therefore|moreover|furthermore|in addition|for example|for instance|as a result|consequently|thus|overall)\b/gi);
  const evidence = count(text,/\b(because|for example|for instance|according to|research|study|data|as a result)\b/gi);
  const avg = ws.length / Math.max(ss.length,1), diversity = unique.size / Math.max(ws.length,1);
  const structureMoves = analyzeStructure(text,type).detected.length;
  const structureTotal = Object.keys(PATTERNS[type]).length;
  const target = type === "email" ? 100 : 120;
  const structure = quarter(1.2 + 2.5*(structureMoves/structureTotal) + Math.min(paragraphs,4)*.25);
  const content = quarter(1.4 + Math.min(ws.length/target,1)*1.2 + Math.min(evidence,4)*.4 + (prompt.value.trim() ? topicFit(prompt.value,text)*.8 : .4));
  const coherence = quarter(1.8 + Math.min(transitions,5)*.35 + (paragraphs>=3?.7:0) + (diversity>=.45?.5:0));
  const detail = quarter(1.4 + Math.min(evidence,4)*.55 + (ss.length>=7?.7:.2));
  const grammar = quarter(2 + (avg>=10&&avg<=28?1:0) + (ss.every(s=>words(s).length<=36)?1:0) + (ss.length>=6?.5:0));
  const vocabulary = quarter(2 + (diversity>=.55?1.5:diversity>=.45?.8:.3) + Math.min(transitions,4)*.25);
  const dims = [{name:"Structure",score:structure},{name:"Content",score:content},{name:"Coherence",score:coherence},{name:"Example",score:detail},{name:"Grammar",score:grammar},{name:"Vocabulary",score:vocabulary}];
  let raw = dims.reduce((sum,d)=>sum+d.score*(d.name==="Grammar"?2.4:1),0)/7.4-.55;
  if (ws.length < target) raw -= .35;
  if (paragraphs <= 1) raw -= .35;
  if (!evidence) raw -= .2;
  return {dims,internal:half(raw),band:half(clamp(raw+1,1,6)),words:ws.length,paragraphs,transitions,evidence,diversity};
}

function topicFit(promptText,answerText) {
  const stop = new Set(["the","and","that","with","this","from","what","should","would","could","about","your"]);
  const keys = [...new Set(words(promptText).map(x=>x.toLowerCase()).filter(x=>x.length>=4&&!stop.has(x)))].slice(0,12);
  const answer = new Set(words(answerText).map(x=>x.toLowerCase()));
  return keys.length ? keys.filter(k=>answer.has(k)).length/keys.length : .5;
}

function list(id,items,empty) { $(id).innerHTML = (items.length?items:[empty]).map(x=>`<li>${escapeHtml(x)}</li>`).join(""); }
function escapeHtml(s) { const d=document.createElement("div"); d.textContent=s; return d.innerHTML; }
function renderBars(dims) { $("dimensions").innerHTML=dims.map(d=>`<div class="rubric-row"><span class="rubric-name">${d.name}</span><div class="rubric-track"><span class="rubric-fill" style="width:${d.score*20}%"></span></div><strong class="rubric-val">${d.score.toFixed(2)}</strong></div>`).join(""); }

function render() {
  const text=essay.value.trim(), wc=words(text).length;
  if (wc<60) { $("status").textContent="최소 60단어 이상 작성해 주세요."; return; }
  const type=detectType(text), result=score(text,type), moves=analyzeStructure(text,type);
  $("bandScore").textContent=result.band.toFixed(1); $("taskName").textContent=type==="email"?"Write an Email":"Academic Discussion";
  $("summary").textContent=`${wc}단어 답안입니다. 핵심 구조 ${moves.detected.length}/${Object.keys(PATTERNS[type]).length}개가 감지됐습니다.`;
  renderBars(result.dims); list("detected",moves.detected.map(x=>LABELS[x]),"아직 감지된 항목이 없습니다."); list("missing",moves.missing.map(x=>LABELS[x]),"핵심 구조가 모두 포함됐습니다.");
  $("nextAction").textContent=moves.missing.length?`${LABELS[moves.missing[0]]}을(를) 한 문장으로 보완하세요.`:"각 근거가 질문에 직접 연결되는지 검토하세요.";
  const strengths=[],weaknesses=[]; if(result.words >= (type==="email"?100:120)) strengths.push("권장 분량을 충족했습니다."); else weaknesses.push("핵심 근거나 상황 설명을 더해 권장 분량을 채우세요."); if(result.paragraphs>=3) strengths.push("문단별 기능이 비교적 분명합니다."); else weaknesses.push("아이디어 경계에 맞춰 문단을 나누세요."); if(result.evidence>=2) strengths.push("이유·예시·결과 연결이 보입니다."); else weaknesses.push("주장 뒤에 구체적인 이유와 예시를 추가하세요."); if(result.transitions>=2) strengths.push("연결어로 흐름을 표시했습니다."); else weaknesses.push("For example, As a result 같은 연결 표현을 활용하세요.");
  list("strengths",strengths,"감지된 강점보다 보완 항목이 먼저 보입니다."); list("weaknesses",weaknesses,"큰 구조 누락이 감지되지 않았습니다.");
  const starters=type==="email"?["I am writing regarding...","Could you please...?","I would also appreciate it if...","Thank you for your assistance."]:["I believe this matters because...","I agree with [Name]'s point that...","One practical example is...","As a result, this would..."];
  $("starters").innerHTML=starters.map(x=>`<div class="starter">${escapeHtml(x)}</div>`).join(""); $("results").classList.remove("hidden"); $("status").textContent="브라우저 안에서 분석을 완료했습니다."; $("results").scrollIntoView({behavior:"smooth",block:"start"});
}

function update() { const text=essay.value, wc=words(text).length; $("wordCount").textContent=`단어 ${wc}`; const type=text.trim()?detectType(text):null; $("typeBadge").textContent=type?(type==="email"?"Write an Email":"Academic Discussion"):"유형 감지 대기"; localStorage.setItem(storageKey,JSON.stringify({essay:text,prompt:prompt.value})); }
try { const saved=JSON.parse(localStorage.getItem(storageKey)||"{}"); essay.value=saved.essay||""; prompt.value=saved.prompt||""; } catch (_) {}
essay.addEventListener("input",update); prompt.addEventListener("input",update); $("scoreBtn").addEventListener("click",render); $("clearBtn").addEventListener("click",()=>{if(confirm("작성 중인 내용을 비울까요?")){essay.value="";prompt.value="";localStorage.removeItem(storageKey);$("results").classList.add("hidden");update();}}); document.addEventListener("keydown",e=>{if((e.metaKey||e.ctrlKey)&&e.key==="Enter")render();}); update();
if ("serviceWorker" in navigator) window.addEventListener("load",()=>navigator.serviceWorker.register("service-worker.js"));
