# 굿즈 소진현황

메가박스·CGV의 공식 굿즈 소진현황을 30분마다 수집해서 한 페이지에 모아 보여주고, 상태가 바뀐 기록(보유 → 소량 → 소진)을 남깁니다.

```
GitHub Actions (30분마다)
  └ crawler/main.py ── 메가박스·CGV 어댑터 ──▶ docs/data/current.json  (지금 상태)
                                            └▶ docs/data/history.json  (변화 이력)
GitHub Pages
  └ docs/index.html  ── 위 JSON을 읽어서 표시 (검색 · 체인/지역/상태 필터 · 이력 탭)
```

## 현재 상태

- ✅ 수집 → 저장 → 이력 기록 → 웹페이지
- ✅ `crawler/adapters/cgv.py`: 완성 (CGV 공개 API 3단계: 이벤트 목록 → 특전 목록 → 극장별 재고)
- ✅ `crawler/adapters/megabox.py`: 이벤트 목록(메가Pick·영화 탭) → 상세 페이지의 굿즈번호 → 극장별 재고
  - 굿즈 이벤트 판별 단어: `KEYWORDS` (증정·포스터·프리미어·오리지널 티켓·아트그라피)
  - 상세 페이지의 '굿즈 소진현황 보기' 버튼(`data-pn`)이 있는 이벤트만 수집
- 테스트: `python tests/run.py` (저장된 실제 응답으로 파싱 확인, 네트워크 불필요)

## 처음 설정 (한 번만)

1. GitHub에서 새 저장소를 만들고 이 폴더 내용을 그대로 올립니다.
   (웹에서 하려면: 저장소 생성 → **Add file → Upload files** → 폴더 안 파일을 전부 끌어다 놓기. `.github` 폴더가 숨김 폴더라 빠지기 쉬우니 꼭 확인)
2. **Settings → Pages** → Source: `Deploy from a branch`, Branch: `main` / 폴더 `/docs` → Save
   잠시 후 `https://<아이디>.github.io/<저장소이름>/` 에서 페이지가 열립니다.
3. **Settings → Actions → General** → 맨 아래 *Workflow permissions* 가 `Read and write permissions` 인지 확인 (아니면 바꾸고 Save)
4. **Actions** 탭 → `굿즈 소진현황 수집` → **Run workflow** 로 한 번 실행해서 확인

> 샘플 데이터로 페이지만 보고 싶으면: **Settings → Secrets and variables → Actions → Variables** 에 `USE_SAMPLE` = `1`. 지우면 실제 수집으로 돌아오고 데이터는 자동 초기화됩니다.

## 로컬에서 실행해 보기

```bash
pip install -r requirements.txt
USE_SAMPLE=1 python crawler/main.py       # 샘플 (Windows PowerShell: $env:USE_SAMPLE=1; python crawler/main.py)
python -m http.server -d docs 8000        # http://localhost:8000 에서 확인
```

## 알아둘 점

- **해외 서버 문제**: GitHub Actions는 미국 등 해외 서버에서 돌아갑니다. 국내 사이트가 해외 접속을 막으면 Actions에서는 수집이 실패할 수 있어요. 이 경우 페이지 상단에 오류가 뜨고, 그때는 수집만 내 PC에서 돌리는 방식으로 바꿀 수 있습니다.
- **수집 예절**: CGV는 robots.txt로 자동 접근을 제한하고 있습니다. 개인 용도로만 쓰고, 주기는 30분 이상, 요청 사이엔 1초씩 쉬도록 되어 있습니다.
- **실행 지연**: GitHub의 예약 실행은 서버 상황에 따라 늦어질 수 있습니다. "마지막 확인" 시각을 참고하세요.
- **커밋이 쌓임**: 데이터가 바뀔 때마다 커밋이 하나씩 생깁니다. 정상입니다.
- 이력은 최근 5000건까지만 보관합니다 (`crawler/main.py`의 `MAX_HISTORY`).

## 어댑터 형식

각 어댑터의 `fetch()`는 아래 형태의 리스트를 반환하면 됩니다 (`adapters/common.py`의 `make_item`).

```python
{"chain": "메가박스", "event": "영화 제목", "goods": "오리지널 티켓",
 "theater": "코엑스", "region": "서울", "status": "보유|소량|소진|미확인", "link": "이벤트 URL"}
```

사이트 표기('소량보유', '소진임박' 등)는 `normalize_status()`가 자동으로 표준값으로 바꿉니다.
