from datetime import datetime


class Transaction:

    def __init__(self, amount, date=None):

        self.amount = float(amount)

        self.date = (
            date
            if date
            else datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

    def to_dict(self):

        return {
            "amount": self.amount,
            "date": self.date
        }

    @classmethod
    def from_dict(cls, data):

        return cls(
            amount=data["amount"],
            date=data["date"]
        )


class Person:

    def __init__(
        self,
        name,
        transactions=None
    ):

        self.name = name

        self.transactions = [
            Transaction.from_dict(t)
            if isinstance(t, dict)
            else t
            for t in (transactions or [])
        ]

    @property
    def budget(self):

        return sum(
            transaction.amount
            for transaction in self.transactions
        )

    def add_transaction(self, amount):

        self.transactions.append(
            Transaction(
                amount=amount
            )
        )

    def remove_transaction(self, transaction):

        if transaction in self.transactions:

            self.transactions.remove(
                transaction
            )

    def to_dict(self):

        return {
            "name": self.name,

            "transactions": [
                transaction.to_dict()
                for transaction in self.transactions
            ]
        }

    @classmethod
    def from_dict(cls, data):

        return cls(
            name=data["name"],
            transactions=[
                Transaction.from_dict(
                    transaction
                )
                for transaction
                in data.get(
                    "transactions",
                    []
                )
            ]
        )


class Expense:

    def __init__(
        self,
        title,
        amount,
        items=None,
        date=None,
        receipt=None,
        merchant=None,
        receipt_date=None
    ):

        self.title = title

        self.amount = float(
            amount
        )

        self.items = (
            items
            if items is not None
            else {}
        )

        self.date = (
            date
            if date
            else datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        self.receipt = receipt

        # Markt des Belegs
        self.merchant = merchant

        # Datum, das auf dem Beleg erkannt wurde
        self.receipt_date = receipt_date

    def to_dict(self):

        serialized_items = {
            beverage.name: count
            for beverage, count
            in self.items.items()
        }

        return {
            "title": self.title,
            "amount": self.amount,
            "date": self.date,
            "items": serialized_items,
            "receipt": self.receipt,

            "merchant": self.merchant,
            "receipt_date": self.receipt_date
        }

    @classmethod
    def from_dict(
        cls,
        data,
        beverage_objects
    ):

        raw_items = data.get(
            "items",
            {}
        )

        restored_items = {}

        if beverage_objects and raw_items:

            beverage_map = {
                beverage.name: beverage
                for beverage
                in beverage_objects
            }

            for name, count in raw_items.items():

                if name in beverage_map:

                    restored_items[
                        beverage_map[name]
                    ] = int(count)

        return cls(
            title=data.get(
                "title",
                ""
            ),

            amount=data.get(
                "amount",
                0.0
            ),

            date=data.get(
                "date",
                ""
            ),

            items=restored_items,

            receipt=data.get(
                "receipt"
            ),

            merchant=data.get(
                "merchant"
            ),

            receipt_date=data.get(
                "receipt_date"
            )
        )


class Beverage:

    def __init__(
        self,
        name: str,
        count: int = 0,
        aliases=None,
        market_aliases=None
    ):

        self.name = name

        self.count = int(
            count
        )

        # Allgemeine Bezeichnungen
        self.aliases = list(
            aliases or []
        )

        # Marktbezogene Bezeichnungen
        #
        # Beispiel:
        #
        # {
        #     "REWE": [
        #         "UR KROE 20X0,5"
        #     ],
        #     "EDEKA": [
        #         "UR-KROE"
        #     ]
        # }
        #
        self.market_aliases = {
            str(market): list(
                values or []
            )
            for market, values
            in (
                market_aliases or {}
            ).items()
        }

    def add_alias(
        self,
        alias,
        market=None
    ):

        if alias is None:
            return

        alias = str(
            alias
        ).strip()

        if not alias:
            return

        # Derselbe Name wie die Sorte selbst
        # muss nicht als Alias gespeichert werden.
        if alias.lower() == self.name.lower():
            return

        if market:

            market = str(
                market
            ).strip()

            if not market:
                market = None

        if market:

            values = self.market_aliases.setdefault(
                market,
                []
            )

            # Doppelte Aliase vermeiden
            if not any(
                existing.lower() == alias.lower()
                for existing in values
            ):

                values.append(
                    alias
                )

        else:

            if not any(
                existing.lower() == alias.lower()
                for existing in self.aliases
            ):

                self.aliases.append(
                    alias
                )

    def to_dict(self):

        return {
            "name": self.name,
            "count": self.count,
            "aliases": self.aliases,
            "market_aliases": self.market_aliases
        }

    @classmethod
    def from_dict(
        cls,
        data
    ):

        return cls(
            name=data.get(
                "name",
                ""
            ),

            count=data.get(
                "count",
                0
            ),

            aliases=data.get(
                "aliases",
                []
            ),

            market_aliases=data.get(
                "market_aliases",
                {}
            )
        )