#!/usr/bin/env python3
"""Build Montage Tech (688008.SH) dashboard HTML."""
import json, math

# ── Load & sort data ──
with open("montage_daily.json") as f:
    raw = json.load(f)
raw.sort(key=lambda d: d["trade_date"])  # ascending

n = len(raw)
dates = []
opens, highs, lows, closes, vols = [], [], [], [], []
for d in raw:
    dt = d["trade_date"]
    dates.append(f"{dt[:4]}-{dt[4:6]}-{dt[6:8]}")
    opens.append(d["open"])
    highs.append(d["high"])
    lows.append(d["low"])
    closes.append(d["close"])
    vols.append(d["vol"])

# ── Helpers ──
def sma(arr, period):
    """Simple moving average."""
    out = [None] * len(arr)
    for i in range(period - 1, len(arr)):
        out[i] = sum(arr[i - period + 1 : i + 1]) / period
    return out

def ema(arr, period):
    """Exponential moving average with Wilder initialization."""
    out = [None] * len(arr)
    # seed with SMA
    s = sum(arr[:period]) / period
    out[period - 1] = s
    k = 2 / (period + 1)
    for i in range(period, len(arr)):
        out[i] = arr[i] * k + out[i - 1] * (1 - k)
    return out

def std_dev(arr, period, ma):
    """Rolling standard deviation."""
    out = [None] * len(arr)
    for i in range(period - 1, len(arr)):
        m = ma[i]
        var = sum((arr[j] - m) ** 2 for j in range(i - period + 1, i + 1)) / period
        out[i] = math.sqrt(var)
    return out

# ── Indicators ──
ma5 = sma(closes, 5)
ma10 = sma(closes, 10)
ma20 = sma(closes, 20)
ma60 = sma(closes, 60)
vol_ma5 = sma(vols, 5)

# MACD
ema12 = ema(closes, 12)
ema26 = ema(closes, 26)
dif = [None] * n
for i in range(25, n):
    dif[i] = ema12[i] - ema26[i]
dea = [None] * n
# seed DEA with first 9 DIF values
# Find first valid DIF index
first_dif = next(i for i, v in enumerate(dif) if v is not None)  # 25
dea_start = first_dif + 9 - 1  # 33
if dea_start < n:
    s_dif = sum(dif[first_dif : first_dif + 9]) / 9
    dea[dea_start] = s_dif
    k_d = 2 / 10
    for i in range(dea_start + 1, n):
        dea[i] = dif[i] * k_d + dea[i - 1] * (1 - k_d)
macd_hist = [None] * n
# MACD histogram starts when DEA is valid
dea_first = next((i for i, v in enumerate(dea) if v is not None), None)
if dea_first is not None:
    for i in range(dea_first, n):
        macd_hist[i] = 2 * (dif[i] - dea[i])

# RSI(14) – Wilder's smoothing
rsi = [None] * n
period = 14
if n > period:
    # Initial average gains/losses
    avg_gain = 0
    avg_loss = 0
    for i in range(1, period + 1):
        chg = closes[i] - closes[i - 1]
        if chg > 0:
            avg_gain += chg
        else:
            avg_loss -= chg
    avg_gain /= period
    avg_loss /= period
    # Wilder's smoothing
    for i in range(period + 1, n):
        rs = avg_gain / avg_loss if avg_loss > 1e-10 else 100
        rsi[i] = 100 - (100 / (1 + rs))
        chg = closes[i] - closes[i - 1]
        g = chg if chg > 0 else 0
        l = -chg if chg < 0 else 0
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period
    # Compute last RSI
    rs = avg_gain / avg_loss if avg_loss > 1e-10 else 100
    rsi[n - 1] = 100 - (100 / (1 + rs))

# Bollinger Bands (20,2)
bb_mid = ma20
bb_std = std_dev(closes, 20, ma20)
bb_upper = [None] * n
bb_lower = [None] * n
for i in range(19, n):
    bb_upper[i] = bb_mid[i] + 2 * bb_std[i]
    bb_lower[i] = bb_mid[i] - 2 * bb_std[i]

# ── Metrics ──
total_rows = n
date_start = dates[0]
date_end = dates[-1]
latest_close = closes[-1]
pre_close = raw[-1]["pre_close"]
change_pct_val = raw[-1]["pct_chg"]
change_amt = raw[-1]["change"]
range_high = max(highs)
range_low = min(lows)
avg_vol = sum(vols) / n
rsi_latest = rsi[-1] if rsi[-1] is not None else None

# ── Format helpers ──
def fmt(num, dec=2):
    return f"{num:.{dec}f}"

def jarr(arr):
    """JSON-safe array with None→null."""
    return json.dumps(arr)

# ── Generate HTML ──
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>澜起科技 Montage Tech · AI QUANT Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0d1117;color:#c9d1d9;font-family:-apple-system,'Segoe UI',sans-serif;padding:20px}}
.header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid #21262d}}
.header h1{{font-size:20px;color:#58a6ff}}
.header .meta{{font-size:12px;color:#8b949e}}
.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-bottom:12px}}
.metric-card{{background:#161b22;border:1px solid #21262d;border-radius:6px;padding:10px 12px}}
.metric-card .label{{font-size:11px;color:#8b949e;margin-bottom:2px}}
.metric-card .value{{font-size:18px;font-weight:600}}
.metric-card .sub{{font-size:11px;color:#8b949e;margin-top:2px}}
.up{{color:#3fb950}}.down{{color:#f85149}}.warn{{color:#d2991d}}
.chart-box{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:8px;margin-bottom:10px}}
.chart-box .title{{font-size:12px;color:#8b949e;margin-bottom:4px;padding-left:4px}}
.chart-row{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px}}
.note{{text-align:center;color:#8b949e;font-size:11px;margin-top:10px;padding:8px;background:#161b22;border:1px solid #21262d;border-radius:6px}}
</style>
</head>
<body>

<div class="header">
<div><h1>澜起科技 Montage Tech · 688008.SH</h1>
<div class="meta">Tushare Pro · {date_start} ~ {date_end} · {total_rows}个交易日</div></div>
<div class="meta" style="text-align:right">
<span style="color:#58a6ff;font-size:18px;">¥{fmt(latest_close)}</span><br>
<span class="{'up' if change_pct_val >= 0 else 'down'}">{'+' if change_amt >= 0 else ''}{fmt(change_amt)} ({'+' if change_pct_val >= 0 else ''}{fmt(change_pct_val)}%)</span>
</div></div>

<div class="metrics">
<div class="metric-card"><div class="label">数据条数</div><div class="value">{total_rows}</div></div>
<div class="metric-card"><div class="label">区间</div><div class="value">{date_start}</div><div class="sub">至 {date_end}</div></div>
<div class="metric-card"><div class="label">最新收盘</div><div class="value">¥{fmt(latest_close)}</div><div class="sub {'up' if change_pct_val >= 0 else 'down'}">{'+' if change_pct_val >= 0 else ''}{fmt(change_pct_val)}%</div></div>
<div class="metric-card"><div class="label">涨跌额</div><div class="value {'up' if change_amt >= 0 else 'down'}">{'+' if change_amt >= 0 else ''}{fmt(change_amt)}</div></div>
<div class="metric-card"><div class="label">区间最高/最低</div><div class="value"><span class="up">{fmt(range_high)}</span>/<span class="down">{fmt(range_low)}</span></div></div>
<div class="metric-card"><div class="label">日均成交量</div><div class="value">{fmt(avg_vol/10000,1)}万手</div></div>
<div class="metric-card"><div class="label">RSI(14)</div><div class="value {'warn' if rsi_latest and 30 <= rsi_latest <= 70 else ('up' if rsi_latest and rsi_latest > 70 else 'down')}">{fmt(rsi_latest) if rsi_latest else '--'}</div></div>
<div class="metric-card"><div class="label">MACD信号</div><div class="value {'up' if (n>=34 and macd_hist[n-1] and macd_hist[n-1]>0) else 'down'}">{fmt(macd_hist[n-1]) if (n>=34 and macd_hist[n-1] is not None) else '--'}</div></div>
</div>

<div class="chart-box"><div class="title">K线图 + MA均线 + 布林带</div><div id="kline" style="height:420px"></div></div>
<div class="chart-row">
<div class="chart-box"><div class="title">成交量</div><div id="volume" style="height:160px"></div></div>
<div class="chart-box"><div class="title">MACD (12,26,9)</div><div id="macd-chart" style="height:160px"></div></div>
</div>
<div class="chart-row">
<div class="chart-box"><div class="title">RSI(14)</div><div id="rsi-chart" style="height:160px"></div></div>
<div class="chart-box"><div class="title">技术指标总览</div><div id="summary" style="height:160px;display:flex;align-items:center;justify-content:center;color:#8b949e;font-size:13px;padding:20px;line-height:1.8">
MA5: ¥{fmt(ma5[-1])}&emsp;MA10: ¥{fmt(ma10[-1])}&emsp;MA20: ¥{fmt(ma20[-1])}&emsp;MA60: ¥{fmt(ma60[-1])}<br>
布林上轨: ¥{fmt(bb_upper[-1])}&emsp;中轨: ¥{fmt(bb_mid[-1])}&emsp;下轨: ¥{fmt(bb_lower[-1])}<br>
MACD DIF: {fmt(dif[-1])}&emsp;DEA: {fmt(dea[-1])}&emsp;柱: {fmt(macd_hist[-1])}&emsp;RSI(14): {fmt(rsi_latest) if rsi_latest else '--'}
</div></div>
</div>

<div class="note">
  daily_basic 接口限频 · 无 PE/PB 估值数据 · 成交量单位: 手
</div>

<script>
var dates = {jarr(dates)};
var closes = {jarr(closes)};
var opens = {jarr(opens)};
var highs = {jarr(highs)};
var lows = {jarr(lows)};
var vols = {jarr(vols)};
var ma5 = {jarr(ma5)};
var ma10 = {jarr(ma10)};
var ma20 = {jarr(ma20)};
var ma60 = {jarr(ma60)};
var dif = {jarr(dif)};
var dea = {jarr(dea)};
var macd = {jarr(macd_hist)};
var rsi = {jarr(rsi)};
var bb_upper = {jarr(bb_upper)};
var bb_mid = {jarr(bb_mid)};
var bb_lower = {jarr(bb_lower)};
var vol_ma5 = {jarr(vol_ma5)};

// K-line chart
var c = LightweightCharts.createChart(document.getElementById('kline'),{{
    layout:{{background:{{color:'#161b22'}},textColor:'#8b949e'}},
    grid:{{vertLines:{{color:'#21262d'}},horzLines:{{color:'#21262d'}}}},
    crosshair:{{mode:0}},
    rightPriceScale:{{borderColor:'#30363d'}},
    timeScale:{{borderColor:'#30363d',timeVisible:false}},
    width:document.getElementById('kline').clientWidth,
    height:420
}});
c.addCandlestickSeries({{
    upColor:'#3fb950',downColor:'#f85149',
    borderUpColor:'#3fb950',borderDownColor:'#f85149',
    wickUpColor:'#3fb950',wickDownColor:'#f85149'
}}).setData(dates.map(function(d,i){{return {{time:d,open:opens[i],high:highs[i],low:lows[i],close:closes[i]}}}}));

// MA lines
[{{c:'#f0e68c',d:ma5}},{{c:'#ffa500',d:ma10}},{{c:'#ff69b4',d:ma20}},{{c:'#00ced1',d:ma60}}].forEach(function(m){{
    var s = c.addLineSeries({{color:m.c,lineWidth:1,lastValueVisible:false,priceLineVisible:false}});
    s.setData(dates.map(function(d,i){{return {{time:d,value:m.d[i]}}}}).filter(function(x){{return x.value!=null}}));
}});

// Bollinger Bands
[{{c:'rgba(139,148,158,0.3)',d:bb_upper}},{{c:'rgba(139,148,158,0.5)',d:bb_mid}},{{c:'rgba(139,148,158,0.3)',d:bb_lower}}].forEach(function(b){{
    var s = c.addLineSeries({{color:b.c,lineWidth:1,lastValueVisible:false,priceLineVisible:false}});
    s.setData(dates.map(function(d,i){{return {{time:d,value:b.d[i]}}}}).filter(function(x){{return x.value!=null}}));
}});

// Volume chart
var vc = LightweightCharts.createChart(document.getElementById('volume'),{{
    layout:{{background:{{color:'#161b22'}},textColor:'#8b949e'}},
    grid:{{vertLines:{{color:'#21262d'}},horzLines:{{color:'#21262d'}}}},
    rightPriceScale:{{borderColor:'#30363d'}},
    timeScale:{{borderColor:'#30363d',timeVisible:false}},
    width:document.getElementById('volume').clientWidth,
    height:160
}});
vc.priceScale('left').applyOptions({{visible:false}});
vc.addHistogramSeries({{priceFormat:{{type:'volume'}}}}).setData(dates.map(function(d,i){{
    return {{time:d,value:vols[i],color:closes[i]>=opens[i]?'rgba(63,185,80,0.5)':'rgba(248,81,73,0.5)'}}
}}));
vc.addLineSeries({{color:'#f0e68c',lineWidth:1,priceLineVisible:false,lastValueVisible:false}}).setData(
    dates.map(function(d,i){{return {{time:d,value:vol_ma5[i]}}}}).filter(function(x){{return x.value!=null}})
);

// MACD chart
var mc = LightweightCharts.createChart(document.getElementById('macd-chart'),{{
    layout:{{background:{{color:'#161b22'}},textColor:'#8b949e'}},
    grid:{{vertLines:{{color:'#21262d'}},horzLines:{{color:'#21262d'}}}},
    crosshair:{{mode:0}},
    rightPriceScale:{{borderColor:'#30363d'}},
    timeScale:{{borderColor:'#30363d',timeVisible:false}},
    width:document.getElementById('macd-chart').clientWidth,
    height:160
}});
mc.addHistogramSeries({{priceFormat:{{type:'volume'}}}}).setData(
    dates.map(function(d,i){{return {{time:d,value:macd[i],color:macd[i]!=null?(macd[i]>=0?'rgba(63,185,80,0.6)':'rgba(248,81,73,0.6)'):null}}}}).filter(function(x){{return x.value!=null}})
);
mc.addLineSeries({{color:'#f0e68c',lineWidth:1,lastValueVisible:false,priceLineVisible:false}}).setData(
    dates.map(function(d,i){{return {{time:d,value:dif[i]}}}}).filter(function(x){{return x.value!=null}})
);
mc.addLineSeries({{color:'#ff69b4',lineWidth:1,lastValueVisible:false,priceLineVisible:false}}).setData(
    dates.map(function(d,i){{return {{time:d,value:dea[i]}}}}).filter(function(x){{return x.value!=null}})
);

// RSI chart
var rc = LightweightCharts.createChart(document.getElementById('rsi-chart'),{{
    layout:{{background:{{color:'#161b22'}},textColor:'#8b949e'}},
    grid:{{vertLines:{{color:'#21262d'}},horzLines:{{color:'#21262d'}}}},
    crosshair:{{mode:0}},
    rightPriceScale:{{borderColor:'#30363d'}},
    timeScale:{{borderColor:'#30363d',timeVisible:false}},
    width:document.getElementById('rsi-chart').clientWidth,
    height:160
}});
rc.addLineSeries({{color:'#d2991d',lineWidth:1.5,lastValueVisible:true}}).setData(
    dates.map(function(d,i){{return {{time:d,value:rsi[i]}}}}).filter(function(x){{return x.value!=null}})
);
// Overbought/Oversold reference lines
rc.addLineSeries({{color:'rgba(248,81,73,0.4)',lineWidth:1,priceLineVisible:false,lastValueVisible:false}}).setData([{{time:dates[0],value:70}},{{time:dates[dates.length-1],value:70}}]);
rc.addLineSeries({{color:'rgba(63,185,80,0.4)',lineWidth:1,priceLineVisible:false,lastValueVisible:false}}).setData([{{time:dates[0],value:30}},{{time:dates[dates.length-1],value:30}}]);

// Resize handler
window.addEventListener('resize',function(){{[c,vc,mc,rc].forEach(function(ch){{ch.applyOptions({{width:ch._container.clientWidth}})}})}});
</script>
</body>
</html>'''

with open("montage_dashboard.html", "w", encoding="utf-8") as f:
    f.write(html)

# ── Print summary ──
print(f"✅ montage_dashboard.html generated successfully!")
print(f"   Records: {total_rows}")
print(f"   Date range: {date_start} ~ {date_end}")
print(f"   Latest close: ¥{fmt(latest_close)} ({'+' if change_pct_val >= 0 else ''}{fmt(change_pct_val)}%)")
print(f"   Range: ¥{fmt(range_low)} ~ ¥{fmt(range_high)}")
print(f"   Avg volume: {fmt(avg_vol/10000,1)} 万手")
print(f"   RSI(14): {fmt(rsi_latest) if rsi_latest else 'N/A'}")
print(f"   MA5: {fmt(ma5[-1])}, MA10: {fmt(ma10[-1])}, MA20: {fmt(ma20[-1])}, MA60: {fmt(ma60[-1])}")
print(f"   BB Upper: {fmt(bb_upper[-1])}, Mid: {fmt(bb_mid[-1])}, Lower: {fmt(bb_lower[-1])}")
print(f"   MACD DIF: {fmt(dif[-1])}, DEA: {fmt(dea[-1])}, Hist: {fmt(macd_hist[-1])}")
