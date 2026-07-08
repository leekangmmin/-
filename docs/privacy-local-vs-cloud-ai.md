# Privacy: Local vs Cloud AI (Phase 7)

**Date**: 2026-07-08

---

## 데이터 흐름

### 기본 분석 (Offline Core)

```
에세이 입력 → Python 프로세스 내 분석 → 결과 표시
                                          ↓
                                     SQLite DB 저장 (로컬)
```

- **네트워크 호출**: 없음
- **데이터 이탈**: 없음
- **의존성**: Python 실행 환경만 필요

### 로컬 AI 분석 (Rule + Optional LLM)

```
에세이 입력 → LocalAIManager → RuleLocalAIProvider (기본)
                           ↘ OllamaLocalProvider (localhost:11434)
                           ↘ LlamaCppLocalProvider (localhost:8080)
                                            ↓
                                       결과 표시 (별도 레이블)
```

- **네트워크 호출**: localhost/127.0.0.1 외 없음 (비loopback 거부)
- **데이터 이탈**: 없음 (loopback 전용)
- **의존성**: Ollama/llama.cpp 선택적 설치

### 클라우드 AI 분석 (사용자 활성 필요)

```
에세이 입력 → HTTPS → OpenAI API
                    → Anthropic API
                    → Google API
                         ↓
                    결과 표시
```

- **네트워크 호출**: 외부 API (HTTPS)
- **데이터 이탈**: API 제공자 서버로 전송됨
- **의존성**: API 키 + 인터넷 연결

---

## API 키 저장 방식

- SQLite DB (`app_settings` 테이블)에 평문 저장
- `.env` 파일에서도 읽을 수 있음 (개발용)
- 백업 시 API 키는 자동 제거 (VACUUM)
- 클라이언트 번들에 포함되지 않음

**주의사항**: 로컬 데스크톱 앱이므로 키체인/암호화는 미적용. 파일 접근 권한이 있는 사용자는 키를 읽을 수 있음.

---

## 보안 경계

### Loopback 전용 규칙 (Local AI)

```python
if not url.startswith("http://127.0.0.1") and not url.startswith("http://localhost"):
    return error("보안상 로컬호스트 주소만 허용됩니다")
```

- Ollama/LlamaCpp 연결은 127.0.0.1 또는 localhost만 허용
- 고급 설정에서 비loopback 허용 가능하나 기본 비활성화
- 경고 표시 후에만 활성화

### 프롬프트 인젝션 방어

- RuleLocalAIProvider: 정규식 기반으로만 동작 (LLM 없음 → 인젝션 불가)
- Ollama/LlamaCpp: 시스템 프롬프트와 사용자 입력 분리, JSON 형식 강제

---

## 로그 정책

- 기본: 에세이 텍스트를 로그에 기록하지 않음
- 디버그 모드: 길이 + 해시만 기록 (원문 제외)
- `_content_fingerprint()` 사용: `len=XXX sha256=XXX`

---

## 사용자에게 보여주는 개인정보 고지

### 기본 분석 시
"기기 안에서 바로 분석해요. 인터넷이나 API 키가 필요하지 않아요."

### 로컬 AI 활성 시
"설치된 로컬 AI 모델을 사용해 더 자세한 표현 개선을 제안해요. 답안은 기기 밖으로 나가지 않아요."

### Ollama 사용 시
"로컬 Ollama 서버로 전송됩니다. 일반적으로 기기 안에서 처리되지만, 사용자의 Ollama 설정은 앱이 통제하지 않습니다."

### Cloud AI 활성 시 (사용자가 직접 켠 경우만)
"선택한 외부 AI 서비스로 답안이 전송될 수 있어요. 비용이 발생할 수 있습니다."

---

## 네트워크 접근 요약

| 모드 | 외부 네트워크 | Loopback 네트워크 | 비고 |
|------|--------------|-------------------|------|
| 기본 분석 | 없음 | 없음 | 완전 오프라인 |
| 로컬 AI (Rule) | 없음 | 없음 | 완전 오프라인 |
| 로컬 AI (Ollama) | 없음 | localhost:11434 | Ollama 자체 네트워크는 통제 불가 |
| 로컬 AI (llama.cpp) | 없음 | localhost:8080 | llama.cpp 서버 통제는 사용자 책임 |
| 클라우드 AI | api.openai.com 등 | 없음 | API 키 필요, 유료 |
