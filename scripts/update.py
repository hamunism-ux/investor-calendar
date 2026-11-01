#!/usr/bin/env python3
"""
自動抓取事件 → data/events_auto.json
每個來源各自獨立：任一來源失敗時，沿用上一次該來源的資料，網站不會變空。

來源：
  twse-hol    證交所開休市日程        https://openapi.twse.com.tw/v1/holidaySchedule/holidaySchedule
  twse-agm    上市公司股東會公告      https://openapi.twse.com.tw/v1/opendata/t187ap38_L
  mops        上市公司每日重大訊息    https://openapi.twse.com.tw/v1/opendata/t187ap04_L（只給前一日，本程式會累積）
  twse-punish 處置股                  https://openapi.twse.com.tw/v1/announcement/punish
  nasdaq-earn 美股下次財報日          https://api.nasdaq.com/api/analyst/{SYM}/earnings-date
  nasdaq-div  美股除息日              https://api.nasdaq.com/api/quote/{SYM}/dividends?assetclass=stocks
"""
import json, re, sys, datetime, hashlib, pathlib, time
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HOLD = json.loads((DATA / "holdings.json").read_text(encoding="utf-8"))
TW = {h["sym"]: h["name"] for h in HOLD if h["market"] == "tw"}
US = {h["sym"]: h["name"] for h in HOLD if h["market"] == "us"}
TODAY = datetime.date.today()
TODAY_S = TODAY.isoformat()
KEEP_FROM = (TODAY - datetime.timedelta(days=45)).isoformat()   # 太舊的自動事件會清掉

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*", "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8"}

def get_json(url, **kw):
    r = requests.get(url, headers=UA, timeout=40, **kw)
    r.raise_for_status()
    return r.json()

def roc(s):
    """民國 YYYMMDD / YYY/MM/DD → ISO"""
    if not s: return None
    s = str(s).strip().replace("/", "").replace("-", "")
    m = re.match(r"^(\d{2,3})(\d{2})(\d{2})$", s)
    if not m: return None
    y, mo, d = int(m.group(1)) + 1911, int(m.group(2)), int(m.group(3))
    try: return datetime.date(y, mo, d).isoformat()
    except ValueError: return None

def us_date(s):
    """'Nov 19, 2026' / '11/19/2026' / '2026-11-19' → ISO"""
    if not s: return None
    s = str(s).strip()
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
        try: return datetime.datetime.strptime(s, fmt).date().isoformat()
        except ValueError: pass
    return None

def hid(*parts):
    return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()[:10]

def ev(id_, d, c, sym, t, k, u=None, tm=None, n=None, e=None, st="o"):
    return {"id": id_, "d": d, "e": e, "c": c, "sym": sym, "t": t, "k": k, "tm": tm, "st": st, "u": u, "n": n}

# ---------- 來源 ----------
def src_twse_holiday():
    out = []
    for r in get_json("https://openapi.twse.com.tw/v1/holidaySchedule/holidaySchedule"):
        d = roc(r.get("Date")); name = r.get("Name", "").strip(); desc = r.get("Description", "").replace("<br>", "")
        if not d or d < KEEP_FROM: continue
        if "交易" in name and "休" not in desc and "放假" not in desc:
            t = f"台股：{name}"
        else:
            t = f"台股休市：{name}"
        out.append(ev("twse-hol:" + d + ":" + hid(name), d, "holiday", None, t, "holiday",
                      u="https://www.twse.com.tw/zh/trading/holiday.html", n=desc or None))
    return out

def src_twse_agm():
    out = []
    for r in get_json("https://openapi.twse.com.tw/v1/opendata/t187ap38_L"):
        code = str(r.get("公司代號", "")).strip()
        if code not in TW: continue
        typ = r.get("股東常(臨時)會日期-常或臨時", "").strip() or "常會"
        d = roc(r.get("股東常(臨時)會日期-日期"))
        if not d or d < KEEP_FROM: continue
        n = []
        s, e2 = roc(r.get("停止過戶起訖日期-起")), roc(r.get("停止過戶起訖日期-訖"))
        if s and e2: n.append(f"停止過戶 {s[5:]}～{e2[5:]}")
        cash = r.get("預擬配發現金(股利)(元/股)-盈餘")
        if cash not in (None, "", "0", "0.0"): n.append(f"擬配現金股利 {cash} 元")
        pub = roc(r.get("公告日期"))
        if pub: n.append(f"{pub} 公告")
        out.append(ev(f"twse-agm:{code}:{typ}:{d}", d, "tw", code, f"{TW[code]} 股東{typ}", "agm",
                      u=f"https://mops.twse.com.tw/mops/web/t108sb27_q1", n="；".join(n) or None))
    return out

KW_MOPS = re.compile(r"法人說明會|法說|除息|除權|股利|股息|股東會|股東常會|股東臨時會|現金增資|分割|買回|董事會決議|營收|財務報告|財務報表")
def src_mops():
    out = []
    for r in get_json("https://openapi.twse.com.tw/v1/opendata/t187ap04_L"):
        code = str(r.get("公司代號", "")).strip()
        if code not in TW: continue
        subj = (r.get("主旨") or "").strip()
        if not KW_MOPS.search(subj): continue
        spoke = roc(r.get("發言日期")); fact = roc(r.get("事實發生日")) or spoke
        if not fact: continue
        desc = (r.get("說明") or "").replace("\r", " ").replace("\n", " ").strip()
        # 法說會公告：事實發生日通常就是法說會日期；其他公告用事實發生日
        k = "earnings" if re.search(r"法人說明會|法說", subj) else "dividend" if re.search(r"除息|除權|股利|股息", subj) else "agm" if "股東" in subj else "news"
        # 試著從說明裡抓更精確的日期（例如「除息交易日：115/12/10」「法人說明會日期：115/01/15」）
        m = re.search(r"(?:除息交易日|除權交易日|法人說明會日期|召開日期|日期)[：:]\s*(\d{2,3})[/年](\d{1,2})[/月](\d{1,2})", desc)
        d = fact
        if m:
            d2 = roc(f"{int(m.group(1)):03d}{int(m.group(2)):02d}{int(m.group(3)):02d}")
            if d2 and d2 >= spoke: d = d2
        out.append(ev(f"mops:{code}:{spoke}:{hid(subj)}", d, "tw", code, f"{TW[code]} {subj}", k,
                      u="https://mops.twse.com.tw/mops/web/t05sr01_1", n=(desc[:160] + ("…" if len(desc) > 160 else "")) or None,
                      tm=f"{spoke} 公告" if spoke else None))
    return out

def src_twse_punish():
    out = []
    data = get_json("https://openapi.twse.com.tw/v1/announcement/punish")
    for r in data:
        vals = {k: str(v) for k, v in r.items()}
        code = next((v.strip() for k, v in vals.items() if "代號" in k), None)
        if code not in TW: continue
        dates = [roc(v) for k, v in vals.items() if "日期" in k or "期間" in k]
        dates = [x for x in dates if x]
        d = min(dates) if dates else TODAY_S
        e = max(dates) if len(dates) > 1 else None
        out.append(ev(f"twse-punish:{code}:{d}", d, "tw", code, f"{TW[code]} 列為處置股票", "news", e=e,
                      u="https://www.twse.com.tw/zh/announcement/punish.html", n="證交所處置股公告"))
    return out

MONTH_DATE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? (\d{1,2}), (\d{4})")
def src_nasdaq_earn():
    out, errs = [], []
    for sym, name in US.items():
        s = sym.replace(".", "-")
        try:
            data = get_json(f"https://api.nasdaq.com/api/analyst/{s}/earnings-date")
            txt = json.dumps(data, ensure_ascii=False)
            d = None
            dd = (data.get("data") or {})
            for key in ("dateReportEarnings", "earningsDate", "date"):
                if dd.get(key): d = us_date(dd[key]); break
            if not d:
                m = MONTH_DATE.search(txt)
                if m: d = us_date(f"{m.group(1)[:3]} {m.group(2)}, {m.group(3)}")
            if not d:
                errs.append(f"{sym}: 找不到日期 {txt[:120]}"); continue
            if d < KEEP_FROM: continue
            tm = dd.get("timeReportEarnings") or None
            out.append(ev(f"nasdaq-earn:{sym}", d, "us", sym, f"{name}（{sym}）財報日", "earnings",
                          u=f"https://www.nasdaq.com/market-activity/stocks/{s.lower()}/earnings",
                          tm=tm, n="Nasdaq 公布；若為預估值，Nasdaq 會在公司正式公告後更新"))
        except Exception as ex:
            errs.append(f"{sym}: {ex}")
        time.sleep(1)
    if not out and errs: raise RuntimeError("; ".join(errs))
    if errs: print("  nasdaq-earn 部分失敗:", "; ".join(errs))
    return out

def src_nasdaq_div():
    out, errs = [], []
    for sym, name in US.items():
        s = sym.replace(".", "-")
        try:
            data = get_json(f"https://api.nasdaq.com/api/quote/{s}/dividends", params={"assetclass": "stocks"})
            rows = ((data.get("data") or {}).get("dividends") or {}).get("rows") or []
            for r in rows:
                d = us_date(r.get("exOrEffDate"))
                if not d or d < KEEP_FROM: continue
                pay = us_date(r.get("paymentDate")); amt = r.get("amount")
                n = []
                if amt and amt != "N/A": n.append(f"每股 {amt}")
                if pay: n.append(f"發放 {pay}")
                out.append(ev(f"nasdaq-div:{sym}:{d}", d, "us", sym, f"{name}（{sym}）除息日", "dividend",
                              u=f"https://www.nasdaq.com/market-activity/stocks/{s.lower()}/dividend-history", n="；".join(n) or None))
        except Exception as ex:
            errs.append(f"{sym}: {ex}")
        time.sleep(1)
    if not out and errs: raise RuntimeError("; ".join(errs))
    if errs: print("  nasdaq-div 部分失敗:", "; ".join(errs))
    return out

SOURCES = [
    ("twse-hol", src_twse_holiday),
    ("twse-agm", src_twse_agm),
    ("mops", src_mops),
    ("twse-punish", src_twse_punish),
    ("nasdaq-earn", src_nasdaq_earn),
    ("nasdaq-div", src_nasdaq_div),
]
ACCUMULATE = {"mops", "twse-punish"}   # 來源只給當日資料，要和舊資料累積

def main():
    out_path = DATA / "events_auto.json"
    prev = {"events": [], "sources": {}}
    if out_path.exists():
        try: prev = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception: pass
    prev_by_id = {e["id"]: e for e in prev.get("events", []) if e.get("id")}
    prev_src = prev.get("sources", {})

    new_events, sources = [], {}
    for name, fn in SOURCES:
        try:
            got = fn()
            if name in ACCUMULATE:
                old = [e for e in prev_by_id.values() if e["id"].startswith(name + ":") and e["d"] >= KEEP_FROM]
                ids = {e["id"] for e in got}
                got = got + [e for e in old if e["id"] not in ids]
            sources[name] = {"ok": True, "n": len(got), "at": TODAY_S}
            print(f"✓ {name}: {len(got)} 筆")
        except Exception as ex:
            got = [e for e in prev_by_id.values() if e["id"].startswith(name + ":") and e["d"] >= KEEP_FROM]
            sources[name] = {"ok": False, "n": len(got), "at": prev_src.get(name, {}).get("at"), "error": str(ex)[:200]}
            print(f"✗ {name}: {ex} → 沿用上次 {len(got)} 筆")
        new_events.extend(got)

    # 新／改 標記
    for e in new_events:
        old = prev_by_id.get(e["id"])
        if not old:
            e["added"] = TODAY_S
        else:
            e["added"] = old.get("added")
            e["changed"] = TODAY_S if (old.get("d") != e["d"] or old.get("e") != e.get("e")) else old.get("changed")
    new_events.sort(key=lambda x: (x["d"], x["sym"] or "~", x["t"]))
    out_path.write_text(json.dumps({"updated": TODAY_S, "sources": sources, "events": new_events}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"寫入 {len(new_events)} 筆 → {out_path}")
    failed = [k for k, v in sources.items() if not v["ok"]]
    if failed: print("::warning::來源失敗：" + ", ".join(failed))

if __name__ == "__main__":
    main()
