"""실제 사이트 대신 쓰는 가짜 데이터 (USE_SAMPLE=1). 페이지·이력 동작 확인용."""
from __future__ import annotations

import random

from .common import make_item

NAME = "샘플"

THEATERS = {
    "메가박스": [("코엑스", "서울"), ("홍대", "서울"), ("성수", "서울"), ("목동", "서울"),
              ("하남스타필드", "경기"), ("고양스타필드", "경기"), ("분당", "경기"),
              ("송도", "인천"), ("대전신세계", "대전"), ("대구신세계", "대구")],
    "CGV": [("용산아이파크몰", "서울"), ("왕십리", "서울"), ("영등포", "서울"),
            ("강남", "서울"), ("압구정", "서울"), ("판교", "경기"),
            ("광교", "경기"), ("인천", "인천"), ("센텀시티", "부산"), ("대구", "대구")],
}
EVENTS = {
    "메가박스": [("가을의 끝에서", ["오리지널 티켓", "A3 포스터"]),
              ("우주 탐사선 7호", ["돌비 포스터", "드로잉 카드"])],
    "CGV": [("가을의 끝에서", ["TTT", "필름마크"]),
            ("우주 탐사선 7호", ["IMAX 포스터"])],
}


def fetch() -> list[dict]:
    rnd = random.Random()
    items = []
    for chain, theaters in THEATERS.items():
        for event, goods_list in EVENTS[chain]:
            for goods in goods_list:
                for name, region in theaters:
                    status = rnd.choices(["보유", "소량보유", "소진", "준비중"], weights=[5, 2, 3, 1])[0]
                    items.append(make_item(chain=chain, event=event, goods=goods,
                                           theater=name, region=region, status=status))
    return items
