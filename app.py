import os
import sys
import time
import json
import threading
from datetime import datetime, date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

try:
    from models import db, User, Stock, Candle, Position, Trade, JournalDay, EconomicEvent
    from engine import MarketSimulator, BehavioralEngine, AICoach, TableauExporter
except ImportError:
    from tradex.models import db, User, Stock, Candle, Position, Trade, JournalDay, EconomicEvent
    from tradex.engine import MarketSimulator, BehavioralEngine, AICoach, TableauExporter


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'tradex-pro-secret-key-2026')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///tradex.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Initialize market engine
    market_sim = MarketSimulator(app)
    ai_coach = AICoach()

    # Create tables and initial seed data
    with app.app_context():
        db.create_all()
        market_sim.seed_initial_data()

        # Seed default user if none exists (clean slate, 0 trades)
        if User.query.count() == 0:
            demo_user = User(
                username="Atharv",
                email="trader@tradex.com",
                starting_cash=100000.0,
                cash_balance=100000.0,
                daily_max_loss=2500.0,
                max_risk_per_trade_pct=2.0
            )
            demo_user.set_password("tradex123")
            db.session.add(demo_user)
            db.session.commit()


    # Background 1-second price ticking thread
    def run_market_loop():
        while True:
            try:
                market_sim.tick()
            except Exception as e:
                pass
            time.sleep(1.0)

    if not app.config.get('TESTING'):
        tick_thread = threading.Thread(target=run_market_loop, daemon=True)
        tick_thread.start()


    # ------------------ AUTH ROUTES ------------------

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            user = User.query.filter((User.email == email) | (User.username == email)).first()
            if user and user.check_password(password):
                login_user(user, remember=True)
                flash('Welcome back to TradeX!', 'success')
                return redirect(url_for('dashboard'))
            flash('Invalid email or password.', 'error')
        return render_template('auth/login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            starting_cash = float(request.form.get('starting_cash', 100000.0))

            if User.query.filter_by(email=email).first():
                flash('Email already registered. Please login.', 'error')
                return redirect(url_for('login'))

            new_user = User(
                username=username or email.split('@')[0],
                email=email,
                starting_cash=starting_cash,
                cash_balance=starting_cash,
                daily_max_loss=starting_cash * 0.025,
                max_risk_per_trade_pct=2.0
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            login_user(new_user)
            flash('Account created successfully!', 'success')
            return redirect(url_for('dashboard'))
        return render_template('auth/register.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('Logged out safely.', 'info')
        return redirect(url_for('login'))

    # ------------------ MAIN PAGES ------------------

    @app.route('/')
    @app.route('/dashboard')
    @login_required
    def dashboard():
        stocks = Stock.query.all()
        positions = Position.query.filter_by(user_id=current_user.id).all()
        
        # Calculate active portfolio metrics
        stock_price_map = {s.symbol: s.price for s in stocks}
        holdings_value = sum(p.qty * stock_price_map.get(p.symbol, p.avg_price) for p in positions)
        net_worth = current_user.cash_balance + holdings_value
        unrealized_pnl = sum((stock_price_map.get(p.symbol, p.avg_price) - p.avg_price) * p.qty for p in positions)

        recent_trades = Trade.query.filter_by(user_id=current_user.id).order_by(Trade.timestamp.desc()).limit(5).all()
        events = EconomicEvent.query.filter_by(is_active=True).limit(4).all()

        return render_template('dashboard.html',
                               stocks=stocks,
                               positions=positions,
                               stock_price_map=stock_price_map,
                               holdings_value=holdings_value,
                               net_worth=net_worth,
                               unrealized_pnl=unrealized_pnl,
                               recent_trades=recent_trades,
                               events=events,
                               active_tab='dashboard')

    @app.route('/trades')
    @login_required
    def trades():
        user_trades = Trade.query.filter_by(user_id=current_user.id).order_by(Trade.timestamp.desc()).all()
        return render_template('trades.html', trades=user_trades, active_tab='trades')

    @app.route('/journal')
    @login_required
    def journal():
        days = JournalDay.query.filter_by(user_id=current_user.id).order_by(JournalDay.date_str.desc()).all()
        today_str = date.today().strftime('%Y-%m-%d')
        today_journal = JournalDay.query.filter_by(user_id=current_user.id, date_str=today_str).first()
        today_trades = Trade.query.filter(
            Trade.user_id == current_user.id,
            Trade.timestamp >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        ).all()

        return render_template('journal.html',
                               days=days,
                               today_journal=today_journal,
                               today_trades=today_trades,
                               today_str=today_str,
                               active_tab='journal')

    @app.route('/behavioral-lab')
    @app.route('/behavioral_lab')
    @login_required
    def behavioral_lab():
        all_trades = Trade.query.filter_by(user_id=current_user.id).all()
        engine = BehavioralEngine(all_trades, current_user.starting_cash)
        profile = engine.analyze()
        return render_template('behavioral_lab.html', profile=profile, active_tab='behavioral_lab')

    @app.route('/playbooks')
    @login_required
    def playbooks():
        all_trades = Trade.query.filter_by(user_id=current_user.id).all()
        engine = BehavioralEngine(all_trades, current_user.starting_cash)
        profile = engine.analyze()
        return render_template('playbooks.html', profile=profile, active_tab='playbooks')

    @app.route('/progress-tracker')
    @app.route('/progress_tracker')
    @login_required
    def progress_tracker():

        all_trades = Trade.query.filter_by(user_id=current_user.id).all()
        engine = BehavioralEngine(all_trades, current_user.starting_cash)
        profile = engine.analyze()
        
        # Portfolio value
        stocks = Stock.query.all()
        stock_price_map = {s.symbol: s.price for s in stocks}
        positions = Position.query.filter_by(user_id=current_user.id).all()
        holdings_value = sum(p.qty * stock_price_map.get(p.symbol, p.avg_price) for p in positions)
        net_worth = current_user.cash_balance + holdings_value
        all_time_pnl = net_worth - current_user.starting_cash
        all_time_pnl_pct = (all_time_pnl / current_user.starting_cash * 100) if current_user.starting_cash > 0 else 0

        return render_template('progress_tracker.html',
                               profile=profile,
                               net_worth=net_worth,
                               all_time_pnl=all_time_pnl,
                               all_time_pnl_pct=all_time_pnl_pct,
                               active_tab='progress_tracker')

    @app.route('/news')
    @login_required
    def news():
        events = EconomicEvent.query.order_by(EconomicEvent.id.asc()).all()
        return render_template('news_calendar.html', events=events, active_tab='news')

    @app.route('/settings')
    @login_required
    def settings():
        return render_template('settings.html', active_tab='settings')

    # ------------------ API & REAL-TIME ENDPOINTS ------------------

    @app.route('/api/market/ticks')
    def get_market_ticks():
        """Fast 1-second polling endpoint returning live market tick data."""
        stocks = Stock.query.all()
        return jsonify({
            'timestamp': int(time.time()),
            'stocks': [s.to_dict() for s in stocks],
            'news': market_sim.last_news,
            'shock': market_sim.active_shock
        })

    @app.route('/api/stream/market')
    def stream_market():
        """SSE stream broadcasting 1-second price ticks and news headlines."""
        def event_stream():
            while True:
                stocks = Stock.query.all()
                stocks_data = [s.to_dict() for s in stocks]
                data = {
                    'timestamp': int(time.time()),
                    'stocks': stocks_data,
                    'news': market_sim.last_news,
                    'shock': market_sim.active_shock
                }
                yield f"data: {json.dumps(data)}\n\n"
                time.sleep(1.0)

        response = Response(event_stream(), mimetype="text/event-stream")
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        return response

    @app.route('/api/candles/<symbol>')
    def get_candles(symbol):
        """Returns raw 1-second OHLCV candles. JS side aggregates to chosen timeframe."""
        sym = symbol.upper()
        # Fetch last 7200 candles (2 hours of 1-second data)
        candles = (Candle.query
                   .filter_by(symbol=sym)
                   .order_by(Candle.timestamp.desc())
                   .limit(7200)
                   .all())
        candles = list(reversed(candles))  # ascending time order

        if candles:
            return jsonify([c.to_dict() for c in candles])

        # Fallback: generate synthetic history in-memory (first launch, no DB candles yet)
        now_ts = int(time.time())
        stock  = Stock.query.filter_by(symbol=sym).first()
        base_p = stock.price if stock else 100.0
        vol    = stock.volatility if stock else 0.03
        import random, math
        data = []
        mom  = 0.0
        for i in range(7200, 0, -1):
            if random.random() < 0.015:
                mom = random.choice([-1, 1]) * random.uniform(0.0002, 0.001)
            delta = mom * base_p + random.gauss(0, vol * 0.035 * base_p)
            o = round(base_p, 2)
            c = round(max(0.50, base_p + delta), 2)
            h = round(max(o, c) + abs(random.gauss(0, vol * 0.015 * base_p)), 2)
            l = round(min(o, c) - abs(random.gauss(0, vol * 0.015 * base_p)), 2)
            data.append({'time': now_ts - i, 'open': o, 'high': h, 'low': l, 'close': c, 'volume': random.randint(40, 400)})
            base_p = float(c)
        return jsonify(data)




    @app.route('/api/trade/order', methods=['POST'])
    @login_required
    def place_order():
        """Places a BUY or SELL order with instant risk checks."""
        data = request.get_json() or {}
        symbol = data.get('symbol', '').upper()
        side = data.get('side', 'BUY').upper()
        qty = int(data.get('qty', 0))

        if qty <= 0 or not symbol:
            return jsonify({'success': False, 'message': 'Invalid order parameters'}), 400

        stock = Stock.query.get(symbol)
        if not stock:
            return jsonify({'success': False, 'message': 'Stock symbol not found'}), 404

        price = stock.price
        total_cost = price * qty

        now_ts = int(time.time())
        realized_pnl = 0.0
        realized_pnl_pct = 0.0
        holding_sec = 0

        if side == 'BUY':
            if current_user.cash_balance < total_cost:
                return jsonify({'success': False, 'message': f'Insufficient cash. Required: ${total_cost:,.2f}'}), 400

            current_user.cash_balance -= total_cost
            pos = Position.query.filter_by(user_id=current_user.id, symbol=symbol).first()
            if pos:
                new_qty = pos.qty + qty
                pos.avg_price = ((pos.qty * pos.avg_price) + total_cost) / new_qty
                pos.qty = new_qty
                pos.updated_at = datetime.utcnow()
            else:
                pos = Position(user_id=current_user.id, symbol=symbol, qty=qty, avg_price=price)
                db.session.add(pos)

        elif side == 'SELL':
            pos = Position.query.filter_by(user_id=current_user.id, symbol=symbol).first()
            if not pos or pos.qty < qty:
                return jsonify({'success': False, 'message': f'Insufficient position to sell. Open: {pos.qty if pos else 0}'}), 400

            # Calculate realized P&L
            cost_basis = pos.avg_price * qty
            proceeds = price * qty
            realized_pnl = proceeds - cost_basis
            realized_pnl_pct = (realized_pnl / cost_basis * 100) if cost_basis > 0 else 0
            
            # Approximate holding duration from position updated_at
            if pos.updated_at:
                holding_sec = max(1, int((datetime.utcnow() - pos.updated_at).total_seconds()))

            current_user.cash_balance += proceeds
            pos.qty -= qty
            if pos.qty == 0:
                db.session.delete(pos)
            else:
                pos.updated_at = datetime.utcnow()

        # Record trade
        trade = Trade(
            user_id=current_user.id,
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            timestamp=datetime.utcnow(),
            unix_time=now_ts,
            realized_pnl=realized_pnl,
            realized_pnl_pct=realized_pnl_pct,
            holding_seconds=holding_sec,
            setup_tag=data.get('setup_tag', 'Discretionary'),
            emotion_tag=data.get('emotion_tag', 'Calm'),
            confidence=int(data.get('confidence', 3)),
            target_price=float(data.get('target_price')) if data.get('target_price') else None,
            stop_loss_price=float(data.get('stop_loss_price')) if data.get('stop_loss_price') else None,
            notes=data.get('notes', '')
        )
        db.session.add(trade)

        # Update JournalDay for today
        today_str = date.today().strftime('%Y-%m-%d')
        j_day = JournalDay.query.filter_by(user_id=current_user.id, date_str=today_str).first()
        if not j_day:
            j_day = JournalDay(user_id=current_user.id, date_str=today_str, daily_pnl=0.0, trade_count=0, win_count=0, loss_count=0)
            db.session.add(j_day)

        j_day.trade_count += 1
        j_day.daily_pnl += realized_pnl
        if realized_pnl > 0:
            j_day.win_count += 1
        elif realized_pnl < 0:
            j_day.loss_count += 1

        db.session.commit()

        # Query current open positions for user
        user_positions = Position.query.filter_by(user_id=current_user.id).all()
        pos_list = []
        for p in user_positions:
            stk = Stock.query.get(p.symbol)
            c_price = stk.price if stk else p.avg_price
            pnl = (c_price - p.avg_price) * p.qty
            pnl_pct = ((c_price - p.avg_price) / p.avg_price * 100) if p.avg_price > 0 else 0
            pos_list.append({
                'symbol': p.symbol,
                'qty': p.qty,
                'avg_price': round(p.avg_price, 2),
                'current_price': round(c_price, 2),
                'pnl': round(pnl, 2),
                'pnl_pct': round(pnl_pct, 2)
            })

        return jsonify({
            'success': True,
            'message': f'Successfully executed {side} {qty} {symbol} @ ${price:,.2f}',
            'trade_id': trade.id,
            'cash_balance': round(current_user.cash_balance, 2),
            'positions': pos_list
        })

    @app.route('/api/positions')
    @login_required
    def get_positions():
        """Returns all open positions with real-time trailing P&L."""
        user_positions = Position.query.filter_by(user_id=current_user.id).all()
        pos_list = []
        for p in user_positions:
            stk = Stock.query.get(p.symbol)
            c_price = stk.price if stk else p.avg_price
            pnl = (c_price - p.avg_price) * p.qty
            pnl_pct = ((c_price - p.avg_price) / p.avg_price * 100) if p.avg_price > 0 else 0
            pos_list.append({
                'symbol': p.symbol,
                'qty': p.qty,
                'avg_price': round(p.avg_price, 2),
                'current_price': round(c_price, 2),
                'pnl': round(pnl, 2),
                'pnl_pct': round(pnl_pct, 2)
            })
        return jsonify({'positions': pos_list, 'cash_balance': round(current_user.cash_balance, 2)})


    @app.route('/api/trade/journal/<int:trade_id>', methods=['POST'])
    @login_required
    def update_trade_journal(trade_id):
        """Saves instant 3-click post-trade tags and notes."""
        trade = Trade.query.filter_by(id=trade_id, user_id=current_user.id).first_or_404()
        data = request.get_json() or {}
        
        trade.setup_tag = data.get('setup_tag', trade.setup_tag)
        trade.emotion_tag = data.get('emotion_tag', trade.emotion_tag)
        trade.confidence = int(data.get('confidence', trade.confidence))
        trade.target_price = float(data.get('target_price')) if data.get('target_price') else trade.target_price
        trade.stop_loss_price = float(data.get('stop_loss_price')) if data.get('stop_loss_price') else trade.stop_loss_price
        trade.notes = data.get('notes', trade.notes)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Journal entry recorded successfully.'})

    @app.route('/api/journal/day/<date_str>')
    @login_required
    def get_journal_day(date_str):
        """Returns details for a specific date's journal and trades."""
        j_day = JournalDay.query.filter_by(user_id=current_user.id, date_str=date_str).first()
        all_user_trades = Trade.query.filter_by(user_id=current_user.id).all()
        matching_trades = [t.to_dict() for t in all_user_trades if t.timestamp and t.timestamp.strftime('%Y-%m-%d') == date_str]
        
        daily_pnl = j_day.daily_pnl if j_day else sum(t['realized_pnl'] for t in matching_trades)
        trade_count = j_day.trade_count if j_day else len(matching_trades)
        win_count = j_day.win_count if j_day else len([t for t in matching_trades if t['realized_pnl'] > 0])
        reflection_note = j_day.reflection_note if j_day else ''
        
        feedback = None
        if j_day and j_day.ai_feedback:
            try:
                feedback = json.loads(j_day.ai_feedback)
            except Exception:
                feedback = j_day.ai_feedback

        return jsonify({
            'date_str': date_str,
            'daily_pnl': round(daily_pnl, 2),
            'trade_count': trade_count,
            'win_count': win_count,
            'reflection_note': reflection_note,
            'ai_feedback': feedback,
            'trades': matching_trades
        })

    @app.route('/api/journal/save_day', methods=['POST'])
    @login_required
    def save_journal_day():
        data = request.get_json() or {}
        date_str = data.get('date_str', date.today().strftime('%Y-%m-%d'))
        note = data.get('reflection_note', '')

        j_day = JournalDay.query.filter_by(user_id=current_user.id, date_str=date_str).first()
        if not j_day:
            j_day = JournalDay(user_id=current_user.id, date_str=date_str)
            db.session.add(j_day)
        
        j_day.reflection_note = note
        if 'trade_count' in data:
            j_day.trade_count = int(data['trade_count'])
        if 'win_count' in data:
            j_day.win_count = int(data['win_count'])
        if 'daily_pnl' in data:
            j_day.daily_pnl = float(data['daily_pnl'])

        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Daily reflection saved.',
            'date_str': date_str,
            'daily_pnl': round(j_day.daily_pnl, 2),
            'trade_count': j_day.trade_count,
            'win_count': j_day.win_count
        })

    @app.route('/api/ai/review_day', methods=['POST'])
    @login_required
    def ai_review_day():
        """On-demand AI Assistant review of a specific trading day."""
        data = request.get_json() or {}
        date_str = data.get('date_str', date.today().strftime('%Y-%m-%d'))
        
        j_day = JournalDay.query.filter_by(user_id=current_user.id, date_str=date_str).first()
        if not j_day:
            j_day = JournalDay(user_id=current_user.id, date_str=date_str, daily_pnl=0.0, trade_count=0)
            db.session.add(j_day)
        
        if 'reflection_note' in data and data['reflection_note']:
            j_day.reflection_note = data['reflection_note']
        if 'trade_count' in data:
            j_day.trade_count = int(data['trade_count'])
        if 'win_count' in data:
            j_day.win_count = int(data['win_count'])
        if 'daily_pnl' in data:
            j_day.daily_pnl = float(data['daily_pnl'])

        db.session.commit()

        # Fetch trades for that day
        day_trades = Trade.query.filter(Trade.user_id == current_user.id).all()
        matching_trades = [t for t in day_trades if t.timestamp and t.timestamp.strftime('%Y-%m-%d') == date_str]

        feedback = ai_coach.review_daily_journal(j_day, matching_trades)
        j_day.ai_feedback = json.dumps(feedback)
        db.session.commit()

        return jsonify({'success': True, 'feedback': feedback})


    @app.route('/api/ai/diagnose_profile', methods=['POST'])
    @login_required
    def ai_diagnose_profile():
        """On-demand AI psychological profile analysis for Behavioral Lab."""
        all_trades = Trade.query.filter_by(user_id=current_user.id).all()
        engine = BehavioralEngine(all_trades, current_user.starting_cash)
        profile = engine.analyze()
        
        journal_entries = JournalDay.query.filter_by(user_id=current_user.id).all()
        diagnosis = ai_coach.diagnose_trader_profile(profile, all_trades, journal_entries)
        
        return jsonify({'success': True, 'diagnosis': diagnosis, 'profile': profile})

    @app.route('/api/progress/update_risk', methods=['POST'])
    @login_required
    def update_risk_settings():
        """Updates Starting Cash, Max Daily Loss, and Risk % inside Progress Tracker."""
        data = request.get_json() or {}
        if 'starting_cash' in data:
            current_user.starting_cash = float(data['starting_cash'])
        if 'daily_max_loss' in data:
            current_user.daily_max_loss = float(data['daily_max_loss'])
        if 'max_risk_per_trade_pct' in data:
            current_user.max_risk_per_trade_pct = float(data['max_risk_per_trade_pct'])
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Risk limits and capital settings saved.'})

    @app.route('/api/settings/update_emails', methods=['POST'])
    @login_required
    def update_secondary_emails():
        """Manage and add secondary emails in Settings."""
        data = request.get_json() or {}
        emails = data.get('secondary_emails', '').strip()
        current_user.secondary_emails = emails
        db.session.commit()
        return jsonify({'success': True, 'message': 'Email preferences updated.'})

    @app.route('/api/export/tableau.csv')
    @login_required
    def export_tableau_csv():
        """Generates downloadable Tableau dataset."""
        trades = Trade.query.filter_by(user_id=current_user.id).order_by(Trade.timestamp.asc()).all()
        csv_content = TableauExporter.export_csv(trades)
        
        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=tradex_tableau_dataset.csv"}
        )

    @app.route('/api/news/shock', methods=['POST'])
    @login_required
    def trigger_shock():
        """Simulate news shock event from News Calendar."""
        data = request.get_json() or {}
        headline = data.get('headline', '🔴 Market Shock Event Triggered!')
        factor = float(data.get('factor', 1.5))
        market_sim.trigger_news_shock(headline, factor)
        return jsonify({'success': True, 'message': f'News shock initiated: {headline}'})

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='127.0.0.1', port=5000, debug=True)
