"""어댑터 공통 도구: 표준 아이템 형식과 상태 정규화."""
from __future__ import annotations

import requests

# 페이지에서 쓰는 표준 상태값
AVAILABLE = "보유"
LOW = "소량"
SOLD_OUT = "소진"
UNKNOWN = "미확인"
PREPARING = "준비중"  # 아직 증정 시작 전

_STATUS_WORDS = [
    (PREPARING, ("준비중", "준비 중", "예정")),
    (LOW, ("소량", "임박", "적음", "low")),        # '소진임박'은 소량 → 소진보다 먼저 확인
    (SOLD_OUT, ("소진", "품절", "종료", "sold")),
    (AVAILABLE, ("보유", "여유", "충분", "가능", "available")),
]


def normalize_status(raw) -> str:
    """사이트마다 다른 상태 표기('소량보유', '소진임박', 'Y' 등)를 표준값으로 바꾼다.
    사이트가 코드값(예: '01','02')을 쓰면 각 어댑터에서 먼저 글자로 바꿔서 넘길 것."""
    if raw is None:
        return UNKNOWN
    text = str(raw).strip().lower()
    for status, words in _STATUS_WORDS:  # 위에서부터 확인 ('소량보유' → 소량, '소진임박' → 소량)
        if any(w in text for w in words):
            return status
    return UNKNOWN


def make_item(*, chain: str, event: str, goods: str, theater: str,
              status, region: str = "", link: str = "") -> dict:
    """모든 어댑터가 반환해야 하는 표준 아이템."""
    return {
        "chain": chain,          # "CGV" / "메가박스"
        "event": event.strip(),  # 영화·이벤트 이름
        "goods": goods.strip(),  # 굿즈 이름 (예: 오리지널 티켓, A3 포스터)
        "theater": theater.strip(),
        "region": region.strip(),
        "status": normalize_status(status),
        "link": link,
    }


def item_key(item: dict) -> str:
    return "|".join([item["chain"], item["event"], item["goods"], item["theater"]])


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"),
        "Accept-Language": "ko-KR,ko;q=0.9",
    })
    return s
