# 의존성

| 파일 | 역할 |
| --- | --- |
| `operations.txt` | 설치 진입점: FinRL-X 운영, SAC, API, APScheduler |
| `moe.txt` | 같은 환경의 CUDA·동결 Expert 라이브러리 |
| `base.txt` | 공통 Python·공개 정책 의존성 |

`설치.cmd`는 `operations.txt`를 설치합니다. FinRL-X·FinRL·키움 공식 SDK는 `scripts/install_windows.py`의 고정 commit으로 설치합니다. Python 환경은 `.venv` 하나입니다. React는 `frontend/package.json`과 `package-lock.json`을 사용합니다.
