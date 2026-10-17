"""pytest 없이도 테스트 실행: python tests/run.py"""
import inspect, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

class MonkeyPatch:
    def __init__(self): self._undo = []
    def setattr(self, obj, name, value):
        self._undo.append((obj, name, getattr(obj, name))); setattr(obj, name, value)
    def undo(self):
        for obj, name, value in reversed(self._undo): setattr(obj, name, value)

failed = 0
for mod_name in ["test_cgv", "test_megabox"]:
    mod = __import__(mod_name)
    for name, fn in inspect.getmembers(mod, inspect.isfunction):
        if not name.startswith("test_"): continue
        mp = MonkeyPatch()
        try:
            fn(mp) if "monkeypatch" in inspect.signature(fn).parameters else fn()
            print(f"PASS {mod_name}.{name}")
        except Exception as e:
            failed += 1; print(f"FAIL {mod_name}.{name}: {e!r}")
        finally:
            mp.undo()
sys.exit(1 if failed else 0)
