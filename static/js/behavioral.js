// TradeX - Behavioral Lab & AI Trader Psychology Diagnosis

let biasRadarChart = null;

function initBehavioralRadar(scores) {
  const ctx = document.getElementById('behavioralRadarCanvas');
  if (!ctx) return;

  const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const textColor = isDark ? '#9ca3af' : '#64748b';
  const gridColor = isDark ? '#1f293d' : '#e2e8f0';

  const data = {
    labels: [
      'FOMO Resistance',
      'Loss Cutting Discipline',
      'Tilt Control (Anti-Revenge)',
      'Plan Adherence',
      'Win Consistency'
    ],
    datasets: [{
      label: 'Your Psychology Score (100 = Perfect)',
      data: [
        100 - (scores.fomo_score || 0),
        100 - (scores.disposition_score || 0),
        100 - (scores.tilt_score || 0),
        scores.discipline_score || 100,
        Math.min(100, (scores.win_rate || 50) * 1.5)
      ],
      fill: true,
      backgroundColor: 'rgba(99, 102, 241, 0.25)',
      borderColor: '#6366f1',
      pointBackgroundColor: '#8b5cf6',
      pointBorderColor: '#fff',
      pointHoverBackgroundColor: '#fff',
      pointHoverBorderColor: '#6366f1'
    }]
  };

  biasRadarChart = new Chart(ctx, {
    type: 'radar',
    data: data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          angleLines: { color: gridColor },
          grid: { color: gridColor },
          pointLabels: {
            color: textColor,
            font: { size: 11, family: "'Inter', sans-serif", weight: '600' }
          },
          suggestedMin: 0,
          suggestedMax: 100,
          ticks: { display: false }
        }
      },
      plugins: {
        legend: { display: false }
      }
    }
  });
}

function triggerAIArchetypeDiagnosis() {
  const btn = document.getElementById('btn-diagnose-psychology');
  const resultsContainer = document.getElementById('ai-diagnosis-results');

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>🧠 Diagnosing Psychological Patterns...</span>`;
  }

  fetch('/api/ai/diagnose_profile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  })
  .then(res => res.json())
  .then(data => {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<span>✨ Re-Analyze My Psychology</span>`;
    }

    if (data.success && data.diagnosis) {
      renderArchetypeDiagnosis(data.diagnosis);
    }
  })
  .catch(err => {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<span>✨ Re-Analyze My Psychology</span>`;
    }
    console.error("Diagnosis error:", err);
  });
}

function renderArchetypeDiagnosis(diag) {
  const archetypeBadge = document.getElementById('diag-archetype-badge');
  const descEl = document.getElementById('diag-archetype-desc');
  const dosList = document.getElementById('diag-dos-list');
  const dontsList = document.getElementById('diag-donts-list');
  const mistakesList = document.getElementById('diag-mistakes-list');

  if (archetypeBadge) archetypeBadge.textContent = diag.archetype;
  if (descEl) descEl.textContent = diag.description;

  if (dosList) {
    dosList.innerHTML = (diag.dos || []).map(d => `<li style="color: var(--color-bull); margin-bottom: 8px; font-weight: 500;">${d}</li>`).join('');
  }

  if (dontsList) {
    dontsList.innerHTML = (diag.donts || []).map(d => `<li style="color: var(--color-bear); margin-bottom: 8px; font-weight: 500;">${d}</li>`).join('');
  }

  if (mistakesList) {
    mistakesList.innerHTML = (diag.core_mistakes || []).map(m => `<li style="margin-bottom: 6px; color: var(--text-muted);">⚠️ ${m}</li>`).join('');
  }

  const card = document.getElementById('ai-diagnosis-card');
  if (card) card.scrollIntoView({ behavior: 'smooth' });
}
