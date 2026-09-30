//+------------------------------------------------------------------+
//|                                          PropSafe_Breakout.mq5   |
//|  Prop-firm-safe session breakout EA with hard risk guards.       |
//|  Signal: London/NY session range breakout, H1 trend filter,      |
//|  ATR stop, R:R target, trailing.  Guards: daily loss cap, total  |
//|  drawdown cap, max positions, weekend flat, time blackout.       |
//|  DEMO / STRATEGY TESTER USE.  No edge is claimed; test it first. |
//+------------------------------------------------------------------+
#property copyright "Furtumatic-V2"
#property version   "1.00"
#property strict
#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\AccountInfo.mqh>

//---------------- inputs ----------------
input group "RISK (prop-firm rules)"
input double InpRiskPercent      = 0.5;    // Risk per trade, % of balance
input double InpDailyLossCap     = 4.0;    // Stop trading for the day at this % loss (firm limit usually 5)
input double InpTotalDDCap       = 8.0;    // Stop trading entirely at this % drawdown from initial balance (firm limit usually 10)
input double InpProfitTargetPct  = 10.0;   // Stop trading once account is up this % (evaluation passed)
input int    InpMaxPositions     = 2;      // Max concurrent positions across symbols
input bool   InpFlatBeforeWeekend= true;   // Close everything Friday before the cutoff
input int    InpFridayCloseHour  = 20;     // Server hour on Friday to go flat
input bool   InpDemoOnly         = true;   // Refuse to trade unless the account is a demo account

input group "SIGNAL"
input ENUM_TIMEFRAMES InpTF      = PERIOD_M15; // Entry timeframe
input int    InpRangeStartHour   = 7;      // Session range start (server time), e.g. 07:00
input int    InpRangeEndHour     = 9;      // Session range end, e.g. 09:00 (London open range)
input int    InpTradeUntilHour   = 16;     // No new entries after this hour
input int    InpATRPeriod        = 14;     // ATR period (entry TF)
input double InpStopATR          = 1.5;    // Stop distance in ATR
input double InpRewardRisk       = 2.0;    // Take profit as multiple of stop
input double InpMinRangeATR      = 0.5;    // Skip if session range < this many ATR (dead market)
input double InpMaxRangeATR      = 3.0;    // Skip if session range > this many ATR (already moved)
input bool   InpUseTrendFilter   = true;   // Only trade with the H1 EMA slope
input int    InpTrendEMA         = 50;     // H1 EMA period for the trend filter
input bool   InpUseTrailing      = true;   // Trail the stop after 1R
input double InpTrailATR         = 1.0;    // Trailing distance in ATR
input int    InpBlackoutStartMin = -1;     // Minute-of-day to start a no-trade window (-1 = off), e.g. 14*60+28 for 14:28
input int    InpBlackoutEndMin   = -1;     // Minute-of-day to end it, e.g. 14*60+35
input long   InpMagic            = 77001;  // Magic number

//---------------- globals ----------------
CTrade         trade;
CPositionInfo  pos;
CAccountInfo   acc;
int      hATR = INVALID_HANDLE, hEMA = INVALID_HANDLE;
double   initialBalance = 0.0;
double   dayStartEquity = 0.0;
datetime dayStamp = 0;
datetime lastBar = 0;
double   rangeHigh = 0, rangeLow = 0;
datetime rangeDay = 0;
bool     tradedToday = false;
bool     haltedForGood = false;

//---------------- helpers ----------------
bool IsDemo() { return AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_DEMO; }

datetime DayOf(datetime t) { return t - (t % 86400); }

void RollDay()
{
   datetime today = DayOf(TimeCurrent());
   if(today != dayStamp)
   {
      dayStamp = today;
      dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
      tradedToday = false;
      rangeDay = 0;
   }
}

// true when any risk guard says "no new trades"
bool RiskGuardsBlock(string &why)
{
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   if(haltedForGood) { why = "halted (total drawdown or target reached)"; return true; }
   if(initialBalance > 0)
   {
      double ddPct = 100.0 * (initialBalance - equity) / initialBalance;
      if(ddPct >= InpTotalDDCap) { haltedForGood = true; CloseAll("total drawdown cap"); why = "total drawdown cap hit"; return true; }
      double upPct = 100.0 * (balance - initialBalance) / initialBalance;
      if(upPct >= InpProfitTargetPct) { haltedForGood = true; CloseAll("profit target reached"); why = "profit target reached"; return true; }
   }
   if(dayStartEquity > 0)
   {
      double dayLossPct = 100.0 * (dayStartEquity - equity) / dayStartEquity;
      if(dayLossPct >= InpDailyLossCap) { CloseAll("daily loss cap"); why = "daily loss cap hit"; return true; }
   }
   return false;
}

int OpenPositionsAll()
{
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(pos.SelectByIndex(i) && pos.Magic() == InpMagic) n++;
   return n;
}

bool HavePositionOnSymbol()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(pos.SelectByIndex(i) && pos.Magic() == InpMagic && pos.Symbol() == _Symbol) return true;
   return false;
}

void CloseAll(string reason)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(pos.SelectByIndex(i) && pos.Magic() == InpMagic)
         trade.PositionClose(pos.Ticket());
   Print("PropSafe: closed all positions - ", reason);
}

double ATR()
{
   double b[1];
   if(CopyBuffer(hATR, 0, 1, 1, b) != 1) return 0.0;
   return b[0];
}

int TrendDir()   // +1 up, -1 down, 0 flat/unknown
{
   if(!InpUseTrendFilter) return 0;
   double e[3];
   if(CopyBuffer(hEMA, 0, 1, 3, e) != 3) return 0;
   if(e[2] > e[0]) return 1;
   if(e[2] < e[0]) return -1;
   return 0;
}

// lot size so that stopDist loss == risk% of balance, respecting broker limits
double LotsForRisk(double stopDist)
{
   double balance   = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskMoney = balance * InpRiskPercent / 100.0;
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   if(tickSize <= 0 || tickValue <= 0 || stopDist <= 0) return 0.0;
   double lossPerLot = stopDist / tickSize * tickValue;
   double lots = riskMoney / lossPerLot;
   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double step   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   lots = MathFloor(lots / step) * step;
   if(lots < minLot) return 0.0;        // refuse rather than over-risk with the minimum lot
   if(lots > maxLot) lots = maxLot;
   // also cap so that this trade alone cannot breach the daily cap
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double roomToday = dayStartEquity * InpDailyLossCap / 100.0 - (dayStartEquity - equity);
   if(roomToday <= 0) return 0.0;
   double maxLotsToday = MathFloor((roomToday / lossPerLot) / step) * step;
   if(lots > maxLotsToday) lots = maxLotsToday;
   if(lots < minLot) return 0.0;
   return lots;
}

bool InBlackout()
{
   if(InpBlackoutStartMin < 0 || InpBlackoutEndMin < 0) return false;
   MqlDateTime t; TimeToStruct(TimeCurrent(), t);
   int m = t.hour * 60 + t.min;
   return (m >= InpBlackoutStartMin && m <= InpBlackoutEndMin);
}

// build today's session range once the range window has closed
bool BuildRange()
{
   datetime today = DayOf(TimeCurrent());
   if(rangeDay == today) return true;
   MqlDateTime t; TimeToStruct(TimeCurrent(), t);
   if(t.hour < InpRangeEndHour) return false;
   datetime from = today + InpRangeStartHour * 3600;
   datetime to   = today + InpRangeEndHour * 3600;
   MqlRates r[];
   int n = CopyRates(_Symbol, InpTF, from, to, r);
   if(n <= 0) return false;
   rangeHigh = r[0].high; rangeLow = r[0].low;
   for(int i = 1; i < n; i++) { if(r[i].high > rangeHigh) rangeHigh = r[i].high; if(r[i].low < rangeLow) rangeLow = r[i].low; }
   rangeDay = today;
   return true;
}

void Trail()
{
   if(!InpUseTrailing) return;
   double atr = ATR(); if(atr <= 0) return;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!pos.SelectByIndex(i) || pos.Magic() != InpMagic || pos.Symbol() != _Symbol) continue;
      double open = pos.PriceOpen(), sl = pos.StopLoss(), tp = pos.TakeProfit();
      double risk = MathAbs(open - sl); if(risk <= 0) continue;
      if(pos.PositionType() == POSITION_TYPE_BUY)
      {
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         if(bid - open < risk) continue;                       // trail only after 1R
         double newSL = NormalizeDouble(bid - InpTrailATR * atr, _Digits);
         if(newSL > sl && newSL > open) trade.PositionModify(pos.Ticket(), newSL, tp);
      }
      else
      {
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         if(open - ask < risk) continue;
         double newSL = NormalizeDouble(ask + InpTrailATR * atr, _Digits);
         if((sl == 0 || newSL < sl) && newSL < open) trade.PositionModify(pos.Ticket(), newSL, tp);
      }
   }
}

//---------------- events ----------------
int OnInit()
{
   if(InpDemoOnly && !IsDemo() && !MQLInfoInteger(MQL_TESTER))
   {
      Alert("PropSafe: this account is not a demo account. Refusing to run.");
      return INIT_FAILED;
   }
   hATR = iATR(_Symbol, InpTF, InpATRPeriod);
   hEMA = iMA(_Symbol, PERIOD_H1, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   if(hATR == INVALID_HANDLE || hEMA == INVALID_HANDLE) return INIT_FAILED;
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(20);
   initialBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   RollDay();
   Print("PropSafe ready. Initial balance ", initialBalance, " daily cap ", InpDailyLossCap, "% total cap ", InpTotalDDCap, "%");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { Comment(""); }

void OnTick()
{
   RollDay();
   string why = "";
   bool blocked = RiskGuardsBlock(why);

   // weekend flat
   MqlDateTime t; TimeToStruct(TimeCurrent(), t);
   if(InpFlatBeforeWeekend && t.day_of_week == 5 && t.hour >= InpFridayCloseHour && OpenPositionsAll() > 0)
      CloseAll("weekend flat");

   Trail();

   Comment(StringFormat("PropSafe | eq %.2f | day P/L %.2f%% | DD %.2f%% | pos %d | %s",
           AccountInfoDouble(ACCOUNT_EQUITY),
           dayStartEquity > 0 ? 100.0 * (AccountInfoDouble(ACCOUNT_EQUITY) - dayStartEquity) / dayStartEquity : 0.0,
           initialBalance > 0 ? 100.0 * (initialBalance - AccountInfoDouble(ACCOUNT_EQUITY)) / initialBalance : 0.0,
           OpenPositionsAll(), blocked ? why : "ok"));

   // new-bar logic only
   datetime bar = iTime(_Symbol, InpTF, 0);
   if(bar == lastBar) return;
   lastBar = bar;

   if(blocked || tradedToday || InBlackout()) return;
   if(t.day_of_week == 0 || t.day_of_week == 6) return;
   if(t.hour < InpRangeEndHour || t.hour >= InpTradeUntilHour) return;
   if(InpFlatBeforeWeekend && t.day_of_week == 5 && t.hour >= InpFridayCloseHour - 1) return;
   if(OpenPositionsAll() >= InpMaxPositions || HavePositionOnSymbol()) return;
   if(!BuildRange()) return;

   double atr = ATR(); if(atr <= 0) return;
   double range = rangeHigh - rangeLow;
   if(range < InpMinRangeATR * atr || range > InpMaxRangeATR * atr) return;

   double close1 = iClose(_Symbol, InpTF, 1);
   int trend = TrendDir();
   double stopDist = InpStopATR * atr;
   double lots = LotsForRisk(stopDist);
   if(lots <= 0) return;

   if(close1 > rangeHigh && (trend >= 0))
   {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double sl = NormalizeDouble(ask - stopDist, _Digits);
      double tp = NormalizeDouble(ask + InpRewardRisk * stopDist, _Digits);
      if(trade.Buy(lots, _Symbol, ask, sl, tp, "PropSafe long")) tradedToday = true;
   }
   else if(close1 < rangeLow && (trend <= 0))
   {
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double sl = NormalizeDouble(bid + stopDist, _Digits);
      double tp = NormalizeDouble(bid - InpRewardRisk * stopDist, _Digits);
      if(trade.Sell(lots, _Symbol, bid, sl, tp, "PropSafe short")) tradedToday = true;
   }
}
//+------------------------------------------------------------------+
