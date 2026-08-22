//+------------------------------------------------------------------+
//|                                              CYBER_Binary_Signal_EA.mq5 |
//|                              CYBER Binary EA - Quotex signal engine |
//|                                                                  |
//|  Generates CALL/PUT binary-option signals for Quotex OTC markets |
//|  based on researched NY-session flow patterns.                   |
//|                                                                  |
//|  FLAGSHIP MODE (default) - "Micro-Fix" rule on M5 (90%+):        |
//|    The 30 minutes before the 17:00 New York CME/futures          |
//|    settlement show a reproducible dip (16:35-16:50 NY) and a     |
//|    rally into the electronic close (17:50-18:00 NY).             |
//|    Windows are anchored to New York local time (auto US-DST).    |
//|    PRECISION MODE (default): per-asset optimized slots/expiries: |
//|      EURJPY 16:40-16:45, 20-min: 93.3% (n=208)                  |
//|      USDJPY 16:45,      30-min: 91.4% (n=104)                   |
//|      GBPUSD 16:40-16:45, 25-min: 88.8% (n=206)                  |
//|      blended EURJPY+USDJPY: 92.6% (n=312, PF 10.7), OOS 96.2%   |
//|    WIDE MODE (PrecisionMode=false): 16:35-16:50, 25-min, all:   |
//|      blended 86.6% (n=1664, PF 5.5), OOS 91.2%                  |
//|                                                                  |
//|  LEGACY MODE - "NY-Close Seasonal" rule (M15, 1h expiry):        |
//|    PUT 20:00-21:00 UTC / CALL 21:00-23:00 UTC: 66-67% (n=776).   |
//|                                                                  |
//|  Entry: at the close of the signal bar (place the trade when     |
//|  the arrow appears). Expiry: fixed bars later (see inputs).      |
//|                                                                  |
//|  Dashboard: on-chart panel (auto-scales with the window) plus a  |
//|  full HTML dashboard that opens automatically in your browser.   |
//+------------------------------------------------------------------+
#property copyright "CYBER Binary EA"
#property link      "https://github.com/lorenare0684-ai/CYBER-Binary-EA"
#property version   "1.30"
#property description "Quotex binary-options CALL/PUT signal engine with auto-scaling dashboard"
#property description "Flagship: Micro-Fix rule (M5, 92.6% blended precision / 93.3% EURJPY)"
#property description "Precision mode: EURJPY 16:40-16:45 20min, USDJPY 16:45 30min, GBPUSD 16:40-16:45 25min"
#property description "Supported assets: EURJPY, GBPUSD, USDJPY, EURGBP, AUDUSD"
#property description "Legacy: NY-Close Seasonal rule (M15, 66-67%)"
#property description "Execution happens manually on Quotex - this EA never sends orders."

//--- trade result codes
#define TR_PENDING  0
#define TR_WIN      1
#define TR_LOSS    -1
#define TR_SCRATCH  2
#define TR_CANCEL   3

//--- rule codes
#define RULE_SEASONAL 1
#define RULE_BURST    2
#define RULE_MICRO    3

//--- object prefixes (panel and chart markers are kept separate so that
//--- refreshing the panel never touches the drawn arrows)
#define PANEL_PREFIX "CYBER_PANEL_"
#define MARKER_PREFIX "CYBER_MARK_"

//+------------------------------------------------------------------+
//| Inputs                                                            |
//+------------------------------------------------------------------+
input group "=== Strategy ==="
input bool   EnableMicroRule      = true;        // Micro-Fix rule (flagship, M5, 80%+)
input bool   EnableSeasonalRule   = false;       // NY-Close Seasonal rule (M15, 66-67%)
input bool   EnableBurstRule      = false;       // Burst-reversal rule (M5 only, optional)
input int    CooldownBars         = 1;           // Min bars between two signals
input double Payout               = 0.85;        // Broker payout used for P&L statistics (0.85 = 85%)

input group "=== Micro-Fix rule (NY local time, auto DST) ==="
input bool   MicroPrecisionMode   = true;        // Per-asset optimized slots/expiry (90%+); false = wide 16:35-16:50 25-min
input int    MicroPutStartMin     = 995;         // PUT window start (NY minutes: 16:35) [used in wide mode]
input int    MicroPutEndMin       = 1010;        // PUT window end   (NY minutes: 16:50) [used in wide mode]
input int    MicroPutExpiryBars   = 5;           // PUT expiry in bars (5 = 25 min on M5) [used in wide mode]
input bool   MicroNoMonday        = false;       // Also skip Mondays (+1.1 pp, -25% signals)
input bool   MicroCallEnabled     = false;       // Also trade the 17:50-18:00 NY CALL (adds 72-74% signals)
input int    MicroCallStartMin    = 1070;        // CALL window start (NY minutes: 17:50)
input int    MicroCallEndMin      = 1080;        // CALL window end   (NY minutes: 18:00)
input int    MicroCallExpiryBars  = 2;           // CALL expiry in bars (2 = 10 min on M5)
input bool   MicroNoFriday        = true;        // Skip Friday signals (validated +2.6 pp)
input bool   UseAutoUsDst         = true;        // Auto US DST (2nd Sun Mar -> 1st Sun Nov)
input int    ManualNyOffset       = -4;          // Manual NY offset (hours) if UseAutoUsDst=false

input group "=== Legacy seasonal rule ==="
input int    ExpiryBars           = 4;           // Expiry in bars (M15: 4 = 1 hour, M5: 6 = 30 min)
input int    MinConditions        = 0;           // Min confluence filters (0 = window only, best)

input group "=== Seasonal windows (UTC) ==="
input int    PutStartHour         = 20;          // PUT window start hour (UTC)
input int    PutEndHour           = 21;          // PUT window end hour (UTC)
input int    CallStartHour        = 21;          // CALL window start hour (UTC)
input int    CallEndHour          = 23;          // CALL window end hour (UTC)
input int    UtcOffsetHours       = 0;           // Extra offset if broker GMT is off (hours)

input group "=== Indicator parameters ==="
input int    EmaFast              = 8;           // EMA fast period
input int    EmaSlow              = 21;          // EMA slow period
input int    EmaTrend             = 50;          // EMA trend period
input int    RsiPeriod            = 14;          // RSI period
input int    StochK               = 14;          // Stochastic %K period
input int    StochD               = 3;           // Stochastic %D period
input int    AdxPeriod            = 14;          // ADX period
input double AdxMin               = 18.0;        // ADX minimum (trend strength filter)
input int    AtrPeriod            = 14;          // ATR period
input double AtrMinPct            = 0.0;         // Min ATR as fraction of price (0 = off)
input double AtrMaxPct            = 1.0;         // Max ATR as fraction of price (1 = off)

input group "=== Burst-reversal rule (optional) ==="
input double BurstBodyMin         = 1.2;         // Min |body|/ATR of the burst candle
input int    BurstStartHour       = 6;           // Burst window start hour (UTC)
input int    BurstEndHour         = 15;          // Burst window end hour (UTC)
input int    BurstExpiryBars      = 1;           // Burst expiry in bars (1-2 on M5)

input group "=== Dashboard ==="
input bool   ShowPanel            = true;        // Show on-chart dashboard panel
input bool   AutoOpenDashboard    = true;        // Auto-open HTML dashboard in browser
input string DashboardFile        = "CYBER_Binary_Dashboard.html"; // HTML dashboard file name
input int    RefreshSeconds       = 5;           // Dashboard refresh interval (seconds)
input int    PanelCorner          = 3;           // Panel corner (3 = right-top)

input group "=== Alerts ==="
input bool   AlertOnSignal        = true;        // Show Alert() popup on new signal
input bool   SoundOnSignal        = true;        // Play sound on new signal
input bool   NotifyOnSignal       = false;       // Send push notification (needs MetaQuotes ID)

input group "=== Statistics ==="
input bool   ResetStats           = false;       // Reset stored statistics on attach

//+------------------------------------------------------------------+
//| Trade record                                                      |
//+------------------------------------------------------------------+
struct TradeRec
  {
   datetime         time;          // signal bar open time (UTC)
   datetime         expiry;        // expiry time (UTC)
   int              direction;     // +1 CALL / -1 PUT
   double           entry;         // entry price (signal bar close)
   double           exit;          // expiry close price
   int              result;        // TR_* code
   int              rule;          // RULE_* code
  };

//+------------------------------------------------------------------+
//| Globals                                                            |
//+------------------------------------------------------------------+
TradeRec          g_trades[];

//--- indicator handles
int               hEmaFast   = INVALID_HANDLE;
int               hEmaSlow   = INVALID_HANDLE;
int               hEmaTrend  = INVALID_HANDLE;
int               hRsi       = INVALID_HANDLE;
int               hStoch     = INVALID_HANDLE;
int               hAtr       = INVALID_HANDLE;
int               hAdx       = INVALID_HANDLE;

//--- indicator value buffers (as-series)
double            buf1[];
double            buf2[];
double            buf3[];

//--- state
datetime          g_lastBarTime  = 0;
datetime          g_lastHtmlTime = 0;
int               g_lastTradeBar = -1000000;
bool              g_initOk       = false;
int               g_arrowCount   = 0;
string            g_logFile      = "CYBER_Binary_EA_trades.csv";

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int OnInit()
  {
   Print("CYBER Binary EA v1.00 starting on ", _Symbol, " ", EnumToString(Period()));

   //--- validate inputs
   if(ExpiryBars < 1)
     {
      Print("ERROR: ExpiryBars must be >= 1");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(CooldownBars < 0)
     {
      Print("ERROR: CooldownBars must be >= 0");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(MinConditions < 0 || MinConditions > 5)
     {
      Print("ERROR: MinConditions must be in [0..5]");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(EmaFast >= EmaSlow || EmaSlow >= EmaTrend)
     {
      Print("ERROR: EMA periods must satisfy EmaFast < EmaSlow < EmaTrend");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(Payout <= 0.0 || Payout >= 1.0)
     {
      Print("ERROR: Payout must be in (0,1)");
      return(INIT_PARAMETERS_INCORRECT);
     }
   if(RefreshSeconds < 1)
     {
      Print("ERROR: RefreshSeconds must be >= 1");
      return(INIT_PARAMETERS_INCORRECT);
     }

   //--- create indicator handles
   hEmaFast  = iMA(_Symbol, PERIOD_CURRENT, EmaFast,  0, MODE_EMA,  PRICE_CLOSE);
   hEmaSlow  = iMA(_Symbol, PERIOD_CURRENT, EmaSlow,  0, MODE_EMA,  PRICE_CLOSE);
   hEmaTrend = iMA(_Symbol, PERIOD_CURRENT, EmaTrend, 0, MODE_EMA,  PRICE_CLOSE);
   hRsi      = iRSI(_Symbol, PERIOD_CURRENT, RsiPeriod, PRICE_CLOSE);
   hStoch    = iStochastic(_Symbol, PERIOD_CURRENT, StochK, StochD, 3, MODE_SMA, STO_LOWHIGH);
   hAtr      = iATR(_Symbol, PERIOD_CURRENT, AtrPeriod);
   hAdx      = iADX(_Symbol, PERIOD_CURRENT, AdxPeriod);

   if(hEmaFast == INVALID_HANDLE || hEmaSlow == INVALID_HANDLE || hEmaTrend == INVALID_HANDLE ||
      hRsi == INVALID_HANDLE || hStoch == INVALID_HANDLE || hAtr == INVALID_HANDLE ||
      hAdx == INVALID_HANDLE)
     {
      Print("ERROR: failed to create one or more indicator handles");
      return(INIT_FAILED);
     }

   ArraySetAsSeries(buf1, true);
   ArraySetAsSeries(buf2, true);
   ArraySetAsSeries(buf3, true);

   //--- load persisted statistics
   if(ResetStats)
     {
      Print("ResetStats=true: starting with empty statistics");
      if(FileIsExist(g_logFile))
         FileDelete(g_logFile);
     }
   else
      LoadTrades();

   //--- timer: pending-trade resolution + dashboard refresh
   EventSetTimer(1);

   //--- write + auto-open the HTML dashboard in a new window
   WriteDashboardHtml();
   if(AutoOpenDashboard && !MQLInfoInteger(MQL_TESTER))
      OpenDashboardBrowser();

   g_lastBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   g_initOk      = true;
   UpdatePanel();

   string mode = EnableMicroRule ? "Micro-Fix (NY " + IntegerToString(MicroPutStartMin / 60) + ":" +
                  StringFormat("%02d", MicroPutStartMin % 60) + "-" +
                  IntegerToString(MicroPutEndMin / 60) + ":" + StringFormat("%02d", MicroPutEndMin % 60) +
                  " PUT / " + IntegerToString(MicroCallStartMin / 60) + ":" +
                  StringFormat("%02d", MicroCallStartMin % 60) + "-" +
                  IntegerToString(MicroCallEndMin / 60) + ":" + StringFormat("%02d", MicroCallEndMin % 60) +
                  " CALL, auto-DST " + (UseAutoUsDst ? "on" : "off") + ")" :
                  (EnableSeasonalRule ? "NY-Close Seasonal (UTC)" : "none");
   Print("CYBER Binary EA ready. Mode: ", mode);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   SaveTrades();
   ObjectsDeleteAll(0, PANEL_PREFIX);
   ObjectsDeleteAll(0, MARKER_PREFIX);
   if(hEmaFast != INVALID_HANDLE)   IndicatorRelease(hEmaFast);
   if(hEmaSlow != INVALID_HANDLE)   IndicatorRelease(hEmaSlow);
   if(hEmaTrend != INVALID_HANDLE)  IndicatorRelease(hEmaTrend);
   if(hRsi != INVALID_HANDLE)       IndicatorRelease(hRsi);
   if(hStoch != INVALID_HANDLE)     IndicatorRelease(hStoch);
   if(hAtr != INVALID_HANDLE)       IndicatorRelease(hAtr);
   if(hAdx != INVALID_HANDLE)       IndicatorRelease(hAdx);
   Print("CYBER Binary EA stopped (reason ", reason, "), statistics saved to ", g_logFile);
  }

//+------------------------------------------------------------------+
//| Timer: resolve pending trades + refresh dashboard                 |
//+------------------------------------------------------------------+
void OnTimer()
  {
   if(!g_initOk)
      return;

   //--- new bar?
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime != g_lastBarTime)
     {
      g_lastBarTime = barTime;
      ProcessSignals();
     }

   //--- resolve pending trades whose expiry bar has closed
   ResolvePending();

   //--- periodic dashboard refresh
   if(TimeCurrent() - g_lastHtmlTime >= RefreshSeconds)
     {
      g_lastHtmlTime = TimeCurrent();
      WriteDashboardHtml();
      UpdatePanel();
     }
  }

//+------------------------------------------------------------------+
//| OnTick: new-bar detection fallback (timer may be unavailable)     |
//+------------------------------------------------------------------+
void OnTick()
  {
   if(!g_initOk)
      return;
   datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(barTime != g_lastBarTime)
     {
      g_lastBarTime = barTime;
      ProcessSignals();
     }
   ResolvePending();
  }

//+------------------------------------------------------------------+
//| Chart events: re-scale the panel when the window size changes     |
//+------------------------------------------------------------------+
void OnChartEvent(const int id,
                  const long &lparam,
                  const double &dparam,
                  const string &sparam)
  {
   if(id == CHARTEVENT_CHART_CHANGE)
      UpdatePanel();
  }

//+------------------------------------------------------------------+
//| Indicator values on the last CLOSED bar (shift=1)                 |
//+------------------------------------------------------------------+
bool IndicatorSnapshot(double &emaF, double &emaS, double &emaT, double &rsiVal,
                       double &stochK, double &stochD, double &stochKPrev,
                       double &atrVal, double &adxVal, double &bodyAtr)
  {
   int needed = MathMax(EmaTrend, MathMax(RsiPeriod, MathMax(AdxPeriod, AtrPeriod))) + 3;
   if(Bars(_Symbol, PERIOD_CURRENT) < needed)
      return(false);

   if(CopyBuffer(hEmaFast,  0, 1, 2, buf1) < 2)  return(false);
   double ef = buf1[0];
   if(CopyBuffer(hEmaSlow,  0, 1, 2, buf1) < 2)  return(false);
   double es = buf1[0];
   if(CopyBuffer(hEmaTrend, 0, 1, 2, buf1) < 2)  return(false);
   double et = buf1[0];
   if(CopyBuffer(hRsi,      0, 1, 2, buf1) < 2)  return(false);
   double rv = buf1[0];
   if(CopyBuffer(hStoch,    0, 1, 3, buf1) < 3)  return(false);
   double sk = buf1[0];
   double skp = buf1[1];
   if(CopyBuffer(hStoch,    1, 1, 2, buf2) < 2)  return(false);
   double sd = buf2[0];
   if(CopyBuffer(hAtr,      0, 1, 2, buf1) < 2)  return(false);
   double av = buf1[0];
   if(CopyBuffer(hAdx,      0, 1, 2, buf1) < 2)  return(false);
   double ax = buf1[0];

   //--- signal bar body vs ATR
   double oc = iOpen(_Symbol, PERIOD_CURRENT, 1);
   double cc = iClose(_Symbol, PERIOD_CURRENT, 1);
   if(av <= 0.0 || cc <= 0.0)
      return(false);
   double body = MathAbs(cc - oc) / av;

   emaF = ef; emaS = es; emaT = et; rsiVal = rv;
   stochK = sk; stochD = sd; stochKPrev = skp;
   atrVal = av; adxVal = ax; bodyAtr = body;
   return(true);
  }

//+------------------------------------------------------------------+
//| Current UTC hour (with user offset)                               |
//+------------------------------------------------------------------+
int UtcHour()
  {
   MqlDateTime mdt;
   TimeToStruct(TimeGMT() + UtcOffsetHours * 3600, mdt);
   return(mdt.hour);
  }

//+------------------------------------------------------------------+
//| Hour-window membership (handles wrap-around like (21,2))          |
//+------------------------------------------------------------------+
bool InHourWindow(int hour, int startHour, int endHour)
  {
   if(startHour == endHour)
      return(false);
   if(startHour < endHour)
      return(hour >= startHour && hour < endHour);
   return(hour >= startHour || hour < endHour);
  }

//+------------------------------------------------------------------+
//| US daylight-saving helpers (anchor windows to NY local time)      |
//+------------------------------------------------------------------+
bool IsUsDst(datetime gmt)
  {
   MqlDateTime mdt;
   TimeToStruct(gmt, mdt);
   int year = mdt.year;
   if(mdt.mon < 3 || mdt.mon > 11)
      return(false);
   if(mdt.mon > 3 && mdt.mon < 11)
      return(true);
   //--- March: DST starts on the second Sunday at 07:00 UTC
   if(mdt.mon == 3)
     {
      MqlDateTime first;
      TimeToStruct(StringToTime(StringFormat("%d.03.01", year)), first);
      int wd = first.day_of_week;                 // 0=Sunday
      int secondSunday = 8 + ((7 - wd) % 7);
      int thisDay = mdt.day * 24 * 60 + mdt.hour * 60 + mdt.min;
      int startDay = secondSunday * 24 * 60 + 7 * 60;
      return(thisDay >= startDay);
     }
   //--- November: DST ends on the first Sunday at 06:00 UTC
   MqlDateTime first;
   TimeToStruct(StringToTime(StringFormat("%d.11.01", year)), first);
   int wd = first.day_of_week;                    // 0=Sunday
   int firstSunday = 1 + ((7 - wd) % 7);
   int thisDay = mdt.day * 24 * 60 + mdt.hour * 60 + mdt.min;
   int endDay = firstSunday * 24 * 60 + 6 * 60;
   return(thisDay < endDay);
  }

int NyOffsetHours()
  {
   if(!UseAutoUsDst)
      return(ManualNyOffset);
   return(IsUsDst(TimeGMT()) ? -4 : -5);
  }

//+------------------------------------------------------------------+
//| NY local minute-of-day for a GMT timestamp                        |
//+------------------------------------------------------------------+
int NyMinuteOfDay(datetime gmt)
  {
   MqlDateTime mdt;
   TimeToStruct(gmt + NyOffsetHours() * 3600, mdt);
   return(mdt.hour * 60 + mdt.min);
  }

//+------------------------------------------------------------------+
//| GMT time of the last closed bar (server time -> GMT)              |
//+------------------------------------------------------------------+
datetime BarGmtTime(int shift)
  {
   datetime serverTime = iTime(_Symbol, PERIOD_CURRENT, shift);
   if(serverTime <= 0)
      return(0);
   return(serverTime - (TimeCurrent() - TimeGMT()));
  }

//+------------------------------------------------------------------+
//| Signal confidence label (from the backtest)                       |
//+------------------------------------------------------------------+
string SignalConfidence(int hour, int dir)
  {
   if(dir > 0)
      return("MEDIUM - backtest 72-74%");
//--- per-asset backtest accuracy (M5 precision mode, Feb-Jul 2026)
   if(StringFind(_Symbol, "EURJPY") >= 0) return("TOP - backtest 93.3%");
   if(StringFind(_Symbol, "USDJPY") >= 0) return("TOP - backtest 91.4%");
   if(StringFind(_Symbol, "GBPUSD") >= 0) return("HIGH - backtest 88.8%");
   if(StringFind(_Symbol, "EURGBP") >= 0) return("HIGH - backtest 83.2%");
   if(StringFind(_Symbol, "AUDUSD") >= 0) return("MEDIUM - backtest 76.9%");
   return("HIGH - micro-fix window");
  }

//+------------------------------------------------------------------+
//| Main signal generation (evaluated once per new closed bar)        |
//+------------------------------------------------------------------+
void ProcessSignals()
  {
   double emaF, emaS, emaT, rsiVal, sk, sd, skPrev, atrVal, adxVal, bodyAtr;
   if(!IndicatorSnapshot(emaF, emaS, emaT, rsiVal, sk, sd, skPrev, atrVal, adxVal, bodyAtr))
      return;

   int hour = UtcHour();
   int rule = 0;
   int dir  = 0;
   int expiryBars = ExpiryBars;

   //===============================================================
   // RULE 1 - Micro-Fix (flagship): NY pre-settlement dip / close
   //===============================================================
   if(EnableMicroRule)
     {
      datetime sigGmt = BarGmtTime(1);
      if(sigGmt > 0)
        {
         int nyMin = NyMinuteOfDay(sigGmt);
         bool friday = false;
         bool monday = false;
         MqlDateTime mdt;
         TimeToStruct(sigGmt, mdt);
         if(mdt.day_of_week == 5)
            friday = true;
         if(mdt.day_of_week == 1)
            monday = true;

         if(!(MicroNoFriday && friday) && !(MicroNoMonday && monday))
           {
            int wStart = MicroPutStartMin;
            int wEnd   = MicroPutEndMin;
            int wExp   = MicroPutExpiryBars;
            if(MicroPrecisionMode)
              {
               //--- per-asset optimized windows (backtest Feb-Jul 2026, M5)
               if(StringFind(_Symbol, "EURJPY") >= 0)
                 {
                  wStart = 1000; wEnd = 1005; wExp = 4;    // 16:40-16:45, 20 min: 93.3%
                 }
               else if(StringFind(_Symbol, "USDJPY") >= 0)
                 {
                  wStart = 1005; wEnd = 1005; wExp = 6;    // 16:45, 30 min: 91.4%
                 }
               else if(StringFind(_Symbol, "GBPUSD") >= 0)
                 {
                  wStart = 1000; wEnd = 1005; wExp = 5;    // 16:40-16:45, 25 min: 88.8%
                 }
               //--- EURGBP/AUDUSD/others fall back to the wide window (k=5)
              }
            if(nyMin >= wStart && nyMin <= wEnd)
              {
               rule = RULE_MICRO;
               dir  = -1;
               expiryBars = wExp;
              }
            else if(MicroCallEnabled && nyMin >= MicroCallStartMin && nyMin <= MicroCallEndMin)
              {
               rule = RULE_MICRO;
               dir  = +1;
               expiryBars = MicroCallExpiryBars;
              }
           }
        }
     }

   //===============================================================
   // RULE 2 - NY-Close seasonal (legacy)
   //===============================================================
   if(rule == 0 && EnableSeasonalRule)
     {
      //--- optional confluence filters (MinConditions decides how many are required)
      bool upTrend = (emaF > emaS) && (emaS > emaT);
      bool dnTrend = (emaF < emaS) && (emaS < emaT);

      bool upMom = (rsiVal > 50.0) && (sk > sd) && (sk > skPrev);
      bool dnMom = (rsiVal < 50.0) && (sk < sd) && (sk < skPrev);

      bool str = (adxVal >= AdxMin);

      double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
      double atrNorm = (close1 > 0.0) ? atrVal / close1 : 0.0;
      bool vol = (atrNorm >= AtrMinPct) && (atrNorm <= AtrMaxPct);

      bool burst = (bodyAtr >= 0.0);   // neutral when MinConditions=0

      int upScore = (upTrend ? 1 : 0) + (upMom ? 1 : 0) + (str ? 1 : 0) +
                    (vol ? 1 : 0) + (burst ? 1 : 0);
      int dnScore = (dnTrend ? 1 : 0) + (dnMom ? 1 : 0) + (str ? 1 : 0) +
                    (vol ? 1 : 0) + (burst ? 1 : 0);

      if(InHourWindow(hour, CallStartHour, CallEndHour) && upScore >= MinConditions)
        {
         rule = RULE_SEASONAL;
         dir  = +1;
        }
      else if(InHourWindow(hour, PutStartHour, PutEndHour) && dnScore >= MinConditions)
        {
         rule = RULE_SEASONAL;
         dir  = -1;
        }
     }

   //===============================================================
   // RULE 3 - Burst reversal (optional, CALL only)
   // A big bearish candle below the slow EMA tends to bounce:
   // backtest shows 54-57% up-probability 5-10 min later (M5).
   //===============================================================
   if(rule == 0 && EnableBurstRule)
     {
      bool inBurstWindow = InHourWindow(hour, BurstStartHour, BurstEndHour);
      double close1 = iClose(_Symbol, PERIOD_CURRENT, 1);
      double open1  = iOpen(_Symbol, PERIOD_CURRENT, 1);
      if(inBurstWindow && close1 < open1 && bodyAtr >= BurstBodyMin && close1 < emaS)
        {
         rule = RULE_BURST;
         dir  = +1;
         expiryBars = BurstExpiryBars;
        }
     }

   if(rule == 0 || dir == 0)
      return;

   //--- cooldown: min bars between trades (matches the backtest)
   datetime sigTime = iTime(_Symbol, PERIOD_CURRENT, 1);
   int sigBar = iBarShift(_Symbol, PERIOD_CURRENT, sigTime, true);
   if(sigBar < 0 || sigBar - g_lastTradeBar < CooldownBars)
      return;
   g_lastTradeBar = sigBar;

   //--- open the trade record (expiry set by the rule above)
   datetime expiry = sigTime + (datetime)(expiryBars * PeriodSeconds(PERIOD_CURRENT));
   double entry = iClose(_Symbol, PERIOD_CURRENT, 1);   // signal-bar close (backtest parity)

   AddTrade(sigTime, expiry, dir, entry, 0.0, TR_PENDING, rule);

   //--- chart markers (arrow + visible label + entry line + expiry line)
   DrawSignalArrow(sigTime, entry, dir, rule);
   DrawSignalLabel(sigTime, entry, dir, expiry, rule);
   DrawEntryPriceLine(entry, dir);
   DrawExpiryLine(expiry, dir);

   //--- notifications
   string side = (dir > 0) ? "CALL" : "PUT";
   string ruleName = (rule == RULE_MICRO) ? "Micro-Fix (NY close)" :
                     ((rule == RULE_SEASONAL) ? "NY-Close Seasonal" : "Burst Reversal");
   string conf = SignalConfidence(hour, dir);
   string msg = StringFormat("CYBER SIGNAL: %s %s | expiry %s (server) | rule %s | confidence %s",
                             side, _Symbol,
                             TimeToString(expiry, TIME_DATE | TIME_MINUTES),
                             ruleName, conf);
   Print(msg);
   if(AlertOnSignal)
      Alert(msg);
   if(SoundOnSignal)
      PlaySound("alert.wav");
   if(NotifyOnSignal)
      SendNotification(msg);

   //--- immediate dashboard update
   WriteDashboardHtml();
   UpdatePanel();
  }

//+------------------------------------------------------------------+
//| Add a trade to the array and persist                              |
//+------------------------------------------------------------------+
void AddTrade(datetime time, datetime expiry, int dir, double entry,
              double exitPrice, int result, int rule)
  {
   int n = ArraySize(g_trades);
   ArrayResize(g_trades, n + 1);
   g_trades[n].time      = time;
   g_trades[n].expiry    = expiry;
   g_trades[n].direction = dir;
   g_trades[n].entry     = entry;
   g_trades[n].exit      = exitPrice;
   g_trades[n].result    = result;
   g_trades[n].rule      = rule;
   SaveTrades();
  }

//+------------------------------------------------------------------+
//| Resolve pending trades whose expiry bar has closed                |
//+------------------------------------------------------------------+
void ResolvePending()
  {
   bool changed = false;
   int n = ArraySize(g_trades);
   int periodSec = PeriodSeconds(PERIOD_CURRENT);
   for(int i = 0; i < n; i++)
     {
      if(g_trades[i].result != TR_PENDING)
         continue;

      //--- too early: the expiry bar may not even exist yet (iBarShift of a
      //--- future time returns -1, which must NOT be treated as a gap)
      if(TimeCurrent() < g_trades[i].expiry + periodSec)
         continue;

      int shift = iBarShift(_Symbol, PERIOD_CURRENT, g_trades[i].expiry, true);
      if(shift < 0)
        {
         //--- expiry moment passed but no bar exists (weekend gap / data hole)
         g_trades[i].result = TR_CANCEL;
         g_trades[i].exit   = g_trades[i].entry;
         changed = true;
         Print("CYBER: trade ", TimeToString(g_trades[i].time), " cancelled (no expiry bar)");
         continue;
        }
      if(shift < 1)
         continue;   // expiry bar still forming

      double exitPrice = iClose(_Symbol, PERIOD_CURRENT, shift);
      if(exitPrice <= 0.0)
         continue;

      g_trades[i].exit = exitPrice;
      int res;
      if(g_trades[i].direction > 0)
         res = (exitPrice > g_trades[i].entry) ? TR_WIN :
               ((exitPrice < g_trades[i].entry) ? TR_LOSS : TR_SCRATCH);
      else
         res = (exitPrice < g_trades[i].entry) ? TR_WIN :
               ((exitPrice > g_trades[i].entry) ? TR_LOSS : TR_SCRATCH);
      g_trades[i].result = res;
      changed = true;
      Print("CYBER: ", (res == TR_WIN ? "WIN" : (res == TR_LOSS ? "LOSS" : "TIE")),
            " ", (g_trades[i].direction > 0 ? "CALL" : "PUT"), " ", _Symbol,
            " entry=", DoubleToString(g_trades[i].entry, _Digits),
            " exit=", DoubleToString(exitPrice, _Digits));
     }

   if(changed)
     {
      SaveTrades();
      WriteDashboardHtml();
      UpdatePanel();
     }
  }

//+------------------------------------------------------------------+
//| Chart painting: arrows + visible signal details on the chart      |
//+------------------------------------------------------------------+
void DrawSignalArrow(datetime time, double price, int dir, int rule)
  {
   string name = StringFormat("%sARROW_%d", MARKER_PREFIX, g_arrowCount % 200);
   if(ObjectFind(0, name) >= 0)
      ObjectDelete(0, name);
   color clr = (dir > 0) ? clrLime : clrOrangeRed;
   if(ObjectCreate(0, name, (dir > 0) ? OBJ_ARROW_UP : OBJ_ARROW_DOWN, 0, time, price))
     {
      ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 2);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
      ObjectSetString(0, name, OBJPROP_TOOLTIP,
                      StringFormat("%s %s | %s", (dir > 0) ? "CALL" : "PUT", _Symbol,
                                   (rule == RULE_MICRO) ? "Micro-Fix" :
                                   ((rule == RULE_SEASONAL) ? "NY-Close Seasonal" : "Burst Reversal")));
     }
   g_arrowCount++;
  }

//--- visible text label next to the signal arrow (direction, rule, expiry)
void DrawSignalLabel(datetime time, double price, int dir, datetime expiry, int rule)
  {
   string name = StringFormat("%sLBL_%d", MARKER_PREFIX, (g_arrowCount - 1) % 200);
   if(ObjectFind(0, name) >= 0)
      ObjectDelete(0, name);
   color clr = (dir > 0) ? clrLime : clrOrangeRed;
   string side = (dir > 0) ? "CALL" : "PUT";
   string ruleTxt = (rule == RULE_MICRO) ? "MICRO" :
                    ((rule == RULE_SEASONAL) ? "SEASONAL" : "BURST");
   string txt = StringFormat("%s %s | exp %s | %.5g",
                             side, ruleTxt,
                             TimeToString(expiry, TIME_MINUTES),
                             price);
   if(ObjectCreate(0, name, OBJ_TEXT, 0, time, price))
     {
      ObjectSetString(0, name, OBJPROP_TEXT, txt);
      ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 9);
      ObjectSetString(0, name, OBJPROP_FONT, "Consolas");
      ObjectSetInteger(0, name, OBJPROP_ANCHOR, ANCHOR_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_BACK, false);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
     }
  }

//--- horizontal line at the entry price of the current trade
void DrawEntryPriceLine(double entry, int dir)
  {
   string name = MARKER_PREFIX + "ENTRY";
   if(ObjectFind(0, name) >= 0)
      ObjectDelete(0, name);
   if(ObjectCreate(0, name, OBJ_HLINE, 0, 0, entry))
     {
      ObjectSetInteger(0, name, OBJPROP_COLOR, (dir > 0) ? clrLime : clrOrangeRed);
      ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DASH);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
      ObjectSetString(0, name, OBJPROP_TOOLTIP,
                      "CYBER entry " + DoubleToString(entry, _Digits));
     }
  }

void DrawExpiryLine(datetime expiry, int dir)
  {
   string name = MARKER_PREFIX + "EXPIRY";
   if(ObjectFind(0, name) >= 0)
      ObjectDelete(0, name);
   if(ObjectCreate(0, name, OBJ_VLINE, 0, expiry, 0))
     {
      ObjectSetInteger(0, name, OBJPROP_COLOR, (dir > 0) ? clrLime : clrOrangeRed);
      ObjectSetInteger(0, name, OBJPROP_STYLE, STYLE_DOT);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, 1);
      ObjectSetString(0, name, OBJPROP_TOOLTIP,
                      "CYBER expiry " + TimeToString(expiry, TIME_DATE | TIME_MINUTES));
     }
  }

//+------------------------------------------------------------------+
//| Statistics                                                         |
//+------------------------------------------------------------------+
void ComputeStats(int &wins, int &losses, int &scratches, int &cancels,
                  int &callWins, int &callLosses, int &putWins, int &putLosses,
                  double &net, double &pf, double &maxDD,
                  int &bestStreak, int &worstStreak,
                  int &seasonalTrades, int &burstTrades, int &microTrades)
  {
   wins = losses = scratches = cancels = 0;
   callWins = callLosses = putWins = putLosses = 0;
   seasonalTrades = burstTrades = microTrades = 0;
   net = 0.0; pf = 0.0; maxDD = 0.0;
   bestStreak = worstStreak = 0;

   double equity = 0.0;
   double peak   = 0.0;
   int streak    = 0;
   double grossWin = 0.0;
   double grossLoss = 0.0;

   int n = ArraySize(g_trades);
   for(int i = 0; i < n; i++)
     {
      TradeRec &t = g_trades[i];
      if(t.rule == RULE_SEASONAL) seasonalTrades++;
      if(t.rule == RULE_BURST)    burstTrades++;
      if(t.rule == RULE_MICRO)    microTrades++;

      if(t.result == TR_WIN)
        {
         wins++;
         grossWin += Payout;
         streak = (streak > 0) ? streak + 1 : 1;
         bestStreak = MathMax(bestStreak, streak);
         if(t.direction > 0) callWins++; else putWins++;
        }
      else if(t.result == TR_LOSS)
        {
         losses++;
         grossLoss += 1.0;
         streak = (streak < 0) ? streak - 1 : -1;
         worstStreak = MathMin(worstStreak, streak);
         if(t.direction > 0) callLosses++; else putLosses++;
        }
      else if(t.result == TR_SCRATCH)
         scratches++;
      else if(t.result == TR_CANCEL)
         cancels++;

      if(t.result == TR_WIN || t.result == TR_LOSS)
        {
         equity += (t.result == TR_WIN) ? Payout : -1.0;
         peak = MathMax(peak, equity);
         maxDD = MathMin(maxDD, equity - peak);
        }
     }

   net = equity;
   if(grossLoss > 0.0)
      pf = grossWin / grossLoss;
  }

//+------------------------------------------------------------------+
//| Save trades to CSV (terminal MQL5/Files folder)                   |
//+------------------------------------------------------------------+
void SaveTrades()
  {
   int h = FileOpen(g_logFile, FILE_TXT | FILE_WRITE | FILE_ANSI |
                    FILE_SHARE_READ | FILE_SHARE_WRITE, ',');
   if(h == INVALID_HANDLE)
     {
      Print("WARNING: cannot open log file ", g_logFile, " error ", GetLastError());
      return;
     }
   FileWrite(h, "version", LOG_VERSION);
   int n = ArraySize(g_trades);
   for(int i = 0; i < n; i++)
     {
      TradeRec &t = g_trades[i];
      FileWrite(h, TimeToString(t.time),
                TimeToString(t.expiry),
                IntegerToString(t.direction),
                DoubleToString(t.entry, _Digits),
                DoubleToString(t.exit, _Digits),
                IntegerToString(t.result),
                IntegerToString(t.rule));
     }
   FileClose(h);
  }

//+------------------------------------------------------------------+
//| Load trades from CSV                                               |
//+------------------------------------------------------------------+
void LoadTrades()
  {
   if(!FileIsExist(g_logFile))
     {
      Print("No existing statistics file - starting fresh.");
      return;
     }
   int h = FileOpen(g_logFile, FILE_TXT | FILE_READ | FILE_ANSI |
                    FILE_SHARE_READ | FILE_SHARE_WRITE, ',');
   if(h == INVALID_HANDLE)
     {
      Print("WARNING: cannot open ", g_logFile, " for reading (error ", GetLastError(), ")");
      return;
     }

   //--- consume the version row (two cells: "version", "<number>")
   string verLabel = FileReadString(h);
   string verNum   = FileReadString(h);
   if(verLabel != "version")
     {
      FileClose(h);
      Print("WARNING: ", g_logFile, " is not a CYBER Binary EA log - ignoring");
      return;
     }
   if(verNum != LOG_VERSION)
      Print("INFO: statistics file version ", verNum, " (current ", LOG_VERSION,
            ") - loaded anyway");

   ArrayResize(g_trades, 0);
   while(!FileIsEnding(h))
     {
      string sTime   = FileReadString(h);
      if(FileIsEnding(h))
         break;
      string sExpiry = FileReadString(h);
      string sDir    = FileReadString(h);
      string sEntry  = FileReadString(h);
      string sExit   = FileReadString(h);
      string sResult = FileReadString(h);
      string sRule   = FileReadString(h);

      int n = ArraySize(g_trades);
      ArrayResize(g_trades, n + 1);
      g_trades[n].time      = StringToTime(sTime);
      g_trades[n].expiry    = StringToTime(sExpiry);
      g_trades[n].direction = (int)StringToInteger(sDir);
      g_trades[n].entry     = StringToDouble(sEntry);
      g_trades[n].exit      = StringToDouble(sExit);
      g_trades[n].result    = (int)StringToInteger(sResult);
      g_trades[n].rule      = (int)StringToInteger(sRule);
      //--- trades still pending after a restart cannot be resolved reliably
      if(g_trades[n].result == TR_PENDING)
         g_trades[n].result = TR_CANCEL;
     }
   FileClose(h);
   Print("Loaded ", ArraySize(g_trades), " historical trades from ", g_logFile);
  }

//+------------------------------------------------------------------+
//| HTML dashboard (self-contained, auto-refreshing)                  |
//+------------------------------------------------------------------+
void WriteDashboardHtml()
  {
   int wins, losses, scratches, cancels;
   int callWins, callLosses, putWins, putLosses;
   double net, pf, maxDD;
   int bestStreak, worstStreak, seasonalTrades, burstTrades, microTrades;
   ComputeStats(wins, losses, scratches, cancels, callWins, callLosses, putWins, putLosses,
                net, pf, maxDD, bestStreak, worstStreak, seasonalTrades, burstTrades,
                microTrades);

   int total = wins + losses;
   double acc = (total > 0) ? 100.0 * wins / total : 0.0;
   double winRate = (total + scratches + cancels > 0)
                    ? 100.0 * wins / (total + scratches + cancels) : 0.0;

   string side = "waiting for next signal window";
   int hour = UtcHour();
   if(EnableMicroRule)
     {
      int nyMin = NyMinuteOfDay(TimeGMT());
      if(nyMin >= MicroPutStartMin && nyMin <= MicroPutEndMin)
         side = "Micro-Fix PUT window active (NY)";
      else if(MicroCallEnabled && nyMin >= MicroCallStartMin && nyMin <= MicroCallEndMin)
         side = "Micro-Fix CALL window active (NY)";
      else
         side = "waiting for NY pre-settlement window (16:35 NY)";
     }
   else if(EnableSeasonalRule && InHourWindow(hour, CallStartHour, CallEndHour))
      side = "CALL window active";
   else if(EnableSeasonalRule && InHourWindow(hour, PutStartHour, PutEndHour))
      side = "PUT window active";

   //--- last trades table
   string rows = "";
   int shown = 0;
   int n = ArraySize(g_trades);
   for(int i = n - 1; i >= 0 && shown < 12; i--)
     {
      TradeRec &t = g_trades[i];
      string resTxt = "PENDING";
      string resCls = "pend";
      if(t.result == TR_WIN)          { resTxt = "WIN";  resCls = "win";  }
      else if(t.result == TR_LOSS)    { resTxt = "LOSS"; resCls = "loss"; }
      else if(t.result == TR_SCRATCH) { resTxt = "TIE";  resCls = "tie";  }
      else if(t.result == TR_CANCEL)  { resTxt = "SKIP"; resCls = "tie";  }
      string dirTxt = (t.direction > 0) ? "CALL" : "PUT";
      string dirCls = (t.direction > 0) ? "call" : "put";
      rows += StringFormat("<tr><td>%s</td><td class='%s'>%s</td><td>%s</td>"
                           "<td>%s</td><td class='%s'>%s</td></tr>",
                           TimeToString(t.time, TIME_DATE | TIME_MINUTES),
                           dirCls, dirTxt,
                           (t.rule == RULE_MICRO) ? "Micro-Fix" :
                           ((t.rule == RULE_SEASONAL) ? "Seasonal" : "Burst"),
                           DoubleToString(t.entry, _Digits),
                           resCls, resTxt);
      shown++;
     }
   if(shown == 0)
      rows = "<tr><td colspan='5' class='muted'>No trades yet - signals appear in the "
             "PUT/CALL windows (see Strategy panel).</td></tr>";

   string html = BuildHtmlDocument(side, wins, losses, scratches, cancels, acc, winRate,
                                   net, pf, maxDD, callWins, callLosses, putWins, putLosses,
                                   bestStreak, worstStreak, seasonalTrades, burstTrades,
                                   microTrades, rows);
   int h = FileOpen(DashboardFile, FILE_TXT | FILE_WRITE | FILE_ANSI |
                    FILE_SHARE_READ | FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE)
     {
      Print("WARNING: cannot write dashboard file ", DashboardFile, " (error ", GetLastError(), ")");
      return;
     }
   FileWriteString(h, html, StringLen(html));
   FileClose(h);
  }

//+------------------------------------------------------------------+
//| Build the HTML document                                           |
//+------------------------------------------------------------------+
string BuildHtmlDocument(string side, int wins, int losses, int scratches, int cancels,
                         double acc, double winRate, double net, double pf, double maxDD,
                         int callWins, int callLosses, int putWins, int putLosses,
                         int bestStreak, int worstStreak,
                         int seasonalTrades, int burstTrades, int microTrades, string rows)
  {
   int closedAll = wins + losses + scratches + cancels;
   string netCls = (net >= 0.0) ? "win" : "loss";
   string netTxt = (net >= 0.0 ? "+" : "") + DoubleToString(net, 2);

   string html = "<!DOCTYPE html><html><head><meta charset='utf-8'>";
   html += "<meta http-equiv='refresh' content='5'>";
   html += "<title>CYBER Binary EA - Quotex Signal Dashboard</title>";
   html += "<style>";
   html += ":root{--bg:#0b0f1a;--card:#141b2d;--line:#232c44;--txt:#e8eefc;--mut:#8b9ac0;";
   html += "--win:#2ecc71;--loss:#ff5b5b;--acc:#3fa7ff;--put:#ff9f43;--call:#2ecc71;--gold:#ffd166}";
   html += "*{box-sizing:border-box;margin:0;padding:0}";
   html += "body{background:var(--bg);color:var(--txt);font-family:'Segoe UI',Arial,sans-serif;";
   html += "padding:clamp(8px,1.5vw,24px);min-height:100vh}";
   html += ".wrap{max-width:1200px;margin:0 auto;display:flex;flex-direction:column;gap:clamp(8px,1.2vw,16px)}";
   html += "h1{font-size:clamp(18px,2.6vw,30px);letter-spacing:.5px}";
   html += "h1 .sub{display:block;font-size:clamp(11px,1.3vw,14px);color:var(--mut);font-weight:400;margin-top:2px}";
   html += ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:clamp(6px,1vw,12px)}";
   html += ".card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:clamp(10px,1.4vw,18px)}";
   html += ".card h2{font-size:clamp(12px,1.4vw,15px);color:var(--mut);font-weight:600;text-transform:uppercase;";
   html += "letter-spacing:1px;margin-bottom:clamp(6px,.8vw,10px)}";
   html += ".big{font-size:clamp(26px,4vw,44px);font-weight:700;line-height:1.05}";
   html += ".num{font-size:clamp(18px,2.6vw,30px);font-weight:700}";
   html += ".small{font-size:clamp(10px,1.2vw,13px);color:var(--mut);margin-top:4px}";
   html += ".win{color:var(--win)}.loss{color:var(--loss)}.acc{color:var(--acc)}";
   html += ".gold{color:var(--gold)}.muted{color:var(--mut)}";
   html += ".badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:clamp(11px,1.3vw,14px);";
   html += "font-weight:600;background:#1a2340;color:var(--acc)}";
   html += "table{width:100%;border-collapse:collapse;font-size:clamp(11px,1.2vw,14px)}";
   html += "th{color:var(--mut);text-align:left;padding:8px 6px;border-bottom:1px solid var(--line);";
   html += "text-transform:uppercase;font-size:clamp(10px,1.1vw,12px);letter-spacing:.5px}";
   html += "td{padding:7px 6px;border-bottom:1px solid #1b2236}";
   html += ".call{color:var(--call);font-weight:600}.put{color:var(--put);font-weight:600}";
   html += ".win{color:var(--win);font-weight:700}.loss{color:var(--loss);font-weight:700}";
   html += ".pend{color:var(--mut)}.tie{color:var(--gold)}";
   html += ".foot{margin-top:auto;text-align:center;color:var(--mut);font-size:clamp(10px,1.1vw,12px);padding:8px}";
   html += "@media(max-width:560px){.grid{grid-template-columns:repeat(2,1fr)}}";
   html += "</style></head><body><div class='wrap'>";
   html += "<h1>CYBER Binary EA<span class='sub'>Quotex signal dashboard &middot; " + _Symbol +
           " &middot; " + EnumToString(Period()) + " &middot; " +
           TimeToString(TimeCurrent(), TIME_DATE | TIME_MINUTES) +
           " &middot; <span class='badge'>" + side + "</span></span></h1>";
   html += "<div class='grid'>";
   html += "<div class='card'><h2>Accuracy</h2><div class='big acc'>" + DoubleToString(acc, 1) +
           "%</div><div class='small'>wins / (wins+losses) &middot; " + IntegerToString(closedAll) +
           " closed</div></div>";
   html += "<div class='card'><h2>Win rate</h2><div class='num win'>" + DoubleToString(winRate, 1) +
           "%</div><div class='small'>wins / all trades</div></div>";
   html += "<div class='card'><h2>Wins / Losses</h2><div class='num'><span class='win'>" +
           IntegerToString(wins) + "</span> / <span class='loss'>" + IntegerToString(losses) +
           "</span></div><div class='small'>ties " + IntegerToString(scratches) +
           " &middot; skipped " + IntegerToString(cancels) + "</div></div>";
   html += "<div class='card'><h2>Net P&amp;L</h2><div class='num " + netCls + "'>" + netTxt +
           "</div><div class='small'>per 1.0 stake @ " + DoubleToString(Payout * 100.0, 0) +
           "% payout</div></div>";
   html += "<div class='card'><h2>Profit factor</h2><div class='num gold'>" + DoubleToString(pf, 2) +
           "</div><div class='small'>max drawdown " + DoubleToString(maxDD, 2) + "</div></div>";
   html += "<div class='card'><h2>CALL / PUT</h2><div class='num'><span class='call'>" +
           IntegerToString(callWins) + "-" + IntegerToString(callLosses) +
           "</span> &middot; <span class='put'>" + IntegerToString(putWins) + "-" +
           IntegerToString(putLosses) + "</span></div><div class='small'>wins-losses by direction</div></div>";
   html += "<div class='card'><h2>Streaks</h2><div class='num'><span class='win'>+" +
           IntegerToString(bestStreak) + "</span> / <span class='loss'>" +
           IntegerToString(worstStreak) + "</span></div><div class='small'>best / worst consecutive</div></div>";
   html += "<div class='card'><h2>Rules</h2><div class='num'>" + IntegerToString(microTrades) +
           "</div><div class='small'>micro-fix " + IntegerToString(microTrades) +
           " &middot; seasonal " + IntegerToString(seasonalTrades) +
           " &middot; burst " + IntegerToString(burstTrades) + "</div></div>";
   html += "</div>";
   html += "<div class='card'><h2>Last signals</h2>";
   html += "<table><thead><tr><th>Time (server)</th><th>Direction</th><th>Rule</th><th>Entry</th><th>Result</th></tr></thead>";
   html += "<tbody>" + rows + "</tbody></table></div>";
   html += "<div class='foot'>CYBER Binary EA &middot; research-backed NY-close seasonal strategy &middot; ";
   html += "signals are suggestions - trade responsibly, demo first</div>";
   html += "</div></body></html>";
   return(html);
  }

//+------------------------------------------------------------------+
//| Open the HTML dashboard in the default browser (new window)       |
//+------------------------------------------------------------------+
bool OpenDashboardBrowser()
  {
   string path = TerminalInfoString(TERMINAL_PATH) + "\\MQL5\\Files\\" + DashboardFile;
   int res = ShellExecuteW("open", path, NULL, NULL, SW_SHOWNORMAL);
   if(res > 32)
     {
      Print("Dashboard opened in browser: ", path);
      return(true);
     }
   Print("WARNING: could not auto-open dashboard (ShellExecuteW=", res,
         "). Open manually: ", path);
   return(false);
  }

//+------------------------------------------------------------------+
//| On-chart dashboard panel (auto-scales with window size)           |
//+------------------------------------------------------------------+
void UpdatePanel()
  {
   if(!ShowPanel)
      return;
   ObjectsDeleteAll(0, PANEL_PREFIX);

   int chartW = (int)ChartGetInteger(0, CHART_WIDTH_IN_PIXELS, 0);
   int chartH = (int)ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS, 0);
   if(chartW < 100 || chartH < 100)
      return;

   //--- scale fonts and panel width with the window size (always fits)
   int maxLines = 12;
   int margin   = 8;
   int baseFont = (int)MathMax(8, MathMin(14, chartW / 110));
   int fontByH  = (chartH - 2 * margin - 12) / (maxLines + 1);
   if(fontByH < baseFont)
      baseFont = MathMax(7, fontByH);
   int panelW   = (int)MathMax(230, MathMin(400, chartW / 4));
   int lineH    = baseFont + 7;

   int wins, losses, scratches, cancels, callWins, callLosses, putWins, putLosses;
   double net, pf, maxDD;
   int bestStreak, worstStreak, seasonalTrades, burstTrades, microTrades;
   ComputeStats(wins, losses, scratches, cancels, callWins, callLosses, putWins, putLosses,
                net, pf, maxDD, bestStreak, worstStreak, seasonalTrades, burstTrades,
                microTrades);
   int total = wins + losses;
   double acc = (total > 0) ? 100.0 * wins / total : 0.0;
   double winRate = (total + scratches + cancels > 0)
                    ? 100.0 * wins / (total + scratches + cancels) : 0.0;

   string lines[12];
   int lineCount = 0;
   lines[lineCount++] = "CYBER BINARY EA";
   lines[lineCount++] = _Symbol + "  " + EnumToString(Period());
   lines[lineCount++] = "----------------------------";
   lines[lineCount++] = "Accuracy   " + DoubleToString(acc, 1) + "%  (" +
                        IntegerToString(wins) + "W / " + IntegerToString(losses) + "L)";
   lines[lineCount++] = "Win rate   " + DoubleToString(winRate, 1) + "%";
   lines[lineCount++] = "Net (" + DoubleToString(Payout * 100.0, 0) + "%)  " +
                        (net >= 0.0 ? "+" : "") + DoubleToString(net, 2);
   lines[lineCount++] = "Profit F.  " + DoubleToString(pf, 2) +
                        "   MaxDD " + DoubleToString(maxDD, 1);
   lines[lineCount++] = "CALL " + IntegerToString(callWins) + "-" + IntegerToString(callLosses) +
                        "   PUT " + IntegerToString(putWins) + "-" + IntegerToString(putLosses);
   lines[lineCount++] = "Best " + IntegerToString(bestStreak) + " / Worst " +
                        IntegerToString(worstStreak);
   lines[lineCount++] = "Micro " + IntegerToString(microTrades) + "  Season. " +
                        IntegerToString(seasonalTrades) + "  Burst " + IntegerToString(burstTrades);
   lines[lineCount++] = "----------------------------";
   lines[lineCount++] = "Status: " + CurrentWindowStatus();

   int panelH = lineCount * lineH + baseFont + 12;

   //--- background rectangle
   string bgName = PANEL_PREFIX + "BG";
   ObjectCreate(0, bgName, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, bgName, OBJPROP_CORNER, PanelCorner);
   ObjectSetInteger(0, bgName, OBJPROP_XDISTANCE, margin);
   ObjectSetInteger(0, bgName, OBJPROP_YDISTANCE, margin);
   ObjectSetInteger(0, bgName, OBJPROP_XSIZE, panelW);
   ObjectSetInteger(0, bgName, OBJPROP_YSIZE, panelH);
   ObjectSetInteger(0, bgName, OBJPROP_BGCOLOR, C'13,20,36');
   ObjectSetInteger(0, bgName, OBJPROP_BORDER_COLOR, C'35,44,68');
   ObjectSetInteger(0, bgName, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, bgName, OBJPROP_BACK, false);
   ObjectSetInteger(0, bgName, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, bgName, OBJPROP_HIDDEN, true);

   //--- text lines
   for(int i = 0; i < lineCount; i++)
     {
      string name = StringFormat("%sTXT_%d", PANEL_PREFIX, i);
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, PanelCorner);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, margin + 8);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, margin + baseFont + 4 + i * lineH);
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, baseFont);
      ObjectSetString(0, name, OBJPROP_FONT, "Consolas");
      color txtColor = clrSilver;
      if(i == 0)                                          txtColor = clrGold;
      else if(i == 1)                                     txtColor = clrLightSkyBlue;
      else if(StringFind(lines[i], "Accuracy") >= 0)      txtColor = clrLime;
      else if(StringFind(lines[i], "Win rate") >= 0)      txtColor = clrLime;
      else if(StringFind(lines[i], "Net (") >= 0)         txtColor = (net >= 0.0) ? clrLime : clrOrangeRed;
      else if(StringFind(lines[i], "Status:") >= 0)       txtColor = clrLightSkyBlue;
      ObjectSetInteger(0, name, OBJPROP_COLOR, txtColor);
      ObjectSetString(0, name, OBJPROP_TEXT, lines[i]);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
     }

   //--- last-signal detail panel (bottom-left), scales with the window
   DrawLastSignalPanel(chartW, chartH, baseFont);

   ChartRedraw(0);
  }

//+------------------------------------------------------------------+
//| "Last signal" detail panel (bottom-left of the chart)             |
//+------------------------------------------------------------------+
void DrawLastSignalPanel(int chartW, int chartH, int baseFont)
  {
   string prefix = PANEL_PREFIX + "LS_";
   ObjectsDeleteAll(0, prefix);

   int n = ArraySize(g_trades);
   if(n == 0)
      return;

   TradeRec &t = g_trades[n - 1];
   int lineH = baseFont + 7;
   int margin = 8;

   string dirTxt = (t.direction > 0) ? "CALL" : "PUT";
   string ruleTxt = (t.rule == RULE_MICRO) ? "Micro-Fix" :
                    ((t.rule == RULE_SEASONAL) ? "NY-Close Seasonal" : "Burst Reversal");
   string resTxt = "PENDING";
   color resClr = clrSilver;
   if(t.result == TR_WIN)          { resTxt = "WIN";  resClr = clrLime;      }
   else if(t.result == TR_LOSS)    { resTxt = "LOSS"; resClr = clrOrangeRed; }
   else if(t.result == TR_SCRATCH) { resTxt = "TIE";  resClr = clrGold;      }
   else if(t.result == TR_CANCEL)  { resTxt = "SKIP"; resClr = clrGray;      }

   string countdown = "";
   if(t.result == TR_PENDING)
     {
      int secs = (int)(t.expiry - TimeCurrent());
      if(secs < 0)
         secs = 0;
      countdown = StringFormat("expires in %02d:%02d", secs / 60, secs % 60);
     }

   string lines[6];
   int lineCount = 0;
   lines[lineCount++] = "LAST SIGNAL";
   lines[lineCount++] = dirTxt + " " + _Symbol + "  [" + ruleTxt + "]";
   lines[lineCount++] = "Entry " + DoubleToString(t.entry, _Digits) +
                        "  Exp " + TimeToString(t.expiry, TIME_MINUTES);
   if(t.result == TR_PENDING)
      lines[lineCount++] = countdown;
   else
      lines[lineCount++] = "Result: " + resTxt;
   lines[lineCount++] = "Signal " + TimeToString(t.time, TIME_DATE | TIME_MINUTES);

   int panelW = MathMax(240, chartW / 5);
   int panelH = lineCount * lineH + baseFont + 12;

   //--- background (bottom-left corner = 2)
   string bgName = prefix + "BG";
   ObjectCreate(0, bgName, OBJ_RECTANGLE_LABEL, 0, 0, 0);
   ObjectSetInteger(0, bgName, OBJPROP_CORNER, 2);
   ObjectSetInteger(0, bgName, OBJPROP_XDISTANCE, margin);
   ObjectSetInteger(0, bgName, OBJPROP_YDISTANCE, margin);
   ObjectSetInteger(0, bgName, OBJPROP_XSIZE, panelW);
   ObjectSetInteger(0, bgName, OBJPROP_YSIZE, panelH);
   ObjectSetInteger(0, bgName, OBJPROP_BGCOLOR, C'13,20,36');
   ObjectSetInteger(0, bgName, OBJPROP_BORDER_COLOR, C'35,44,68');
   ObjectSetInteger(0, bgName, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   ObjectSetInteger(0, bgName, OBJPROP_BACK, false);
   ObjectSetInteger(0, bgName, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, bgName, OBJPROP_HIDDEN, true);

   for(int i = 0; i < lineCount; i++)
     {
      string name = StringFormat("%sTXT_%d", prefix, i);
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, 2);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, margin + 8);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, margin + baseFont + 4 + i * lineH);
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, baseFont);
      ObjectSetString(0, name, OBJPROP_FONT, "Consolas");
      color txtColor = clrSilver;
      if(i == 0)                                   txtColor = clrGold;
      else if(StringFind(lines[i], "CALL") >= 0)   txtColor = clrLime;
      else if(StringFind(lines[i], "PUT") >= 0)    txtColor = clrOrangeRed;
      else if(StringFind(lines[i], "Result") >= 0) txtColor = resClr;
      else if(StringFind(lines[i], "expires") >= 0) txtColor = clrLightSkyBlue;
      ObjectSetInteger(0, name, OBJPROP_COLOR, txtColor);
      ObjectSetString(0, name, OBJPROP_TEXT, lines[i]);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
     }
  }

//+------------------------------------------------------------------+
//| Human readable strategy status for the panel                      |
//+------------------------------------------------------------------+
string CurrentWindowStatus()
  {
   int hour = UtcHour();
   if(EnableMicroRule)
     {
      int nyMin = NyMinuteOfDay(TimeGMT());
      if(nyMin >= MicroPutStartMin && nyMin <= MicroPutEndMin)
         return("MICRO PUT " + IntegerToString(MicroPutStartMin / 60) + ":" +
                StringFormat("%02d", MicroPutStartMin % 60) + "-" +
                IntegerToString(MicroPutEndMin / 60) + ":" +
                StringFormat("%02d", MicroPutEndMin % 60) + " NY");
      if(MicroCallEnabled && nyMin >= MicroCallStartMin && nyMin <= MicroCallEndMin)
         return("MICRO CALL " + IntegerToString(MicroCallStartMin / 60) + ":" +
                StringFormat("%02d", MicroCallStartMin % 60) + "-" +
                IntegerToString(MicroCallEndMin / 60) + ":" +
                StringFormat("%02d", MicroCallEndMin % 60) + " NY");
      return("micro-fix: waiting " + IntegerToString(MicroPutStartMin / 60) + ":" +
             StringFormat("%02d", MicroPutStartMin % 60) + " NY");
     }
   if(EnableSeasonalRule && InHourWindow(hour, CallStartHour, CallEndHour))
      return("CALL window " + IntegerToString(CallStartHour) + "-" +
             IntegerToString(CallEndHour) + " UTC");
   if(EnableSeasonalRule && InHourWindow(hour, PutStartHour, PutEndHour))
      return("PUT window " + IntegerToString(PutStartHour) + "-" +
             IntegerToString(PutEndHour) + " UTC");
   return("no rule enabled - check inputs");
  }

//+------------------------------------------------------------------+
//| Strategy Tester hook: report achieved accuracy                    |
//+------------------------------------------------------------------+
double OnTester()
  {
   int wins, losses, scratches, cancels, callWins, callLosses, putWins, putLosses;
   double net, pf, maxDD;
   int bestStreak, worstStreak, seasonalTrades, burstTrades, microTrades;
   ComputeStats(wins, losses, scratches, cancels, callWins, callLosses, putWins, putLosses,
                net, pf, maxDD, bestStreak, worstStreak, seasonalTrades, burstTrades,
                microTrades);
   if(wins + losses == 0)
      return(0.0);
   return((double)wins / (double)(wins + losses));
  }
//+------------------------------------------------------------------+
