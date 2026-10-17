"""메가박스 굿즈 소진현황 어댑터.

흐름
  1) 이벤트 목록   POST /on/oh/ohe/Event/eventMngDiv.do  (탭별 eventDivCd, HTML 응답)
  2) 이벤트 상세   GET /event/detail?eventNo=…  → '굿즈 소진현황 보기' 버튼의 data-pn(굿즈번호)
                   (버튼이 없으면 소진현황을 제공하지 않는 이벤트로 보고 건너뜀)
  3) 극장별 재고   POST /on/oh/ohe/Event/selectGoodsStockPrco.do  (eventNo, goodsNo / HTML 응답)
"""
from __future__ import annotations

import html
import re
import time

from .common import make_item, session

NAME = "메가박스"
SITE = "https://www.megabox.co.kr"
DETAIL_URL = SITE + "/event/detail?eventNo={}"
DELAY = 1.0

# 이벤트 창의 탭 → eventDivCd
TABS = {
    "메가Pick": "CED03",
    "영화": "CED01",
}

# 이름에 이 단어가 하나라도 있으면 굿즈 이벤트 후보
KEYWORDS = ["증정", "포스터", "프리미어", "오리지널 티켓", "아트그라피"]

_EVENT = re.compile(
    r'<a[^>]*data-no="(?P<no>\d+)"[^>]*>.*?<p class="tit">\s*(?P<title>.*?)\s*</p>'
    r'\s*<p class="date">\s*(?P<date>.*?)\s*</p>', re.S)
_MOVIE = re.compile(r"<([^<>]+)>")


def _session():
    s = session()
    s.headers.update({
        "Accept": "text/html, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": SITE,
        "Referer": SITE + "/event/megabox",
    })
    return s


def parse_event_list(page: str) -> list[dict]:
    events = []
    for m in _EVENT.finditer(page):
        title = html.unescape(m["title"]).strip()
        events.append({"no": m["no"], "title": title, "date": m["date"].strip()})
    return events


def is_goods_event(title: str) -> bool:
    return any(k in title for k in KEYWORDS)


def split_title(title: str) -> tuple[str, str]:
    """'<룩백> 돌비 포스터 증정 이벤트' → ('룩백', '돌비 포스터')
       '메가박스 오리지널 티켓 No.189 <룩백>' → ('룩백', '오리지널 티켓 No.189')"""
    m = _MOVIE.search(title)
    if not m:
        return title, "굿즈"
    movie = m[1].strip()
    goods = (title[:m.start()] + " " + title[m.end():])
    goods = re.sub(r"메가박스|증정|이벤트|\s+", " ", goods)
    goods = re.sub(r"\s+", " ", goods).strip(" |-")
    return movie, goods or "굿즈"


def list_events(s) -> list[dict]:
    found: dict[str, dict] = {}
    for tab, div_cd in TABS.items():
        body = {"currentPage": "1", "recordCountPerPage": "1000", "eventStatCd": "ONG",
                "eventTitle": "", "eventDivCd": div_cd, "eventTyCd": "", "orderReqCd": "ONGlist"}
        r = s.post(SITE + "/on/oh/ohe/Event/eventMngDiv.do", json=body, timeout=20)
        r.raise_for_status()
        for ev in parse_event_list(r.text):
            if is_goods_event(ev["title"]):
                found[ev["no"]] = ev
        time.sleep(DELAY)
    return list(found.values())


# 상세 페이지의 소진현황 버튼:
# <button id="btnSelectGoodsStock" data-pn="FG001138" data-nm="&amp;amp;lt;호프&amp;amp;gt;돌비포스터...">
_STOCK_BTN = re.compile(r'<button[^>]*btnSelectGoodsStock[^>]*>', re.S)
_ATTR = re.compile(r'data-(pn|nm)="([^"]*)"')


def _unescape_all(text: str) -> str:
    """여러 번 이스케이프된 문자열('&amp;amp;lt;')을 끝까지 풀기"""
    for _ in range(5):
        new = html.unescape(text)
        if new == text:
            break
        text = new
    return text


def parse_goods_buttons(page: str) -> list[dict]:
    """상세 페이지 → [{"no": "FG001138", "name": "<호프>돌비포스터(재)"}]
    버튼이 없으면 빈 리스트 = 소진현황을 제공하지 않는 이벤트."""
    goods: dict[str, str] = {}
    for tag in _STOCK_BTN.findall(page):
        attrs = dict(_ATTR.findall(tag))
        if attrs.get("pn"):
            goods.setdefault(attrs["pn"], _unescape_all(attrs.get("nm", "")).strip())
    return [{"no": no, "name": name} for no, name in goods.items()]


def find_goods(s, event_no: str) -> list[dict]:
    r = s.get(DETAIL_URL.format(event_no), timeout=20)
    r.raise_for_status()
    return parse_goods_buttons(r.text)


_AREA = re.compile(r'<li class="area-cont[^"]*"[^>]*>.*?<button[^>]*>\s*(?P<region>.*?)\s*</button>'
                   r'(?P<body>.*?)</ul>\s*</div>', re.S)
_BRCH = re.compile(r'<li[^>]*class="brch"[^>]*>\s*<a>(?P<name>.*?)</a>(?P<rest>.*?)</li>', re.S)
_SPAN = re.compile(r"<span[^>]*>\s*(.*?)\s*</span>", re.S)
_POPUP_TITLE = re.compile(r'<div class="tit">\s*(.*?)\s*</div>', re.S)


def parse_stock(page: str, *, event: str, goods: str, link: str) -> list[dict]:
    items = []
    for area in _AREA.finditer(page):
        region = re.sub(r"\s*\(\d+\)\s*$", "", html.unescape(area["region"])).strip()
        for b in _BRCH.finditer(area["body"]):
            span = _SPAN.search(b["rest"])
            status = html.unescape(span[1]) if span else None
            items.append(make_item(chain=NAME, event=event, goods=goods,
                                   theater=html.unescape(b["name"]), region=region,
                                   status=status, link=link))
    return items


def popup_title(page: str) -> str:
    m = _POPUP_TITLE.search(page)
    return html.unescape(m[1]).strip() if m else ""


def fetch_stock(s, event: dict) -> list[dict]:
    movie, goods = split_title(event["title"])
    link = DETAIL_URL.format(event["no"])
    goods_list = find_goods(s, event["no"])
    items: list[dict] = []
    for g in goods_list:
        goods_no = g["no"]
        time.sleep(DELAY)
        r = s.post(SITE + "/on/oh/ohe/Event/selectGoodsStockPrco.do",
                   data={"eventNo": event["no"], "goodsNo": goods_no},
                   headers={"Referer": link}, timeout=20)
        r.raise_for_status()
        name = goods
        if len(goods_list) > 1:  # 한 이벤트에 굿즈가 여러 개면 버튼의 굿즈 이름으로 구분
            name = (_MOVIE.sub("", g["name"]).strip()
                    or _MOVIE.sub("", popup_title(r.text)).strip() or f"{goods} ({goods_no})")
        items.extend(parse_stock(r.text, event=movie, goods=name, link=link))
    return items


def fetch() -> list[dict]:
    s = _session()
    items: list[dict] = []
    for ev in list_events(s):
        time.sleep(DELAY)
        items.extend(fetch_stock(s, ev))
    return items
