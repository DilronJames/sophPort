"""Password strength analyzer, Python CLI + library.

Scores a password the way an attacker would: by the size of the search space
it lives in, not by checklists. Companion JS port (static/js/password.js)
runs the same logic in the browser so live web analysis never sends the
password over the wire.

Usage:
    python password.py 'my password here'
    python password.py --interactive
"""

from __future__ import annotations

import argparse
import getpass
import math
import re
from dataclasses import dataclass, field
from typing import Any

# Charset class sizes, kept conservative; an attacker assumes the largest
# class their dictionary supports.
CHARSET_LOWER   = 26
CHARSET_UPPER   = 26
CHARSET_DIGITS  = 10
CHARSET_SYMBOLS = 33
CHARSET_SPACE   = 1
CHARSET_OTHER   = 100   # anything outside ASCII printable (UTF-8 letters, etc.)

# Attacker speed presets (guesses per second).
ATTACKER_SPEEDS = {
    "throttled online (10/s)":      10,
    "fast online (1k/s)":           1_000,
    "offline slow hash (1M/s)":     1_000_000,
    "offline GPU farm (10B/s)":     10_000_000_000,
}

# Small built-in dictionary, passwords that everyone tries first.
# Not exhaustive; in production you'd check against rockyou.txt or HIBP.
COMMON_PASSWORDS = {
    "password", "passw0rd", "p@ssw0rd", "p@ssword",
    "123456", "12345678", "123456789", "qwerty", "qwertyuiop",
    "letmein", "iloveyou", "admin", "welcome", "monkey",
    "dragon", "abc123", "111111", "000000", "1q2w3e4r",
    "trustno1", "sunshine", "princess", "football", "starwars",
    "superman", "batman", "master", "ninja", "shadow",
    "michael", "andrew", "joshua", "matthew",
}

# Common keyboard sequences for adjacent-key detection.
KEYBOARD_ROWS = [
    "qwertyuiop", "asdfghjkl", "zxcvbnm",
    "1234567890",
    "qazwsxedcrfvtgbyhnujmikolp",  # zig-zag
]

STRENGTH_LABELS = [
    ("Critical",  0,  28,  "#ef4444"),
    ("Weak",     28,  40,  "#f97316"),
    ("Fair",     40,  60,  "#eab308"),
    ("Strong",   60,  80,  "#22c55e"),
    ("Vault",    80, 999,  "#16ff65"),
]


@dataclass
class PasswordReport:
    """Everything we know about a password's strength."""
    length: int
    charset_size: int
    charsets_used: list[str]
    raw_entropy_bits: float           # length * log2(alphabet)
    effective_entropy_bits: float     # after penalties for common patterns
    strength_label: str
    strength_color: str
    strength_score: int               # 0-100
    crack_times: dict[str, str]       # human-readable durations
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "length": self.length,
            "charset_size": self.charset_size,
            "charsets_used": self.charsets_used,
            "raw_entropy_bits": round(self.raw_entropy_bits, 1),
            "effective_entropy_bits": round(self.effective_entropy_bits, 1),
            "strength_label": self.strength_label,
            "strength_color": self.strength_color,
            "strength_score": self.strength_score,
            "crack_times": self.crack_times,
            "issues": self.issues,
            "suggestions": self.suggestions,
        }


# ---------------------------------------------------------------------------
# Analysis primitives
# ---------------------------------------------------------------------------

def detect_charset(pw: str) -> tuple[int, list[str]]:
    """Return (effective alphabet size, list of charset class names)."""
    used = []
    size = 0
    if re.search(r"[a-z]", pw): used.append("lowercase"); size += CHARSET_LOWER
    if re.search(r"[A-Z]", pw): used.append("uppercase"); size += CHARSET_UPPER
    if re.search(r"\d",  pw):   used.append("digits");    size += CHARSET_DIGITS
    if re.search(r"[!-/:-@\[-`{-~]", pw):
        used.append("symbols"); size += CHARSET_SYMBOLS
    if " " in pw:
        used.append("spaces"); size += CHARSET_SPACE
    if re.search(r"[^\x20-\x7e]", pw):
        used.append("extended"); size += CHARSET_OTHER
    return max(size, 1), used


def has_sequential_run(pw: str, min_len: int = 4) -> bool:
    """True if pw contains a sequential run like 'abcd' or '1234'."""
    pw = pw.lower()
    for i in range(len(pw) - min_len + 1):
        chunk = pw[i:i + min_len]
        if all(ord(chunk[j + 1]) - ord(chunk[j]) == 1 for j in range(min_len - 1)):
            return True
    return False


def has_repeating_run(pw: str, min_len: int = 3) -> bool:
    """True if pw contains a repeat like 'aaaa' or '!!!!'."""
    return bool(re.search(r"(.)\1{" + str(min_len - 1) + ",}", pw))


def has_keyboard_walk(pw: str, min_len: int = 4) -> bool:
    """True if pw contains an adjacent-key walk like 'qwerty' or 'asdf'."""
    pw_l = pw.lower()
    for row in KEYBOARD_ROWS:
        for i in range(len(row) - min_len + 1):
            if row[i:i + min_len] in pw_l:
                return True
    return False


def is_common(pw: str) -> bool:
    return pw.lower() in COMMON_PASSWORDS


def is_year(pw: str) -> bool:
    """True if pw is just a 4-digit year-ish number (1900-2099)."""
    return bool(re.fullmatch(r"(19|20)\d{2}", pw))


def humanize_seconds(s: float) -> str:
    """Convert a number of seconds into a short human-readable string."""
    if s < 1:
        return "instant"
    if s < 60:
        return f"{s:.0f} sec"
    if s < 3_600:
        return f"{s / 60:.0f} min"
    if s < 86_400:
        return f"{s / 3_600:.1f} hours"
    if s < 31_536_000:
        return f"{s / 86_400:.0f} days"
    years = s / 31_536_000
    if years < 1_000:
        return f"{years:,.0f} years"
    if years < 1_000_000:
        return f"{years / 1_000:,.0f}K years"
    if years < 1_000_000_000:
        return f"{years / 1_000_000:,.0f}M years"
    if years < 1_000_000_000_000:
        return f"{years / 1_000_000_000:,.0f}B years"
    return "heat-death of the universe"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def analyze(pw: str) -> PasswordReport:
    """Score a password and explain why it scored that way."""
    if pw is None:
        pw = ""

    length = len(pw)
    charset_size, used = detect_charset(pw)
    raw_bits = length * math.log2(charset_size) if length > 0 else 0.0

    issues: list[str] = []
    suggestions: list[str] = []
    penalty = 0.0

    if length == 0:
        issues.append("Empty.")
        suggestions.append("Type a password to get a score.")
    if length < 8 and length > 0:
        issues.append("Shorter than 8 characters.")
        suggestions.append("Add length - every extra character roughly doubles the cost.")
    if length < 12 and length >= 8:
        suggestions.append("Aim for 14+ characters for online-attack resistance.")

    if is_common(pw):
        issues.append("This is on every cracker's first-pass list.")
        penalty += 40
    if has_sequential_run(pw):
        issues.append("Contains a sequential run (e.g. 'abcd' / '1234').")
        penalty += 12
    if has_repeating_run(pw):
        issues.append("Has a repeating-character run.")
        penalty += 10
    if has_keyboard_walk(pw):
        issues.append("Includes an adjacent-key walk (e.g. 'qwerty').")
        penalty += 12
    if is_year(pw):
        issues.append("Just a year - guessed in seconds.")
        penalty += 25
    if length > 0 and len(used) == 1:
        suggestions.append("Mix in at least one other character class.")
    if "symbols" not in used and length > 0:
        suggestions.append("Add a symbol - it triples the effective alphabet.")

    effective_bits = max(raw_bits - penalty, 0.0)

    # Map bits → 0-100 score (80 bits ≈ 100%).
    score = max(0, min(100, int(effective_bits / 80 * 100)))
    label, color = "Critical", "#ef4444"
    for name, lo, hi, c in STRENGTH_LABELS:
        if lo <= effective_bits < hi:
            label, color = name, c
            break

    # Crack-time estimates: guesses ≈ 2^bits (half the keyspace on average).
    guesses = 2 ** effective_bits / 2
    crack_times = {
        name: humanize_seconds(guesses / rate)
        for name, rate in ATTACKER_SPEEDS.items()
    }

    return PasswordReport(
        length=length,
        charset_size=charset_size,
        charsets_used=used,
        raw_entropy_bits=raw_bits,
        effective_entropy_bits=effective_bits,
        strength_label=label,
        strength_color=color,
        strength_score=score,
        crack_times=crack_times,
        issues=issues,
        suggestions=suggestions,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_report(pw: str, report: PasswordReport) -> None:
    line = "=" * 64
    print(line)
    print(f"  Password length     : {report.length}")
    print(f"  Charset classes     : {', '.join(report.charsets_used) or 'none'}")
    print(f"  Effective alphabet  : {report.charset_size}")
    print(f"  Raw entropy         : {report.raw_entropy_bits:.1f} bits")
    print(f"  Effective entropy   : {report.effective_entropy_bits:.1f} bits  "
          f"({report.strength_label})")
    print(f"  Strength score      : {report.strength_score} / 100")
    print("-" * 64)
    print("  Time to crack:")
    for name, t in report.crack_times.items():
        print(f"    {name:<32} {t}")
    if report.issues:
        print("-" * 64)
        print("  Issues:")
        for i in report.issues:
            print(f"    - {i}")
    if report.suggestions:
        print("-" * 64)
        print("  Suggestions:")
        for s in report.suggestions:
            print(f"    + {s}")
    print(line)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Password strength analyzer")
    p.add_argument("password", nargs="?", help="Password to score")
    p.add_argument("--interactive", "-i", action="store_true",
                   help="Prompt for password without echoing")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    if args.interactive or not args.password:
        try:
            pw = getpass.getpass("Password: ")
        except (KeyboardInterrupt, EOFError):
            print()
            return
    else:
        pw = args.password
    report = analyze(pw)
    print_report(pw, report)


if __name__ == "__main__":
    main()
