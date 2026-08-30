// TradeX — Real-time Terminal, Position Tracking & Execution Engine

let lastPrices = {};
let activeSide = 'BUY';
let currentTradeId = null;
let sseActive = false;
let lastSseTickMs = 0;
let userPositions = [];

document.addEventListener('DOMContentLoaded', () => {
  initRealtimeMarketStream();
  setupOrderDock();
  setupPostTradeModal();
  fetchActivePositions();
});

// ── Dual-Engine Stream (SSE primary, polling only as dead-man fallback) ─────
function initRealtimeMarketStream() {
  try {
    const es = new EventSource('/api/stream/market');

    es.onmessage = (evt) => {
      sseActive = true;
      lastSseTickMs = Date.now();
      try { processMarketTickData(JSON.parse(evt.data)); } catch (_) {}
    };

    es.onerror = () => { sseActive = false; };
  } catch (_) { sseActive = false; }

  // Polling fallback — only fires if SSE has been silent for >2 seconds
  setInterval(() => {
    const silentMs = Date.now() - lastSseTickMs;
    if (silentMs < 2000) return;

    fetch('/api/market/ticks')
      .then(r => r.json())
      .then(data => processMarketTickData(data))
      .catch(() => {});
  }, 1200);
}

function processMarketTickData(data) {
  if (!data || !data.stocks) return;

  data.stocks.forEach(stock => {
    updateStockWatchlistRow(stock);

    if (typeof updateLiveCandle === 'function') {
      updateLiveCandle(stock.symbol, stock.price);
    }
  });

  if (data.news) {
    const el = document.getElementById('top-news-headline');
    if (el && el.textContent !== data.news) el.textContent = data.news;
  }

  updatePositionsPnL();
}

// ── Watchlist Row ────────────────────────────────────────────────────────────
function updateStockWatchlistRow(stock) {
  const sym = stock.symbol;
  const old = lastPrices[sym] || stock.price;
  lastPrices[sym] = stock.price;

  const priceCell  = document.getElementById(`price-val-${sym}`);
  const changeCell = document.getElementById(`change-val-${sym}`);

  if (priceCell) {
    priceCell.textContent = `$${stock.price.toFixed(2)}`;
    priceCell.classList.remove('tick-up', 'tick-down');
    void priceCell.offsetWidth;
    priceCell.classList.add(stock.price >= old ? 'tick-up' : 'tick-down');
  }

  if (changeCell) {
    const bull = stock.change >= 0;
    changeCell.className = `mono ${bull ? 'bull' : 'bear'}`;
    changeCell.textContent = `${bull ? '+' : ''}${stock.change_pct.toFixed(2)}%`;
  }

  const sel = document.getElementById('order-symbol-select');
  if (sel && sel.value === sym) {
    const dp = document.getElementById('order-dock-current-price');
    if (dp) dp.textContent = `$${stock.price.toFixed(2)}`;
    recalcOrderEstimate();
  }
}

// ── Real-Time Open Positions Management ─────────────────────────────────────
function fetchActivePositions() {
  fetch('/api/positions')
    .then(r => r.json())
    .then(data => {
      if (data && data.positions) {
        userPositions = data.positions;
        renderPositionsTable(userPositions);
      }
    })
    .catch(err => console.warn('Could not fetch active positions:', err));
}

function renderPositionsTable(positions) {
  userPositions = positions || [];
  const container = document.getElementById('positions-table-container');
  const countBadge = document.getElementById('open-positions-count');

  if (countBadge) {
    countBadge.textContent = `${userPositions.length} Open`;
  }

  if (!container) return;

  if (userPositions.length === 0) {
    container.innerHTML = `
      <div style="padding: 40px 20px; text-align: center; color: var(--text-muted);" id="empty-positions-placeholder">
        <p style="font-size: 14px; margin-bottom: 8px;">No open positions.</p>
        <p style="font-size: 12px; color: var(--text-dim);">Execute a trade on the order dock to start tracking live P&L.</p>
      </div>
    `;
    return;
  }

  let html = `
    <div class="table-responsive">
      <table class="tradex-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th style="text-align: right;">Qty</th>
            <th style="text-align: right;">Avg Buy</th>
            <th style="text-align: right;">Current</th>
            <th style="text-align: right;">P&L ($)</th>
            <th style="text-align: center;">Action</th>
          </tr>
        </thead>
        <tbody id="positions-tbody">
  `;

  userPositions.forEach(pos => {
    const curr = lastPrices[pos.symbol] || pos.current_price || pos.avg_price;
    const pnl = (curr - pos.avg_price) * pos.qty;
    const pnl_pct = pos.avg_price > 0 ? ((curr - pos.avg_price) / pos.avg_price * 100) : 0;
    const isBull = pnl >= 0;

    html += `
      <tr id="pos-row-${pos.symbol}">
        <td><strong style="color: var(--text-main); cursor: pointer;" onclick="switchSymbolChart('${pos.symbol}'); document.getElementById('order-symbol-select').value='${pos.symbol}'; recalcOrderEstimate();">${pos.symbol}</strong></td>
        <td style="text-align: right;" class="mono" id="pos-qty-${pos.symbol}">${pos.qty}</td>
        <td style="text-align: right;" class="mono" id="pos-avg-${pos.symbol}">$${pos.avg_price.toFixed(2)}</td>
        <td style="text-align: right;" class="mono" id="pos-curr-${pos.symbol}">$${curr.toFixed(2)}</td>
        <td style="text-align: right; font-weight: 700;" class="mono ${isBull ? 'bull' : 'bear'}" id="pos-pnl-${pos.symbol}">
          ${isBull ? '+' : ''}$${pnl.toFixed(2)} (${isBull ? '+' : ''}${pnl_pct.toFixed(2)}%)
        </td>
        <td style="text-align: center;">
          <button class="tag-chip" style="background: var(--color-bear-bg); color: var(--color-bear); border-color: var(--color-bear-border); padding: 4px 10px; font-size: 11px; font-weight: 700; cursor: pointer;" onclick="closeOpenPosition('${pos.symbol}', ${pos.qty});">
            ⚡ Close
          </button>
        </td>
      </tr>
    `;
  });

  html += `
        </tbody>
      </table>
    </div>
  `;

  container.innerHTML = html;
}

function updatePositionsPnL() {
  if (!userPositions || userPositions.length === 0) return;

  userPositions.forEach(pos => {
    const curr = lastPrices[pos.symbol];
    if (curr === undefined) return;

    const pnl = (curr - pos.avg_price) * pos.qty;
    const pnl_pct = pos.avg_price > 0 ? ((curr - pos.avg_price) / pos.avg_price * 100) : 0;
    const isBull = pnl >= 0;

    const currEl = document.getElementById(`pos-curr-${pos.symbol}`);
    const pnlEl = document.getElementById(`pos-pnl-${pos.symbol}`);

    if (currEl) currEl.textContent = `$${curr.toFixed(2)}`;
    if (pnlEl) {
      pnlEl.className = `mono ${isBull ? 'bull' : 'bear'}`;
      pnlEl.textContent = `${isBull ? '+' : ''}$${pnl.toFixed(2)} (${isBull ? '+' : ''}${pnl_pct.toFixed(2)}%)`;
    }
  });
}

function closeOpenPosition(symbol, qty) {
  const currPrice = lastPrices[symbol] || 100;
  if (!confirm(`Confirm close market position: SELL ${qty} ${symbol} @ ~$${currPrice.toFixed(2)}?`)) {
    return;
  }

  fetch('/api/trade/order', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol: symbol, side: 'SELL', qty: qty })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      currentTradeId = data.trade_id;

      if (typeof addExecutionMarker === 'function') {
        addExecutionMarker('SELL', currPrice);
      }

      const fmt = (v) => `$${v.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
      if (data.cash_balance !== undefined) {
        ['header-cash-balance', 'dashboard-cash-display'].forEach(id => {
          const el = document.getElementById(id);
          if (el) el.textContent = fmt(data.cash_balance);
        });
      }

      renderPositionsTable(data.positions);
      openPostTradeModal(symbol, 'SELL', qty, currPrice);
    } else {
      alert(`Close Position Failed: ${data.message}`);
    }
  })
  .catch(err => console.error('Error closing position:', err));
}

// ── Order Dock ───────────────────────────────────────────────────────────────
function setupOrderDock() {
  const btnBuy  = document.getElementById('tab-order-buy');
  const btnSell = document.getElementById('tab-order-sell');
  const qty     = document.getElementById('order-qty-input');
  const exec    = document.getElementById('btn-execute-order');
  const sel     = document.getElementById('order-symbol-select');

  if (btnBuy && btnSell) {
    btnBuy.addEventListener('click', () => {
      activeSide = 'BUY';
      btnBuy.classList.add('active-buy');
      btnSell.classList.remove('active-sell');
      if (exec) { exec.className = 'btn-order-execute btn-buy'; exec.textContent = `BUY ${sel?.value || ''}`; }
    });
    btnSell.addEventListener('click', () => {
      activeSide = 'SELL';
      btnSell.classList.add('active-sell');
      btnBuy.classList.remove('active-buy');
      if (exec) { exec.className = 'btn-order-execute btn-sell'; exec.textContent = `SELL ${sel?.value || ''}`; }
    });
  }

  qty?.addEventListener('input', recalcOrderEstimate);

  sel?.addEventListener('change', () => {
    if (typeof switchSymbolChart === 'function') switchSymbolChart(sel.value);
    if (exec) exec.textContent = `${activeSide} ${sel.value}`;
    recalcOrderEstimate();
  });

  exec?.addEventListener('click', placeTradeOrder);
}

function recalcOrderEstimate() {
  const sel  = document.getElementById('order-symbol-select');
  const qty  = document.getElementById('order-qty-input');
  const cost = document.getElementById('order-est-cost');
  if (!sel || !qty || !cost) return;
  const total = (parseInt(qty.value) || 0) * (lastPrices[sel.value] || 100);
  cost.textContent = `$${total.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
}

function placeTradeOrder() {
  const sel  = document.getElementById('order-symbol-select');
  const qty  = document.getElementById('order-qty-input');
  const exec = document.getElementById('btn-execute-order');
  const symbol = sel?.value || 'NVDA';
  const shares = parseInt(qty?.value || 10);

  if (shares <= 0) { alert('Enter a valid quantity > 0'); return; }

  exec.disabled = true;
  exec.textContent = 'Executing…';

  fetch('/api/trade/order', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, side: activeSide, qty: shares })
  })
  .then(r => r.json())
  .then(data => {
    exec.disabled = false;
    exec.textContent = `${activeSide} ${symbol}`;

    if (data.success) {
      currentTradeId = data.trade_id;
      const price = lastPrices[symbol] || 100;

      if (typeof addExecutionMarker === 'function') addExecutionMarker(activeSide, price);

      const fmt = (v) => `$${v.toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
      if (data.cash_balance !== undefined) {
        ['header-cash-balance', 'dashboard-cash-display'].forEach(id => {
          const el = document.getElementById(id);
          if (el) el.textContent = fmt(data.cash_balance);
        });
      }

      // Live update the Active Open Positions Table instantly
      if (data.positions) {
        renderPositionsTable(data.positions);
      }

      openPostTradeModal(symbol, activeSide, shares, price);
    } else {
      alert(`Order failed: ${data.message}`);
    }
  })
  .catch(() => {
    exec.disabled = false;
    exec.textContent = `${activeSide} ${symbol}`;
  });
}

// ── Post-Trade 3-Click Journal Modal ─────────────────────────────────────────
function setupPostTradeModal() {
  document.querySelectorAll('.tag-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const group = chip.parentElement;
      group.querySelectorAll('.tag-chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
    });
  });

  document.getElementById('btn-save-post-trade-journal')?.addEventListener('click', () => {
    if (!currentTradeId) return closeModal();

    fetch(`/api/trade/journal/${currentTradeId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        setup_tag:      document.querySelector('#setup-tag-group .tag-chip.active')?.dataset.value   || 'Discretionary',
        emotion_tag:    document.querySelector('#emotion-tag-group .tag-chip.active')?.dataset.value || 'Calm',
        confidence:     parseInt(document.getElementById('post-trade-confidence')?.value || 4),
        target_price:   document.getElementById('post-trade-target')?.value  || null,
        stop_loss_price:document.getElementById('post-trade-stop')?.value    || null,
        notes:          document.getElementById('post-trade-notes')?.value   || ''
      })
    })
    .then(r => r.json())
    .then(() => { closeModal(); })
    .catch(() => closeModal());
  });

  document.getElementById('btn-skip-post-trade-journal')?.addEventListener('click', () => {
    closeModal();
  });
}

function openPostTradeModal(symbol, side, qty, price) {
  const info = document.getElementById('post-trade-exec-info');
  if (info) info.textContent = `Executed ${side} ${qty} ${symbol} @ $${price.toFixed(2)}`;
  document.getElementById('post-trade-modal')?.classList.add('active');
}

function closeModal() {
  document.getElementById('post-trade-modal')?.classList.remove('active');
}
