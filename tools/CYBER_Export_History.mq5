//+------------------------------------------------------------------+
//| CYBER_Export_History.mq5                                         |
//| Export the FULL history of the current chart to small CSV chunks |
//| so they can be uploaded to GitHub / shared easily.               |
//|                                                                  |
//| HOW TO USE:                                                      |
//|  1. Open the EURJPY M5 chart (the exact symbol+timeframe you run |
//|     the EA on).                                                  |
//|  2. Drag this script onto the chart (Scripts folder).            |
//|  3. It writes MQL5\Files\CYBER_<Symbol>_<Period>_history[_partN]|
//|     .csv files (File > Open Data Folder > MQL5 > Files).         |
//|  4. Upload ALL part files to the repository (GitHub web:         |
//|     Add file > Upload files - they are small). Tell me the path. |
//|                                                                  |
//| Compact mode writes only time(server)+close (all the analyzer    |
//| needs) - ~18 bytes per bar. 500,000 bars per chunk ~ 9 MB.       |
//| Chunks are chronological: part 1 = oldest bars.                  |
//+------------------------------------------------------------------+
#property strict

input int  ExportBars  = 0;        // Bars to export (0 = ALL available history)
input int  ChunkBars   = 500000;   // Max bars per output file (0 = single file)
input bool CompactOnly = true;     // true = time+close only (small files)

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

   int chunk = (ChunkBars > 0) ? ChunkBars : got;
   int parts = (got + chunk - 1) / chunk;
   string base = "CYBER_" + SymbolFileName() + "_" + EnumToString(_Period) + "_history";
   string offset = DoubleToString((TimeCurrent() - TimeGMT()) / 3600.0, 2);
   string gmtNow = TimeToString(TimeGMT(), TIME_DATE | TIME_MINUTES);

   for(int p = 0; p < parts; p++)
     {
      int startIdx = p * chunk;                       // chronological index (0 = oldest)
      int endIdx   = MathMin(startIdx + chunk, got);
      string fname = base + ((parts > 1) ? StringFormat("_part%02d", p + 1) : "") + ".csv";

      int h = FileOpen(fname, FILE_TXT | FILE_WRITE | FILE_ANSI |
                             FILE_SHARE_READ | FILE_SHARE_WRITE, ',');
      if(h == INVALID_HANDLE)
        {
         Print("ERROR: cannot write ", fname, " (error ", GetLastError(), ")");
         continue;
        }

      FileWrite(h, "#offset_hours", offset);
      FileWrite(h, "#export_gmt", gmtNow);
      FileWrite(h, "#part", IntegerToString(p + 1), IntegerToString(parts));
      FileWrite(h, "#bars", IntegerToString(endIdx - startIdx));
      if(CompactOnly)
         FileWrite(h, "time(server)", "close");
      else
         FileWrite(h, "time(server)", "open", "high", "low", "close",
                   "tick_volume", "spread", "real_volume");

      for(int j = startIdx; j < endIdx; j++)
        {
         int i = got - 1 - j;                        // as-series index of bar j
         if(CompactOnly)
            FileWrite(h,
                      TimeToString(rates[i].time, TIME_DATE | TIME_MINUTES),
                      DoubleToString(rates[i].close, _Digits));
         else
            FileWrite(h,
                      TimeToString(rates[i].time, TIME_DATE | TIME_MINUTES),
                      DoubleToString(rates[i].open, _Digits),
                      DoubleToString(rates[i].high, _Digits),
                      DoubleToString(rates[i].low, _Digits),
                      DoubleToString(rates[i].close, _Digits),
                      IntegerToString(rates[i].tick_volume),
                      IntegerToString(rates[i].spread),
                      IntegerToString(rates[i].real_volume));
        }
      FileClose(h);
      Print("Exported part ", p + 1, "/", parts, " (", endIdx - startIdx,
            " bars) to MQL5\\Files\\", fname);
     }

   Print("DONE: ", got, " bars in ", parts, " file(s) | server offset from GMT ",
         offset, "h | export GMT ", gmtNow);
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
