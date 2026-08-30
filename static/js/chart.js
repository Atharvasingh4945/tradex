// TradeX — TradingView Chart Engine (timeframe-stable, aggregation-correct)

let tvChart       = null;
let candleSeries  = null;
let volumeSeries  = null;
let ema9Series    = null;
let ema21Series   = null;
let vwapSeries    = null;

let activeSymbol      = 'NVDA';
let chartMarkers      = [];
let barInterval       = 1;        // 1-second real-time continuous candles

let isLoadingCandles  = false;
let lastBarBucketSeen = 0;        // dedup new-bar creation

let indOn = { ema9: true, ema21: true, vwap: true, volume: false };

// ── Chart Init ───────────────────────────────────────────────────────────────
function initTradingViewChart(containerId, symbol = 'NVDA') {
  activeSymbol = symbol;
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = '';

  const dark = window.matchMedia?.('(prefers-color-scheme: dark)').matches;
  const bg   = dark ? '#0d121f' : '#ffffff';
  const grid = dark ? '#151d2d' : '#f1f5f9';
  const text = dark ? '#9ca3af' : '#64748b';

  tvChart = LightweightCharts.createChart(container, {
    width:  container.clientWidth,
    height: container.clientHeight || 460,
    layout:          { background: { color: bg }, textColor: text, fontFamily: "'JetBrains Mono', monospace" },
    grid:            { vertLines: { color: grid }, horzLines: { color: grid } },
    crosshair:       { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor: grid, scaleMargins: { top: 0.08, bottom: 0.15 }, autoScale: true },
    timeScale:       { borderColor: grid, timeVisible: true, secondsVisible: true, rightOffset: 8, barSpacing: 11 },
  });

  candleSeries = tvChart.addCandlestickSeries({
    upColor: '#00e676', downColor: '#ff1744',
    borderVisible: false, wickUpColor: '#00e676', wickDownColor: '#ff1744',
  });

  ema9Series  = tvChart.addLineSeries({ color: '#3b82f6', lineWidth: 2, priceLineVisible: false, title: 'EMA 9',  visible: indOn.ema9  });
  ema21Series = tvChart.addLineSeries({ color: '#f97316', lineWidth: 2, priceLineVisible: false, title: 'EMA 21', visible: indOn.ema21 });
  vwapSeries  = tvChart.addLineSeries({ color: '#eab308', lineWidth: 2, priceLineVisible: false,
                  lineStyle: LightweightCharts.LineStyle.Solid, title: 'VWAP', visible: indOn.vwap });
  volumeSeries = tvChart.addHistogramSeries({
    priceFormat: { type: 'volume' }, priceScaleId: '',
    scaleMargins: { top: 0.88, bottom: 0 }, visible: indOn.volume
  });

  loadCandleData(symbol);

  window.addEventListener('resize', () => {
    if (tvChart && container) tvChart.applyOptions({ width: container.clientWidth });
  });
}

// ── Aggregate 1-second DB candles → chosen barInterval ───────────────────────
function aggregateToBarInterval(rawCandles, intervalSecs) {
  if (!rawCandles || rawCandles.length === 0) return [];

  const buckets = {};
  rawCandles.forEach(c => {
    const bucket = Math.floor(c.time / intervalSecs) * intervalSecs;
    if (!buckets[bucket]) {
      buckets[bucket] = {
        time:   bucket,
        open:   c.open,
        high:   c.high,
        low:    c.low,
        close:  c.close,
        volume: c.volume || 0
      };
    } else {
      const b = buckets[bucket];
      b.high   = Math.max(b.high,  c.high);
      b.low    = Math.min(b.low,   c.low);
      b.close  = c.close;
      b.volume += (c.volume || 0);
    }
  });

  // Sort by time, return array
  return Object.values(buckets).sort((a, b) => a.time - b.time);
}

// ── Load & Aggregate from API ─────────────────────────────────────────────────
function loadCandleData(symbol) {
  isLoadingCandles  = true;
  activeCandle      = null;
  rawCandlesHistory = [];
  lastBarBucketSeen = 0;

  fetch(`/api/candles/${symbol}`)
    .then(r => r.json())
    .then(data => {
      if (!data || data.length === 0) { isLoadingCandles = false; return; }

      // Sort raw 1-second candles then aggregate to current barInterval
      const raw1s    = [...data].sort((a, b) => a.time - b.time);
      const agg      = aggregateToBarInterval(raw1s, barInterval);
      rawCandlesHistory = agg;

      const candleData = agg.map(c => ({ time: c.time, open: c.open, high: c.high, low: c.low, close: c.close }));
      const volData    = agg.map(c => ({
        time: c.time, value: c.volume || 100,
        color: c.close >= c.open ? 'rgba(0,230,118,0.4)' : 'rgba(255,23,68,0.4)'
      }));

      candleSeries.setData(candleData);
      volumeSeries.setData(volData);
      applyAllIndicators();

      if (agg.length > 0) {
        activeCandle      = { ...agg[agg.length - 1] };
        lastBarBucketSeen = activeCandle.time;
      }

      candleSeries.setMarkers(chartMarkers);
      tvChart.timeScale().scrollToRealTime();
    })
    .catch(err => console.error('Candle load error:', err))
    .finally(() => { isLoadingCandles = false; });
}

// ── Live 1-second tick → update or create aggregated bar ─────────────────────
function updateLiveCandle(symbol, price) {
  if (symbol !== activeSymbol || !candleSeries) return;
  if (isLoadingCandles) return;   // blocked while historical data loads

  const nowSec        = Math.floor(Date.now() / 1000);
  const barBucketTime = Math.floor(nowSec / barInterval) * barInterval;

  if (!activeCandle || barBucketTime > activeCandle.time) {
    // Guard: only open a new bar once per bucket boundary
    if (barBucketTime === lastBarBucketSeen && activeCandle) {
      // Same bucket already opened — just update
      activeCandle.high  = Math.max(activeCandle.high,  price);
      activeCandle.low   = Math.min(activeCandle.low,   price);
      activeCandle.close = price;
    } else {
      // Seal the completed bar into history
      if (activeCandle) {
        rawCandlesHistory.push({ ...activeCandle });
        if (rawCandlesHistory.length > 300) rawCandlesHistory.shift();
      }
      lastBarBucketSeen = barBucketTime;
      const open = activeCandle?.close ?? price;
      activeCandle = {
        time:   barBucketTime,
        open,
        high:   Math.max(open, price),
        low:    Math.min(open, price),
        close:  price,
        volume: Math.floor(Math.random() * 80) + 40
      };
    }
  } else {
    // Normal in-progress update
    activeCandle.high  = Math.max(activeCandle.high,  price);
    activeCandle.low   = Math.min(activeCandle.low,   price);
    activeCandle.close = price;
  }

  candleSeries.update(activeCandle);

  if (volumeSeries && indOn.volume) {
    volumeSeries.update({
      time:  activeCandle.time,
      value: activeCandle.volume || 100,
      color: activeCandle.close >= activeCandle.open ? 'rgba(0,230,118,0.45)' : 'rgba(255,23,68,0.45)'
    });
  }

  // Incremental indicator push (no full recalc needed every tick)
  pushLiveIndicators(price);
}

// ── Indicators ────────────────────────────────────────────────────────────────
function applyAllIndicators() {
  if (!rawCandlesHistory.length) return;
  if (ema9Series)  ema9Series.setData(calcEMA(rawCandlesHistory, 9));
  if (ema21Series) ema21Series.setData(calcEMA(rawCandlesHistory, 21));
  if (vwapSeries)  vwapSeries.setData(calcVWAP(rawCandlesHistory));
}

function pushLiveIndicators(price) {
  if (!activeCandle) return;
  const t = activeCandle.time;
  const prev = rawCandlesHistory.length > 0 ? rawCandlesHistory[rawCandlesHistory.length - 1].close : price;

  if (ema9Series && indOn.ema9) {
    const k = 2 / 10;
    ema9Series.update({ time: t, value: +(((price - prev) * k + prev).toFixed(2)) });
  }
  if (ema21Series && indOn.ema21) {
    const k = 2 / 22;
    ema21Series.update({ time: t, value: +(((price - prev) * k + prev).toFixed(2)) });
  }
  if (vwapSeries && indOn.vwap) {
    const all = [...rawCandlesHistory, activeCandle];
    const v   = calcVWAP(all);
    if (v.length) vwapSeries.update(v[v.length - 1]);
  }
}

function calcEMA(data, period) {
  const k = 2 / (period + 1);
  let ema = data[0].close;
  return data.map((c, i) => {
    if (i > 0) ema = (c.close - ema) * k + ema;
    return { time: c.time, value: +ema.toFixed(2) };
  });
}

function calcVWAP(data) {
  let cumVol = 0, cumTpv = 0;
  return data.map(c => {
    const vol = c.volume || 100;
    cumVol  += vol;
    cumTpv  += ((c.high + c.low + c.close) / 3) * vol;
    return { time: c.time, value: +(cumTpv / cumVol).toFixed(2) };
  });
}

// ── Indicator Toggle ──────────────────────────────────────────────────────────
function toggleIndicator(type) {
  indOn[type] = !indOn[type];
  const btn = document.getElementById(`btn-ind-${type}`);
  if (btn) {
    if (indOn[type]) btn.classList.add('active', type);
    else             btn.classList.remove('active', type);
  }
  ({ ema9: ema9Series, ema21: ema21Series, vwap: vwapSeries, volume: volumeSeries })[type]
    ?.applyOptions({ visible: indOn[type] });
}

// ── Symbol switch ─────────────────────────────────────────────────────────────
function switchSymbolChart(symbol) {
  if (symbol === activeSymbol) return;
  activeSymbol = symbol;
  const el = document.getElementById('chart-active-symbol');
  if (el) el.textContent = symbol;
  loadCandleData(symbol);
}

// ── Timeframe switch ──────────────────────────────────────────────────────────
function setTimeframe(seconds) {
  if (barInterval === seconds) return;   // no-op if already on this TF
  barInterval = seconds;
  loadCandleData(activeSymbol);
}

// ── Execution markers ─────────────────────────────────────────────────────────
function addExecutionMarker(side, price, ts = null) {
  if (!candleSeries) return;
  const t      = Math.floor((ts || Date.now() / 1000));
  const bucket = Math.floor(t / barInterval) * barInterval;
  chartMarkers.push({
    time:     bucket,
    position: side === 'BUY' ? 'belowBar'  : 'aboveBar',
    color:    side === 'BUY' ? '#00e676'   : '#ff1744',
    shape:    side === 'BUY' ? 'arrowUp'   : 'arrowDown',
    text:     `${side} @ $${price.toFixed(2)}`,
    size: 2
  });
  candleSeries.setMarkers(chartMarkers);
}
