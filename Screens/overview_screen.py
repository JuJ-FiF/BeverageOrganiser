import flet as ft
import asyncio

from Utils.classes import Expense
from Utils.animations import booking_animation


class OverviewScreen(ft.Column):

    def __init__(self, app):
        super().__init__(
            expand=True,
            spacing=16
        )

        self.app = app

        self.total_income_label = ft.Text(
            "Eingesammelt: 0.00 €",
            color=ft.Colors.GREEN_400,
            size=16
        )

        self.total_expense_label = ft.Text(
            "Ausgegeben: 0.00 €",
            color=ft.Colors.RED_400,
            size=16
        )

        self.balance_label = ft.Text(
            "Kassenbestand: 0.00 €",
            size=18,
            weight=ft.FontWeight.BOLD
        )

        self.expense_list = ft.ListView(
            expand=True,
            spacing=4
        )

        self.controls = [
            ft.Container(
                padding=12,
                content=ft.Card(
                    content=ft.Container(
                        padding=16,
                        content=ft.Column(
                            spacing=8,
                            controls=[
                                self.total_income_label,
                                self.total_expense_label,
                                ft.Divider(),
                                self.balance_label
                            ]
                        )
                    )
                )
            ),

            ft.Container(
                padding=ft.Padding.symmetric(
                    horizontal=16
                ),
                content=ft.FilledButton(
                    "Ausgabe / Getränkeeinkauf buchen",
                    icon=ft.Icons.RECEIPT_LONG,
                    on_click=self.open_add_expense_dialog
                )
            ),

            ft.Container(
                padding=ft.Padding.symmetric(
                    horizontal=16
                ),
                content=ft.Text(
                    "Ausgabenhistorie:",
                    weight=ft.FontWeight.BOLD
                )
            ),

            ft.Container(
                expand=True,
                padding=ft.Padding.symmetric(
                    horizontal=16
                ),
                content=self.expense_list
            )
        ]

        self.update_overview()

    # ---------------------------------------------------------
    # ÜBERSICHT AKTUALISIEREN
    # ---------------------------------------------------------

    def update_overview(self):
        total_income = sum(
            person.budget
            for person in self.app.person_objects
        )

        total_expenses = sum(
            expense.amount
            for expense in self.app.expense_objects
        )

        balance = total_income - total_expenses

        self.total_income_label.value = (
            f"Eingesammelt: {total_income:.2f} €"
        )

        self.total_expense_label.value = (
            f"Ausgegeben: {total_expenses:.2f} €"
        )

        self.balance_label.value = (
            f"Kassenbestand: {balance:.2f} €"
        )

        self.expense_list.controls.clear()

        for expense in reversed(self.app.expense_objects):
            tile = ft.Container(
                bgcolor="#D7C9A8",
                border_radius=10,
                padding=ft.Padding.only(
                    left=16,
                    bottom=4
                ),
                content=ft.ListTile(
                    title=ft.Text(
                        expense.title.replace(", ", ",\n"),
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLACK,
                        style=ft.TextStyle(height=1.1)
                    ),
                    subtitle=ft.Text(
                        f"Datum: {expense.date}",
                        color=ft.Colors.BLACK_87
                    ),
                    trailing=ft.Text(
                        f"-{expense.amount:.2f} €",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.RED_400,
                        text_align=ft.TextAlign.RIGHT
                    ),
                    content_padding=ft.Padding.only(right=16)
                )
            )

            gesture = ft.GestureDetector(
                content=tile,
                on_long_press=lambda e, exp=expense:
                self.confirm_delete_expense(exp)
            )

            self.expense_list.controls.append(gesture)

    # ---------------------------------------------------------
    # AUSGABE LÖSCHEN
    # ---------------------------------------------------------

    def confirm_delete_expense(self, expense):

        def delete_action(e):
            # 1. Getränkezähler wieder reduzieren
            if hasattr(expense, "items") and expense.items:
                for beverage, count in expense.items.items():
                    beverage.count = max(0, beverage.count - count)

            # 2. Ausgabe aus der Liste entfernen
            if expense in self.app.expense_objects:
                self.app.expense_objects.remove(expense)

            self.app.save_data()
            self.update_overview()

            # 3. Getränkeliste-View aktualisieren, falls vorhanden
            if "beverage_main" in self.app.screens:
                self.app.screens["beverage_main"].update_list()

            asyncio.create_task(booking_animation(self.app.page, animation="delete"))

            self.app.page.pop_dialog()
            self.app.page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Ausgabe löschen"),
            content=ft.Text(
                f'Möchtest du die Ausgabe "{expense.title}" '
                f'({expense.amount:.2f} €) wirklich löschen? '
                f'Die gebuchten Getränke werden vom Gesamtzähler wieder abgezogen.'
            ),
            actions=[
                ft.TextButton(
                    "Abbrechen",
                    on_click=lambda e: self.app.page.pop_dialog()
                ),
                ft.FilledButton(
                    "Löschen",
                    on_click=delete_action
                )
            ]
        )

        self.app.page.show_dialog(dialog)

    # ---------------------------------------------------------
    # AUSGABE HINZUFÜGEN
    # ---------------------------------------------------------

    def open_add_expense_dialog(self, e=None):

        amount_field = ft.TextField(
            label="Gesamtbetrag in €",
            hint_text="z.B. 24.50",
            keyboard_type=ft.KeyboardType.NUMBER
        )

        session_counts = {
            beverage: 0
            for beverage in self.app.beverage_objects
        }

        count_labels = {}

        beverage_list = ft.ListView(
            height=220,
            spacing=2
        )

        def increment_beverage(beverage):
            session_counts[beverage] += 1

            count_labels[beverage].value = (
                f"{session_counts[beverage]}x"
            )

            self.app.page.update()

        def reset_counts(e=None):
            for beverage in session_counts:
                session_counts[beverage] = 0
                count_labels[beverage].value = "0x"

            self.app.page.update()

        for beverage in self.app.beverage_objects:

            count_label = ft.Text(
                "0x",
                width=40,
                text_align=ft.TextAlign.RIGHT
            )

            count_labels[beverage] = count_label

            tile = ft.ListTile(
                title=ft.Text(
                    f"{beverage.name} "
                    f"(Gesamt: {beverage.count})"
                ),
                trailing=count_label,
                on_click=lambda e, b=beverage:
                    increment_beverage(b)
            )

            beverage_list.controls.append(tile)

        beverage_list.controls.append(
            ft.ListTile(
                title=ft.Text(
                    "✖ Auswahl leeren"
                ),
                on_click=reset_counts
            )
        )

        def save(e):

            selected_items = [
                f"{count}x {beverage.name}"
                for beverage, count in session_counts.items()
                if count > 0
            ]

            title = ", ".join(selected_items)
            amount_raw = amount_field.value.strip()

            if not title or not amount_raw:
                return

            try:
                amount = float(amount_raw.replace(",", "."))
            except ValueError:
                amount_field.error_text = "Bitte einen gültigen Betrag eingeben."
                amount_field.update()
                return

                # Nur Getränke mit count > 0 ins Item-Dict übernehmen
            purchased_items = {
                beverage: count
                for beverage, count in session_counts.items()
                if count > 0
            }

            # Neuer Expense mit items-Referenz
            new_expense = Expense(
                title=title,
                amount=amount,
                items=purchased_items
            )

            self.app.expense_objects.append(new_expense)

            # Gesamtzähler der Getränke erhöhen
            for beverage, added_count in purchased_items.items():
                beverage.count += added_count

            self.app.save_data()
            self.update_overview()

            if "beverage_main" in self.app.screens:
                self.app.screens["beverage_main"].update_list()

            asyncio.create_task(booking_animation(self.app.page, animation="success"))

            self.app.page.pop_dialog()
            self.app.page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Ausgabe buchen"),
            content=ft.Column(
                controls=[
                    beverage_list,
                    amount_field
                ],
                tight=True,
                spacing=12
            ),
            actions=[
                ft.TextButton(
                    "Abbrechen",
                    on_click=lambda e:
                        self.app.page.pop_dialog()
                ),
                ft.FilledButton(
                    "Buchen",
                    on_click=save
                )
            ]
        )

        self.app.page.show_dialog(dialog)

    # ---------------------------------------------------------
    # REFRESH
    # ---------------------------------------------------------

    def refresh(self):
        self.update_overview()