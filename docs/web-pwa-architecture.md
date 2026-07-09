# Web / PWA Architecture

## 현재 구현

- FastAPI가 `/`와 `/static/*`에서 정적 UI를 제공한다.
- `/api/capabilities`가 desktop/web feature flag를 제공한다.
- UI는 360px 이상 모바일 폭을 고려한 CSS 보강을 포함한다.
- 기본 채점은 API 키 없이 Offline Core로 작동한다.

## `/api/capabilities`

예상 필드:

```json
{
  "mode": "desktop_or_web",
  "offline_core": true,
  "api_key_required": false,
  "local_ai": true,
  "cloud_ai": false,
  "backup_restore": true,
  "pdf": true,
  "build_a_sentence": true,
  "draft_autosave": true,
  "history": true,
  "pwa": false,
  "admin_api": false,
  "hosted_ai": false,
  "score_policy": "heuristic_score_only"
}
```

## PWA 미완료 조건

아직 PWA 완료가 아니다. 필요한 작업:

- web app manifest
- service worker
- offline cache policy
- installability test
- iOS Safari/Android Chrome viewport 검증
- hosted data policy

## Desktop과 Hosted Web 분리

- Desktop: local storage, backup/restore, optional local AI 가능.
- Hosted Web: 서버 계정/게스트 데이터 정책, rate limit, hosted AI cost control 필요.
