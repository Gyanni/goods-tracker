"""CGV 특전(굿즈) 소진현황 어댑터.

CGV 웹 '특전 소진현황'(https://cgv.co.kr/evt/giveawayState)이 쓰는 공개 API를 사용한다.
로그인 불필요.

흐름
  1) 이벤트 목록   searchSaprmEvtListForPage  → saprmEvntNo 목록
  2) 특전 목록     searchSaprmEvtProdList    → spmtlNo 목록 (이벤트당 1개 이상)
  3) 극장별 재고   searchSaprmEvtTgtsiteList   → 극장 · 지역 · inventStatus

참고: CGV는 robots.txt로 자동 접근을 제한하고 있으니 개인 용도로만,
수집 주기를 넉넉히 두고 요청 사이에 쉬도록 한다.
"""
from __future__ import annotations

import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from .common import AVAILABLE, LOW, SOLD_OUT, UNKNOWN, make_item, session

NAME = "CGV"
BASE = "https://cgv.co.kr/api/v1/content/event/saprm/saprm"
CO_CD = "A420"
DETAIL_URL = "https://cgv.co.kr/evt/giveawayStateDetail?saprmEvntNo={}"
PAGE_SIZE = 50
DELAY = 1.0  # 요청 사이 대기(초)

# inventStatus 색상 → 표준 상태. 'green' 외의 값은 아직 실제로 확인 못 함.
# 실제 데이터에서 다른 값이 보이면 여기 추가 (모르는 값은 '미확인'으로 표시됨)
INVENT_STATUS = {
    "green": AVAILABLE,
    "yellow": LOW, "orange": LOW,
    "red": SOLD_OUT, "gray": SOLD_OUT, "grey": SOLD_OUT, "black": SOLD_OUT,
}

_TITLE = re.compile(r"^\s*\[(?P<event>[^\]]+)\]\s*(?P<goods>.+)$")


def _session():
    s = session()
    s.headers.update({"Accept": "application/json",
                      "Referer": "https://cgv.co.kr/evt/giveawayState"})
    return s


def _get(s, path: str, **params):
    r = s.get(f"{BASE}/{path}", params={"coCd": CO_CD, **params}, timeout=20)
    r.raise_for_status()
    body = r.json()
    if body.get("statusCode") != 0:
        raise RuntimeError(f"{path}: {body.get('statusMessage')}")
    return body["data"]


def split_title(title: str) -> tuple[str, str]:
    """'[전자오락수호대] A3 런칭 포스터' → ('전자오락수호대', 'A3 런칭 포스터')"""
    m = _TITLE.match(title or "")
    if m:
        return m["event"].strip(), m["goods"].strip()
    return (title or "").strip(), "특전"


def list_events(s) -> list[dict]:
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y%m%d")
    events: dict[str, dict] = {}
    start = 0
    for _ in range(20):  # 안전장치: 최대 20페이지
        data = _get(s, "searchSaprmEvtListForPage", startRow=start, listCount=PAGE_SIZE)
        rows = data.get("list") or []
        for row in rows:
            if (row.get("evntEndYmd") or "99999999") < today:
                continue  # 끝난 이벤트 제외
            events[row["saprmEvntNo"]] = row
        start += PAGE_SIZE
        if not rows or start >= (data.get("totalCount") or 0):
            break
        time.sleep(DELAY)
    return list(events.values())


def list_products(s, evt_no: str) -> list[dict]:
    """이벤트 하나에 딸린 특전(굿즈) 목록 → [{"spmtlNo", "name"}]"""
    rows = _get(s, "searchSaprmEvtProdList", saprmEvntNo=evt_no) or []
    return [{"spmtlNo": r["spmtlNo"],
             "name": r.get("onlnExpoNm") or r.get("spmtlProdNm") or ""} for r in rows]


def parse_sites(rows: list[dict], *, event: str, goods: str, link: str) -> list[dict]:
    items = []
    for r in rows:
        raw = (r.get("inventStatus") or "").lower()
        status = INVENT_STATUS.get(raw, UNKNOWN)
        if status == UNKNOWN and raw:
            print(f"[CGV] 처음 보는 inventStatus 값: {raw!r} ({r.get('expoSiteNm')})")
        items.append(make_item(
            chain=NAME, event=event, goods=goods,
            theater=r.get("expoSiteNm") or r.get("siteNm", ""),
            region=r.get("regnGrpNm", ""), status=status, link=link,
        ))
    return items


def fetch() -> list[dict]:
    s = _session()
    items: list[dict] = []
    for ev in list_events(s):
        evt_no = ev["saprmEvntNo"]
        event, goods = split_title(ev.get("evntOnlnExpoNm") or ev.get("saprmEvntNm"))
        link = DETAIL_URL.format(evt_no)
        time.sleep(DELAY)
        products = list_products(s, evt_no)
        for prod in products:
            # 특전이 여러 개면 각 특전 이름을 굿즈 이름으로 사용
            name = goods
            if len(products) > 1 and prod["name"]:
                name = split_title(prod["name"])[1]
            time.sleep(DELAY)
            rows = _get(s, "searchSaprmEvtTgtsiteList", saprmEvntNo=evt_no, spmtlNo=prod["spmtlNo"])
            items.extend(parse_sites(rows or [], event=event, goods=name, link=link))
    return items
