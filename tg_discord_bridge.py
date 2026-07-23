#!/usr/bin/env python3
"""
S21 텔레그램-디스코드 브릿지 봇
- 텔레그램 메시지를 디스코드 채널로 전달
- 디스코드 메시지를 텔레그램으로 전달

사용법:
  export DISCORD_BOT_TOKEN="여기에_봇토큰"
  export TG_TOKEN="여기에_텔레그램_토큰"
  export TG_CHAT="여기에_텔레그램_챗ID"
  python3 tg_discord_bridge.py

필요 권한 (Discord Developer Portal → Bot):
  - Message Content Intent ✅
  - Send Messages
  - Read Messages / View Channels
"""

import os
import sys
import asyncio
import discord

DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT = os.environ.get("TG_CHAT", "")
DISCORD_CHANNEL_ID = os.environ.get("DISCORD_CHANNEL_ID", "")

if not DISCORD_TOKEN:
    print("❌ DISCORD_BOT_TOKEN 환경변수가 설정되지 않았습니다.")
    print("   Discord Developer Portal → Bot → Token 복사 후 export")
    sys.exit(1)

class S21Bridge(discord.Client):
    async def on_ready(self):
        print(f"✅ 디스코드 봇 연결됨: {self.user} (ID: {self.user.id})")
        channel = self.get_channel(int(DISCORD_CHANNEL_ID)) if DISCORD_CHANNEL_ID else None
        if channel:
            await channel.send("🟢 **S21 브릿지 봇 온라인**")
            print(f"   채널 #{channel.name} 에 온라인 메시지 전송")
        else:
            print("   ⚠️ DISCORD_CHANNEL_ID 미설정 또는 채널을 찾을 수 없음")

    async def on_message(self, message):
        if message.author == self.user:
            return
        if TG_TOKEN and TG_CHAT:
            import urllib.request
            text = f"[디스코드] {message.author.name}: {message.content}"
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            data = f"chat_id={TG_CHAT}&text={text}&parse_mode=HTML".encode()
            try:
                urllib.request.urlopen(url, data=data, timeout=5)
            except Exception as e:
                print(f"⚠️ TG 전송 실패: {e}")

if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True
    client = S21Bridge(intents=intents)
    asyncio.run(client.start(DISCORD_TOKEN))
