# TradeX — Institutional Trading Simulator & Behavioral Journal

> **TradeX** is a modern, high-performance stock trading simulator with real-time 1-second price movement, interactive TradingView charts, technical indicators (EMA 9, EMA 21, VWAP, Volume), an on-demand AI trading coach, and deep behavioral psychology analytics.

---

## 🚀 Key Features

### 1. ⚡ Live 1-Second Continuous Market Simulation
- **1-Second Price Engine**: Continuous jump-diffusion stochastic price walk across 8 equities (NVDA, SPY, TSLA, AAPL, BYTE, ALFA, CRUX, FIN).
- **TradingView Lightweight Charts v4**: Real-time 1-second candlestick bars, wicks, and volume histograms updated live without refreshing.
- **Dynamic Trade Markers**: Instant BUY (Green arrow) and SELL (Red arrow) execution markers pinned directly to the chart.

### 2. 📈 Technical Indicators Toolbar
- **EMA 9 (Fast EMA)**: Instant blue trend indicator (`#3b82f6`).
- **EMA 21 (Medium EMA)**: Instant orange/red trend confirmation line (`#f97316`).
- **VWAP (Volume-Weighted Average Price)**: Institutional benchmark line (`#eab308`).
- **Volume**: Non-overlapping bottom pane with on/off toggle.

### 3. 🧠 Behavioral Psychology & Trader Archetypes
- **Bias Detection**: FOMO Chase Score, Disposition Effect (cutting winners early vs holding losers), Tilt / Revenge trading index, and Strategy Plan Adherence.
- **Trader Archetype Profiling**: Categorizes trading style into data-driven profiles like *"The Disciplined Sniper"*, *"The FOMO Chaser"*, *"The Reluctant Loss-Cutter"*, and *"The Tilt Gambler"*.
- **5-Axis Radar Matrix**: Visualizes Discipline, Risk Control, Patience, Edge, and Adaptability.

### 4. 🤖 On-Demand AI Supportive Coach
- **Session Reviews**: Request AI feedback on your daily journaling and trades on demand.
- **Actionable DOs & DON'Ts**: Personalized tips based on your actual execution data.

### 5. 📊 Tableau 1-Click CSV Export & Progress Tracker
- **Standardized Export**: Download execution histories complete with MAE, MFE, holding time, setup tags, and emotion classifications for external analysis in Tableau / Excel.
- **Daily Heatmap Calendar**: Color-coded P&L grid summarizing daily performance.

### 6. 📰 Live Macro News Feed
- Card-based economic calendar with High 🔴, Medium 🟠, and Low 🟡 impact events.
- **⚡ Inject Volatility**: Simulate real-time macroeconomic shocks directly into stock volatility.

---

## 🛠️ Tech Stack

- **Backend**: Python, Flask, SQLAlchemy, Flask-Login, APScheduler, NumPy, Pandas
- **Frontend**: Server-rendered Jinja2 HTML5, Custom Fintech CSS (Glassmorphism & dark/light auto-detection), TradingView Lightweight Charts v4, Chart.js
- **Database**: SQLite (local) / PostgreSQL ready

---

## 🏁 Quickstart

### 1. Clone & Setup Virtual Environment
```bash
git clone <repository_url>
cd tradex
python -m venv .venv

# Windows
.\.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python run.py
```

Open your browser at: **`http://127.0.0.1:5055`**

**Default Credentials:**
- **Email:** `trader@tradex.com`
- **Password:** `tradex123`
*(Or click "Sign up here" to create a fresh clean account with your desired starting cash).*
