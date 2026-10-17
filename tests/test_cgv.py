"""저장된 실제 응답으로 CGV 어댑터 파싱을 확인 (네트워크 없이 실행)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "crawler"))
from adapters import cgv  # noqa: E402

FX = Path(__file__).parent / "fixtures"
EVENTS = json.loads((FX / "cgv_event_list.json").read_text(encoding="utf-8"))
PRODS = json.loads((FX / "cgv_prod_list.json").read_text(encoding="utf-8"))
SITES = json.loads((FX / "cgv_site_list.json").read_text(encoding="utf-8"))


class FakeResp:
    def __init__(self, body): self.body = body
    def raise_for_status(self): pass
    def json(self): return self.body


class FakeSession:
    def __init__(self): self.calls = []; self.headers = {}
    def get(self, url, params=None, timeout=None):
        self.calls.append((url.rsplit("/", 1)[-1], params))
        if url.endswith("searchSaprmEvtListForPage"):
            body = json.loads(json.dumps(EVENTS))
            if params["startRow"] > 0:
                body["data"]["list"] = []
            return FakeResp(body)
        if url.endswith("searchSaprmEvtProdList"):
            return FakeResp(PRODS)
        return FakeResp(SITES)


def test_split_title():
    assert cgv.split_title("[전자오락수호대] A3 런칭 포스터 (feat. 가스파드)") == ("전자오락수호대", "A3 런칭 포스터 (feat. 가스파드)")
    assert cgv.split_title("이름만") == ("이름만", "특전")


def test_parse_sites():
    items = cgv.parse_sites(SITES["data"], event="침묵의 빛", goods="포스터", link="x")
    assert len(items) == 5
    assert items[0]["theater"] == "강변" and items[0]["region"] == "서울"
    assert all(i["status"] == "보유" for i in items)


def test_fetch_flow(monkeypatch):
    fake = FakeSession()
    monkeypatch.setattr(cgv, "_session", lambda: fake)
    monkeypatch.setattr(cgv, "DELAY", 0)
    items = cgv.fetch()
    names = [c[0] for c in fake.calls]
    assert names[0] == "searchSaprmEvtListForPage"
    stock_calls = [p for n, p in fake.calls if n == "searchSaprmEvtTgtsiteList"]
    assert stock_calls and all(p["spmtlNo"] == "2026101255034501" and p["coCd"] == "A420" for p in stock_calls)
    assert items and items[0]["chain"] == "CGV"
