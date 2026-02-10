#!/bin/bash
# Telegram 메시지 전송 래퍼
# 표준 입력에서 TELEGRAM_MESSAGE_START/END 사이의 메시지를 추출하여 Telegram으로 전송

set -e

# 임시 파일
TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

# 표준 입력을 임시 파일에 저장
cat > $TMPFILE

# TELEGRAM_MESSAGE_START와 END 사이의 내용만 추출
awk '/📱 TELEGRAM_MESSAGE_START/,/📱 TELEGRAM_MESSAGE_END/' $TMPFILE | \
  grep -v "📱 TELEGRAM_MESSAGE" | \
  grep -v "^=====" | \
  sed '/^$/d' > ${TMPFILE}.msg

# 메시지가 있으면 전송
if [ -s ${TMPFILE}.msg ]; then
    # 여기에 실제 메시지를 삽입
    # OpenClaw를 통해 현재 세션으로 메시지를 보냄
    MSG=$(cat ${TMPFILE}.msg)
    
    echo "$MSG"
    
    # 실제 전송은 나중에 구현 (일단 echo로 출력)
    # openclaw message send --message "$MSG" 등
fi
