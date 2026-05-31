"""Print the paper-trading scorecard.  Usage:  python paper_report.py"""
import paper_log


def main():
    s = paper_log.stats()
    print("\n===== PAPER-TRADING SCORECARD =====")
    for k, v in s.items():
        print(f"  {k.replace('_', ' '):28s}: {v}")
    if s["closed"] == 0:
        print("\n  No closed paper trades yet. Let the pipeline run during market hours.")
    else:
        verdict = ("edge looks positive" if s["expectancy_per_trade_rs"] > 0
                   else "no edge yet — DO NOT go live")
        print(f"\n  Verdict: {verdict}.")
        print("  Rule of thumb: want 30+ closed trades and positive expectancy before risking real money.")


if __name__ == "__main__":
    main()
