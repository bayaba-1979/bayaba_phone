#!/usr/bin/env bash
# 라디오 초대권 시스템 설치 — 의존성 + 스케줄링
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "🎙 라디오 초대권 자동화 설치"
echo "============================"
echo ""

# ── Python 의존성 ──────────────────────────────────
echo "📦 Python 패키지 설치..."
pip3 install requests beautifulsoup4 lxml --break-system-packages -q 2>/dev/null || \
pip3 install requests beautifulsoup4 lxml -q

# ── DeepSeek 키 확인 ───────────────────────────────
if [ -z "${DEEPSEEK_API_KEY:-}" ] && [ -z "${ANTHROPIC_AUTH_TOKEN:-}" ]; then
    # .bashrc에서 가져오기 시도
    if [ -f ~/.bashrc ]; then
        source ~/.bashrc 2>/dev/null || true
    fi
    if [ -z "${DEEPSEEK_API_KEY:-}" ] && [ -z "${ANTHROPIC_AUTH_TOKEN:-}" ]; then
        echo "⚠️  DEEPSEEK_API_KEY가 설정되지 않았습니다."
        echo "   generate.py는 API 없이 템플릿 fallback으로 동작합니다."
        echo "   .bashrc에 export DEEPSEEK_API_KEY='sk-...' 추가 후 재시도하세요."
    else
        echo "✅ DeepSeek API 키 확인됨"
    fi
else
    echo "✅ DeepSeek API 키 확인됨"
fi

# ── 테스트 실행 ────────────────────────────────────
echo ""
echo "🧪 사연 생성 테스트 (백건우 리사이틀)..."
python3 generate.py --test --channel classic 2>&1 | head -20
echo ""

# ── 크론 등록 ──────────────────────────────────────
# S21 proot에서는 cron 데몬이 없을 수 있음 → 양쪽 다 시도
CRON_JOB="0 22 * * 0 cd $ROOT && /usr/bin/python3 main.py >> $ROOT/dispatch.log 2>&1"

if command -v crontab &>/dev/null; then
    # 기존 라디오 티켓 크론 제거 후 재등록
    (crontab -l 2>/dev/null | grep -v 'radio_ticket/main.py' || true) > /tmp/cron_tmp
    echo "$CRON_JOB" >> /tmp/cron_tmp
    crontab /tmp/cron_tmp && rm /tmp/cron_tmp
    echo "✅ crontab 등록 완료: 매주 일요일 22:00"
    echo "   확인: crontab -l"
else
    echo "⚠️ crontab 없음 — 수동 실행 가이드:"
    echo ""
    echo "   # 일요일 밤 10시에 직접 실행:"
    echo "   python3 $ROOT/main.py"
    echo ""
    echo "   # 또는 Claude Code에게 일요일 밤 10시에 실행해달라고 부탁:"
    echo "   '매주 일요일 밤 10시에 cd $ROOT && python3 main.py 실행해줘'"
    echo ""
fi

# ── systemd 타이머 시도 ────────────────────────────
if command -v systemctl &>/dev/null && systemctl --version &>/dev/null 2>&1; then
    SERVICE_NAME="radio-ticket"
    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=Radio Ticket Crawler + Generator
After=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 $ROOT/main.py
WorkingDirectory=$ROOT
Environment=DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}
User=root

[Install]
WantedBy=multi-user.target
EOF

    cat > "/etc/systemd/system/${SERVICE_NAME}.timer" << EOF
[Unit]
Description=Weekly Radio Ticket Dispatch (Sun 10pm)
Requires=${SERVICE_NAME}.service

[Timer]
OnCalendar=Sun *-*-* 22:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    systemctl daemon-reload 2>/dev/null || true
    systemctl enable "${SERVICE_NAME}.timer" 2>/dev/null || true
    systemctl start "${SERVICE_NAME}.timer" 2>/dev/null || true
    echo "✅ systemd 타이머 등록 완료 (${SERVICE_NAME}.timer)"
    echo "   확인: systemctl status ${SERVICE_NAME}.timer"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 설치 완료!"
echo ""
echo "  📂 파일: $ROOT/"
echo "  📋 설정: config.json"
echo "  🕷 크롤러: crawl.py"
echo "  ✍️ 생성기: generate.py"
echo "  🚀 메인: main.py"
echo "  📝 로그: dispatch.log"
echo ""
echo "  🧪 테스트 실행:"
echo "     python3 $ROOT/generate.py --test --channel classic"
echo ""
echo "  🚀 수동 실행:"
echo "     python3 $ROOT/main.py"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
