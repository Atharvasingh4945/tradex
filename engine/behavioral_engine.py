import pandas as pd
import numpy as np
from datetime import datetime

class BehavioralEngine:
    def __init__(self, trades, starting_cash=100000.0):
        self.trades = trades
        self.starting_cash = starting_cash

    def analyze(self):
        """Processes trade log and computes deep psychological behavioral metrics."""
        if not self.trades or len(self.trades) == 0:
            return self._empty_profile()

        # Convert to DataFrame
        data = []
        for t in self.trades:
            data.append({
                'id': t.id,
                'symbol': t.symbol,
                'side': t.side,
                'qty': t.qty,
                'price': t.price,
                'timestamp': t.timestamp,
                'unix_time': t.unix_time,
                'realized_pnl': t.realized_pnl,
                'realized_pnl_pct': t.realized_pnl_pct,
                'holding_seconds': t.holding_seconds,
                'setup_tag': t.setup_tag or 'Discretionary',
                'emotion_tag': t.emotion_tag or 'Calm',
                'confidence': t.confidence or 3,
                'target_price': t.target_price,
                'stop_loss_price': t.stop_loss_price,
                'notes': t.notes or '',
                'followed_plan': t.followed_plan
            })

        df = pd.DataFrame(data)
        
        # Core performance stats
        total_trades = len(df)
        closed_trades = df[df['realized_pnl'] != 0.0]
        
        wins = closed_trades[closed_trades['realized_pnl'] > 0]
        losses = closed_trades[closed_trades['realized_pnl'] < 0]
        
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / len(closed_trades) * 100) if len(closed_trades) > 0 else 0.0
        
        total_realized_pnl = float(df['realized_pnl'].sum())
        gross_profit = float(wins['realized_pnl'].sum()) if win_count > 0 else 0.0
        gross_loss = abs(float(losses['realized_pnl'].sum())) if loss_count > 0 else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 1.0)
        
        avg_win = float(wins['realized_pnl'].mean()) if win_count > 0 else 0.0
        avg_loss = abs(float(losses['realized_pnl'].mean())) if loss_count > 0 else 0.0
        risk_reward_ratio = (avg_win / avg_loss) if avg_loss > 0 else (1.0 if avg_win > 0 else 0.0)

        # 1. FOMO Score (0 to 100)
        # Based on FOMO emotion tags + buying at extreme rallies
        fomo_tags = df[df['emotion_tag'].str.contains('FOMO|Hype|Excited', case=False, na=False)]
        fomo_tag_ratio = len(fomo_tags) / total_trades
        fomo_score = min(100, int(fomo_tag_ratio * 70 + (30 if win_rate < 40 and total_trades > 3 else 10)))

        # 2. Disposition Effect (Holding winners too short, holding losers too long)
        avg_win_hold = float(wins['holding_seconds'].mean()) if win_count > 0 else 30.0
        avg_loss_hold = float(losses['holding_seconds'].mean()) if loss_count > 0 else 30.0
        
        if avg_win_hold > 0:
            disposition_ratio = avg_loss_hold / avg_win_hold
        else:
            disposition_ratio = 1.0
        
        # Normalize disposition score (0 to 100, >50 means severe reluctance to cut losses)
        disposition_score = min(100, int(max(0, (disposition_ratio - 0.5) * 35)))

        # 3. Revenge / Tilt Meter
        # Checks if trades were executed within 60 seconds of a losing trade
        df_sorted = df.sort_values('unix_time').reset_index(drop=True)
        revenge_count = 0
        for i in range(1, len(df_sorted)):
            prev = df_sorted.iloc[i - 1]
            curr = df_sorted.iloc[i]
            time_diff = curr['unix_time'] - prev['unix_time']
            if prev['realized_pnl'] < 0 and time_diff < 90:
                revenge_count += 1
        
        revenge_rate = revenge_count / total_trades if total_trades > 0 else 0
        tilt_score = min(100, int(revenge_rate * 150))

        # 4. Plan Adherence
        followed_count = int(df['followed_plan'].sum())
        discipline_score = int(followed_count / total_trades * 100) if total_trades > 0 else 100

        # Breakdown by Setup
        setup_stats = []
        for setup, group in df.groupby('setup_tag'):
            c_group = group[group['realized_pnl'] != 0.0]
            s_wins = len(c_group[c_group['realized_pnl'] > 0])
            s_total = len(group)
            s_pnl = float(group['realized_pnl'].sum())
            s_wr = (s_wins / len(c_group) * 100) if len(c_group) > 0 else 0.0
            setup_stats.append({
                'setup': setup,
                'trades': s_total,
                'win_rate': round(s_wr, 1),
                'pnl': round(s_pnl, 2)
            })

        # Breakdown by Emotion
        emotion_stats = []
        for emotion, group in df.groupby('emotion_tag'):
            c_group = group[group['realized_pnl'] != 0.0]
            e_wins = len(c_group[c_group['realized_pnl'] > 0])
            e_total = len(group)
            e_pnl = float(group['realized_pnl'].sum())
            e_wr = (e_wins / len(c_group) * 100) if len(c_group) > 0 else 0.0
            emotion_stats.append({
                'emotion': emotion,
                'trades': e_total,
                'win_rate': round(e_wr, 1),
                'pnl': round(e_pnl, 2)
            })

        # Determine Trader Archetype
        archetype, archetype_desc, mistakes, prescriptions = self._classify_archetype(
            win_rate, fomo_score, disposition_score, tilt_score, discipline_score, disposition_ratio, setup_stats, emotion_stats
        )

        return {
            'total_trades': total_trades,
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': round(win_rate, 1),
            'total_realized_pnl': round(total_realized_pnl, 2),
            'profit_factor': round(profit_factor, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'risk_reward_ratio': round(risk_reward_ratio, 2),
            'avg_win_hold': round(avg_win_hold, 1),
            'avg_loss_hold': round(avg_loss_hold, 1),
            'fomo_score': fomo_score,
            'disposition_score': disposition_score,
            'tilt_score': tilt_score,
            'discipline_score': discipline_score,
            'archetype': archetype,
            'archetype_description': archetype_desc,
            'core_mistakes': mistakes,
            'prescriptions': prescriptions,
            'setup_stats': setup_stats,
            'emotion_stats': emotion_stats
        }

    def _classify_archetype(self, win_rate, fomo, disposition, tilt, discipline, disp_ratio, setups, emotions):
        """Classifies the psychological archetype and diagnoses specific errors."""
        mistakes = []
        prescriptions = []

        if fomo >= 50:
            mistakes.append("Chasing momentum at the peak of green candles (FOMO entry).")
            prescriptions.append("Wait for pullbacks to support / VWAP before executing entries.")
        
        if disposition >= 50 or disp_ratio > 2.0:
            mistakes.append(f"Holding losing trades {round(disp_ratio, 1)}x longer than winning trades (Disposition bias).")
            prescriptions.append("Set a hard stop-loss upon entry and exit immediately when invalidated.")

        if tilt >= 40:
            mistakes.append("Revenge trading rapidly after taking a loss.")
            prescriptions.append("Enforce a mandatory 3-minute cooldown timer after every red trade.")

        if discipline < 70:
            mistakes.append("Failing to follow defined exit and target rules.")
            prescriptions.append("Only take trades where risk/reward is at least 1:2 and predetermined.")

        # Default advice if clean
        if not mistakes:
            mistakes.append("Occasional hesitation on planned setups.")
            prescriptions.append("Keep maintaining disciplined position sizing and risk management.")

        # Determine Title
        if fomo > 55:
            archetype = "The FOMO Chaser"
            desc = "You are drawn to rapid price surges and often buy near candle peaks. You enter out of fear of missing out rather than following structured setups."
        elif disposition > 55 or disp_ratio > 2.5:
            archetype = "The Reluctant Loss-Cutter"
            desc = "You take quick profits on winning trades to feel good, but hold losing positions hoping they will recover to break-even, risking severe drawdowns."
        elif tilt > 45:
            archetype = "The Revenge Gambler"
            desc = "You take losses personally. When a trade goes red, your immediate instinct is to fire off another trade to make the money back immediately."
        elif win_rate >= 60 and discipline >= 75:
            archetype = "The Disciplined Sniper"
            desc = "You execute with high patience, respect your invalidation levels, and balance risk/reward systematically."
        elif win_rate < 45:
            archetype = "The Inconsistent Scalper"
            desc = "You flip positions frequently without strong conviction, causing commissions and slippage to erode your equity curve."
        else:
            archetype = "The Developing Systematic Trader"
            desc = "You have solid foundational instincts but need to sharpen your emotional discipline and trade execution consistency."

        return archetype, desc, mistakes, prescriptions

    def _empty_profile(self):
        return {
            'total_trades': 0,
            'win_count': 0,
            'loss_count': 0,
            'win_rate': 0.0,
            'total_realized_pnl': 0.0,
            'profit_factor': 1.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'risk_reward_ratio': 1.0,
            'avg_win_hold': 0.0,
            'avg_loss_hold': 0.0,
            'fomo_score': 0,
            'disposition_score': 0,
            'tilt_score': 0,
            'discipline_score': 100,
            'archetype': "New Trader",
            'archetype_description': "Execute your first few trades and journal your thoughts to unlock your AI Behavioral Profile.",
            'core_mistakes': ["No trade history yet."],
            'prescriptions': ["Place your first trade on the Dashboard and capture your emotional thesis in the journal."],
            'setup_stats': [],
            'emotion_stats': []
        }
