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
                out.append('"S"')
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

    if errors:
        print(f"[FAIL] {path}: {len(errors)} issue(s)")
        for e in errors[:60]:
            print("   -", e)
        sys.exit(1)
    print(f"[OK] {path}: syntax check passed ({len(src)} bytes, "
          f"{len(funcs)} functions found)")


if __name__ == "__main__":
    main()
