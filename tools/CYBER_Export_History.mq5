//+------------------------------------------------------------------+
//| CYBER_Export_History.mq5                                         |
//| Export the FULL history of the current chart to a CSV file so the |
//| EA's feed can be analyzed against the research data.             |
//|                                                                  |
//| HOW TO USE:                                                      |
//|  1. Open the EURJPY M5 chart (the exact symbol+timeframe you run |
//|     the EA on).                                                  |
//|  2. Drag this script onto the chart (Scripts folder).            |
//|  3. It writes MQL5\Files\CYBER_<Symbol>_<Period>_history.csv    |
//|     (File > Open Data Folder > MQL5 > Files).                    |
//|  4. Upload that CSV to the repository (or attach it in chat).   |
//|                                                                  |
//| The file contains server-time bars (same series the EA scans),   |
//| the broker's server offset from GMT, and the export time.        |
//+------------------------------------------------------------------+
#property strict

input int ExportBars = 0;   // Bars to export (0 = ALL available history)

//+------------------------------------------------------------------+
//| Script program start function                                    |
//+------------------------------------------------------------------+
void OnStart()
  {
   int want = (ExportBars > 0) ? ExportBars : 2000000;

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int got = CopyRates(_Symbol, _Period, 0, want, rates);
   if(got < 2)
     {
      Print("ERROR: no history available (CopyRates returned ", got, ")");
      return;
     }

   string fname = "CYBER_" + SymbolFileName() + "_" + EnumToString(_Period) + "_history.csv";
   int h = FileOpen(fname, FILE_TXT | FILE_WRITE | FILE_ANSI |
                          FILE_SHARE_READ | FILE_SHARE_WRITE, ',');
   if(h == INVALID_HANDLE)
     {
      Print("ERROR: cannot write ", fname, " (error ", GetLastError(), ")");
      return;
     }

   FileWrite(h, "#offset_hours", DoubleToString((TimeCurrent() - TimeGMT()) / 3600.0, 2));
   FileWrite(h, "#export_gmt", TimeToString(TimeGMT(), TIME_DATE | TIME_MINUTES));
   FileWrite(h, "#bars", IntegerToString(got));
   FileWrite(h, "time(server)", "open", "high", "low", "close",
             "tick_volume", "spread", "real_volume");

   for(int i = got - 1; i >= 0; i--)      // oldest -> newest
      FileWrite(h,
                TimeToString(rates[i].time, TIME_DATE | TIME_MINUTES),
                DoubleToString(rates[i].open, _Digits),
                DoubleToString(rates[i].high, _Digits),
                DoubleToString(rates[i].low, _Digits),
                DoubleToString(rates[i].close, _Digits),
                IntegerToString(rates[i].tick_volume),
                IntegerToString(rates[i].spread),
                IntegerToString(rates[i].real_volume));

   FileClose(h);
   Print("Exported ", got, " bars to MQL5\\Files\\", fname,
         " | server offset from GMT ",
         DoubleToString((TimeCurrent() - TimeGMT()) / 3600.0, 2),
         "h | export GMT ", TimeToString(TimeGMT(), TIME_DATE | TIME_MINUTES));
  }

//+------------------------------------------------------------------+
//| Symbol name made safe for a file name                             |
//+------------------------------------------------------------------+
string SymbolFileName()
  {
   string s = _Symbol;
   for(int i = 0; i < StringLen(s); i++)
     {
      ushort c = StringGetCharacter(s, i);
      if(c == '/' || c == '\\' || c == ':' || c == '*' || c == '?' ||
         c == '"' || c == '<' || c == '>' || c == '|')
         StringSetCharacter(s, i, '_');
     }
   return(s);
  }
//+------------------------------------------------------------------+
