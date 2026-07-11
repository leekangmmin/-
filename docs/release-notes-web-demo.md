# 웹 데모 릴리스 노트 (초안 — 실제 공개 URL 배포 전)

이 문서는 **아직 실제로 배포되지 않은** 공개 웹 데모를 위한 릴리스 노트
템플릿이다. `docs/hosted-web-deployment.md`의 절차로 실제 배포를 완료하면
이 문서를 실제 URL과 함께 갱신한다. 현재는 초안이며, 존재하지 않는 URL을
지어내지 않는다.

## 상태

**Hosted demo: pending**(공개 URL 없음). 이번 단계에서 완료한 것은 "누구나
`docker run` 한 줄로 브라우저 접속 가능한 이미지"까지다. 실제 공개
URL로 상시 서비스하는 것은 별도 결정(비용·운영 주체·rate limit 인프라)이
필요해 이번 단계에서 수행하지 않았다.

## 브라우저에서 되는 것

- Offline Core 채점 (문법·어휘·구조·주제 적합성)
- 결과 화면 (영역별 점수, 문장별 첨삭, 리라이팅 예시)
- Build a Sentence (15문항)
- PDF 리포트 다운로드 (한글 포함, Docker 이미지에 Noto Sans CJK 폰트 내장)
- 작성 중 답안 자동 저장(draft)
- 기록 조회

API 키 없이, 인터넷의 외부 AI 호출 없이 전부 작동한다.

## 브라우저에서 안 되는 것 (hosted 모드, `TOEFL_WEB_MODE=1`)

- 로컬 AI(Ollama/llama.cpp) 패널 — 데스크톱 전용, hosted에서는 숨김
- 로컬 파일 백업/복원 UI — 공유 서버에서 노출하면 다른 사용자 데이터에
  접근할 위험이 있어 숨김(운영자가 컨테이너/볼륨 레벨에서 직접 백업해야 함)
- PWA 설치(홈 화면에 추가) — 아직 구현되지 않음. web app manifest와
  service worker가 없다(`docs/web-pwa-architecture.md` 참고)
- 계정/로그인 — 없음. 세션 간 데이터 격리가 보장되지 않는다

## Windows 데스크톱 앱

**제공되지 않는다.** 이 웹 데모/Docker 이미지가 Windows 사용자가 설치 없이
쓸 수 있는 현재 경로다. Windows용 `.exe` 데스크톱 패키징은 `windows/` 아래
빌드 스크립트가 준비되어 있으나 실제 Windows 머신에서의 최종 smoke test는
아직 완료되지 않았다(`docs/windows-release-report.md` 참고) — 이번 웹 데모
작업으로 그 상태가 바뀌지는 않았다.

## 전문가 정확도 보증

없음. 밴드 점수는 공개 기준을 참고한 연습용 추정치이며, 전문가 채점
데이터 기반 정확도 캘리브레이션은 완료되지 않았다(`docs/expert-validation-plan.md`).

## 개인정보

`docs/web-privacy.md` 참고 — 데스크톱과 달리 답안이 채점을 위해 서버로
전송된다. 클라우드 AI는 기본 비활성이며 켜기 전까지 외부로 전송되지 않는다.

## 검증 방법

```bash
docker build -t toefl-writing-scorer .
./scripts/docker_sanity_test.sh
```

## 다음 단계 (실제 배포 시 이 문서에 채워야 할 것)

- [ ] 실제 hosted URL
- [ ] 실제 배포 플랫폼과 리전
- [ ] rate limit 실측 설정값
- [ ] HTTPS 인증서 발급 방식
- [ ] 모니터링/알림 여부
- [ ] 실제 배포일
