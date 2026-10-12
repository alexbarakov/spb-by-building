"""Russian heritage-register dates → (lo, hi): '1805-1816 гг.', '1790-е гг.', '2 пол. XIX в.', 'кон. XIX в.',
'нач. XVIII в.', 'сер. XIX в.', '1 четв. XX в.', 'XVIII в.'. The first date in the text dates the building."""
import re

ROMAN = {"XVII": 17, "XVIII": 18, "XIX": 19, "XX": 20, "XXI": 21}
PART = [  # (pattern before the century, offset from the century start, span)
    (r"1\s*пол", 0, 49), (r"2\s*пол", 50, 49), (r"1\s*четв", 0, 24), (r"2\s*четв", 25, 24),
    (r"3\s*четв", 50, 24), (r"4\s*четв", 75, 24), (r"нач", 0, 20), (r"сер", 40, 20), (r"кон", 80, 19),
    (r"1\s*трет", 0, 33), (r"2\s*трет", 33, 33), (r"3\s*трет", 66, 33),
]
RE_RANGE_DEC = re.compile(r"(1[7-9]\d\d|20[0-2]\d)\s*[-–—]\s*(1[7-9]\d0|20[0-2]0)-е")
RE_RANGE = re.compile(r"(1[7-9]\d\d|20[0-2]\d)\s*[-–—]\s*(1[7-9]\d\d|20[0-2]\d)")
RE_DECADE = re.compile(r"(1[7-9]\d0|20[0-2]0)-е")
RE_YEAR = re.compile(r"(?<!\d)(1[7-9]\d\d|20[0-2]\d)(?!\d)")
RE_CENT = re.compile(r"((?:\d\s*(?:пол|четв|трет)|нач|сер|кон)\.?\s*)?\b(XXI|XX|XIX|XVIII|XVII)\s*в")


def parse(text):
    if not isinstance(text, str):
        return None
    t = text.replace("Х", "X").replace("І", "I").replace("Ⅹ", "X")
    found = []
    for m in RE_RANGE_DEC.finditer(t):
        found.append((m.start() - 0.1, (int(m.group(1)), int(m.group(2)) + 9)))
    for m in RE_RANGE.finditer(t):
        found.append((m.start(), (int(m.group(1)), int(m.group(2)))))
    for m in RE_DECADE.finditer(t):
        found.append((m.start(), (int(m.group(1)), int(m.group(1)) + 9)))
    for m in RE_YEAR.finditer(t):
        found.append((m.start() + 0.5, (int(m.group(1)), int(m.group(1)))))
    for m in RE_CENT.finditer(t):
        c = ROMAN[m.group(2)]
        lo, span = (c - 1) * 100, 99
        if m.group(1):
            for pat, off, sp in PART:
                if re.match(pat, m.group(1)):
                    lo, span = lo + off, sp
                    break
        found.append((m.start(), (lo, lo + span)))
    if not found:
        return None
    lo, hi = min(found)[1]
    return (lo, hi) if 1700 <= lo <= 2025 and lo <= hi else None


if __name__ == "__main__":
    for s in ["1805-1816 гг., ск. Ж. Камберлен", "1785-1800 гг., 2 пол. XIX в. (перестройка)", "2 пол. ХIХ в.",
              "кон. XIX в.", "нач. XVIII в., 1770-е гг.", "1850-1870-е гг.", "1790-е гг.", "1894 г., 1898 г.", "1 четв. XX в."]:
        print(parse(s), "←", s)
