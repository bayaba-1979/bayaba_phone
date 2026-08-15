#!/usr/bin/env python3
"""
history_category_map.py — 업무수첩(history) 110개 원고 → 티스토리 Ch 카테고리 SSOT.

권위 트리: ./tistory-categories.txt (8 PART · 31 Chapter · 125 콘텐츠).
이 파일은 그 트리 안에서 "history 업무수첩 원고 한 편 = Ch 한 칸"을 배정한다.

⚠️ Ch 항목은 에디터 메뉴에서 "- ChN.M 이름" 으로 표시된다(post.py _set_category).
   이름은 tistory-categories.txt 와 **정확히** 일치해야 한다(·×→ 등 특수문자 포함).

⚠️ PART 3/4/6/7/8 은 블로그에 아직 카테고리가 생성 안 됐을 수 있다.
   (설치가이드가 PART 1/2/5 만 만들었기 때문). history 발행 전에
   tistory-categories.txt 로 해당 PART/Ch 를 먼저 생성해야 _set_category 가 성공한다.

소비처: director_gate.py (overrides 의 category 산출)
"""
from __future__ import annotations

from pathlib import Path

# ── 권위 트리 (참조용) — tistory-categories.txt 의 8 Part · 31 Chapter ────────
PART_TREE: dict[str, str] = {
    "Ch1.1": "Ch1.1 워크스테이션 백서",
    "Ch1.2": "Ch1.2 Termux·proot·Ubuntu",
    "Ch1.3": "Ch1.3 Claude Code·DeepSeek 배선",
    "Ch1.4": "Ch1.4 GitHub·Pages·무료전시장",
    "Ch1.5": "Ch1.5 실전 설치 사례",
    "Ch2.1": "Ch2.1 텔레그램·보고회의실",
    "Ch2.2": "Ch2.2 Discord·커뮤니티",
    "Ch2.3": "Ch2.3 Phone MCP·하드웨어 제어",
    "Ch2.4": "Ch2.4 건강체크·돌봄 데몬",
    "Ch3.1": "Ch3.1 파이프라인 개요·백서",
    "Ch3.2": "Ch3.2 P0 URL→콘텐츠 이해",
    "Ch3.3": "Ch3.3 P1·P2 캡처·음성합성",
    "Ch3.4": "Ch3.4 P3·P4 영상·자막",
    "Ch3.5": "Ch3.5 Director·연출 시스템",
    "Ch3.6": "Ch3.6 BGM·브릿지·인코딩",
    "Ch4.1": "Ch4.1 3트랙 목소리 전략",
    "Ch4.2": "Ch4.2 ParksyTTS·온디바이스 추론",
    "Ch4.3": "Ch4.3 Edge TTS·Piper",
    "Ch4.4": "Ch4.4 RVC·학습·녹음",
    "Ch5.1": "Ch5.1 Paste Pipeline",
    "Ch5.2": "Ch5.2 루프백·사이버네틱 검증",
    "Ch5.3": "Ch5.3 YouTube·네이버 연동",
    "Ch5.4": "Ch5.4 WSL 슬롯·확장 로드맵",
    "Ch6.1": "Ch6.1 2계층·5×5×5 생태계",
    "Ch6.2": "Ch6.2 슬롯 아키텍처·환경 독립",
    "Ch6.3": "Ch6.3 ROI·공짜 클라우드 정당화",
    "Ch6.4": "Ch6.4 4로봇·에이전트 방법론",
    "Ch7.1": "Ch7.1 기초생계·치매·장애 솔루션",
    "Ch7.2": "Ch7.2 대화록·방법론·아이덴티티",
    "Ch8.1": "Ch8.1 설치 삽질 포스트모템",
    "Ch8.2": "Ch8.2 케이스스터디·벤치마크",
    "Ch8.3": "Ch8.3 업무일지 하이라이트",
}

# ── history 원고(basename) → Ch ─────────────────────────────────────────────
HISTORY_CATEGORY: dict[str, str] = {
    # PART 1: 온보딩
    "00-INDEX.md":                          "Ch1.1 워크스테이션 백서",
    "01-arch.md":                           "Ch1.1 워크스테이션 백서",
    "39-naver-lecture-s21-voice-intro_Grok.md": "Ch1.1 워크스테이션 백서",
    "15-proot-report.md":                   "Ch1.2 Termux·proot·Ubuntu",
    "29-grok-cli-installed.md":             "Ch1.2 Termux·proot·Ubuntu",
    "07-cli-reference.md":                  "Ch1.3 Claude Code·DeepSeek 배선",
    "04-github-pages.md":                   "Ch1.4 GitHub·Pages·무료전시장",
    "41-beginner-install-manual_Grok.md":   "Ch1.5 실전 설치 사례",
    "46-first-install-case-study-meeting-prep_Boss.md": "Ch1.5 실전 설치 사례",

    # PART 2: 인프라
    "03-telegram.md":                       "Ch2.1 텔레그램·보고회의실",
    "02-discord.md":                        "Ch2.2 Discord·커뮤니티",
    "10-phone-mcp.md":                      "Ch2.3 Phone MCP·하드웨어 제어",
    "11-health.md":                         "Ch2.4 건강체크·돌봄 데몬",

    # PART 3: PD Pipeline
    "78-pd-pipeline-whitepaper_Claude.md":  "Ch3.1 파이프라인 개요·백서",
    "72-pd-pipeline-standard-v2-lock_Grok.md": "Ch3.1 파이프라인 개요·백서",
    "58-video-three-tracks_Grok.md":        "Ch3.1 파이프라인 개요·백서",
    "59-grok-video-process-whitepaper_Grok.md": "Ch3.1 파이프라인 개요·백서",
    "73-pd-grok-notebook-report_Grok.md":   "Ch3.1 파이프라인 개요·백서",
    "86-pd-two-lanes-free-vs-grok_Claude.md": "Ch3.1 파이프라인 개요·백서",
    "33-hybrid-image-video-whitepaper.md":  "Ch3.1 파이프라인 개요·백서",
    "71-pd-intro-v2-slide-black-fix_Grok.md": "Ch3.4 P3·P4 영상·자막",
    "48-director-video-recurrence_Grok.md": "Ch3.5 Director·연출 시스템",
    "49-director-community-research_Grok.md": "Ch3.5 Director·연출 시스템",
    "50-director-pro-v3-visual-proof_Grok.md": "Ch3.5 Director·연출 시스템",
    "51-scout-v2-community-research_Grok.md": "Ch3.5 Director·연출 시스템",
    "52-director-vision-qa-loop_Grok.md":   "Ch3.5 Director·연출 시스템",
    "53-director-plan-settings_Grok.md":    "Ch3.5 Director·연출 시스템",
    "54-director-pro-v5-five-act_Grok.md":  "Ch3.5 Director·연출 시스템",
    "55-director-pro-v6-perfect_Grok.md":   "Ch3.5 Director·연출 시스템",
    "56-director-perfect-ship-process_Grok.md": "Ch3.5 Director·연출 시스템",
    "57-director-community-a-bar_Grok.md":  "Ch3.5 Director·연출 시스템",
    "60-director-pro-v8-wish_Grok.md":      "Ch3.5 Director·연출 시스템",
    "64-process-80-squeeze_Grok.md":        "Ch3.5 Director·연출 시스템",
    "62-grok-plugin-video-pipe_Grok.md":    "Ch3.6 BGM·브릿지·인코딩",
    "63-video-plugin-standard-v1_Grok.md":  "Ch3.6 BGM·브릿지·인코딩",
    "65-video-playable-encode-fix_Grok.md": "Ch3.6 BGM·브릿지·인코딩",
    "66-grok-pd-voice-bridge-not-page-raster_Grok.md": "Ch3.6 BGM·브릿지·인코딩",
    "67-grok-subscribe-voice-bgm-hurdle_Grok.md": "Ch3.6 BGM·브릿지·인코딩",
    "68-imagine-prompt-standard-v1_Grok.md": "Ch3.6 BGM·브릿지·인코딩",
    "70-font-bgm-fix_Grok.md":              "Ch3.6 BGM·브릿지·인코딩",
    "69-session-resume-pd-bridge-v1_Grok.md": "Ch3.6 BGM·브릿지·인코딩",

    # PART 4: AI 목소리
    "80-ai-voice-actor-whitepaper_Boss.md": "Ch4.1 3트랙 목소리 전략",
    "70-ai-voice-core-gift-local-train_Grok.md": "Ch4.1 3트랙 목소리 전략",
    "74-tts-rvc-lightweight-solution_Claude.md": "Ch4.2 ParksyTTS·온디바이스 추론",
    "69-voice-engine-plugin-final_Grok.md": "Ch4.3 Edge TTS·Piper",
    "81-helena-rvc-dubbing-standard_Claude.md": "Ch4.4 RVC·학습·녹음",
    "82-helena-rvc-baseline-lords-prayer_Grok.md": "Ch4.4 RVC·학습·녹음",
    "rvc-environment-gap_Claude.md":        "Ch4.4 RVC·학습·녹음",
    "rvc-failure-analysis_Claude.md":       "Ch4.4 RVC·학습·녹음",

    # PART 5: 출판·배포
    "05-tistory.md":                        "Ch5.1 Paste Pipeline",
    "24-paste-pipeline.md":                 "Ch5.1 Paste Pipeline",
    "26-naver-parsing-solution.md":         "Ch5.1 Paste Pipeline",
    "tistory-master-guide_Claude.md":       "Ch5.1 Paste Pipeline",
    "91-automation-caution_Claude.md":      "Ch5.2 루프백·사이버네틱 검증",
    "92-automation-line-boss-to-publish_Claude.md": "Ch5.2 루프백·사이버네틱 검증",
    "44-naver-admin-automation-review_Grok.md": "Ch5.2 루프백·사이버네틱 검증",
    "45-naver-admin-playwright-feasibility_Grok.md": "Ch5.2 루프백·사이버네틱 검증",
    "75-translation-logic-management_Claude.md": "Ch5.2 루프백·사이버네틱 검증",
    "76-page-writing-standard_Claude.md":   "Ch5.2 루프백·사이버네틱 검증",
    "06-youtube.md":                        "Ch5.3 YouTube·네이버 연동",
    "23-naver-webzine-solution.md":         "Ch5.3 YouTube·네이버 연동",
    "41-naver-blog-intro-final.md":         "Ch5.3 YouTube·네이버 연동",
    "42-marine-quilt-naver-design_Grok.md": "Ch5.3 YouTube·네이버 연동",
    "84-youtube-two-channel-momentum_Boss.md": "Ch5.3 YouTube·네이버 연동",
    "naver-intro-article.md":               "Ch5.3 YouTube·네이버 연동",
    "40-pc-wsl-setup_Boss.md":              "Ch5.4 WSL 슬롯·확장 로드맵",

    # PART 6: 설계·아키텍처
    "12-dtslib-gift.md":                    "Ch6.1 2계층·5×5×5 생태계",
    "32-ecosystem-whitepaper.md":           "Ch6.1 2계층·5×5×5 생태계",
    "35-ecosystem-whitepaper-v1.1.md":      "Ch6.1 2계층·5×5×5 생태계",
    "36-project-planning-vs-helena_Grok.md": "Ch6.1 2계층·5×5×5 생태계",
    "40-definitive-dev-whitepaper.md":      "Ch6.1 2계층·5×5×5 생태계",
    "08-secrets.md":                        "Ch6.2 슬롯 아키텍처·환경 독립",
    "46-fridge-architecture_Claude.md":     "Ch6.2 슬롯 아키텍처·환경 독립",
    "46-node-protocol-architecture.md":     "Ch6.2 슬롯 아키텍처·환경 독립",
    "18-workcenters.md":                    "Ch6.2 슬롯 아키텍처·환경 독립",
    "19-final-strategy.md":                 "Ch6.2 슬롯 아키텍처·환경 독립",
    "20-workcenters-final.md":              "Ch6.2 슬롯 아키텍처·환경 독립",
    "42-hq-affiliate-architecture.md":      "Ch6.2 슬롯 아키텍처·환경 독립",
    "21-integrated-dev-plan.md":            "Ch6.3 ROI·공짜 클라우드 정당화",
    "34-stt-zero-cost-justification.md":    "Ch6.3 ROI·공짜 클라우드 정당화",
    "37-free-runtime-planner-whitepaper_Grok.md": "Ch6.3 ROI·공짜 클라우드 정당화",
    "39-self-platform-justification.md":    "Ch6.3 ROI·공짜 클라우드 정당화",
    "87-ai-core-utilization-map_Boss.md":   "Ch6.3 ROI·공짜 클라우드 정당화",
    "allocation-rate-2026-07-28.md":        "Ch6.3 ROI·공짜 클라우드 정당화",
    "25-multi-ai-strategy.md":              "Ch6.4 4로봇·에이전트 방법론",
    "27-claude-grok-pipeline.md":           "Ch6.4 4로봇·에이전트 방법론",
    "28-grok-github-bridge.md":             "Ch6.4 4로봇·에이전트 방법론",
    "30-agent-file-marks.md":               "Ch6.4 4로봇·에이전트 방법론",
    "31-agent-roles_Grok.md":               "Ch6.4 4로봇·에이전트 방법론",
    "43-ui-less-architect.md":              "Ch6.4 4로봇·에이전트 방법론",
    "83-momentum-2026-08-14_Grok.md":       "Ch6.4 4로봇·에이전트 방법론",
    "85-grok-plugin-where-saved_Grok.md":   "Ch6.4 4로봇·에이전트 방법론",
    "88-coding-agent-options-free-lane_Boss.md": "Ch6.4 4로봇·에이전트 방법론",
    "ai-agents-cc-ds-grok-comparison-2026-07-25.md": "Ch6.4 4로봇·에이전트 방법론",

    # PART 7: 돌봄 트랙 (기술의 목적)
    "14-daemon-design.md":                  "Ch7.1 기초생계·치매·장애 솔루션",
    "38-s21-voice-driven-analysis.md":      "Ch7.1 기초생계·치매·장애 솔루션",
    "47-human-ai-dialogue-crisis.md":       "Ch7.2 대화록·방법론·아이덴티티",
    "16-textbook-methodology.md":           "Ch7.2 대화록·방법론·아이덴티티",

    # PART 8: 실전 — 후기와 교훈
    "42-pc-sapjil-postmortem_Boss.md":      "Ch8.1 설치 삽질 포스트모템",
    "22-s21-benchmark.md":                  "Ch8.2 케이스스터디·벤치마크",
    "13-midterm-eval-v2.md":                "Ch8.3 업무일지 하이라이트",
    "13-midterm-eval.md":                   "Ch8.3 업무일지 하이라이트",
    "89-wrapup-2026-08-14_Boss.md":         "Ch8.3 업무일지 하이라이트",
    "90-midpoint-consolidation-2026-08-14_Boss.md": "Ch8.3 업무일지 하이라이트",
    "17-merged-chronicle.md":               "Ch8.3 업무일지 하이라이트",
    "99-devlog.md":                         "Ch8.3 업무일지 하이라이트",
    "session-2026-07-26_Grok.md":           "Ch8.3 업무일지 하이라이트",
    "61-session-deepseek-cc-2026-08-02_Grok.md": "Ch1.3 Claude Code·DeepSeek 배선",
    "40-lecture-draft-s21-voice-vol0_Grok.md": "Ch8.3 업무일지 하이라이트",
    "supergrok-community-research-2026-07-25.md": "Ch3.5 Director·연출 시스템",
}


def history_category_for(path: str | Path) -> str:
    """history 원고 경로 → Ch 카테고리. 미등록이면 빈 문자열(미분류)."""
    name = Path(path).name
    return HISTORY_CATEGORY.get(name, "")
