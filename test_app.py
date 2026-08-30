import os
import sys
import unittest
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from app import create_app
    from models import db, User, Stock, Candle, Trade, Position, JournalDay, EconomicEvent
    from engine import BehavioralEngine, AICoach, TableauExporter
except ImportError:
    from tradex.app import create_app
    from tradex.models import db, User, Stock, Candle, Trade, Position, JournalDay, EconomicEvent
    from tradex.engine import BehavioralEngine, AICoach, TableauExporter

class TradeXTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_database_seeded(self):
        with self.app.app_context():
            stocks = Stock.query.all()
            self.assertGreaterEqual(len(stocks), 6)
            
            user = User.query.filter_by(email="trader@tradex.com").first()
            self.assertIsNotNone(user)
            self.assertEqual(user.starting_cash, 100000.0)

            candles = Candle.query.filter_by(symbol="NVDA").all()
            self.assertGreaterEqual(len(candles), 10)

            events = EconomicEvent.query.all()
            self.assertGreaterEqual(len(events), 3)

    def test_behavioral_engine_and_trade(self):
        with self.app.app_context():
            user = User.query.filter_by(email="trader@tradex.com").first()
            
            # Create a real test trade
            t = Trade(
                user_id=user.id,
                symbol="NVDA",
                side="BUY",
                qty=10,
                price=880.0,
                timestamp=datetime.utcnow(),
                unix_time=int(time.time()),
                realized_pnl=150.0,
                realized_pnl_pct=1.7,
                holding_seconds=120,
                setup_tag="Dip Buy",
                emotion_tag="Calm",
                confidence=5
            )
            db.session.add(t)
            db.session.commit()

            trades = Trade.query.filter_by(user_id=user.id).all()
            engine = BehavioralEngine(trades, user.starting_cash)
            profile = engine.analyze()

            self.assertIn('archetype', profile)
            self.assertIn('fomo_score', profile)
            self.assertGreaterEqual(profile['win_count'], 1)


            # Test Tableau exporter
            csv_data = TableauExporter.export_csv(trades)
            self.assertIn("Trade_ID,Timestamp,Date", csv_data)
            self.assertIn("NVDA", csv_data)

            # Test AI coach
            j_day = JournalDay(
                user_id=user.id,
                date_str="2026-08-23",
                daily_pnl=150.0,
                trade_count=1,
                win_count=1
            )
            coach = AICoach()
            feedback = coach.review_daily_journal(j_day, trades)
            self.assertIn('session_date', feedback)
            self.assertIn('what_went_well', feedback)

if __name__ == '__main__':
    unittest.main()
