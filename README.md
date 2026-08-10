# Discord 영문 공지 자동 번역 봇

Discord에서 팔로우하여 받은 영문 공지를 GitHub Actions가 약 5분마다 확인하고 DeepL API Free로 한국어 번역해 별도 채널에 게시합니다.

기존 DeepL API Free 키(`:fx`로 끝남)와 신규 DeepL API Developer 키를 자동으로 구분해 알맞은 API 주소를 사용합니다.

## 필요한 GitHub Actions Secrets

- `DISCORD_BOT_TOKEN`: Discord 봇 토큰
- `DEEPL_API_KEY`: DeepL API Free 인증 키
- `SOURCE_CHANNEL_ID`: 영문 공지를 받는 원본 채널 ID
- `TARGET_CHANNEL_ID`: 한국어 번역을 올릴 채널 ID

## Discord 봇 권한

원본 채널: 채널 보기, 메시지 기록 보기

번역 채널: 채널 보기, 메시지 보내기, 링크 첨부, 파일 첨부, 메시지 기록 보기

Discord Developer Portal의 Bot 페이지에서 **Message Content Intent**를 켜야 합니다.

## 첫 실행

Actions 탭에서 `Discord announcement translator`를 선택하고 `Run workflow`를 누릅니다. 첫 실행은 현재 최신 공지를 기준점으로만 저장하며 기존 공지를 번역하지 않습니다. 그 후 원본 채널에 새 영문 공지를 올리고 다시 수동 실행해 시험합니다.
