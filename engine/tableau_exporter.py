import io
import csv
import pandas as pd

class TableauExporter:
    @staticmethod
    def export_csv(trades):
        """Generates a clean CSV file string formatted for Tableau / PowerBI / Excel."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers tailored for financial & psychological visualization
        headers = [
            "Trade_ID",
            "Timestamp",
            "Date",
            "Time",
            "Symbol",
            "Side",
            "Quantity",
            "Execution_Price",
            "Realized_PnL",
            "Realized_PnL_Pct",
            "Win_Loss_Flag",
            "Holding_Duration_Seconds",
            "Holding_Duration_Minutes",
            "Setup_Tag",
            "Emotion_Tag",
            "Confidence_Rating",
            "Followed_Plan_Flag",
            "Target_Price",
            "Stop_Loss_Price",
            "MAE_Dollars",
            "MFE_Dollars",
            "Notes"
        ]
        writer.writerow(headers)

        for t in trades:
            ts_str = t.timestamp.strftime('%Y-%m-%d %H:%M:%S') if t.timestamp else ""
            date_str = t.timestamp.strftime('%Y-%m-%d') if t.timestamp else ""
            time_str = t.timestamp.strftime('%H:%M:%S') if t.timestamp else ""
            win_flag = "WIN" if t.realized_pnl > 0 else ("LOSS" if t.realized_pnl < 0 else "BE")
            hold_min = round(t.holding_seconds / 60.0, 2) if t.holding_seconds else 0.0

            writer.writerow([
                t.id,
                ts_str,
                date_str,
                time_str,
                t.symbol,
                t.side,
                t.qty,
                round(t.price, 2),
                round(t.realized_pnl, 2),
                round(t.realized_pnl_pct, 2),
                win_flag,
                t.holding_seconds,
                hold_min,
                t.setup_tag or "Discretionary",
                t.emotion_tag or "Calm",
                t.confidence or 3,
                1 if t.followed_plan else 0,
                round(t.target_price, 2) if t.target_price else "",
                round(t.stop_loss_price, 2) if t.stop_loss_price else "",
                round(t.mae, 2) if t.mae else 0.0,
                round(t.mfe, 2) if t.mfe else 0.0,
                t.notes or ""
            ])

        output.seek(0)
        return output.getvalue()
