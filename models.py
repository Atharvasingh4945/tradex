from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    secondary_emails = db.Column(db.Text, default="")  # Comma separated
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Capital & Risk Settings (Configured in Progress Tracker)
    starting_cash = db.Column(db.Float, default=100000.0)
    cash_balance = db.Column(db.Float, default=100000.0)
    daily_max_loss = db.Column(db.Float, default=2500.0)
    max_risk_per_trade_pct = db.Column(db.Float, default=2.0)
    
    # Relationships
    trades = db.relationship('Trade', backref='user', lazy=True, cascade="all, delete-orphan")
    positions = db.relationship('Position', backref='user', lazy=True, cascade="all, delete-orphan")
    journal_days = db.relationship('JournalDay', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_secondary_email_list(self):
        if not self.secondary_emails:
            return []
        return [e.strip() for e in self.secondary_emails.split(",") if e.strip()]


class Stock(db.Model):
    __tablename__ = 'stocks'
    symbol = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sector = db.Column(db.String(50), default="Technology")
    price = db.Column(db.Float, nullable=False)
    prev_close = db.Column(db.Float, nullable=False)
    high = db.Column(db.Float, nullable=False)
    low = db.Column(db.Float, nullable=False)
    volume = db.Column(db.BigInteger, default=1000000)
    volatility = db.Column(db.Float, default=0.015)
    last_tick_direction = db.Column(db.Integer, default=0) # 1 for up, -1 for down, 0 for neutral
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def change(self):
        return round(self.price - self.prev_close, 2)

    @property
    def change_pct(self):
        return round((self.change / self.prev_close * 100) if self.prev_close > 0 else 0, 2)

    def to_dict(self):
        return {
            'symbol': self.symbol,
            'name': self.name,
            'sector': self.sector,
            'price': round(self.price, 2),
            'prev_close': round(self.prev_close, 2),
            'change': self.change,
            'change_pct': self.change_pct,
            'high': round(self.high, 2),
            'low': round(self.low, 2),
            'volume': self.volume,
            'last_tick_direction': self.last_tick_direction
        }



class Candle(db.Model):
    __tablename__ = 'candles'
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False, index=True)
    timeframe = db.Column(db.String(10), default='1s') # 1s, 5s, 1m
    timestamp = db.Column(db.Integer, nullable=False, index=True) # Unix timestamp in seconds
    open = db.Column(db.Float, nullable=False)
    high = db.Column(db.Float, nullable=False)
    low = db.Column(db.Float, nullable=False)
    close = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Float, default=100)

    def to_dict(self):
        return {
            'time': self.timestamp,
            'open': round(self.open, 2),
            'high': round(self.high, 2),
            'low': round(self.low, 2),
            'close': round(self.close, 2),
            'volume': round(self.volume, 2)
        }


class Position(db.Model):
    __tablename__ = 'positions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    avg_price = db.Column(db.Float, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self, current_price=None):
        curr = current_price if current_price is not None else self.avg_price
        market_val = self.qty * curr
        cost_basis = self.qty * self.avg_price
        unrealized_pnl = market_val - cost_basis
        unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
        return {
            'id': self.id,
            'symbol': self.symbol,
            'qty': self.qty,
            'avg_price': round(self.avg_price, 2),
            'current_price': round(curr, 2),
            'market_value': round(market_val, 2),
            'cost_basis': round(cost_basis, 2),
            'unrealized_pnl': round(unrealized_pnl, 2),
            'unrealized_pnl_pct': round(unrealized_pnl_pct, 2)
        }


class Trade(db.Model):
    __tablename__ = 'trades'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    side = db.Column(db.String(4), nullable=False) # 'BUY' or 'SELL'
    qty = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    unix_time = db.Column(db.Integer, nullable=False) # For TradingView marker alignment
    
    # Realized metrics (calculated upon closing position)
    realized_pnl = db.Column(db.Float, default=0.0)
    realized_pnl_pct = db.Column(db.Float, default=0.0)
    holding_seconds = db.Column(db.Integer, default=0)
    mae = db.Column(db.Float, default=0.0) # Maximum Adverse Excursion
    mfe = db.Column(db.Float, default=0.0) # Maximum Favorable Excursion
    
    # Behavioral & Journaling fields (3-click post trade)
    setup_tag = db.Column(db.String(50), default="Discretionary") # Breakout, Dip Buy, VWAP Reversal, Support Bounce, FOMO Chase
    emotion_tag = db.Column(db.String(50), default="Calm") # Calm, FOMO/Excited, Anxious/Panic, Greedy, Bored/Gambling
    confidence = db.Column(db.Integer, default=3) # 1 to 5
    target_price = db.Column(db.Float, nullable=True)
    stop_loss_price = db.Column(db.Float, nullable=True)
    notes = db.Column(db.Text, default="")
    
    # Invalidation adherence
    followed_plan = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side,
            'qty': self.qty,
            'price': round(self.price, 2),
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'unix_time': self.unix_time,
            'realized_pnl': round(self.realized_pnl, 2),
            'realized_pnl_pct': round(self.realized_pnl_pct, 2),
            'holding_seconds': self.holding_seconds,
            'mae': round(self.mae, 2),
            'mfe': round(self.mfe, 2),
            'setup_tag': self.setup_tag,
            'emotion_tag': self.emotion_tag,
            'confidence': self.confidence,
            'target_price': round(self.target_price, 2) if self.target_price else None,
            'stop_loss_price': round(self.stop_loss_price, 2) if self.stop_loss_price else None,
            'notes': self.notes,
            'followed_plan': self.followed_plan
        }


class JournalDay(db.Model):
    __tablename__ = 'journal_days'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date_str = db.Column(db.String(10), nullable=False) # 'YYYY-MM-DD'
    daily_pnl = db.Column(db.Float, default=0.0)
    trade_count = db.Column(db.Integer, default=0)
    win_count = db.Column(db.Integer, default=0)
    loss_count = db.Column(db.Integer, default=0)
    reflection_note = db.Column(db.Text, default="")
    ai_feedback = db.Column(db.Text, default="")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'date_str': self.date_str,
            'daily_pnl': round(self.daily_pnl, 2),
            'trade_count': self.trade_count,
            'win_count': self.win_count,
            'loss_count': self.loss_count,
            'win_rate': round(self.win_count / self.trade_count * 100, 1) if self.trade_count > 0 else 0,
            'reflection_note': self.reflection_note,
            'ai_feedback': self.ai_feedback
        }


class EconomicEvent(db.Model):
    __tablename__ = 'economic_events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    currency = db.Column(db.String(10), default="USD")
    impact = db.Column(db.String(10), default="HIGH") # HIGH, MEDIUM, LOW
    forecast = db.Column(db.String(30), default="")
    previous = db.Column(db.String(30), default="")
    actual = db.Column(db.String(30), default="")
    time_str = db.Column(db.String(30), default="Today")
    is_active = db.Column(db.Boolean, default=True)
    shock_factor = db.Column(db.Float, default=0.0) # Induced volatility multiplier
    headline_news = db.Column(db.String(250), default="")

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'currency': self.currency,
            'impact': self.impact,
            'forecast': self.forecast,
            'previous': self.previous,
            'actual': self.actual,
            'time_str': self.time_str,
            'headline_news': self.headline_news
        }
