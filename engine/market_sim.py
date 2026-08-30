import time
import random
import math
from datetime import datetime
try:
    from models import db, Stock, Candle, EconomicEvent
except ImportError:
    from tradex.models import db, Stock, Candle, EconomicEvent

# Initial universe of realistic trading assets
DEFAULT_STOCKS = [
    {"symbol": "NVDA", "name": "NVIDIA Corporation", "sector": "Semiconductors", "price": 884.50, "volatility": 0.045},
    {"symbol": "SPY", "name": "SPDR S&P 500 ETF", "sector": "Index ETF", "price": 520.25, "volatility": 0.018},
    {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Automotive / CleanTech", "price": 175.40, "volatility": 0.055},
    {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Consumer Electronics", "price": 168.20, "volatility": 0.025},
    {"symbol": "BYTE", "name": "Byte Cloud Systems", "sector": "Cloud & AI", "price": 179.20, "volatility": 0.060},
    {"symbol": "ALFA", "name": "Alfa Robotics & AI", "sector": "Robotics", "price": 119.50, "volatility": 0.050},
    {"symbol": "CRUX", "name": "Crux Clean Energy", "sector": "Renewables", "price": 28.75, "volatility": 0.070},
    {"symbol": "FIN", "name": "Finlay Global Bank", "sector": "Financials", "price": 130.80, "volatility": 0.022},
]

DEFAULT_EVENTS = [
    {
        "title": "US Core CPI (MoM)",
        "currency": "USD",
        "impact": "HIGH",
        "forecast": "0.3%",
        "previous": "0.4%",
        "actual": "0.2%",
        "time_str": "12:30 GMT",
        "headline_news": "🔴 Core CPI cools to 0.2%, boosting risk-on appetite across Tech & Indices."
    },
    {
        "title": "FOMC Fed Interest Rate Decision",
        "currency": "USD",
        "impact": "HIGH",
        "forecast": "5.25%",
        "previous": "5.50%",
        "actual": "5.25%",
        "time_str": "18:00 GMT",
        "headline_news": "🔴 Fed cuts rates by 25 bps; Powell notes balanced risk outlook."
    },
    {
        "title": "Non-Farm Employment Change (NFP)",
        "currency": "USD",
        "impact": "HIGH",
        "forecast": "180K",
        "previous": "165K",
        "actual": "215K",
        "time_str": "Tomorrow",
        "headline_news": "🔴 US Labor market surges with 215K new jobs; yields spike."
    },
    {
        "title": "ISM Manufacturing PMI",
        "currency": "USD",
        "impact": "MEDIUM",
        "forecast": "49.5",
        "previous": "48.7",
        "actual": "50.3",
        "time_str": "14:00 GMT",
        "headline_news": "🟠 Manufacturing PMI crosses into expansion territory at 50.3."
    },
    {
        "title": "NVIDIA AI Chip Enterprise Sales",
        "currency": "USD",
        "impact": "HIGH",
        "forecast": "$28.0B",
        "previous": "$24.5B",
        "actual": "$30.2B",
        "time_str": "Just In",
        "headline_news": "🚀 NVDA smashes datacenter revenue guidance by +15%."
    }
]

class MarketSimulator:
    def __init__(self, app):
        self.app = app
        self.active_shock = 0.0 # Volatility shock multiplier
        self.active_shock_decay = 0.95
        self.last_news = "Market is open. 1-second price simulation active."
        self.latest_ticks = {} # symbol -> {price, change, ...}
        self.momentum = {} # symbol -> momentum drift

    def seed_initial_data(self):
        """Seeds stocks, historic candles, and economic events if missing."""
        with self.app.app_context():
            # Check stocks
            if Stock.query.count() == 0:
                now_ts = int(time.time())
                for s in DEFAULT_STOCKS:
                    stock = Stock(
                        symbol=s["symbol"],
                        name=s["name"],
                        sector=s["sector"],
                        price=s["price"],
                        prev_close=round(s["price"] * (1 - random.uniform(-0.015, 0.015)), 2),
                        high=s["price"],
                        low=s["price"],
                        volume=random.randint(500000, 2000000),
                        volatility=s["volatility"]
                    )
                    db.session.add(stock)
                    # ── Generate 1-second historical candles (600 bars = 10 mins) ──
                    base_p = s["price"]
                    vol = s["volatility"]
                    HIST_SECONDS = 600
                    momentum_drift = random.choice([-1, 1]) * random.uniform(0.0002, 0.001)

                    for i in range(HIST_SECONDS, 0, -1):
                        c_time = now_ts - i

                        if random.random() < 0.02:
                            momentum_drift = random.choice([-1, 1]) * random.uniform(0.0002, 0.001)

                        jump = 0.0
                        if random.random() < 0.005:
                            jump = random.gauss(0, vol * 0.4) * base_p

                        noise = random.gauss(0, 1) * vol * 0.025 * base_p
                        delta = momentum_drift * base_p + noise + jump

                        o = round(base_p, 2)
                        c = round(max(0.50, base_p + delta), 2)
                        h = round(max(o, c) + abs(random.gauss(0, vol * 0.01 * base_p)), 2)
                        l = round(min(o, c) - abs(random.gauss(0, vol * 0.01 * base_p)), 2)
                        v = random.randint(40, 400)

                        candle = Candle(
                            symbol=stock.symbol,
                            timeframe='1s',
                            timestamp=c_time,
                            open=o,
                            high=h,
                            low=l,
                            close=c,
                            volume=v
                        )
                        db.session.add(candle)
                        base_p = float(c)

                    stock.price = round(base_p, 2)
                    stock.high = round(max(s["price"], base_p), 2)
                    stock.low = round(min(s["price"], base_p), 2)
                    self.momentum[stock.symbol] = momentum_drift
                    db.session.commit()



            # Check economic events
            if EconomicEvent.query.count() == 0:
                for ev in DEFAULT_EVENTS:
                    event = EconomicEvent(
                        title=ev["title"],
                        currency=ev["currency"],
                        impact=ev["impact"],
                        forecast=ev["forecast"],
                        previous=ev["previous"],
                        actual=ev["actual"],
                        time_str=ev["time_str"],
                        headline_news=ev["headline_news"]
                    )
                    db.session.add(event)
                db.session.commit()

    def tick(self):
        """Executes one lively tick iteration (called every 1 second)."""
        with self.app.app_context():
            now_ts = int(time.time())
            stocks = Stock.query.all()
            if not stocks:
                return {}

            # Decay active shock
            if abs(self.active_shock) > 0.0001:
                self.active_shock *= self.active_shock_decay
            else:
                self.active_shock = 0.0

            tick_data = []

            for stock in stocks:
                # Stochastic momentum walk with lively micro-oscillations
                if stock.symbol not in self.momentum:
                    self.momentum[stock.symbol] = 0.0

                # 10% chance to flip momentum drift
                if random.random() < 0.12:
                    self.momentum[stock.symbol] = random.choice([-1, 1]) * random.uniform(0.0002, 0.0015)

                vol = stock.volatility
                shock_impact = self.active_shock * (1.5 if stock.sector in ["Technology", "Semiconductors", "Cloud & AI"] else 0.8)
                
                # Active price fluctuation: ~0.1% to 0.4% per second
                noise = random.gauss(0, 1) * vol * 0.08
                pct_return = self.momentum[stock.symbol] + noise + (shock_impact * 0.003)

                old_price = stock.price
                # Calculate new price with active change
                delta = round(old_price * pct_return, 2)
                if delta == 0.0:
                    delta = 0.05 * (1 if random.random() > 0.48 else -1)

                new_price = max(0.50, round(old_price + delta, 2))
                
                # Direction: 1 (green tick), -1 (red tick), 0 (flat)
                direction = 1 if new_price > old_price else (-1 if new_price < old_price else 0)
                stock.price = new_price
                stock.last_tick_direction = direction
                stock.high = max(stock.high, new_price)
                stock.low = min(stock.low, new_price)
                stock.volume += random.randint(25, 250)
                stock.updated_at = datetime.utcnow()

                stock_dict = stock.to_dict()
                self.latest_ticks[stock.symbol] = stock_dict
                tick_data.append(stock_dict)

            db.session.commit()

            return {
                "timestamp": now_ts,
                "stocks": tick_data,
                "news": self.last_news,
                "shock": round(self.active_shock, 3)
            }

    def trigger_news_shock(self, headline, shock_factor=1.5):
        """Simulate breaking news impacting market volatility."""
        self.last_news = headline
        self.active_shock = shock_factor
