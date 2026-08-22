#!/usr/bin/env python3
"""Add the last-signal detail panel to the EA."""
import sys

PATH = "ea/CYBER_Binary_Signal_EA.mq5"
src = open(PATH).read()

# --- insert DrawLastSignalPanel before the status function ---
anchor = '''//+------------------------------------------------------------------+
//| Human readable strategy status for the panel                      |
//+------------------------------------------------------------------+'''
panel = '''//+------------------------------------------------------------------+
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

'''
assert anchor in src
src = src.replace(anchor, panel + anchor)

# --- call it from UpdatePanel before ChartRedraw ---
old2 = '''      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
     }
   ChartRedraw(0);
  }'''
new2 = '''      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
     }

   //--- last-signal detail panel (bottom-left), scales with the window
   DrawLastSignalPanel(chartW, chartH, baseFont);

   ChartRedraw(0);
  }'''
assert old2 in src
src = src.replace(old2, new2, 1)

open(PATH, "w").write(src)
print("part 3 ok")
