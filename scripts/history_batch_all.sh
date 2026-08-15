#!/bin/bash
# history_batch_all.sh — 남은 히스토리 원고 전부 연속 발행 (배치 단위 루프)
# 사용: bash scripts/history_batch_all.sh
set -u
cd /root/work

PENDING_PY='
import json, re
route = json.load(open("assets/publish-route.json"))["tistory"]
state = json.load(open("assets/history-upload-state.json"))
done = set(state.get("done", []))
ov = json.load(open("assets/director-overrides.json")).get("posts", {})
SKIP = {"99-devlog.md", "17-merged-chronicle.md"}
def sens(f): return f in SKIP or bool(re.search(r"session", f, re.I))
def blocked(f): return ov.get(f, {}).get("verdict") in ("HOLD", "REVISE")
pending = [e for e in route if e["file"] not in done and not sens(e["file"]) and not blocked(e["file"])]
print(len(pending))
'

# 1) 진행 중인 배치가 있으면 끝날 때까지 대기
for pid in $(pgrep -f "history_batch.py --run" 2>/dev/null); do
  while kill -0 "$pid" 2>/dev/null; do sleep 5; done
done

echo "=== 연속 배치 시작 ==="
for i in $(seq 1 20); do
  pending=$(python3 -c "$PENDING_PY" 2>/dev/null)
  if [ -z "$pending" ] || [ "$pending" = "0" ]; then
    echo "=== [${i}] 발행 대상 0개 → 종료 ==="
    break
  fi
  echo "=== [${i}] 남은 ${pending}개 → 배치 발행 ==="
  python3 tistory-naver/history_batch.py --run 2>&1
  echo "=== [${i}] 완료. 누적: $(python3 -c 'import json;print(json.load(open("assets/history-upload-state.json"))["total"])' 2>/dev/null) ==="
done
echo "=== 연속 배치 종료 ==="
cat assets/history-upload-state.json
