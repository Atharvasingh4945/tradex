// TradeX — Interactive Daily Journal & On-Demand AI Coach Engine

let activeModalDateStr = null;

document.addEventListener('DOMContentLoaded', () => {
  setupPageInteractions();
});

function setupPageInteractions() {
  const btnSaveNotes = document.getElementById('btn-save-daily-notes');
  const btnAskAI = document.getElementById('btn-ask-ai-journal');
  const notesTextarea = document.getElementById('daily-reflection-text');

  if (btnSaveNotes) {
    btnSaveNotes.addEventListener('click', () => {
      const dateStr = btnSaveNotes.dataset.date || new Date().toISOString().split('T')[0];
      const note = notesTextarea ? notesTextarea.value : '';

      btnSaveNotes.disabled = true;
      btnSaveNotes.textContent = "Saving...";

      fetch('/api/journal/save_day', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date_str: dateStr, reflection_note: note })
      })
      .then(res => res.json())
      .then(data => {
        btnSaveNotes.disabled = false;
        btnSaveNotes.textContent = "Saved ✓";
        setTimeout(() => { btnSaveNotes.textContent = "Save Notes"; }, 2000);
      })
      .catch(err => {
        btnSaveNotes.disabled = false;
        btnSaveNotes.textContent = "Save Notes";
        console.error("Error saving journal:", err);
      });
    });
  }

  if (btnAskAI) {
    btnAskAI.addEventListener('click', () => {
      const dateStr = btnAskAI.dataset.date || new Date().toISOString().split('T')[0];
      const note = notesTextarea ? notesTextarea.value : '';
      const aiContainer = document.getElementById('ai-journal-feedback-container');

      btnAskAI.disabled = true;
      btnAskAI.innerHTML = `<span>Analyzing Session...</span>`;

      fetch('/api/ai/review_day', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date_str: dateStr, reflection_note: note })
      })
      .then(res => res.json())
      .then(data => {
        btnAskAI.disabled = false;
        btnAskAI.innerHTML = `<span>✨ Ask AI for Feedback</span>`;

        if (data.success && data.feedback && aiContainer) {
          renderAIFeedbackIntoContainer(aiContainer, data.feedback);
        }
      })
      .catch(err => {
        btnAskAI.disabled = false;
        btnAskAI.innerHTML = `<span>✨ Ask AI for Feedback</span>`;
        console.error("AI review error:", err);
      });
    });
  }

  // Modal Save Button (Saves reflection note AND editable stats)
  const btnModalSave = document.getElementById('btn-modal-save-journal');
  if (btnModalSave) {
    btnModalSave.addEventListener('click', () => {
      if (!activeModalDateStr) return;

      const textarea = document.getElementById('modal-reflection-textarea');
      const tradeCntInput = document.getElementById('modal-day-trade-count');
      const winCntInput = document.getElementById('modal-day-win-count');
      const pnlInput = document.getElementById('modal-day-pnl');

      const note = textarea ? textarea.value : '';
      const tradeCount = tradeCntInput ? parseInt(tradeCntInput.value) || 0 : 0;
      const winCount = winCntInput ? parseInt(winCntInput.value) || 0 : 0;
      const dailyPnl = pnlInput ? parseFloat(pnlInput.value) || 0.0 : 0.0;

      btnModalSave.disabled = true;
      btnModalSave.textContent = "Saving...";

      fetch('/api/journal/save_day', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date_str: activeModalDateStr,
          reflection_note: note,
          trade_count: tradeCount,
          win_count: winCount,
          daily_pnl: dailyPnl
        })
      })
      .then(res => res.json())
      .then(data => {
        btnModalSave.disabled = false;
        btnModalSave.textContent = "Saved ✓";

        // Dynamically update the calendar day box on the heatmap grid
        updateCalendarDayCell(activeModalDateStr, dailyPnl, tradeCount);

        setTimeout(() => { btnModalSave.textContent = "💾 Save Journal Entry"; }, 2000);
      })
      .catch(err => {
        btnModalSave.disabled = false;
        btnModalSave.textContent = "💾 Save Journal Entry";
        console.error("Error saving modal journal:", err);
      });
    });
  }

  // Modal Ask AI Button
  const btnModalAskAI = document.getElementById('btn-modal-ask-ai');
  if (btnModalAskAI) {
    btnModalAskAI.addEventListener('click', () => {
      if (!activeModalDateStr) return;

      const textarea = document.getElementById('modal-reflection-textarea');
      const tradeCntInput = document.getElementById('modal-day-trade-count');
      const winCntInput = document.getElementById('modal-day-win-count');
      const pnlInput = document.getElementById('modal-day-pnl');

      const note = textarea ? textarea.value : '';
      const tradeCount = tradeCntInput ? parseInt(tradeCntInput.value) || 0 : 0;
      const winCount = winCntInput ? parseInt(winCntInput.value) || 0 : 0;
      const dailyPnl = pnlInput ? parseFloat(pnlInput.value) || 0.0 : 0.0;

      const modalAiContainer = document.getElementById('modal-ai-feedback-container');

      btnModalAskAI.disabled = true;
      btnModalAskAI.innerHTML = `<span>Analyzing Session...</span>`;

      fetch('/api/ai/review_day', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date_str: activeModalDateStr,
          reflection_note: note,
          trade_count: tradeCount,
          win_count: winCount,
          daily_pnl: dailyPnl
        })
      })
      .then(res => res.json())
      .then(data => {
        btnModalAskAI.disabled = false;
        btnModalAskAI.innerHTML = `<span>✨ Ask AI for Session Review</span>`;

        if (data.success && data.feedback && modalAiContainer) {
          renderAIFeedbackIntoContainer(modalAiContainer, data.feedback);
        }
      })
      .catch(err => {
        btnModalAskAI.disabled = false;
        btnModalAskAI.innerHTML = `<span>✨ Ask AI for Session Review</span>`;
        console.error("AI modal review error:", err);
      });
    });
  }
}

// ── Open Interactive Day Journal Window ──────────────────────────────────────
function openJournalModal(dateStr) {
  activeModalDateStr = dateStr;

  const modal = document.getElementById('journal-day-modal');
  const subtitleEl = document.getElementById('modal-journal-date-subtitle');
  const tradeCntInput = document.getElementById('modal-day-trade-count');
  const winCntInput = document.getElementById('modal-day-win-count');
  const pnlInput = document.getElementById('modal-day-pnl');
  const textarea = document.getElementById('modal-reflection-textarea');
  const modalAiContainer = document.getElementById('modal-ai-feedback-container');

  if (subtitleEl) subtitleEl.textContent = dateStr;
  if (textarea) textarea.value = "Loading journal notes...";
  if (modalAiContainer) {
    modalAiContainer.style.display = 'none';
    modalAiContainer.innerHTML = '';
  }

  if (modal) modal.classList.add('active');

  // Fetch details for specific date
  fetch(`/api/journal/day/${dateStr}`)
    .then(res => res.json())
    .then(data => {
      if (tradeCntInput) tradeCntInput.value = data.trade_count !== undefined ? data.trade_count : 0;
      if (winCntInput) winCntInput.value = data.win_count !== undefined ? data.win_count : 0;
      if (pnlInput) pnlInput.value = data.daily_pnl !== undefined ? data.daily_pnl.toFixed(2) : '0.00';
      if (textarea) textarea.value = data.reflection_note || '';

      if (data.ai_feedback && modalAiContainer) {
        renderAIFeedbackIntoContainer(modalAiContainer, data.ai_feedback);
      }
    })
    .catch(err => {
      console.error("Error fetching day details:", err);
      if (textarea) textarea.value = "";
    });
}

function closeJournalModal() {
  const modal = document.getElementById('journal-day-modal');
  if (modal) modal.classList.remove('active');
  activeModalDateStr = null;
}

function updateCalendarDayCell(dateStr, pnl, tradeCount) {
  const cell = document.getElementById(`day-cell-${dateStr}`);
  const countSpan = document.getElementById(`day-cell-count-${dateStr}`);
  const pnlDiv = document.getElementById(`day-cell-pnl-${dateStr}`);

  if (cell) {
    cell.classList.remove('green-day', 'red-day');
    if (pnl > 0) {
      cell.classList.add('green-day');
    } else if (pnl < 0) {
      cell.classList.add('red-day');
    }
  }

  if (countSpan) {
    countSpan.textContent = tradeCount > 0 ? `${tradeCount}T` : '';
  }

  if (pnlDiv) {
    const isBull = pnl >= 0;
    if (pnl !== 0 || tradeCount > 0) {
      pnlDiv.className = `mono ${isBull ? 'bull' : 'bear'}`;
      pnlDiv.textContent = `${isBull ? '+' : ''}$${Math.round(pnl)}`;
    } else {
      pnlDiv.className = 'mono';
      pnlDiv.innerHTML = `<span style="font-size: 10px; color: var(--text-dim); text-align: center;">—</span>`;
    }
  }
}

function renderAIFeedbackIntoContainer(container, fb) {
  if (!container || !fb) return;

  let wellList = (fb.what_went_well || []).map(w => `<li style="color: var(--color-bull); margin-bottom: 4px;">✓ ${w}</li>`).join('');
  let improveList = (fb.areas_to_improve || []).map(i => `<li style="color: var(--color-bear); margin-bottom: 4px;">⚠️ ${i}</li>`).join('');

  container.innerHTML = `
    <div style="margin-top: 14px; padding: 16px; background: var(--bg-card-hover); border-radius: var(--radius-md); border-left: 4px solid var(--color-brand);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <span style="font-weight: 700; font-size: 13px;">🤖 AI Session Review: ${fb.status || 'Active'}</span>
        <span class="mono" style="font-weight: 600; font-size: 12px;">P&L: ${fb.pnl || '$0.00'} | Win Rate: ${fb.win_rate || '0%'}</span>
      </div>
      <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 10px;">${fb.emotional_summary || ''}</p>
      
      ${wellList ? `<div style="margin-bottom: 8px;"><strong style="font-size: 12px;">What Went Well:</strong><ul style="list-style: none; padding-left: 0; font-size: 12px; margin-top: 4px;">${wellList}</ul></div>` : ''}
      ${improveList ? `<div style="margin-bottom: 8px;"><strong style="font-size: 12px;">Areas to Improve:</strong><ul style="list-style: none; padding-left: 0; font-size: 12px; margin-top: 4px;">${improveList}</ul></div>` : ''}
      
      <div style="padding: 10px 14px; background: rgba(99, 102, 241, 0.12); border-radius: 6px; font-size: 12px; line-height: 1.5; color: var(--text-main);">
        <strong>💡 Coach Prescription:</strong> ${fb.coach_prescription || 'Keep adhering to your risk management rules.'}
      </div>
    </div>
  `;
  container.style.display = 'block';
}
