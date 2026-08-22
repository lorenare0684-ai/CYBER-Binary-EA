#!/usr/bin/env python3
"""Lightweight MQL5 static checker used to keep the EA clean:
   - strips comments/strings, validates bracket balance
   - finds function definitions & duplicate names
   - checks every statement ends with ';'
   - checks preprocessor lines (#property/#define/#include/input group)
   - reports suspicious constructs (TODO, ',,', double ';;', unterminated strings)
   Exit code 1 on any error, 0 on clean.
"""
import re
import sys


def strip_code(src):
    out = []
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j == -1 else j
        elif c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            if j == -1:
                out.append("/* UNTERMINATED BLOCK COMMENT */")
                i = n
            else:
                i = j + 2
        elif c in "CDTB" and i + 1 < n and src[i + 1] == "'":
            j = i + 2
            while j < n:
                if src[j] == "'":
                    break
                j += 1
            if j >= n:
                out.append("'UNTERMINATED LITERAL'")
                i = n
            else:
                out.append("'1'")
                i = j + 1
        elif c == '"':
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == '"':
                    break
                j += 1
            if j >= n:
                out.append('"UNTERMINATED STRING"')
                i = n
            else:
                out.append('"1"')
                i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def check_balance(code, name):
    errors = []
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    for idx, ch in enumerate(code):
        if ch in "([{":
            stack.append((ch, idx))
        elif ch in ")]}":
            if not stack or stack[-1][0] != pairs[ch]:
                errors.append(f"line {code[:idx].count(chr(10))+1}: unmatched '{ch}'")
            else:
                stack.pop()
    for ch, idx in stack:
        errors.append(f"line {code[:idx].count(chr(10))+1}: unclosed '{ch}'")
    return errors


def find_functions(code):
    # match: <type> <name>(<args>) {  at top level (rough)
    funcs = []
    for m in re.finditer(r"(?m)^(?:[A-Za-z_][\w]*\s+)+([A-Za-z_]\w*)\s*\(([^;{}]*)\)\s*(?:\{|;)", code):
        funcs.append((m.group(1), m.start()))
    return funcs


def statement_check(code):
    """Cheap check: inside function bodies, lines containing ';' balance; and
    '}' must be followed by ';' or another '}' (struct/union), never by text."""
    errors = []
    for m in re.finditer(r"\}([A-Za-z_])", code):
        errors.append(f"line {code[:m.start()].count(chr(10))+1}: '}}' followed by identifier")
    for m in re.finditer(r";\s*;", code):
        errors.append(f"line {code[:m.start()].count(chr(10))+1}: double ';;'")
    return errors


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "ea/CYBER_Binary_Signal_EA.mq5"
    src = open(path, encoding="utf-8-sig").read()
    code = strip_code(src)
    errors = []

    errors += check_balance(code, path)
    errors += statement_check(code)

    # preprocessor sanity
    for m in re.finditer(r"(?m)^\s*(#\w+)(.*)$", src):
        directive, rest = m.group(1), m.group(2)
        if directive == "#property":
            if not re.search(r'"(?:[^"\\]|\\.)*"', rest):
                errors.append(f"line {src[:m.start()].count(chr(10))+1}: #property needs a quoted value")
        elif directive == "#define":
            if not re.search(r"\w+\s+[^\s]", rest):
                errors.append(f"line {src[:m.start()].count(chr(10))+1}: #define needs name and value")

    # input declarations sanity
    for m in re.finditer(r"(?m)^\s*input\s+(group\s+)?[\w\s]+\s+(\w+)\s*=", src):
        pass
    for m in re.finditer(r"(?m)^\s*input\s+(?!group)[\w\s]+(\w+)\s*=([^;]*);", src):
        name, val = m.group(1), m.group(2)
        if not val.strip():
            errors.append(f"line {src[:m.start()].count(chr(10))+1}: input '{name}' has no default value")

    # duplicate function definitions
    funcs = find_functions(code)
    seen = {}
    for name, pos in funcs:
        if name in ("if", "for", "while", "switch", "return", "else"):
            continue
        seen.setdefault(name, []).append(pos)
    for name, poss in seen.items():
        if len(poss) > 1:
            errors.append(f"duplicate function '{name}' defined {len(poss)} times")

    # required entry points
    for ep in ("OnInit", "OnDeinit", "OnTick", "OnTimer"):
        if not re.search(r"\b" + ep + r"\s*\(", code):
            errors.append(f"missing required entry point {ep}()")

    # undeclared identifiers
    unknown = check_identifiers(src, code)
    for name in unknown[:40]:
        errors.append(f"undeclared identifier '{name}'")

    # MQL5 forbids non-parameter references: 'Type &name = ...' local decls
    # (this produced the real 'reference cannot used' MetaEditor errors)
    for m in re.finditer(r"(?:^|[;{]\s*)([A-Za-z_]\w*)\s*&\s*([A-Za-z_]\w*)\s*=", code):
        errors.append(f"line {src[:m.start()].count(chr(10))+1}: reference declaration "
                      f"'{m.group(1)} &{m.group(2)} = ...' is not allowed in MQL5 "
                      f"(references only valid as function parameters) - use a copy or index")

    # string variable compared with a numeric #define: MetaEditor errors
    # 'implicit conversion from int to string' (e.g. verNum != LOG_VERSION)
    string_vars = set()
    for m in re.finditer(r"\bstring\s+([A-Za-z_]\w*)\b", code):
        string_vars.add(m.group(1))
    for m in re.finditer(r"(?m)^\s*input\s+string\s+(\w+)\s*=", src):
        string_vars.add(m.group(1))
    num_defines = {n for n, v in re.findall(r"(?m)^\s*#define\s+(\w+)\s+(\S+)", src)
                   if re.fullmatch(r"[-+]?\d+(\.\d+)?", v)}
    for m in re.finditer(r"\b([A-Za-z_]\w*)\s*(==|!=)\s*([A-Za-z_]\w*)\b", code):
        a, op, b = m.group(1), m.group(2), m.group(3)
        if a in string_vars and b in num_defines:
            errors.append(f"line {src[:m.start()].count(chr(10))+1}: '{a} {op} {b}' "
                          f"compares a string variable with a numeric #define - MetaEditor "
                          f"errors 'implicit conversion from int to string' (make the "
                          f"#define a string literal or use IntegerToString())")
        elif b in string_vars and a in num_defines:
            errors.append(f"line {src[:m.start()].count(chr(10))+1}: '{a} {op} {b}' "
                          f"compares a string variable with a numeric #define - MetaEditor "
                          f"errors 'implicit conversion from int to string' (make the "
                          f"#define a string literal or use IntegerToString())")

    if errors:
        print(f"[FAIL] {path}: {len(errors)} issue(s)")
        for e in errors[:60]:
            print("   -", e)
        sys.exit(1)
    print(f"[OK] {path}: syntax check passed ({len(src)} bytes, "
          f"{len(funcs)} functions found)")




# ---------------------------------------------------------------------------
# Identifier resolution: every identifier used in the code must be declared
# (input, #define, #import, global/local/param) or a known MQL5 builtin.
# ---------------------------------------------------------------------------

MQL5_KEYWORDS = {
    "if", "else", "for", "while", "do", "return", "break", "continue", "switch",
    "case", "default", "struct", "enum", "const", "static", "extern", "virtual",
    "void", "int", "double", "bool", "string", "datetime", "color", "long",
    "ulong", "uchar", "short", "ushort", "char", "float", "this", "true",
    "false", "NULL", "new", "delete", "template", "typename",
}

# Predefined MQL5 variables / compiler constants
MQL5_PREDEFINED = {
    "_Symbol", "_Period", "_Digits", "_Point", "_Bars", "_LastError",
    "_LastTradeError", "_RandomSeed", "_StopFlag", "_UninitReason",
    "_AppliedTo", "_BrokerTime", "_IsOptimization", "_IsTesting", "_IsVisualMode",
    "_IsDLLsAllowed", "_IsExpertEnabled", "_IsTradeAllowed", "_IsTradeContextBusy",
    "PERIOD_CURRENT", "PERIOD_M1", "PERIOD_M5", "PERIOD_M15", "PERIOD_M30",
    "PERIOD_H1", "PERIOD_H4", "PERIOD_D1", "PERIOD_W1", "PERIOD_MN1",
    "INVALID_HANDLE", "INVALID_HISTORY", "CHARTS_MAX", "COPY_TICKS_INFO",
}

# Common MQL5 standard library (functions + constants used in this EA)
MQL5_BUILTINS = {
    # --- object / chart ---
    "ObjectCreate", "ObjectFind", "ObjectDelete", "ObjectsDeleteAll", "ObjectSetInteger",
    "ObjectSetDouble", "ObjectSetString", "ObjectGetInteger", "ObjectGetString",
    "ChartRedraw", "ChartGetInteger", "ChartSetInteger", "ChartSetString", "ChartApplyTemplate",
    "OBJ_ARROW_UP", "OBJ_ARROW_DOWN", "OBJ_TEXT", "OBJ_VLINE", "OBJ_HLINE",
    "OBJ_RECTANGLE_LABEL", "OBJ_LABEL", "OBJ_TREND", "OBJ_BUTTON", "OBJ_EDIT",
    "OBJPROP_COLOR", "OBJPROP_WIDTH", "OBJPROP_STYLE", "OBJPROP_BACK", "OBJPROP_TOOLTIP",
    "OBJPROP_FONTSIZE", "OBJPROP_FONT", "OBJPROP_ANCHOR", "OBJPROP_SELECTABLE",
    "OBJPROP_HIDDEN", "OBJPROP_CORNER", "OBJPROP_XDISTANCE", "OBJPROP_YDISTANCE",
    "OBJPROP_XSIZE", "OBJPROP_YSIZE", "OBJPROP_BGCOLOR", "OBJPROP_BORDER_COLOR",
    "OBJPROP_BORDER_TYPE", "OBJPROP_TEXT", "OBJPROP_STATE", "OBJPROP_ZORDER",
    "OBJPROP_ANGLE", "OBJPROP_RAY_RIGHT", "OBJPROP_PRICE", "OBJPROP_TIME",
    "OBJPROP_LEVELS", "OBJPROP_SCALE", "OBJPROP_DRAWLINES", "OBJPROP_DEVIATION",
    "OBJPROP_ELLIPSE", "OBJPROP_FILL", "OBJPROP_ARROWCODE", "OBJPROP_TIMEFRAMES",
    "OBJPROP_CREATETIME", "OBJPROP_READONLY", "OBJPROP_ALIGN", "OBJPROP_TEXTCOLOR",
    "ANCHOR_LEFT_UPPER", "ANCHOR_LEFT", "ANCHOR_LEFT_LOWER", "ANCHOR_CENTER",
    "ANCHOR_RIGHT", "ANCHOR_RIGHT_UPPER", "ANCHOR_RIGHT_LOWER", "ANCHOR_TOP",
    "ANCHOR_BOTTOM", "ANCHOR_CENTER_UPPER", "ANCHOR_CENTER_LOWER",
    "CORNER_LEFT_UPPER", "CORNER_LEFT_LOWER", "CORNER_RIGHT_UPPER", "CORNER_RIGHT_LOWER",
    "STYLE_SOLID", "STYLE_DASH", "STYLE_DOT", "STYLE_DASHDOT", "STYLE_DASHDOTDOT",
    "BORDER_FLAT", "BORDER_RAISED", "BORDER_SUNKEN",
    "CHART_WIDTH_IN_PIXELS", "CHART_HEIGHT_IN_PIXELS", "CHART_COLOR_BACKGROUND",
    "CHART_COLOR_FOREGROUND", "CHART_SHOW_GRID", "CHART_SHOW_OHLC", "CHART_MODE",
    "ALIGN_RIGHT", "ALIGN_LEFT", "ALIGN_CENTER",
    # --- market data / indicators ---
    "iClose", "iOpen", "iHigh", "iLow", "iTime", "iVolume", "iBars", "iBarShift",
    "iHighest", "iLowest", "iMA", "iRSI", "iStochastic", "iATR", "iBands", "iSAR",
    "iMACD", "iADX", "iCCI", "iMomentum", "iWPR", "iOBV", "iIchimoku", "iFractals",
    "iGator", "iBWMFI", "iDEMA", "iEnvelopes", "iForce", "iOsMA", "iRVI", "iStdDev",
    "iTEMA", "iTriX", "iVIDyA", "iCustom", "CopyBuffer", "CopyRates", "CopyClose",
    "CopyOpen", "CopyHigh", "CopyLow", "CopyTime", "CopyTicks", "CopyTicksRange",
    "SeriesInfoInteger", "Bars", "SymbolInfoDouble", "SymbolInfoInteger",
    "SymbolInfoString", "Symbol", "Period", "Digits", "Point", "MarketInfo",
    "MODE_EMA", "MODE_SMA", "MODE_SMMA", "MODE_LWMA", "MODE_MAIN", "MODE_SIGNAL",
    "MODE_UPPER", "MODE_LOWER", "PRICE_CLOSE", "PRICE_OPEN", "PRICE_HIGH", "PRICE_LOW",
    "PRICE_MEDIAN", "PRICE_TYPICAL", "PRICE_WEIGHTED", "STO_LOWHIGH", "STO_CLOSECLOSE",
    # --- strings / formatting ---
    "StringFormat", "StringLen", "StringFind", "StringSubstr", "StringCompare",
    "StringConcatenate", "StringToLower", "StringToUpper", "StringTrimLeft",
    "StringTrimRight", "StringSplit", "StringToInteger", "StringToDouble",
    "StringToTime", "StringToColor", "IntegerToString", "DoubleToString",
    "TimeToString", "ColorToString", "ShortToString", "CharArrayToString",
    "StringToShortArray", "StringToCharArray", "StringGetCharacter", "StringSetCharacter",
    "StringFill", "StringInit", "StringSetLength", "StringToShortArray",
    "CharToString", "EnumToString",
    # --- math ---
    "MathMax", "MathMin", "MathAbs", "MathRound", "MathFloor", "MathCeil",
    "MathSqrt", "MathPow", "MathLog", "MathLog10", "MathExp", "MathSin", "MathCos",
    "MathTan", "MathArcsin", "MathArccos", "MathArctan", "MathMod", "MathRand",
    "MathSrand", "MathIsValidNumber", "MathSum", "MathMean", "MathMedian",
    # --- time ---
    "TimeCurrent", "TimeGMT", "TimeLocal", "TimeToStruct", "TimeFromStruct",
    "TimeToString", "TimeTradeServer", "TimeDayOfWeek", "TimeDayOfYear",
    "TimeHour", "TimeMinute", "TimeSeconds", "TimeYear", "TimeMonth", "TimeDay",
    "MqlDateTime", "datetime", "TIME_DATE", "TIME_MINUTES", "TIME_SECONDS",
    "TIME_DATE|TIME_MINUTES",
    # --- files ---
    "FileOpen", "FileClose", "FileWrite", "FileWriteString", "FileReadString",
    "FileReadInteger", "FileReadDouble", "FileIsExist", "FileDelete", "FileFlush",
    "FileSeek", "FileTell", "FileSize", "FileIsEnding", "FileGetSize", "FileCopy",
    "FileMove", "FileCreate", "FileFindFirst", "FileFindNext", "FileFindClose",
    "FILE_TXT", "FILE_READ", "FILE_WRITE", "FILE_ANSI", "FILE_UNICODE",
    "FILE_SHARE_READ", "FILE_SHARE_WRITE", "FILE_COMMON", "FILE_BIN", "FILE_CSV",
    "FILE_REWRITE", "FILE_READ|FILE_WRITE",
    # --- terminal / account ---
    "TerminalInfoString", "TerminalInfoInteger", "TerminalInfoDouble",
    "TERMINAL_PATH", "TERMINAL_DATA_PATH", "TERMINAL_NAME", "TERMINAL_COMPANY",
    "TERMINAL_COMMUNITY_ACCOUNT", "TERMINAL_CPU_CORES", "TERMINAL_DLLS_ALLOWED",
    "TERMINAL_LANGUAGE", "TERMINAL_MAXBARS", "TERMINAL_MEMORY_AVAILABLE",
    "TERMINAL_MEMORY_PHYSICAL", "TERMINAL_MEMORY_TOTAL", "TERMINAL_MEMORY_USED",
    "TERMINAL_TRADE_ALLOWED", "TERMINAL_VERSION", "TERMINAL_SCREEN_DPI",
    "AccountInfoDouble", "AccountInfoInteger", "AccountInfoString", "AccountBalance",
    "AccountEquity", "AccountFreeMargin", "AccountProfit", "AccountName",
    "ACCOUNT_BALANCE", "ACCOUNT_EQUITY", "ACCOUNT_MARGIN_FREE", "ACCOUNT_MARGIN_LEVEL",
    "ACCOUNT_LEVERAGE", "ACCOUNT_PROFIT", "ACCOUNT_CURRENCY", "ACCOUNT_LOGIN",
    "ACCOUNT_TRADE_MODE", "ACCOUNT_TRADE_EXPERT", "ACCOUNT_TRADE_ALLOWED",
    "ACCOUNT_MARGIN_SO_MODE", "ACCOUNT_MARGIN_SO_CALL", "ACCOUNT_MARGIN_SO_SO",
    "ACCOUNT_SERVER", "ACCOUNT_COMPANY", "ACCOUNT_NAME", "ACCOUNT_TRADE_MODE_DEMO",
    "ACCOUNT_TRADE_MODE_CONTEST", "ACCOUNT_TRADE_MODE_REAL",
    # --- alerts / misc ---
    "Alert", "Print", "PrintFormat", "Comment", "PlaySound", "SendNotification",
    "SendMail", "Sleep", "GetTickCount", "GetLastError", "ResetLastError",
    "SetErrorDescription", "GetErrorDescription", "DebugBreak", "EventSetTimer",
    "EventSetMillisecondTimer", "EventKillTimer", "EventChartCustom", "ChartIndicatorAdd",
    "ExpertRemove", "TerminalClose", "SignalBaseGetInteger", "SignalBaseSelect",
    # --- colors ---
    "clrBlack", "clrWhite", "clrRed", "clrGreen", "clrBlue", "clrGray", "clrSilver",
    "clrGold", "clrOrange", "clrOrangeRed", "clrLime", "clrYellow", "clrAqua",
    "clrMagenta", "clrCyan", "clrBrown", "clrDarkGray", "clrDarkGreen",
    "clrLightSkyBlue", "clrDodgerBlue", "clrFireBrick", "clrForestGreen", "clrGainsboro",
    "clrHotPink", "clrIndigo", "clrKhaki", "clrLightBlue", "clrLightCoral",
    "clrLightCyan", "clrLightGray", "clrLightGreen", "clrLightPink", "clrLightSalmon",
    "clrLightSeaGreen", "clrLightYellow", "clrLimeGreen", "clrMaroon", "clrMidnightBlue",
    "clrNavy", "clrOlive", "clrOrchid", "clrPaleGoldenrod", "clrPaleGreen",
    "clrPaleTurquoise", "clrPaleVioletRed", "clrPeru", "clrPink", "clrPlum",
    "clrPowderBlue", "clrPurple", "clrRosyBrown", "clrRoyalBlue", "clrSaddleBrown",
    "clrSalmon", "clrSandyBrown", "clrSeaGreen", "clrSeaShell", "clrSienna",
    "clrSkyBlue", "clrSlateBlue", "clrSlateGray", "clrSnow", "clrSpringGreen",
    "clrSteelBlue", "clrTan", "clrTeal", "clrThistle", "clrTomato", "clrTurquoise",
    "clrViolet", "clrWheat", "clrWhiteSmoke", "clrYellowGreen",
    # --- misc used ---
    "INVALID_HANDLE", "OnInit", "OnDeinit", "OnTick", "OnTimer", "OnTester",
    "ArrayResize", "ArraySetAsSeries", "ArraySize", "ArrayInitialize", "ArrayFill",
    "ArrayCopy", "ArrayCompare", "ArrayInsert", "ArrayRemove", "ArrayReverse",
    "ArraySort", "ArrayMaximum", "ArrayMinimum", "ArrayRange", "ArrayGetAsSeries",
    "IndicatorRelease", "MQLInfoInteger", "MQL5_PROGRAM_NAME", "MQL_TESTER",
    "MQL_OPTIMIZATION", "MQL_VISUAL_MODE", "MQL_FRAME_MODE", "MQL_PROFILER",
    "MQL_DEBUG", "MQL_TRACE", "MQL_PROGRAM_TYPE", "MQL_DLLS_ALLOWED",
    "MQL_TRADE_ALLOWED", "MQL_SIGNALS_ALLOWED", "MQL_TERMINAL_MAXBARS",
    "MQL_CODEPAGE", "MQL_LICENSE_TYPE", "PROGRAM_SCRIPT", "PROGRAM_EXPERT",
    "PROGRAM_INDICATOR", "PROGRAM_SERVICE", "PeriodSeconds", "CHARTEVENT_CHART_CHANGE",
    "CHARTEVENT_KEYDOWN", "CHARTEVENT_MOUSE_MOVE", "CHARTEVENT_OBJECT_CREATE",
    "CHARTEVENT_OBJECT_DELETE", "CHARTEVENT_OBJECT_CLICK", "CHARTEVENT_OBJECT_DRAG",
    "CHARTEVENT_OBJECT_ENDEDIT", "CHARTEVENT_CLICK", "CHARTEVENT_CUSTOM",
    "INIT_SUCCEEDED", "INIT_FAILED", "INIT_PARAMETERS_INCORRECT", "INIT_AGENT_NOT_SUPPORTED",
    "MqlRates", "MqlTick", "MqlTradeRequest", "MqlTradeResult", "MqlTradeCheckResult",
    "MqlBookInfo", "MqlParam", "MqlCalendarValue", "MqlCalendarCountry", "MqlCalendarEvent",
    "MqlDateTime", "MqlStr", "MqlError",
    "OnChartEvent", "OnTrade", "OnTradeTransaction", "OnBookEvent",
    "D'", "B'", "C'", "H'", "S'", "W'", "U'",
}


def collect_declared(src, code):
    """Names declared in the file: #define, #import, inputs, functions+params,
    struct names, global/local variables (incl. multi-declarations)."""
    declared = set()

    # #define NAME ...
    for m in re.finditer(r"(?m)^\s*#define\s+(\w+)", src):
        declared.add(m.group(1))

    # #import block declarations
    in_import = False
    for line in src.splitlines():
        s = line.strip()
        if s.startswith("#import") and '"' in s:
            in_import = True
            continue
        if s == "#import":
            in_import = False
            continue
        if in_import:
            for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", s):
                declared.add(m.group(1))

    # input TYPE NAME = ...   (skip 'input group "..."')
    for m in re.finditer(r"(?m)^\s*input\s+(?!group)[\w\s]+?(\w+)\s*=", src):
        declared.add(m.group(1))

    # struct NAME { ... }
    for m in re.finditer(r"\bstruct\s+([A-Za-z_]\w*)", code):
        declared.add(m.group(1))

    # function definitions: NAME(...) -> function name + parameter names
    for m in re.finditer(r"(?m)^\s*(?:[A-Za-z_]\w*\s+)+([A-Za-z_]\w*)\s*\(([^;{}]*)\)\s*(?:\{|;)", code):
        declared.add(m.group(1))
        params = m.group(2)
        depth = 0
        parts = []
        cur = []
        for ch in params:
            if ch == "(":
                depth += 1
            if ch == ")":
                depth -= 1
            if ch == "," and depth == 0:
                parts.append("".join(cur))
                cur = []
            else:
                cur.append(ch)
        if cur:
            parts.append("".join(cur))
        for p in parts:
            p = p.strip()
            if not p:
                continue
            p = p.split("=")[0].strip()
            toks = [t for t in re.split(r"[&*\s]+", p) if t]
            if toks:
                declared.add(toks[-1])

    # variable declarations: TYPE [&] NAME [= init] [, NAME [= init]]* ;
    TYPE_KW = r"(?:const\s+)?(?:int|double|bool|string|datetime|color|long|ulong|" \
              r"uchar|short|ushort|char|float)"
    for m in re.finditer(r"\b" + TYPE_KW + r"\s+([A-Za-z_]\w*)([^;{}]*);", code):
        declared.add(m.group(1))
        rest = m.group(2)
        depth = 0
        seg = []
        for ch in rest:
            if ch in "([":
                depth += 1
            if ch in ")]":
                depth -= 1
            if ch == "," and depth == 0:
                t = re.split(r"[&*\s]+", "".join(seg).strip())
                if t and t[-1]:
                    declared.add(t[-1])
                seg = []
            else:
                seg.append(ch)
        if seg:
            t = re.split(r"[&*\s]+", "".join(seg).strip())
            if t and t[-1]:
                declared.add(t[-1])

    # struct-typed / custom-typed declarations: NAME [&] NAME = ... or ;
    for m in re.finditer(r"(?m)(?:^|[;{])\s*([A-Za-z_]\w*)\s*(?:&\s*)?([A-Za-z_]\w*)\s*(?:=|;|,|\[|\))", code):
        declared.add(m.group(2))

    return declared


def check_identifiers(src, code):
    """Every identifier in the code must be declared or a builtin."""
    declared = collect_declared(src, code)
    # drop preprocessor + input declaration lines, keep only the object of member access
    code = re.sub(r"(?m)^\s*#\w+.*$", "", code)
    code = re.sub(r"(?m)^\s*input\s+.*$", "", code)
    code = re.sub(r"\b(\w+)\.(\w+)", r"\1", code)
    used = set(re.findall(r"\b[A-Za-z_]\w*\b", code))
    known = declared | MQL5_KEYWORDS | MQL5_PREDEFINED | MQL5_BUILTINS
    unknown = sorted(u for u in used if u not in known)
    return unknown




if __name__ == "__main__":
    main()
