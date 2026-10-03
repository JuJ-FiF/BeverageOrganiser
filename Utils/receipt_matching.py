import re
import unicodedata
from difflib import SequenceMatcher
from datetime import datetime


TOTAL_KEYWORDS = (
    "gesamt",
    "summe",
    "endbetrag",
    "end summe",
    "zu zahlen",
    "zahlbetrag",
    "zu zahlen",
    "total",
    "betrag"
)


IGNORE_WORDS = {
    "kasse",
    "bon",
    "beleg",
    "datum",
    "uhrzeit",
    "mwst",
    "ust",
    "inkl",
    "inkl.",
    "brutto",
    "netto",
    "ec",
    "karte",
    "bar",
    "zahlung",
    "gesamt",
    "summe",
    "total",
    "endbetrag"
}


def normalize_text(value):

    if not value:
        return ""

    value = str(value)

    value = unicodedata.normalize(
        "NFKD",
        value
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = value.lower()

    value = (
        value
        .replace("ß", "ss")
        .replace("&", "und")
    )

    value = re.sub(
        r"[^a-z0-9äöü ]+",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def normalize_product_name(value):

    value = normalize_text(
        value
    )

    # Typische Gebinde-/Mengendaten entfernen.
    value = re.sub(
        r"\b\d+\s*[x×]\s*"
        r"\d+(?:[,.]\d+)?\s*"
        r"(?:l|liter|ml|cl)\b",
        " ",
        value
    )

    value = re.sub(
        r"\b\d+\s*(?:kasten|kiste|stk|stuck)\b",
        " ",
        value
    )

    value = re.sub(
        r"\b\d+(?:[,.]\d+)?\s*"
        r"(?:l|liter|ml|cl)\b",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def similarity(
    first,
    second
):

    first = normalize_product_name(
        first
    )

    second = normalize_product_name(
        second
    )

    if not first or not second:
        return 0.0

    if first == second:
        return 1.0

    if first in second or second in first:
        return 0.95

    return SequenceMatcher(
        None,
        first,
        second
    ).ratio()


def parse_date(text):

    if not text:
        return None

    patterns = [
        r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b",
        r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if not match:
            continue

        try:

            if match.group(1).isdigit() and len(
                match.group(1)
            ) == 4:

                year = int(
                    match.group(1)
                )
                month = int(
                    match.group(2)
                )
                day = int(
                    match.group(3)
                )

            else:

                day = int(
                    match.group(1)
                )
                month = int(
                    match.group(2)
                )
                year = int(
                    match.group(3)
                )

                if year < 100:
                    year += 2000

            date = datetime(
                year,
                month,
                day
            )

            return date.strftime(
                "%d.%m.%Y"
            )

        except ValueError:
            pass

    return None


def parse_amount_from_line(
    line
):

    if not line:
        return None

    matches = re.findall(
        r"(?<!\d)"
        r"(\d{1,5}"
        r"(?:[.,]\d{2})?)"
        r"\s*(?:€|EUR)?"
        r"(?!\d)",
        line
    )

    values = []

    for value in matches:

        try:

            value = value.replace(
                ".",
                ""
            ).replace(
                ",",
                "."
            )

            number = float(
                value
            )

            if 0 <= number <= 10000:
                values.append(number)

        except ValueError:
            pass

    if not values:
        return None

    return values[-1]


def parse_total(
    text
):

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # Zuerst explizite Gesamtzeilen.
    for line in lines:

        normalized = normalize_text(
            line
        )

        if any(
            keyword in normalized
            for keyword in TOTAL_KEYWORDS
        ):

            amount = parse_amount_from_line(
                line
            )

            if amount is not None:
                return amount

    # Fallback:
    # letzte plausible Euro-/Betragsangabe.
    candidates = []

    for line in lines:

        if "€" not in line and not re.search(
            r"\d+[.,]\d{2}",
            line
        ):
            continue

        amount = parse_amount_from_line(
            line
        )

        if amount is not None:
            candidates.append(
                amount
            )

    if candidates:
        return candidates[-1]

    return None


def detect_merchant(
    text
):

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    # Bekannte deutsche Märkte.
    known_markets = [
        "rewe",
        "edeka",
        "kaufland",
        "netto",
        "aldi",
        "aldi nord",
        "aldi sud",
        "lidl",
        "penny",
        "norma",
        "getrankewelt",
        "getrankefeinkost",
        "trinkgut",
        "nahkauf"
    ]

    normalized_lines = [
        normalize_text(line)
        for line in lines[:12]
    ]

    for known_market in known_markets:

        for index, line in enumerate(
            normalized_lines
        ):

            if known_market in line:
                return lines[index]

    # Fallback:
    # Erste brauchbare kurze Zeile.
    for line in lines[:8]:

        normalized = normalize_text(
            line
        )

        if not normalized:
            continue

        if parse_date(line):
            continue

        if any(
            word in normalized
            for word in IGNORE_WORDS
        ):
            continue

        if re.search(
            r"\d+[.,]\d{2}",
            normalized
        ):
            continue

        if len(line) > 40:
            continue

        return line.strip()

    return None


def extract_quantity(
    line
):

    normalized = normalize_text(
        line
    )

    # "3 x 8,99 €"
    match = re.search(
        r"\b(\d{1,2})\s*[x×]\s*"
        r"\d{1,5}[.,]\d{2}\b",
        normalized
    )

    if match:

        return int(
            match.group(1)
        )

    # "3 Kisten"
    match = re.search(
        r"\b(\d{1,2})\s*"
        r"(?:kiste|kisten|kasten|kasten)\b",
        normalized
    )

    if match:

        return int(
            match.group(1)
        )

    # "3 Stk"
    match = re.search(
        r"\b(\d{1,2})\s*"
        r"(?:stk|stuck|stück)\b",
        normalized
    )

    if match:

        return int(
            match.group(1)
        )

    # "3x Coca Cola"
    match = re.match(
        r"^\s*(\d{1,2})\s*[x×]\s+",
        normalized
    )

    if match:

        return int(
            match.group(1)
        )

    # Eine erkannte Produktzeile entspricht
    # standardmäßig einer Kiste.
    return 1


def find_beverage_match(
    line,
    beverages,
    merchant=None
):

    best_beverage = None
    best_score = 0.0
    best_alias = None

    merchant_normalized = normalize_text(
        merchant
    )

    for beverage in beverages:

        candidates = [
            beverage.name
        ]

        candidates.extend(
            beverage.aliases
        )

        if merchant_normalized:

            for market, aliases in (
                beverage.market_aliases.items()
            ):

                if normalize_text(
                    market
                ) == merchant_normalized:

                    candidates.extend(
                        aliases
                    )

        for candidate in candidates:

            score = similarity(
                line,
                candidate
            )

            if score > best_score:

                best_score = score
                best_beverage = beverage
                best_alias = candidate

    if best_beverage is None:
        return None

    # Sehr gute Treffer automatisch.
    if best_score >= 0.82:

        return {
            "beverage": best_beverage,
            "score": best_score,
            "alias": best_alias,
            "needs_confirmation": False
        }

    # Mittlere Treffer werden zur Bestätigung
    # angezeigt.
    if best_score >= 0.58:

        return {
            "beverage": best_beverage,
            "score": best_score,
            "alias": best_alias,
            "needs_confirmation": True
        }

    return None


def extract_beverages(
    text,
    beverages,
    merchant=None
):

    results = {}

    uncertain = []

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for line in lines:

        normalized = normalize_product_name(
            line
        )

        if not normalized:
            continue

        if len(normalized) < 3:
            continue

        # Keine Summen-/Zahlungszeilen.
        if any(
            keyword in normalize_text(line)
            for keyword in TOTAL_KEYWORDS
        ):
            continue

        match = find_beverage_match(
            line,
            beverages,
            merchant
        )

        if not match:
            continue

        beverage = match[
            "beverage"
        ]

        quantity = extract_quantity(
            line
        )

        results[beverage] = (
            results.get(
                beverage,
                0
            )
            + quantity
        )

        if match[
            "needs_confirmation"
        ]:

            uncertain.append(
                {
                    "line": line,
                    "beverage": beverage,
                    "score": match["score"],
                    "alias": match["alias"]
                }
            )

    return results, uncertain


def analyze_receipt(
    text,
    beverages
):

    merchant = detect_merchant(
        text
    )

    receipt_date = parse_date(
        text
    )

    total = parse_total(
        text
    )

    items, uncertain = extract_beverages(
        text,
        beverages,
        merchant
    )

    return {
        "merchant": merchant,
        "receipt_date": receipt_date,
        "amount": total,
        "items": items,
        "uncertain_items": uncertain,
        "raw_text": text
    }


def learn_alias(
    beverage,
    alias,
    merchant=None
):

    alias = str(
        alias
    ).strip()

    if not alias:
        return

    normalized_alias = normalize_product_name(
        alias
    )

    if not normalized_alias:
        return

    # Der Hauptname braucht keinen Alias.
    if normalized_alias == normalize_product_name(
        beverage.name
    ):
        return

    if merchant:

        market_key = merchant.strip()

        aliases = beverage.market_aliases.setdefault(
            market_key,
            []
        )

        if not any(
            normalize_product_name(existing)
            == normalized_alias
            for existing in aliases
        ):

            aliases.append(
                alias
            )

    else:

        if not any(
            normalize_product_name(existing)
            == normalized_alias
            for existing in beverage.aliases
        ):

            beverage.aliases.append(
                alias
            )