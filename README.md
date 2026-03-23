# 2026 개정 TOEFL 라이팅 첨삭 프로그램

FastAPI 기반의 토플 라이팅 첨삭 웹앱입니다.

macOS에서는 순수 SwiftUI 네이티브 앱으로 바로 실행할 수 있습니다.

## 포함 기능

- 통합형 / Academic Discussion 답안 평가
- 0-5 점수 + 30점 환산 점수 추정
- 4개 루브릭(Task Fulfillment, Organization, Development, Language Use)
- 프롬프트 적합성 점수 + 매칭/누락 키워드
- 주장-근거-설명 문장 매핑 시각화
- 문법 오류 유형 통계(시제/관사/전치사/Run-on/수일치/문장부호)
- 목표 점수 기반 리라이팅(최소 수정 / 적극 수정)
- 샘플 답안 요소 비교(포함 요소/누락 요소)
- 신뢰도 근거 설명 + 한영 요약 피드백
- 템플릿 코치(오프닝/바디/전환어/클로징)
- 점수 근거 하이라이트(문장별 positive/negative/neutral)
- 약점 사전(오답 패턴 -> 교정 패턴)
- 개인화 코칭(최근 제출 기반 다음 집중 영역)
- 제출 전 위험 경고(precheck)
- PDF 리포트 내보내기
- 성장 대시보드(점수 추이, 상위 오류, 추천 학습 과제)
- 강점/보완점/즉시 실행 액션 플랜 제시
- 문장 단위 첨삭 예시와 고득점 샘플 문단 제공
- 제출 이력 SQLite 저장 및 조회

## 실행 방법

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

브라우저에서 아래 주소를 열면 됩니다.

- http://127.0.0.1:8000

## macOS 앱처럼 실행하기

- 프로젝트 루트에서 [실행.command](실행.command) 더블클릭
- 또는 [토플첨삭기 by이강민.app](토플첨삭기%20by이강민.app) 실행

위 방식은 외부 브라우저를 열지 않고 네이티브 앱 창에서 바로 동작합니다.

## 네이티브 앱 개발 소스

- SwiftUI 클라이언트: [NativeMacApp](NativeMacApp)
- 실행 파일 빌드: `swift build -c release --package-path NativeMacApp`

## Windows 배포

현재 macOS SwiftUI UI는 Windows에서 직접 실행되지 않으므로, Windows에서는 웹 UI를 1클릭 런처(exe)로 배포합니다.

- 런처 소스: [windows/app_launcher.py](windows/app_launcher.py)
- Windows 즉시 실행(소스 기반): [windows/run_windows.bat](windows/run_windows.bat)
- Windows exe 빌드 스크립트: [windows/build_windows.ps1](windows/build_windows.ps1)

### Windows exe 만들기

1. Windows PC에서 PowerShell 실행
2. 프로젝트 루트로 이동
3. 아래 명령 실행

```powershell
powershell -ExecutionPolicy Bypass -File windows/build_windows.ps1
```

빌드가 완료되면 `dist_windows/TOEFLScorer.exe`가 생성됩니다.

### 네이티브 앱 확장 기능

- 현재 결과 탭: 점수/요약/강점/약점/액션/문법 통계
- 성장 대시보드 탭: 평균 지표, 점수 추이, 문법 이슈 바 차트
- 제출 히스토리 탭: 최근 제출 목록, 항목별 PDF 다운로드
- 최신 리포트 PDF 버튼: 가장 최근 제출 결과 바로 다운로드/열기

## API

### POST /api/evaluate

요청 예시:

```json
{
  "prompt_type": "academic_discussion",
  "prompt_text": "Some teachers think students should take more group projects...",
  "essay_text": "I agree with the professor because ..."
}
```

### POST /api/precheck

제출 전 위험 경고(분량/키워드 반영/문단/run-on)를 반환합니다.

### GET /api/history?limit=10

최근 제출 내역을 반환합니다.

### GET /api/dashboard?limit=200

누적 제출 기반 성장 대시보드 데이터를 반환합니다.

### GET /api/report/{submission_id}.pdf

제출별 PDF 리포트를 생성해 다운로드합니다.

## 구조

- app/main.py: FastAPI 엔트리포인트
- app/scorer.py: 루브릭 기반 점수 추정 엔진
- app/feedback.py: 첨삭/개선 피드백 생성
- app/db.py: SQLite 저장
- static/: 프론트엔드 UI

## 주의

- ETS 공식 채점을 대체하는 도구가 아니라, 학습용 추정/피드백 도구입니다.
