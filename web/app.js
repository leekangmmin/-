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
    situation:/\b(unfortunately|especially|specifically|because|due to|after|before|during|when|even though|although|until|the problem|the issue)\b/i,
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
  const entries = Object.entries(PATTERNS[type]);
  const detected = entries.filter(([,re]) => re.test(text)).map(([key]) => key);
  const required = type === "email" ? ["purpose","situation"] : ["stance","reason"];
  const missing = required.filter((key) => !detected.includes(key));
  const requiredDetected = required.filter(key => detected.includes(key));
  return {detected:requiredDetected,missing,requiredCount:required.length};
}

function emailSignals(text) {
  const ss=sentences(text);
  const details=count(text,/\b(unfortunately|especially|specifically|because|due to|after|before|during|when|even though|although|until|already|free|vip|mobile phone|deadline|schedule|order|reservation|visit|tour|workshop|assignment|draft|coupon|passes?)\b/gi);
  const polite=count(text,/\b(could you please|would you please|would (?:also )?(?:appreciate|be grateful)|thank you|truly appreciate|your (?:understanding|assistance|consideration)|sincerely|best regards|kind regards)\b/gi);
  const flow=count(text,/\b(after|before|during|even though|although|until|especially|specifically|once again|also|because|therefore|as a result|in addition)\b/gi);
  const detailSentences=ss.filter(s=>words(s).length>=10&&!/^\s*(dear|hello|hi|sincerely|regards)/i.test(s)).length;
  return {details,polite,flow,detailSentences,purpose:PATTERNS.email.purpose.test(text)};
}

function mattr(ws,windowSize=50) {
  const lowered=ws.map(w=>w.toLowerCase());
  if(!lowered.length) return 0;
  if(lowered.length<=windowSize) return new Set(lowered).size/lowered.length;
  let total=0,n=0;
  for(let i=0;i<=lowered.length-windowSize;i++){total+=new Set(lowered.slice(i,i+windowSize)).size/windowSize;n++;}
  return total/n;
}

function genericPenalty(text) {
  const lower=text.toLowerCase();
  const frames=["in today's society","everyone has different opinions","there are many reasons","this is very important","many things"];
  return Math.min(1.25,frames.filter(x=>(lower.split(x).length-1)>=2).length*.35);
}

function grammarRisk(text) {
  const patterns=[
    /\b(students|people|children|they|we)\s+is\b/gi,
    /\b(we|they)\s+was\b/gi,
    /\b(he|she|it)\s+don't\b/gi,
    /\bthere\s+is\s+(many|several|numerous|students|people|reasons)\b/gi,
    /\bdiscuss(?:es|ed)?\s+about\b/gi,
    /\b(a|an)\s+(information|advice|research|evidence|homework)\b/gi,
    /\bmany\s+(information|advice|research|evidence|homework)\b/gi,
    /\bmore\s+(better|worse|easier|harder)\b/gi
  ];
  return patterns.reduce((sum,re)=>sum+count(text,re),0);
}

function score(text,type) {
  const ws = words(text), ss = sentences(text);
  const paragraphs = text.split(/\n\s*\n/).filter(x=>x.trim()).length;
  const transitions = count(text,/\b(although|while|whereas|however|therefore|moreover|furthermore|in addition|for example|for instance|as a result|consequently|thus|overall|because|since|for these reasons)\b/gi);
  const evidence = count(text,/\b(because|since|for example|for instance|according to|research|study|data|as a result|in my experience)\b/gi);
  const avg = ws.length / Math.max(ss.length,1), diversity = mattr(ws);
  const email=type==="email"?emailSignals(text):null;
  const target = type === "email" ? 80 : 100;
  const development=clamp((ws.length-20)/(target-20),0,1);
  const stance=/\b(i (?:firmly |strongly )?(?:believe|agree|disagree|maintain|support|prefer)|in my view|from my perspective|(?:schools?|students?|universities|people)\s+(?:should|must))\b/i.test(text);
  const reasons=count(text,/\b(because|since|one reason|the reason|due to|so that)\b/gi);
  const examples=count(text,/\b(for example|for instance|in my experience|research|a study|data|a student who|students who|people who)\b/gi);
  const explanations=count(text,/\b(as a result|therefore|consequently|thus|this (?:means|shows|allows|helps)|which (?:means|shows|allows|helps|is))\b/gi);
  const support=reasons+examples+explanations;
  const template=genericPenalty(text);
  const task=type==="email"
    ? quarter(.75+(email.purpose?1.35:0)+development*.75+Math.min(1,email.details/4)*1.25+(email.detailSentences>=3?.55:email.detailSentences*.15)+(email.polite?.25:0)-template)
    : quarter(1+(stance?1.25:0)+development*.75+Math.min(1,support/3)*1.4+(ss.length>=4?.35:0)-template);
  const elaboration=type==="email"
    ? quarter(1+development*.8+Math.min(email.details,5)*.3+Math.min(1,email.detailSentences/4)*.8-template)
    : quarter(1+development*.8+Math.min(reasons,2)*.45+Math.min(examples,2)*.65+Math.min(explanations,2)*.45+(support>=3?.35:0)-template);
  const flowHits=type==="email"?Math.max(transitions,email.flow):transitions;
  const organization=quarter((type==="email"?1.25:1.5)+(ss.length>=3?.75:ss.length*.2)+(type==="email"?(email.purpose?.5:0)+(PATTERNS.email.greeting.test(text)?.45:0)+(PATTERNS.email.closing.test(text)?.45:0):(stance?.5:0))+Math.min(flowHits,3)*.2+.5);
  const sentenceLengths=ss.map(s=>words(s).length), bins=new Set(sentenceLengths.map(n=>n<=10?"s":n<=24?"m":"l")).size;
  const subordination=count(text,/\b(although|because|before|after|if|since|unless|when|whereas|while|who|which|that)\b/gi);
  const syntax=quarter(1.5+Math.min(1,ss.length/6)*.6+Math.min(1,subordination/3)+(.35+.2*bins)+(avg>=11?.45:avg/11*.45));
  const longContent=ws.filter(w=>w.length>=7).length/Math.max(ws.length,1);
  const vocabulary=quarter(1.4+(diversity>=.72?1.2:diversity>=.62?1:diversity>=.52?.8:.5)+Math.min(1.2,longContent/.24*1.2)+Math.min(.35,flowHits*.12)-template);
  const errors=grammarRisk(text), errorDensity=errors/Math.max(ws.length,1)*100;
  const accuracy=quarter(5-Math.min(4.5,errorDensity*.42));
  const dims = [{name:"Task Fulfillment",score:task},{name:"Elaboration",score:elaboration},{name:"Organization",score:organization},{name:"Syntax Range",score:syntax},{name:"Vocabulary Control",score:vocabulary},{name:"Language Accuracy",score:accuracy}];
  const weights={"Task Fulfillment":.24,"Elaboration":.22,"Organization":.14,"Syntax Range":.14,"Vocabulary Control":.12,"Language Accuracy":.14};
  let raw=dims.reduce((sum,d)=>sum+d.score*weights[d.name],0);
  let taskScore=half(raw);
  if(ws.length<20) taskScore=Math.min(taskScore,1);
  else if(ws.length<40) taskScore=Math.min(taskScore,2);
  if(accuracy<=1) taskScore=Math.min(taskScore,2);
  return {dims,taskScore,words:ws.length,paragraphs,transitions,evidence,diversity,errors};
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
  $("bandScore").textContent=result.taskScore.toFixed(1); $("taskName").textContent=type==="email"?"Write an Email":"Academic Discussion";
  $("summary").textContent=`${wc}단어 답안입니다. 핵심 구조 ${moves.detected.length}/${moves.requiredCount}개가 감지됐습니다.`;
  renderBars(result.dims); list("detected",moves.detected.map(x=>LABELS[x]),"아직 감지된 항목이 없습니다."); list("missing",moves.missing.map(x=>LABELS[x]),"핵심 구조가 모두 포함됐습니다.");
  $("nextAction").textContent=moves.missing.length?`${LABELS[moves.missing[0]]}을(를) 한 문장으로 보완하세요.`:"각 근거가 질문에 직접 연결되는지 검토하세요.";
  const strengths=[],weaknesses=[]; if(result.words >= (type==="email"?80:100)) strengths.push("아이디어 전개를 위한 권장 연습 분량을 확보했습니다."); else weaknesses.push("단어 수를 채우기보다 핵심 주장에 관련 이유나 세부 정보를 보태세요."); if(result.evidence>=2) strengths.push("이유·예시·결과를 통한 지원이 보입니다."); else weaknesses.push("가장 중요한 주장에 이유·사례·결과 중 필요한 내용을 구체화하세요."); if(result.errors===0) strengths.push("내장 규칙에서 명백한 문법 오류가 감지되지 않았습니다."); else weaknesses.push(`검출 가능한 언어 오류가 ${result.errors}건 있습니다. 원문 문맥을 확인하세요.`); if(prompt.value.trim()&&topicFit(prompt.value,text)<.25) weaknesses.push("표면 키워드 일치도가 낮습니다. 실제 주제 이탈인지 바꿔쓰기인지 직접 확인하세요(점수 미반영).");
  list("strengths",strengths,"감지된 강점보다 보완 항목이 먼저 보입니다."); list("weaknesses",weaknesses,"큰 구조 누락이 감지되지 않았습니다.");
  const starters=type==="email"?["I am writing regarding...","Could you please...?","I would also appreciate it if...","Thank you for your assistance."]:["I believe this matters because...","I agree with [Name]'s point that...","One practical example is...","As a result, this would..."];
  $("starters").innerHTML=starters.map(x=>`<div class="starter">${escapeHtml(x)}</div>`).join(""); $("results").classList.remove("hidden"); $("status").textContent="브라우저 안에서 분석을 완료했습니다."; $("results").scrollIntoView({behavior:"smooth",block:"start"});
}

function update() { const text=essay.value, wc=words(text).length; $("wordCount").textContent=`단어 ${wc}`; const type=text.trim()?detectType(text):null; $("typeBadge").textContent=type?(type==="email"?"Write an Email":"Academic Discussion"):"유형 감지 대기"; localStorage.setItem(storageKey,JSON.stringify({essay:text,prompt:prompt.value})); }
try { const saved=JSON.parse(localStorage.getItem(storageKey)||"{}"); essay.value=saved.essay||""; prompt.value=saved.prompt||""; } catch (_) {}
essay.addEventListener("input",update); prompt.addEventListener("input",update); $("scoreBtn").addEventListener("click",render); $("clearBtn").addEventListener("click",()=>{if(confirm("작성 중인 내용을 비울까요?")){essay.value="";prompt.value="";localStorage.removeItem(storageKey);$("results").classList.add("hidden");update();}}); document.addEventListener("keydown",e=>{if((e.metaKey||e.ctrlKey)&&e.key==="Enter")render();}); update();
if ("serviceWorker" in navigator) window.addEventListener("load",()=>navigator.serviceWorker.register("service-worker.js"));
