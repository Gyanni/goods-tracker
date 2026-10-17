"""저장된 실제 응답으로 메가박스 어댑터 파싱을 확인 (네트워크 없이 실행)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "crawler"))
from adapters import megabox  # noqa: E402

FX = Path(__file__).parent / "fixtures"
LIST = (FX / "megabox_event_list_ced03.html").read_text(encoding="utf-8")
STOCK = (FX / "megabox_stock.html").read_text(encoding="utf-8")
# 상세 페이지의 실제 버튼 (사용자 캡처)
DETAIL = ('<div><button type="button" class="btn" id="btnSelectGoodsStock" data-pn="FG001138" '
          'data-nm="&amp;amp;lt;호프&amp;amp;gt;돌비포스터&amp;amp;&#35;40;재&amp;amp;&#35;41;">'
          '<span>굿즈 소진현황 보기</span><i class="iconset"></i></button></div>')


class FakeResp:
    def __init__(self, text): self.text = text
    def raise_for_status(self): pass


class FakeSession:
    def __init__(self): self.calls = []; self.headers = {}
    def post(self, url, json=None, data=None, headers=None, timeout=None):
        self.calls.append(("POST", url.rsplit("/", 1)[-1], json or data))
        return FakeResp(LIST if url.endswith("eventMngDiv.do") else STOCK)
    def get(self, url, timeout=None):
        self.calls.append(("GET", url, None))
        return FakeResp(DETAIL if "eventNo=21391" in url else "<html>버튼 없음</html>")


def test_event_list():
    evs = megabox.parse_event_list(LIST)
    assert len(evs) == 22
    goods = [e for e in evs if megabox.is_goods_event(e["title"])]
    titles = [e["title"] for e in goods]
    assert "메가박스 오리지널 티켓 No.189 <룩백>" in titles
    assert "<호프> 특별관 재상영 특가 이벤트" not in titles


def test_split_title():
    assert megabox.split_title("<룩백> 돌비 포스터 증정 이벤트") == ("룩백", "돌비 포스터")
    assert megabox.split_title("메가박스 오리지널 티켓 No.189 <룩백>") == ("룩백", "오리지널 티켓 No.189")


def test_parse_stock():
    items = megabox.parse_stock(STOCK, event="호프", goods="돌비 포스터", link="x")
    assert len(items) == 10
    by = {i["theater"]: i for i in items}
    assert by["목동"]["status"] == "보유" and by["목동"]["region"] == "서울"
    assert by["코엑스"]["status"] == "준비중"
    assert by["대구신세계(동대구)"]["region"] == "부산/대구/경상"


def test_goods_button():
    assert megabox.parse_goods_buttons(DETAIL) == [{"no": "FG001138", "name": "<호프>돌비포스터(재)"}]
    assert megabox.parse_goods_buttons("<html>버튼 없음 FG999999</html>") == []


def test_fetch_flow(monkeypatch):
    fake = FakeSession()
    monkeypatch.setattr(megabox, "_session", lambda: fake)
    monkeypatch.setattr(megabox, "DELAY", 0)
    items = megabox.fetch()
    lists = [c for c in fake.calls if c[1] == "eventMngDiv.do"]
    assert {c[2]["eventDivCd"] for c in lists} == {"CED03", "CED01"}
    stock = [c for c in fake.calls if c[1] == "selectGoodsStockPrco.do"]
    assert stock == [("POST", "selectGoodsStockPrco.do", {"eventNo": "21391", "goodsNo": "FG001138"})]
    assert len(items) == 10 and items[0]["event"] == "호프"
