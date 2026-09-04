import re
from collections import Counter

JAPANESE_RE = re.compile(r'[぀-ヿ一-龯]')

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
}
MONTH_RE = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"


def detect_language(text):
    return "ja" if JAPANESE_RE.search(text) else "en"


# ─── DISPATCHERS ───────────────────────────────────────
def extract_shop(text, lang=None):
    lang = lang or detect_language(text)
    return _extract_shop_en(text) if lang == "en" else _extract_shop_ja(text)


def extract_date(text, lang=None):
    lang = lang or detect_language(text)
    return _extract_date_en(text) if lang == "en" else _extract_date_ja(text)


def extract_total(text, lang=None):
    lang = lang or detect_language(text)
    return _extract_total_en(text) if lang == "en" else _extract_total_ja(text)


# ─── JAPANESE ───────────────────────────────────────────
def _extract_shop_ja(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    ignore = [
        "tel", "fax", "phone", "http", "www",
        "東京都", "大阪府", "神奈川", "埼玉",
        "領収", "レシート", "receipt",
        "合計", "小計", "外税", "税込", "内税",
        "現金", "お釣り", "おつり", "change",
        "〒", "営業", "ありがとう", "thank",
        "登録番号", "インボイス", "invoice",
        "専門店", "販売店", "取扱店",
        "番号", "no.", "number"
    ]

    for line in lines[:10]:
        lower = line.lower()

        if any(word.lower() in lower for word in ignore):
            continue

        digits = sum(c.isdigit() for c in line)
        if digits > len(line) * 0.4:
            continue

        if len(line) < 2:
            continue

        if re.match(r'^[*\-=_#\s]+$', line):
            continue

        if re.search(r'[都道府県市区町村]', line):
            continue

        return line

    return None


def _extract_date_ja(text):
    patterns = [
        (r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", "full"),
        (r"(\d{4})[/](\d{1,2})[/](\d{1,2})", "full"),
        (r"(\d{4})[-](\d{1,2})[-](\d{1,2})", "full"),
        (r"(\d{4})[.](\d{1,2})[.](\d{1,2})", "full"),
        (r"R(\d+)[./](\d{1,2})[./](\d{1,2})", "reiwa"),
        (r"(\d{2})[/](\d{1,2})[/](\d{1,2})", "short"),
    ]

    for pattern, fmt in patterns:
        m = re.search(pattern, text)
        if m:
            g = m.groups()
            try:
                if fmt == "reiwa":
                    year = 2018 + int(g[0])
                elif fmt == "short":
                    year = 2000 + int(g[0])
                else:
                    year = int(g[0])

                month = int(g[1])
                day   = int(g[2])

                if 1 <= month <= 12 and 1 <= day <= 31:
                    return f"{year:04d}-{month:02d}-{day:02d}"
            except Exception:
                continue

    return None


def _extract_total_ja(text):
    # Normalize full-width characters
    text = text.replace("，", ",").replace("．", ".")
    for fw, hw in zip("０１２３４５６７８９", "0123456789"):
        text = text.replace(fw, hw)

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Strategy 1: Find 合計 line then get amount from next lines
    for i, line in enumerate(lines):
        if re.search(r"合\s*計", line):

            # Check if amount is on same line
            m = re.search(r"[¥￥]\s*([\d,]+)", line)
            if m:
                try:
                    amount = float(m.group(1).replace(",", ""))
                    if 100 <= amount <= 1000000:
                        return amount
                except Exception:
                    pass

            # Check next 3 lines for amount
            for j in range(1, 4):
                if i + j < len(lines):
                    next_line = lines[i + j]

                    # Skip lines with brackets like (うち消費税
                    if "(" in next_line or "（" in next_line:
                        continue

                    m = re.search(r"[¥￥]\s*([\d,]+)", next_line)
                    if m:
                        try:
                            amount = float(m.group(1).replace(",", ""))
                            if 100 <= amount <= 1000000:
                                return amount
                        except Exception:
                            continue

    # Strategy 2: Look for largest ¥ amount
    # BUT exclude お釣り (change) amounts
    amounts = []
    skip_next = False

    for i, line in enumerate(lines):
        # Skip お釣り line and its amount
        if re.search(r"お釣り|おつり|お預り|おあずかり", line):
            skip_next = True
            continue

        if skip_next:
            skip_next = False
            continue

        # Find ¥ amounts
        for match in re.findall(r"[¥￥]\s*([\d,]+)", line):
            # Remove closing bracket if present
            match = match.replace(")", "")
            try:
                amount = float(match.replace(",", ""))
                if 100 <= amount <= 100000:
                    amounts.append(amount)
            except Exception:
                continue

    if amounts:
        # Return most frequent amount
        # (合計 and 外税売 often have same value)
        count = Counter(amounts)
        # Get amounts that appear more than once first
        # otherwise return the one just before お釣り
        most_common = count.most_common()

        # Filter out amounts that are too small (tax amounts)
        filtered = [a for a, c in most_common if a >= 500]
        if filtered:
            return filtered[0]

        return most_common[0][0] if most_common else None

    return None


# ─── ENGLISH ────────────────────────────────────────────
def _extract_shop_en(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    ignore = [
        "tel", "fax", "phone", "http", "www", ".com",
        "receipt", "invoice", "order #", "order no",
        "cashier", "register", "store #", "thank you",
        "welcome to", "customer copy", "merchant copy",
        "no.", "number"
    ]

    for line in lines[:10]:
        lower = line.lower()

        if any(word in lower for word in ignore):
            continue

        digits = sum(c.isdigit() for c in line)
        if digits > len(line) * 0.4:
            continue

        if len(line) < 2:
            continue

        if re.match(r'^[*\-=_#\s]+$', line):
            continue

        return line

    return None


def _extract_date_en(text):
    patterns = [
        (r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", "ymd"),
        (r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", "mdy"),
        (r"(\d{1,2})[-/](\d{1,2})[-/](\d{2})\b", "mdy_short"),
    ]

    for pattern, fmt in patterns:
        m = re.search(pattern, text)
        if m:
            g = m.groups()
            try:
                if fmt == "ymd":
                    year, month, day = int(g[0]), int(g[1]), int(g[2])
                elif fmt == "mdy":
                    month, day, year = int(g[0]), int(g[1]), int(g[2])
                else:
                    month, day, year = int(g[0]), int(g[1]), 2000 + int(g[2])

                if 1 <= month <= 12 and 1 <= day <= 31:
                    return f"{year:04d}-{month:02d}-{day:02d}"
            except Exception:
                continue

    m = re.search(
        rf"({MONTH_RE})[a-z]*\.?\s+(\d{{1,2}}),?\s+(\d{{4}})",
        text, re.IGNORECASE
    )
    if m:
        month = MONTHS[m.group(1).lower()]
        day = int(m.group(2))
        year = int(m.group(3))
        if 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"

    m = re.search(
        rf"(\d{{1,2}})\s+({MONTH_RE})[a-z]*\.?,?\s+(\d{{4}})",
        text, re.IGNORECASE
    )
    if m:
        day = int(m.group(1))
        month = MONTHS[m.group(2).lower()]
        year = int(m.group(3))
        if 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"

    return None


def _extract_total_en(text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Strategy 1: line containing "total" (not "subtotal") -> amount on same/next lines
    for i, line in enumerate(lines):
        lower = line.lower()
        if "total" in lower and "sub total" not in lower and "subtotal" not in lower:

            m = re.search(r"\$?\s*([\d,]+\.\d{2})", line)
            if m:
                try:
                    amount = float(m.group(1).replace(",", ""))
                    if 1 <= amount <= 1000000:
                        return amount
                except Exception:
                    pass

            for j in range(1, 4):
                if i + j < len(lines):
                    next_line = lines[i + j]
                    m = re.search(r"\$?\s*([\d,]+\.\d{2})", next_line)
                    if m:
                        try:
                            amount = float(m.group(1).replace(",", ""))
                            if 1 <= amount <= 1000000:
                                return amount
                        except Exception:
                            continue

    # Strategy 2: largest plausible dollar amount, excluding change/tendered lines
    amounts = []
    skip_next = False

    for line in lines:
        if re.search(r"change|cash tendered|amount tendered", line, re.IGNORECASE):
            skip_next = True
            continue

        if skip_next:
            skip_next = False
            continue

        for match in re.findall(r"\$?\s*([\d,]+\.\d{2})", line):
            try:
                amount = float(match.replace(",", ""))
                if 1 <= amount <= 100000:
                    amounts.append(amount)
            except Exception:
                continue

    if amounts:
        return max(amounts)

    return None
