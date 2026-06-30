#!/usr/bin/env python3
"""Generate BLT (铂力特 688333.SH) stock dashboard HTML from daily JSON data."""

import json
import math
from datetime import datetime

# ── Load and sort data ──────────────────────────────────────────────────
with open('/Users/hejin/Desktop/Hermes agent/AI QUANT/blt_daily.json', 'r') as f:
    raw = json.load(f)

# Sort ascending by trade_date
raw.sort(key=lambda r: r['trade_date'])

n = len(raw)
dates = [r['trade_date'] for r in raw]
opens = [r['open'] for r in raw]
highs = [r['high'] for r in raw]
lows = [r['low'] for r in raw]
closes = [r['close'] for r in raw]
vols = [r['vol'] for r in raw]
pct_chg_list = [r['pct_chg'] for r in raw]
changes = [r['change'] for r in raw]

# ── Helper: EMA ────────────────────────────────────────────────────────
def ema(arr, period):
    if len(arr) < period:
        return [None] * len(arr)
    k = 2.0 / (period + 1)
    result = [None] * len(arr)
    # First EMA is SMA
    sma = sum(arr[:period]) / period
    result[period - 1] = sma
    for i in range(period, len(arr)):
        result[i] = arr[i] * k + result[i - 1] * (1 - k)
    return result

# ── Helper: SMA ────────────────────────────────────────────────────────
def sma(arr, period):
    result = [None] * len(arr)
    for i in range(period - 1, len(arr)):
        result[i] = sum(arr[i - period + 1:i + 1]) / period
    return result

# ── Calculate MAs ──────────────────────────────────────────────────────
ma5 = sma(closes, 5)
ma10 = sma(closes, 10)
ma20 = sma(closes, 20)
ma60 = sma(closes, 60)
vol_ma5 = sma(vols, 5)

# ── Calculate MACD (12, 26, 9) ─────────────────────────────────────────
ema12 = ema(closes, 12)
ema26 = ema(closes, 26)

dif = [None] * n
for i in range(n):
    if ema12[i] is not None and ema26[i] is not None:
        dif[i] = round(ema12[i] - ema26[i], 4)

dea = [None] * n
# DEA = 9-period EMA of DIF
# Find first non-None DIF
first_dif_idx = next((i for i, v in enumerate(dif) if v is not None), -1)
if first_dif_idx >= 0:
    # Wait until we have 9 DIF values
    start = first_dif_idx + 8  # need 9 values
    if start < n:
        dea_raw = dif[first_dif_idx:start + 1]
        sma_val = sum(dea_raw) / 9
        dea[start] = sma_val
        k = 2.0 / 10.0
        for i in range(start + 1, n):
            if dif[i] is not None:
                dea[i] = dif[i] * k + dea[i - 1] * (1 - k)

macd_hist = [None] * n
for i in range(n):
    if dif[i] is not None and dea[i] is not None:
        macd_hist[i] = round((dif[i] - dea[i]) * 2, 4)

# ── Calculate RSI(14) ──────────────────────────────────────────────────
rsi = [None] * n
period = 14
if n > period:
    gains = []
    losses = []
    for i in range(1, period + 1):
        diff = closes[i] - closes[i - 1]
        gains.append(diff if diff > 0 else 0)
        losses.append(abs(diff) if diff < 0 else 0)
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = round(100.0 - (100.0 / (1.0 + rs)), 1)

    for i in range(period + 1, n):
        diff = closes[i] - closes[i - 1]
        gain = diff if diff > 0 else 0
        loss = abs(diff) if diff < 0 else 0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = round(100.0 - (100.0 / (1.0 + rs)), 1)

# ── Bollinger Bands (20, 2) ─────────────────────────────────────────────
bb_period = 20
bb_mult = 2
bb_upper = [None] * n
bb_mid = [None] * n
bb_lower = [None] * n
for i in range(bb_period - 1, n):
    window = closes[i - bb_period + 1:i + 1]
    mean = sum(window) / bb_period
    variance = sum((x - mean) ** 2 for x in window) / bb_period
    std = math.sqrt(variance)
    bb_mid[i] = round(mean, 2)
    bb_upper[i] = round(mean + bb_mult * std, 2)
    bb_lower[i] = round(mean - bb_mult * std, 2)

# ── Metrics ─────────────────────────────────────────────────────────────
total_rows = n
date_start = dates[0]
date_end = dates[-1]
# Format dates for display
date_start_disp = f"{date_start[:4]}-{date_start[4:6]}-{date_start[6:8]}"
date_end_disp = f"{date_end[:4]}-{date_end[4:6]}-{date_end[6:8]}"
latest_close = closes[-1]
latest_pct_chg = pct_chg_list[-1]
range_high = max(highs)
range_low = min(lows)
avg_vol = sum(vols) / n

# Calculate change from first close to latest
first_close = closes[0]
total_change = latest_close - first_close
total_pct = (total_change / first_close) * 100

# Latest RSI
latest_rsi = rsi[-1] if rsi[-1] is not None else None

# ── Format JavaScript arrays ────────────────────────────────────────────
def js_array(arr, fmt='.2f'):
    """Format a list as a JavaScript array string."""
    parts = []
    for v in arr:
        if v is None:
            parts.append('null')
        elif isinstance(v, float):
            parts.append(f'{v:{fmt}}')
        else:
            parts.append(str(v))
    return '[' + ','.join(parts) + ']'

# Format dates as "YYYY-MM-DD"
js_dates = '[' + ','.join(f'"{d[:4]}-{d[4:6]}-{d[6:8]}"' for d in dates) + ']'

js_closes = js_array(closes, '.2f')
js_opens = js_array(opens, '.2f')
js_highs = js_array(highs, '.2f')
js_lows = js_array(lows, '.2f')
js_vols = js_array(vols, '.2f')
js_ma5 = js_array(ma5, '.2f')
js_ma10 = js_array(ma10, '.2f')
js_ma20 = js_array(ma20, '.2f')
js_ma60 = js_array(ma60, '.2f')
js_dif = js_array(dif, '.4f')
js_dea = js_array(dea, '.4f')
js_macd = js_array(macd_hist, '.4f')
js_rsi = js_array(rsi, '.1f')
js_bb_upper = js_array(bb_upper, '.2f')
js_bb_mid = js_array(bb_mid, '.2f')
js_bb_lower = js_array(bb_lower, '.2f')
js_vol_ma5 = js_array(vol_ma5, '.2f')

# ── Determine color classes ─────────────────────────────────────────────
change_class = 'up' if latest_pct_chg >= 0 else 'down'
change_sign = '+' if latest_pct_chg >= 0 else ''
total_change_class = 'up' if total_change >= 0 else 'down'
total_change_sign = '+' if total_change >= 0 else ''
rsi_class = 'warn' if (latest_rsi and latest_rsi > 70) else ('up' if (latest_rsi and latest_rsi < 30) else '')

# ── Generate HTML ───────────────────────────────────────────────────────
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>铂力特 BLT · AI QUANT Dashboard</title>
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
<div><h1>铂力特 BLT · 688333.SH</h1>
<div class="meta">Tushare Pro · {date_start_disp} ~ {date_end_disp} · {total_rows}个交易日</div></div>
<div class="meta" style="text-align:right">
<span style="color:#58a6ff;font-size:18px;">¥{latest_close}</span><br>
<span class="{change_class}">{change_sign}{latest_pct_chg:.2f}%</span>
</div></div>

<div class="metrics">
<div class="metric-card"><div class="label">数据行数</div><div class="value">{total_rows}</div></div>
<div class="metric-card"><div class="label">区间涨跌</div><div class="value {total_change_class}">{total_change_sign}{total_change:.2f} ({total_change_sign}{total_pct:.1f}%)</div></div>
<div class="metric-card"><div class="label">RSI(14)</div><div class="value {rsi_class}">{latest_rsi if latest_rsi else 'N/A'}</div></div>
<div class="metric-card"><div class="label">区间最高/最低</div><div class="value"><span class="up">{range_high}</span>/<span class="down">{range_low}</span></div></div>
<div class="metric-card"><div class="label">日均成交</div><div class="value">{avg_vol/10000:.0f}万手</div></div>
</div>

<div class="chart-box"><div class="title">K线图 + MA均线 + 布林带</div><div id="kline" style="height:420px"></div></div>
<div class="chart-row">
<div class="chart-box"><div class="title">成交量</div><div id="volume" style="height:160px"></div></div>
<div class="chart-box"><div class="title">MACD (12,26,9)</div><div id="macd-chart" style="height:160px"></div></div>
</div>
<div class="chart-box"><div class="title">RSI(14)</div><div id="rsi-chart" style="height:160px"></div></div>

<div class="note">
  daily_basic 接口限频 · PE/PB 暂无数据 · 数据来源 Tushare Pro
</div>

<script>
var dates = {js_dates};
var closes = {js_closes};
var opens = {js_opens};
var highs = {js_highs};
var lows = {js_lows};
var vols = {js_vols};
var ma5 = {js_ma5};
var ma10 = {js_ma10};
var ma20 = {js_ma20};
var ma60 = {js_ma60};
var dif = {js_dif};
var dea = {js_dea};
var macd = {js_macd};
var rsi = {js_rsi};
var bb_upper = {js_bb_upper};
var bb_mid = {js_bb_mid};
var bb_lower = {js_bb_lower};
var vol_ma5 = {js_vol_ma5};

var c = LightweightCharts.createChart(document.getElementById('kline'),{{layout:{{background:{{color:'#161b22'}},textColor:'#8b949e'}},grid:{{vertLines:{{color:'#21262d'}},horzLines:{{color:'#21262d'}}}},crosshair:{{mode:0}},rightPriceScale:{{borderColor:'#30363d'}},timeScale:{{borderColor:'#30363d',timeVisible:false}},width:document.getElementById('kline').clientWidth,height:420}});
c.addCandlestickSeries({{upColor:'#3fb950',downColor:'#f85149',borderUpColor:'#3fb950',borderDownColor:'#f85149',wickUpColor:'#3fb950',wickDownColor:'#f85149'}}).setData(dates.map(function(d,i){{return {{time:d,open:opens[i],high:highs[i],low:lows[i],close:closes[i]}}}}));

[{{c:'#f0e68c',d:ma5}},{{c:'#ffa500',d:ma10}},{{c:'#ff69b4',d:ma20}},{{c:'#00ced1',d:ma60}}].forEach(function(m){{var s=c.addLineSeries({{color:m.c,lineWidth:1,lastValueVisible:false,priceLineVisible:false}});s.setData(dates.map(function(d,i){{return {{time:d,value:m.d[i]}}}}).filter(function(x){{return x.value!=null}}))}});
[{{c:'rgba(139,148,158,0.3)',d:bb_upper}},{{c:'rgba(139,148,158,0.5)',d:bb_mid}},{{c:'rgba(139,148,158,0.3)',d:bb_lower}}].forEach(function(b){{var s=c.addLineSeries({{color:b.c,lineWidth:1,lastValueVisible:false,priceLineVisible:false}});s.setData(dates.map(function(d,i){{return {{time:d,value:b.d[i]}}}}).filter(function(x){{return x.value!=null}}))}});

var vc = LightweightCharts.createChart(document.getElementById('volume'),{{layout:{{background:{{color:'#161b22'}},textColor:'#8b949e'}},grid:{{vertLines:{{color:'#21262d'}},horzLines:{{color:'#21262d'}}}},rightPriceScale:{{borderColor:'#30363d'}},timeScale:{{borderColor:'#30363d',timeVisible:false}},width:document.getElementById('volume').clientWidth,height:160}});
vc.priceScale('left').applyOptions({{visible:false}});
vc.addHistogramSeries({{priceFormat:{{type:'volume'}}}}).setData(dates.map(function(d,i){{return {{time:d,value:vols[i],color:closes[i]>=opens[i]?'rgba(63,185,80,0.5)':'rgba(248,81,73,0.5)'}}}}));
vc.addLineSeries({{color:'#f0e68c',lineWidth:1,priceLineVisible:false,lastValueVisible:false}}).setData(dates.map(function(d,i){{return {{time:d,value:vol_ma5[i]}}}}).filter(function(x){{return x.value!=null}}));

var mc = LightweightCharts.createChart(document.getElementById('macd-chart'),{{layout:{{background:{{color:'#161b22'}},textColor:'#8b949e'}},grid:{{vertLines:{{color:'#21262d'}},horzLines:{{color:'#21262d'}}}},crosshair:{{mode:0}},rightPriceScale:{{borderColor:'#30363d'}},timeScale:{{borderColor:'#30363d',timeVisible:false}},width:document.getElementById('macd-chart').clientWidth,height:160}});
mc.addHistogramSeries({{priceFormat:{{type:'volume'}}}}).setData(dates.map(function(d,i){{return {{time:d,value:macd[i],color:macd[i]!=null?(macd[i]>=0?'rgba(63,185,80,0.6)':'rgba(248,81,73,0.6)'):null}}}}).filter(function(x){{return x.value!=null}}));
mc.addLineSeries({{color:'#f0e68c',lineWidth:1,lastValueVisible:false,priceLineVisible:false}}).setData(dates.map(function(d,i){{return {{time:d,value:dif[i]}}}}).filter(function(x){{return x.value!=null}}));
mc.addLineSeries({{color:'#ff69b4',lineWidth:1,lastValueVisible:false,priceLineVisible:false}}).setData(dates.map(function(d,i){{return {{time:d,value:dea[i]}}}}).filter(function(x){{return x.value!=null}}));

var rc = LightweightCharts.createChart(document.getElementById('rsi-chart'),{{layout:{{background:{{color:'#161b22'}},textColor:'#8b949e'}},grid:{{vertLines:{{color:'#21262d'}},horzLines:{{color:'#21262d'}}}},crosshair:{{mode:0}},rightPriceScale:{{borderColor:'#30363d'}},timeScale:{{borderColor:'#30363d',timeVisible:false}},width:document.getElementById('rsi-chart').clientWidth,height:160}});
rc.addLineSeries({{color:'#d2991d',lineWidth:1.5,lastValueVisible:true}}).setData(dates.map(function(d,i){{return {{time:d,value:rsi[i]}}}}).filter(function(x){{return x.value!=null}}));
rc.addLineSeries({{color:'rgba(248,81,73,0.4)',lineWidth:1,priceLineVisible:false,lastValueVisible:false}}).setData([{{time:dates[0],value:70}},{{time:dates[dates.length-1],value:70}}]);
rc.addLineSeries({{color:'rgba(63,185,80,0.4)',lineWidth:1,priceLineVisible:false,lastValueVisible:false}}).setData([{{time:dates[0],value:30}},{{time:dates[dates.length-1],value:30}}]);

window.addEventListener('resize',function(){{[c,vc,mc,rc].forEach(function(ch){{ch.applyOptions({{width:ch._container.clientWidth}})}})}});
</script>
</body>
</html>'''

# ── Write output ────────────────────────────────────────────────────────
output_path = '/Users/hejin/Desktop/Hermes agent/AI QUANT/blt_dashboard.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

# ── Summary ─────────────────────────────────────────────────────────────
print(f"✅ Dashboard generated: {output_path}")
print(f"   Total rows: {total_rows}")
print(f"   Date range: {date_start_disp} ~ {date_end_disp}")
print(f"   Latest close: ¥{latest_close} ({change_sign}{latest_pct_chg:.2f}%)")
print(f"   Range: {range_low} ~ {range_high}")
print(f"   Avg volume: {avg_vol/10000:.0f}万手")
print(f"   Latest RSI(14): {latest_rsi}")
print(f"   MA5 latest: {ma5[-1]:.2f}" if ma5[-1] else "   MA5 latest: null")
print(f"   MA20 latest: {ma20[-1]:.2f}" if ma20[-1] else "   MA20 latest: null")
print(f"   MA60 latest: {ma60[-1]:.2f}" if ma60[-1] else "   MA60 latest: null")
print(f"   MACD DIF latest: {dif[-1]:.4f}" if dif[-1] else "   MACD DIF latest: null")
print(f"   MACD DEA latest: {dea[-1]:.4f}" if dea[-1] else "   MACD DEA latest: null")
print(f"   MACD Hist latest: {macd_hist[-1]:.4f}" if macd_hist[-1] else "   MACD Hist latest: null")
print(f"   BB Upper latest: {bb_upper[-1]:.2f}" if bb_upper[-1] else "   BB Upper latest: null")
print(f"   BB Mid latest: {bb_mid[-1]:.2f}" if bb_mid[-1] else "   BB Mid latest: null")
print(f"   BB Lower latest: {bb_lower[-1]:.2f}" if bb_lower[-1] else "   BB Lower latest: null")
