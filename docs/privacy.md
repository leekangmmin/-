# 개인정보와 데이터 처리

## 기본값

- Offline Core는 인터넷, API 키, 로컬 LLM 없이 작동한다.
- 답안, 점수, 작성 중 draft, 백업은 로컬 사용자 데이터 폴더에 저장된다.
- 클라우드 AI를 사용자가 직접 켜기 전까지 답안은 외부 서비스로 전송되지 않는다.

## 저장 위치

- macOS: `~/Library/Application Support/TOEFL Writing/`
- Windows: `%LOCALAPPDATA%\TOEFL Writing\` 또는 platformdirs가 반환하는 사용자 데이터 경로.
- `TOEFL_DATA_DIR` 환경변수를 쓰면 테스트/개발용 위치로 바꿀 수 있다.

## 백업

- 백업에는 답안 기록, Build a Sentence 기록, draft, 일반 설정이 포함된다.
- API 키는 백업에서 제외해야 한다.
- 복원은 로컬 파일에서만 수행한다.

## AI 기능

- 로컬 AI: Ollama/llama.cpp 같은 loopback runtime만 허용한다.
- 클라우드 AI: 사용자가 직접 활성화하고 키를 저장한 경우에만 작동한다.
- 클라우드 AI를 활성화하면 답안과 문제 지문이 선택한 공급자에게 전송되며,
  검증을 통과한 2026 루브릭 0–5 과제 점수가 표시 점수가 된다.
- 공급자 오류나 응답 검증 실패 시 내장 점수로 돌아가며, 점수 출처와 대체 사유를 표시한다.

## 삭제와 내보내기

- 앱의 데이터 관리 화면에서 전체 삭제를 수행할 수 있다.
- 전체 삭제 전 safety backup을 만든다.
- public hosted web을 만들 경우 계정별 export/delete 정책을 별도로 구현해야 한다.
