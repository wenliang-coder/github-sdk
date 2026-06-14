#!/usr/bin/env python3
"""Pre-step runner: (1) fetch the 5 e-commerce bestseller pages and (2) source
the top products on Alibaba.com — all via ScraperAPI — and write compact extracts
to disk for the agent to read.

Runs as a normal GitHub Actions step (outside the agent firewall sandbox) with
the API key supplied via the SCRAPER_API_KEY secret — so the key never reaches
the agent/LLM. Gracefully no-ops (writes a skip summary) when the key is absent.

Env:
  SCRAPER_API_KEY            ScraperAPI key (required to actually fetch)
  BESTSELLER_SOURCE_LIST     source_list.json path (default repo Lab-04 path)
  BESTSELLER_OUT_DIR         bestseller extract dir
  SOURCING_OUT_DIR           sourcing extract dir
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from overseas_insight_tools import (
    overseas_fetch_bestsellers_to_disk,
    overseas_fetch_sourcing_to_disk,
)

DEFAULT_SOURCE_LIST = "Lab-04-Overseas-Insights/input/api/source_list.json"
DEFAULT_OUT_DIR = "Lab-04-Overseas-Insights/output/signals/bestsellers"
DEFAULT_SOURCING_DIR = "Lab-04-Overseas-Insights/output/signals/sourcing"


def _top_products_from_amazon(bestseller_dir: str, *, limit: int = 6) -> list[dict]:
    """Read the Amazon bestseller extract and return its top product names — the
    sourcing seed (Amazon is the reliable real-data backbone)."""
    f = Path(bestseller_dir) / "amazon-bestsellers-beauty.txt"
    if not f.is_file():
        return []
    names: list[str] = []
    in_names = False
    for line in f.read_text(encoding="utf-8").splitlines():
        if line.startswith("NAME_CANDIDATES:"):
            in_names = True
            continue
        if in_names:
            m = re.match(r"\s+-\s+(.*)", line)
            if m:
                nm = m.group(1).strip()
                # skip generic Amazon Basics filler so suppliers map to real categories
                if nm and "amazon basics" not in nm.lower():
                    names.append(nm)
            else:
                break
    return [{"rank": i + 1, "name": n} for i, n in enumerate(names[:limit])]


def main() -> int:
    api_key = os.environ.get("SCRAPER_API_KEY", "")
    source_list = os.environ.get("BESTSELLER_SOURCE_LIST", DEFAULT_SOURCE_LIST)
    out_dir = os.environ.get("BESTSELLER_OUT_DIR", DEFAULT_OUT_DIR)
    sourcing_dir = os.environ.get("SOURCING_OUT_DIR", DEFAULT_SOURCING_DIR)

    bs = overseas_fetch_bestsellers_to_disk(
        api_key=api_key,
        source_list_path=source_list,
        out_dir=out_dir,
    )
    print(json.dumps({k: v for k, v in bs.items() if k != "results"}, ensure_ascii=False))

    products = _top_products_from_amazon(out_dir, limit=6)
    src = overseas_fetch_sourcing_to_disk(
        api_key=api_key,
        products=products,
        out_dir=sourcing_dir,
    )
    print(json.dumps({k: v for k, v in src.items() if k != "results"}, ensure_ascii=False))
    # Never fail the build on scrape gaps — research is best-effort.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
