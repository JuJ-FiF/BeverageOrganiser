from datetime import datetime


class Transaction:
    def __init__(self, amount, date=None):
        self.amount = float(amount)
        self.date = (
            date
            if date
            else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
    def __init__(self, name, transactions=None):
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
            Transaction(amount=amount)
        )

    def remove_transaction(self, transaction):
        if transaction in self.transactions:
            self.transactions.remove(transaction)

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
                Transaction.from_dict(transaction)
                for transaction in data.get("transactions", [])
            ]
        )


class Expense:

    def __init__(
        self,
        title,
        amount,
        items=None,
        date=None,
        receipt=None
    ):
        self.title = title
        self.amount = float(amount)

        # Intern:
        # {
        #     beverage_object: count
        # }
        self.items = items if items is not None else {}

        self.date = (
            date
            if date
            else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        # Relativer Pfad zum Beleg.
        #
        # Beispiel:
        # receipts/20261003_113500.jpg
        #
        # None = kein Beleg vorhanden.
        self.receipt = receipt

    def to_dict(self):
        serialized_items = {
            beverage.name: count
            for beverage, count in self.items.items()
        }

        return {
            "title": self.title,
            "amount": self.amount,
            "date": self.date,
            "items": serialized_items,
            "receipt": self.receipt
        }

    @classmethod
    def from_dict(cls, data, beverage_objects):

        raw_items = data.get("items", {})
        restored_items = {}

        if beverage_objects and raw_items:

            beverage_map = {
                beverage.name: beverage
                for beverage in beverage_objects
            }

            for name, count in raw_items.items():

                if name in beverage_map:
                    restored_items[
                        beverage_map[name]
                    ] = int(count)

        return cls(
            title=data.get("title", ""),
            amount=data.get("amount", 0.0),
            date=data.get("date", ""),
            items=restored_items,
            receipt=data.get("receipt")
        )


class Beverage:

    def __init__(self, name: str, count: int = 0):
        self.name = name
        self.count = int(count)

    def to_dict(self):
        return {
            "name": self.name,
            "count": self.count
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data.get("name", ""),
            count=data.get("count", 0)
        )