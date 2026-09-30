# PropSafe_Breakout.mq5

A prop-firm-safe MetaTrader 5 Expert Advisor: session-range breakout (default London 07:00-09:00 server time),
H1 EMA trend filter, ATR stop, 2R target, trailing after 1R, one trade per symbol per day.

Hard guards: daily loss cap (default 4%, below the usual 5% firm limit), total drawdown cap (8% vs 10%),
profit-target halt, max concurrent positions, Friday flat, optional time blackout, sizing that cannot
breach the daily cap on its own, refuses to run on a non-demo account unless in the Strategy Tester.

Install: copy to MQL5\Experts\, compile in MetaEditor (F7), attach to XAUUSD or EURUSD M15.
Test: Strategy Tester, "Every tick based on real ticks", 2020-01-01 to today, $10,000, then a separate run
on the last 3 months as out-of-sample. Check the daily-loss and drawdown lines never cross the caps.

No edge is claimed. It is the shell you bolt a validated signal into; the default breakout is a baseline.
Written without a compiler available; if MetaEditor reports an error, send me the line.
