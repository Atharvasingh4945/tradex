import os
import json
import re

class AICoach:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

    def review_daily_journal(self, journal_day, trades):
        """On-demand daily session debrief analyzing trade execution stats AND written journal notes."""
        date_str = journal_day.date_str
        pnl = journal_day.daily_pnl or 0.0
        trade_count = journal_day.trade_count or len(trades)
        win_count = journal_day.win_count or 0
        loss_count = journal_day.loss_count if hasattr(journal_day, 'loss_count') and journal_day.loss_count else max(0, trade_count - win_count)
        note = (journal_day.reflection_note or "").strip()
        note_lower = note.lower()

        # Keyword Sentiment & Setup Analysis from written journal text
        has_loss_text = any(k in note_lower for k in ["loss", "lost", "losing", "drawdown", "red", "minus", "negative"])
        has_reversal_text = any(k in note_lower for k in ["reversal", "reversed", "dumped", "top", "bottom", "turnaround"])
        has_fomo_text = any(k in note_lower for k in ["fomo", "chase", "chased", "impulse", "late", "rushed", "greed", "tilt", "revenge"])
        has_discipline_text = any(k in note_lower for k in ["followed plan", "disciplined", "patient", "stop loss hit", "good risk", "calm"])

        # Breakdown emotions from SQL trade objects
        emotions = [t.emotion_tag for t in trades if getattr(t, 'emotion_tag', None)]
        fomo_trades = [t for t in trades if "FOMO" in (getattr(t, 'emotion_tag', '') or "")]
        planned_trades = [t for t in trades if "Calm" in (getattr(t, 'emotion_tag', '') or "")]
        
        dominant_emotion = max(set(emotions), key=emotions.count) if emotions else ("Frustrated" if (has_loss_text or has_fomo_text) else "Neutral")
        win_rate = (win_count / trade_count * 100) if trade_count > 0 else 0

        # Determine overall session sentiment
        is_truly_green = (pnl > 0) and not (has_loss_text and pnl == 0)
        is_reversal_loss = has_reversal_text or (pnl < 0 and "reversal" in note_lower)

        if is_reversal_loss:
          status = "Reversal Loss Session 🔴"
        elif pnl < 0 or has_loss_text:
          status = "Red Day / Drawdown 🔴"
        elif is_truly_green:
          status = "Green Day 🟢"
        else:
          status = "Journaled Session 📝"

        # Construct structured feedback
        feedback = {
            "session_date": date_str,
            "status": status,
            "pnl": f"${pnl:,.2f}",
            "win_rate": f"{win_rate:.1f}% ({win_count}W / {loss_count}L)",
            "emotional_summary": "",
            "what_went_well": [],
            "areas_to_improve": [],
            "coach_prescription": ""
        }

        # Build Emotional Summary
        if note:
            feedback["emotional_summary"] = f"Journal Note: \"{note}\". Primary emotion detected: '{dominant_emotion}'."
        else:
            feedback["emotional_summary"] = f"Your dominant emotion was '{dominant_emotion}'. Logged {trade_count} trades."

        # Analyze "What Went Well"
        if note:
            feedback["what_went_well"].append("High psychological awareness: You logged a written debrief capturing your mindset.")
        if is_truly_green:
            feedback["what_went_well"].append(f"Successfully locked in ${pnl:,.2f} net profit.")
        if has_discipline_text:
            feedback["what_went_well"].append("Demonstrated risk discipline: Followed stop-loss and risk rules.")

        # Analyze "Areas to Improve"
        if has_reversal_text:
            feedback["areas_to_improve"].append("Reversal Risk: Entering positions into an opposing trend reversal without waiting for price confirmation.")
        if has_fomo_text or len(fomo_trades) > 0:
            feedback["areas_to_improve"].append("FOMO / Impulse Risk: Buying extended candles near local highs instead of waiting for a 9/21 EMA pullback.")
        if pnl < 0 or has_loss_text:
            feedback["areas_to_improve"].append(f"Closed session in a drawdown ({feedback['pnl']}). Review if position sizing exceeded your max risk limit.")

        # Ensure at least 1 point in both lists
        if not feedback["what_went_well"]:
            feedback["what_went_well"].append("Completed session logging: Documenting trade reflections is the key to long-term consistency.")

        if not feedback["areas_to_improve"]:
            feedback["areas_to_improve"].append("Maintain risk consistency: Ensure every entry has a pre-calculated stop-loss.")

        # Generate Actionable Coach Prescription
        if has_reversal_text:
            feedback["coach_prescription"] = "Reversals happen when market momentum exhausts. To avoid reversal traps: 1) Wait for a lower-high / higher-low confirmation before entering, 2) Set a hard stop-loss immediately, and 3) Do not double down on a losing position."
        elif has_fomo_text:
            feedback["coach_prescription"] = "FOMO causes traders to buy the top. Before taking your next trade, ask: 'Is price near support/EMA, or am I chasing a green candle?' If chasing, step away for 3 minutes."
        elif pnl < 0 or has_loss_text:
            feedback["coach_prescription"] = "Red days are an inevitable cost of doing business in trading. Do not hold frustration overnight. Protect your capital and adhere strictly to your maximum daily risk limit tomorrow."
        else:
            feedback["coach_prescription"] = "Solid session journaling. Protect your account capital, stick to your playbook setups, and avoid overconfidence."

        return feedback

    def diagnose_trader_profile(self, behavioral_profile, all_trades, journal_entries):
        """Comprehensive on-demand psychological analysis for Behavioral Lab."""
        archetype = behavioral_profile.get('archetype', 'Developing Systematic Trader')
        fomo = behavioral_profile.get('fomo_score', 0)
        disposition = behavioral_profile.get('disposition_score', 0)
        tilt = behavioral_profile.get('tilt_score', 0)
        discipline = behavioral_profile.get('discipline_score', 100)
        win_rate = behavioral_profile.get('win_rate', 0.0)

        dos = []
        donts = []

        if disposition > 40:
            dos.append("🟢 DO: Set automatic stop-loss orders immediately upon entry to prevent holding losers.")
        else:
            dos.append("🟢 DO: Let winning trades run toward your predetermined take-profit targets.")

        if fomo > 40:
            dos.append("🟢 DO: Wait for price to pull back to the 9/21 EMA or key support before executing.")
        else:
            dos.append("🟢 DO: Stick to your designated Playbook setups (e.g. Dip Buy at Support).")

        dos.append("🟢 DO: Cap maximum daily loss to protect your account capital.")

        if tilt > 30:
            donts.append("🔴 DON'T: Place a new order within 3 minutes of a realized loss (Prevent Revenge Trading).")
        else:
            donts.append("🔴 DON'T: Increase position size after a loss to try and 'break even'.")

        if fomo > 40:
            donts.append("🔴 DON'T: Buy a stock that has formed 3 consecutive large green candles.")
        else:
            donts.append("🔴 DON'T: Enter trades out of boredom or without a clear invalidation level.")

        donts.append("🔴 DON'T: Risk more than 2% of your net worth on any single discretionary trade.")

        analysis_text = f"Based on your trading history and journal entries, your primary trading archetype is **{archetype}** with a discipline score of **{discipline}/100** and a win-rate of **{win_rate}%**."

        return {
            "archetype": archetype,
            "description": behavioral_profile.get('archetype_description', ''),
            "analysis_text": analysis_text,
            "dos": dos,
            "donts": donts,
            "core_mistakes": behavioral_profile.get('core_mistakes', []),
            "prescriptions": behavioral_profile.get('prescriptions', [])
        }
