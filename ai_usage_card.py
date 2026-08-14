"""Claude Code 로컬 트랜스크립트를 파싱해 GitHub용 AI Usage 카드(SVG)를 만든다.

사용법:  python ai_usage_card.py [출력경로.svg]
"""
import glob
import json
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

HANDLE = "@PHONE-BOOT-H"
WEEKS = 26
PROJECTS = os.path.expanduser("~/.claude/projects/*/*.jsonl")

# $/1M tokens (input, output). 접두사 매칭, 긴 것부터.
PRICES = [
    ("claude-fable-5", 10.0, 50.0),
    ("claude-mythos-5", 10.0, 50.0),
    ("claude-opus", 5.0, 25.0),
    ("claude-sonnet", 3.0, 15.0),
    ("claude-haiku", 1.0, 5.0),
]
DEFAULT_PRICE = (5.0, 25.0)

# ponytail: FX 하드코딩. 매일 갱신 필요하면 API 붙이면 됨.
FX = {"USD": 1.0, "KRW": 1418.4, "EUR": 0.8672, "CNY": 6.757}
SYMBOL = {"USD": "$", "KRW": "₩", "EUR": "€", "CNY": "¥"}


def price_for(model):
    for prefix, pin, pout in PRICES:
        if model.startswith(prefix):
            return pin, pout
    return DEFAULT_PRICE


def collect():
    """(총계 dict, {날짜: 토큰수}) 반환."""
    total = defaultdict(float)
    daily = defaultdict(int)
    seen = set()

    for path in glob.glob(PROJECTS):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = rec.get("message") or {}
                usage = msg.get("usage")
                if not usage:
                    continue
                # 같은 응답이 스트리밍 중 여러 줄로 기록됨 → message.id로 1회만
                key = msg.get("id") or rec.get("uuid")
                if key in seen:
                    continue
                seen.add(key)

                model = msg.get("model") or ""
                if model in ("<synthetic>", ""):
                    continue
                pin, pout = price_for(model)

                inp = usage.get("input_tokens", 0)
                out = usage.get("output_tokens", 0)
                read = usage.get("cache_read_input_tokens", 0)
                creation = usage.get("cache_creation") or {}
                w5 = creation.get("ephemeral_5m_input_tokens", 0)
                w1h = creation.get("ephemeral_1h_input_tokens", 0)
                if not (w5 or w1h):
                    w5 = usage.get("cache_creation_input_tokens", 0)

                total["input"] += inp
                total["output"] += out
                total["read"] += read
                total["write"] += w5 + w1h
                total["cost"] += (
                    inp * pin + read * pin * 0.1 + w5 * pin * 1.25 + w1h * pin * 2.0
                    + out * pout
                ) / 1_000_000

                ts = rec.get("timestamp")
                if ts:
                    day = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
                    daily[day.date()] += inp + out + read + w5 + w1h

    return total, daily


def human(n):
    for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if n >= div:
            return f"{n / div:.1f}{unit}"
    return str(int(n))


def grass_cells(daily, today):
    """마지막 칸이 오늘인 7xWEEKS 격자. (x, y, level) 목록."""
    end = today + timedelta(days=6 - today.weekday())  # 그 주 일요일까지 채움
    start = end - timedelta(days=WEEKS * 7 - 1)
    window = [daily.get(start + timedelta(days=i), 0) for i in range(WEEKS * 7)]

    active = sorted(v for v in window if v > 0)
    if active:
        cuts = [active[int(len(active) * q)] for q in (0.25, 0.5, 0.75)]
    else:
        cuts = [1, 1, 1]

    cells = []
    for i, v in enumerate(window):
        day = start + timedelta(days=i)
        if day > today:
            continue
        level = 0 if v == 0 else 1 + sum(v > c for c in cuts)
        cells.append((i // 7, i % 7, level))
    return cells


LEVEL_FILL = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]


def render(total, daily, today):
    tokens = total["input"] + total["output"] + total["read"] + total["write"]
    hit = total["read"] / tokens * 100 if tokens else 0.0
    usd = total["cost"]

    rows = []
    for i, cur in enumerate(("USD", "KRW", "EUR", "CNY")):
        amount = usd * FX[cur]
        text = f"{amount:,.0f}" if cur in ("KRW", "CNY") else f"{amount:,.0f}"
        y = 118 + i * 30
        rows.append(
            f'<text x="196" y="{y}" class="lbl">{cur}</text>'
            f'<text x="330" y="{y}" class="val" text-anchor="end">'
            f"{SYMBOL[cur]} {text}</text>"
        )

    squares = []
    for wx, wy, level in grass_cells(daily, today):
        x = 366 + wx * 13
        y = 96 + wy * 13
        squares.append(
            f'<rect x="{x}" y="{y}" width="10" height="10" rx="2" '
            f'fill="{LEVEL_FILL[level]}"/>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="720" height="230" \
viewBox="0 0 720 230" font-family="ui-monospace,SFMono-Regular,Menlo,monospace">
<style>
  .ttl {{ fill:#f0883e; font-size:15px; font-weight:700; letter-spacing:.5px }}
  .head {{ fill:#7d8590; font-size:10px; letter-spacing:2px }}
  .lbl {{ fill:#7d8590; font-size:12px }}
  .val {{ fill:#39d353; font-size:13px }}
  .big {{ fill:#39d353; font-size:44px; font-weight:700 }}
  .sub {{ fill:#7d8590; font-size:11px }}
  .meta {{ fill:#7d8590; font-size:10px }}
</style>
<rect width="720" height="230" rx="10" fill="#010409"/>
<rect x="4" y="4" width="712" height="222" rx="8" fill="#0d1117"
      stroke="#f0883e" stroke-width="1.5"/>
<text x="26" y="42" class="ttl">⚡ AI Usage</text>
<text x="694" y="38" class="meta" text-anchor="end">{HANDLE}</text>
<text x="694" y="54" class="meta" text-anchor="end">\
API-equivalent · {today.isoformat()}</text>
<line x1="26" y1="62" x2="694" y2="62" stroke="#21262d"/>

<text x="26" y="86" class="head">ALL-TIME</text>
<text x="26" y="142" class="big">{human(tokens)}</text>
<text x="26" y="166" class="sub">tokens · {hit:.1f}% cache-hit</text>

<text x="196" y="86" class="head">COST</text>
{chr(10).join(rows)}

<text x="366" y="86" class="head">GRASS - LAST {WEEKS} WEEKS</text>
{chr(10).join(squares)}
</svg>
"""


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "ai-usage.svg"
    total, daily = collect()
    today = datetime.now(timezone.utc).astimezone().date()
    svg = render(total, daily, today)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"{out} 생성 | ${total['cost']:,.0f} | "
          f"{human(total['input'] + total['output'] + total['read'] + total['write'])} tokens")


def demo():
    """가장 작은 검증: 가격/격자 로직이 깨지면 실패."""
    assert price_for("claude-opus-5") == (5.0, 25.0)
    assert price_for("claude-fable-5") == (10.0, 50.0)
    assert price_for("claude-haiku-4-5") == (1.0, 5.0)
    assert price_for("unknown-model") == DEFAULT_PRICE
    assert human(65_600_000_000) == "65.6B"

    t = date(2026, 8, 14)
    cells = grass_cells({t: 100, t - timedelta(days=1): 5}, t)
    assert len(cells) == WEEKS * 7 - (6 - t.weekday()), len(cells)
    assert cells[-1][2] > 0 and cells[0][2] == 0
    print("demo ok")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        main()
