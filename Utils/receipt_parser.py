import re
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher


KNOWN_MARKETS = [
    "REWE",
    "EDEKA",
    "LIDL",
    "ALDI",
    "ALDI SÜD",
    "ALDI NORD",
    "NETTO",
    "PENNY",
    "KAUFLAND",
    "NORMA",
    "MARKTKAUF",
    "GLOBUS",
    "METRO",
    "SELgROS",
    "TRINKGUT",
    "FRISTO",
    "GETRÄNKE HOFFMANN",
    "GETRÄNKEWELT",
    "GETRÄNKE QUELLE",
]


# ============================================================
# NORMALISIERUNG
# ============================================================

def normalize_text(value):

    if value is None:
        return ""

    value = str(
        value
    )

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

    value = value.replace(
        "ß",
        "ss"
    )

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )

    return " ".join(
        value.split()
    )


# ============================================================
# GELDBETRAG
# ============================================================

def parse_money(value):

    if value is None:
        return None

    value = str(
        value
    ).strip()

    value = re.sub(
        r"[^\d,.\-]",
        "",
        value
    )

    if not value:
        return None

    try:

        # Deutsches Format:
        #
        # 1.234,56
        # 123,45
        #
        if "," in value:

            value = value.replace(
                ".",
                ""
            )

            value = value.replace(
                ",",
                "."
            )

        else:

            # 1234.56
            value = value

        return float(
            value
        )

    except ValueError:

        return None


# ============================================================
# DATUM
# ============================================================

def detect_date(text):

    patterns = [

        r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b",

        r"\b(\d{4})[./-](\d{1,2})[./-](\d{1,2})\b"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if not match:
            continue

        try:

            if len(match.group(1)) == 4:

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

            date = datetime(
                year,
                month,
                day
            )

            return date.strftime(
                "%Y-%m-%d"
            )

        except ValueError:

            continue

    return None


# ============================================================
# MARKT
# ============================================================

def detect_market(lines):

    normalized_lines = [
        normalize_text(line)
        for line in lines
    ]

    # Erst bekannte Märkte suchen
    for market in KNOWN_MARKETS:

        normalized_market = normalize_text(
            market
        )

        for line in normalized_lines:

            if normalized_market in line:

                return market

    # Falls kein bekannter Markt erkannt wurde:
    #
    # Die ersten Zeilen des Belegs enthalten normalerweise
    # Händlername / Marktname.
    #
    ignored_words = {
        "rechnung",
        "kassenbon",
        "bon",
        "datum",
        "uhrzeit",
        "tel",
        "telefon",
        "www",
        "www.",
        "oeffnungszeiten",
        "öffnungszeiten"
    }

    for line in lines[:8]:

        clean = line.strip()

        if not clean:
            continue

        normalized = normalize_text(
            clean
        )

        if not normalized:
            continue

        if normalized in ignored_words:
            continue

        # Datum überspringen
        if re.search(
            r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}",
            clean
        ):
            continue

        # Telefonnummern überspringen
        if re.fullmatch(
            r"[\d\s+()/.-]{6,}",
            clean
        ):
            continue

        # URLs überspringen
        if "www." in clean.lower():
            continue

        return clean[:60]

    return None


# ============================================================
# GESAMTSUMME
# ============================================================

TOTAL_KEYWORDS = [
    "gesamt",
    "summe",
    "endsumme",
    "endbetrag",
    "zu zahlen",
    "zahlbetrag",
    "zahlungsbetrag",
    "total",
    "rechnungsbetrag",
    "gesamtbetrag",
    "zu zahlen"
]


def extract_money_values(line):

    matches = re.findall(
        r"(?<!\d)"
        r"\d{1,3}(?:[.]\d{3})*,\d{2}"
        r"(?!\d)"
        r"|"
        r"(?<!\d)"
        r"\d+,\d{2}"
        r"(?!\d)"
        r"|"
        r"(?<!\d)"
        r"\d+\.\d{2}"
        r"(?!\d)",
        line
    )

    values = []

    for value in matches:

        parsed = parse_money(
            value
        )

        if parsed is not None:

            values.append(
                parsed
            )

    return values


def detect_total(lines):

    # Zuerst gezielt nach einer Summe suchen.
    for line in lines:

        normalized = normalize_text(
            line
        )

        if any(
            keyword in normalized
            for keyword in TOTAL_KEYWORDS
        ):

            values = extract_money_values(
                line
            )

            if values:

                return values[-1]

    # Fallback:
    # letzten Geldbetrag auf dem Beleg verwenden.
    all_values = []

    for line in lines:

        values = extract_money_values(
            line
        )

        all_values.extend(
            values
        )

    if all_values:

        return all_values[-1]

    return None


# ============================================================
# PRODUKTZEILE BEREINIGEN
# ============================================================

def clean_product_line(line):

    value = str(
        line
    ).strip()

    if not value:
        return ""

    # Geldbeträge entfernen
    value = re.sub(
        r"\d{1,3}(?:[.]\d{3})*,\d{2}\s*€?",
        " ",
        value
    )

    value = re.sub(
        r"\d+,\d{2}\s*€?",
        " ",
        value
    )

    value = re.sub(
        r"\d+\.\d{2}\s*€?",
        " ",
        value
    )

    # Häufige Preis-/Mengenangaben entfernen
    value = re.sub(
        r"\b\d+\s*€\b",
        " ",
        value,
        flags=re.IGNORECASE
    )

    return value.strip()


# ============================================================
# KISTENANZAHL
# ============================================================

def extract_case_quantity(line):

    normalized = line.lower()

    # --------------------------------------------------------
    # Explizite Kisten
    #
    # 2 Kiste
    # 2 Kisten
    # 2 Kasten
    # 2 Kästen
    # 2 Gebinde
    # --------------------------------------------------------

    match = re.search(
        r"\b(\d+)\s*"
        r"(?:kiste[n]?|kasten|kästen|"
        r"gebinde[n]?|kiste|kasten)\b",
        normalized
    )

    if match:

        return int(
            match.group(1)
        )

    # --------------------------------------------------------
    # 2x Produkt
    #
    # Aber:
    #
    # 20x0,5L
    # 24x0,33L
    #
    # sind normalerweise die Flaschenanzahl innerhalb
    # einer Kiste und NICHT 20 bzw. 24 Kisten.
    # --------------------------------------------------------

    match = re.search(
        r"(?<!\d)"
        r"(\d+)"
        r"\s*[x×]\s*"
        r"(.+)",
        normalized
    )

    if match:

        quantity = int(
            match.group(1)
        )

        remainder = match.group(2)

        # 20x0,5 / 24x0,33 usw.
        if re.match(
            r"\d+(?:[,.]\d+)?\s*l\b",
            remainder
        ):

            return 1

        # 20x0,5l ohne Leerzeichen
        if re.match(
            r"\d+(?:[,.]\d+)?l\b",
            remainder
        ):

            return 1

        return quantity

    # --------------------------------------------------------
    # Keine explizite Menge
    #
    # Eine erkannte Produktzeile entspricht einer Kiste.
    # --------------------------------------------------------

    return 1


# ============================================================
# MATCHING
# ============================================================

def similarity(
    first,
    second
):

    first = normalize_text(
        first
    )

    second = normalize_text(
        second
    )

    if not first or not second:
        return 0.0

    if first == second:
        return 1.0

    if (
        first in second
        or second in first
    ):

        shorter = min(
            len(first),
            len(second)
        )

        if shorter >= 4:

            return 0.93

    return SequenceMatcher(
        None,
        first,
        second
    ).ratio()


def beverage_candidates(
    beverage,
    market
):

    candidates = []

    # Hauptname
    candidates.append(
        (
            beverage.name,
            False
        )
    )

    # Allgemeine Aliase
    for alias in getattr(
        beverage,
        "aliases",
        []
    ):

        candidates.append(
            (
                alias,
                False
            )
        )

    # Markt-Aliase zuerst
    market_aliases = getattr(
        beverage,
        "market_aliases",
        {}
    )

    if market:

        for market_name, aliases in (
            market_aliases.items()
        ):

            if normalize_text(
                market_name
            ) == normalize_text(
                market
            ):

                for alias in aliases:

                    candidates.insert(
                        0,
                        (
                            alias,
                            True
                        )
                    )

    return candidates


def match_beverage(
    line,
    beverages,
    market
):

    cleaned = clean_product_line(
        line
    )

    normalized_line = normalize_text(
        cleaned
    )

    if not normalized_line:
        return None

    best_beverage = None
    best_alias = None
    best_score = 0.0
    best_market_alias = False

    second_score = 0.0

    for beverage in beverages:

        for alias, is_market_alias in (
            beverage_candidates(
                beverage,
                market
            )
        ):

            score = similarity(
                normalized_line,
                alias
            )

            if score > best_score:

                second_score = best_score

                best_score = score

                best_beverage = beverage

                best_alias = alias

                best_market_alias = (
                    is_market_alias
                )

            elif score > second_score:

                second_score = score

    # Markt-Aliase dürfen etwas toleranter sein.
    threshold = (
        0.78
        if best_market_alias
        else 0.84
    )

    if best_beverage is None:
        return None

    if best_score < threshold:
        return None

    # Wenn zwei Sorten fast gleich gut passen,
    # lieber nicht automatisch entscheiden.
    if (
        second_score >= threshold
        and best_score - second_score < 0.04
    ):

        return {
            "beverage": None,
            "raw_name": cleaned,
            "score": best_score,
            "ambiguous": True
        }

    return {
        "beverage": best_beverage,
        "raw_name": cleaned,
        "score": best_score,
        "ambiguous": False
    }


# ============================================================
# UNGÜLTIGE / IRRELEVANTE ZEILEN
# ============================================================

def looks_like_irrelevant_line(line):

    normalized = normalize_text(
        line
    )

    if not normalized:
        return True

    irrelevant_keywords = [
        "pfand",
        "summe",
        "gesamt",
        "endbetrag",
        "zahlbetrag",
        "zu zahlen",
        "ec",
        "visa",
        "mastercard",
        "barzahlung",
        "kartenzahlung",
        "rueckgeld",
        "ruckgeld",
        "mwst",
        "ust",
        "steuer",
        "rabatt",
        "rabatte"
    ]

    if any(
        keyword in normalized
        for keyword in irrelevant_keywords
    ):

        return True

    # Reine Geldzeile
    if extract_money_values(line):

        if len(
            normalize_text(
                re.sub(
                    r"\d+[,.]\d{2}",
                    "",
                    line
                )
            )
        ) < 3:

            return True

    return False


# ============================================================
# PRODUKT-MATCHING
# ============================================================

def detect_beverages(
    lines,
    beverages,
    market
):

    items = {}

    matches = []

    unmatched = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        if looks_like_irrelevant_line(
            line
        ):
            continue

        result = match_beverage(
            line,
            beverages,
            market
        )

        if result is None:
            continue

        if result.get(
            "ambiguous"
        ):

            unmatched.append(
                {
                    "line": line,
                    "reason": "mehrdeutig"
                }
            )

            continue

        beverage = result[
            "beverage"
        ]

        if beverage is None:
            continue

        count = extract_case_quantity(
            line
        )

        items[beverage] = (
            items.get(
                beverage,
                0
            )
            + count
        )

        matches.append(
            {
                "beverage": beverage,
                "raw_name": line,
                "score": result[
                    "score"
                ]
            }
        )

    return (
        items,
        matches,
        unmatched
    )


# ============================================================
# HAUPTFUNKTION
# ============================================================

def parse_receipt(
    text,
    beverages
):

    if not text:

        return {
            "date": None,
            "market": None,
            "total": None,
            "items": {},
            "matches": [],
            "unmatched": []
        }

    if not beverages:

        return {
            "date": detect_date(text),
            "market": detect_market(
                text.splitlines()
            ),
            "total": detect_total(
                text.splitlines()
            ),
            "items": {},
            "matches": [],
            "unmatched": []
        }

    lines = [
        line.strip()
        for line
        in text.splitlines()
        if line.strip()
    ]

    market = detect_market(
        lines
    )

    receipt_date = detect_date(
        text
    )

    total = detect_total(
        lines
    )

    items, matches, unmatched = (
        detect_beverages(
            lines,
            beverages,
            market
        )
    )

    return {
        "date": receipt_date,
        "market": market,
        "total": total,
        "items": items,
        "matches": matches,
        "unmatched": unmatched
    }