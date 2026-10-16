# 대화 결과 문서

`handlers.py`가 기존 단일 `/api`의 `ai_agent/Hermes/artifact`에 문서 미리보기를 등록합니다. 선택 작업 폴더 또는 Hermes artifacts 폴더 안의 텍스트 문서만 읽습니다. 경로 경계·심볼릭 링크·확장자·설정/인증 파일 제외를 확인하며 HTML·스크립트를 실행하지 않습니다. 최대 1 MiB를 표시하고 잘림 여부를 반환합니다.

프론트 `chat/MessageBody.tsx`의 문서 링크와 `GeneratedFiles.tsx`가 공통 `ui/DocumentPreview.tsx`를 사용합니다. 문서를 읽기 위해 모델을 호출하거나 작업을 중지하지 않습니다. 기존 세션·MCP·모델 경로는 바꾸지 않습니다.
