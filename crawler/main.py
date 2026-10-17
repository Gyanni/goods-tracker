"""굿즈 소진현황 수집기.

실행: python crawler/main.py          (실제 사이트)
      USE_SAMPLE=1 python crawler/main.py  (샘플 데이터)

결과:
  docs/data/current.json  지금 상태 전체
  docs/data/history.json  상태가 바뀐 기록 (보유→소량→소진 등)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
from adapters import cgv, megabox, sample  # noqa: E402
from adapters.common import item_key  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
CURRENT = DATA / "current.json"
HISTORY = DATA / "history.json"
MAX_HISTORY = 5000  # 이력 최대 보관 건수 (오래된 것부터 삭제)
KST = ZoneInfo("Asia/Seoul")


def load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> int:
    now = datetime.now(KST).isoformat(timespec="seconds")
    mode = "sample" if os.getenv("USE_SAMPLE") == "1" else "live"
    sources = [sample] if mode == "sample" else [megabox, cgv]

    prev = load(CURRENT, {"items": [], "sources": {}})
    history = load(HISTORY, [])
    if prev.get("mode") != mode:
        # 샘플 ↔ 실제 전환 시 섞이지 않게 처음부터 새로 기록
        prev, history = {"items": []}, []
    prev_items = {item_key(i): i for i in prev.get("items", [])}

    items: list[dict] = []
    source_state: dict[str, dict] = {}
    failed_chains: set[str] = set()

    for src in sources:
        try:
            got = src.fetch()
            items.extend(got)
            source_state[src.NAME] = {"ok": True, "count": len(got), "checked": now}
            print(f"[{src.NAME}] {len(got)}건")
        except NotImplementedError as e:
            failed_chains.add(src.NAME)
            source_state[src.NAME] = {"ok": False, "error": f"설정 전: {e}", "checked": now}
            print(f"[{src.NAME}] 설정 전 - {e}")
        except Exception as e:  # 한 사이트가 실패해도 다른 사이트는 계속
            failed_chains.add(src.NAME)
            source_state[src.NAME] = {"ok": False, "error": f"{type(e).__name__}: {e}", "checked": now}
            print(f"[{src.NAME}] 실패 - {e!r}")

    # 실패한 체인은 직전 데이터를 유지해 페이지가 비지 않게 한다
    for key, old in prev_items.items():
        if old["chain"] in failed_chains:
            items.append(old)

    # 중복 제거 + 상태 변화 기록
    merged: dict[str, dict] = {}
    for it in items:
        key = item_key(it)
        old = prev_items.get(key)
        if it["chain"] not in failed_chains:
            if old is None or old["status"] != it["status"]:
                it["since"] = now
                history.append({
                    "time": now, "chain": it["chain"], "event": it["event"],
                    "goods": it["goods"], "theater": it["theater"], "region": it["region"],
                    "from": old["status"] if old else None, "to": it["status"],
                })
            else:
                it["since"] = old.get("since", now)
        merged[key] = it

    # 이번 수집에서 사라진 항목(이벤트 종료 등)도 이력에 남김
    for key, old in prev_items.items():
        if key not in merged and old["chain"] not in failed_chains:
            history.append({
                "time": now, "chain": old["chain"], "event": old["event"],
                "goods": old["goods"], "theater": old["theater"], "region": old.get("region", ""),
                "from": old["status"], "to": "목록에서 빠짐",
            })

    save(CURRENT, {"updated": now, "mode": mode, "sources": source_state, "items": list(merged.values())})
    save(HISTORY, history[-MAX_HISTORY:])
    print(f"총 {len(merged)}건 저장, 이력 {len(history)}건")
    # 사이트 오류(설정 전 제외)가 있으면 Actions에 빨간불 → GitHub이 메일로 알려줌
    real_errors = [n for n, s in source_state.items()
                   if not s["ok"] and not s["error"].startswith("설정 전")]
    return 1 if real_errors else 0


if __name__ == "__main__":
    sys.exit(main())
