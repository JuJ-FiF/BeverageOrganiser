import asyncio

import flet as ft
import flet_permission_handler as fph

from Utils.animations import booking_animation
from Utils.receipts import delete_receipt, read_receipt, receipt_exists

from Screens.dialogs import show_confirmation_dialog
from Screens.expense_workflow import ExpenseWorkflowMixin
from Screens.ui_components import primary_button, screen_heading, surface_card


class OverviewScreen(ExpenseWorkflowMixin, ft.Column):

    def __init__(self, app):
        super().__init__(
            expand=True,
            spacing=16
        )

        self.app = app

        # =====================================================
        # BERECHTIGUNGEN
        # =====================================================

        self.permission_handler = fph.PermissionHandler()

        if self.permission_handler not in self.app.page.services:
            self.app.page.services.append(
                self.permission_handler
            )

        # =====================================================
        # ÜBERSICHT
        # =====================================================

        self.total_income_label = ft.Text(
            "Eingesammelt: 0.00 €",
            color=ft.Colors.GREEN_400,
            size=16,
        )

        self.total_expense_label = ft.Text(
            "Ausgegeben: 0.00 €",
            color=ft.Colors.RED_400,
            size=16,
        )

        self.balance_label = ft.Text(
            "Kassenbestand: 0.00 €",
            size=18,
            weight=ft.FontWeight.BOLD
        )

        self.expense_list = ft.ListView(expand=True, spacing=8)

        self.controls = [
            screen_heading(
                "Kassenübersicht",
                "Einnahmen, Ausgaben und aktueller Kassenbestand.",
                primary_button(
                    "Ausgabe buchen",
                    ft.Icons.RECEIPT_LONG,
                    self.open_add_expense_dialog,
                ),
            ),
            surface_card(
                ft.Column(
                    [
                        self.total_income_label,
                        self.total_expense_label,
                        ft.Divider(),
                        self.balance_label,
                    ],
                    spacing=10,
                    tight=True,
                ),
                padding=18,
            ),
            ft.Text("Ausgabenhistorie", size=20, weight=ft.FontWeight.BOLD),
            ft.Container(
                expand=True,
                content=self.expense_list
            ),
        ]

        self.update_overview()

    # =========================================================
    # ÜBERSICHT AKTUALISIEREN
    # =========================================================

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

        for expense in reversed(
            self.app.expense_objects
        ):

            has_receipt = receipt_exists(
                expense.receipt
            )

            title_content = ft.Row(
                spacing=8,
                controls=[
                    ft.Text(
                        expense.title.replace(
                            ", ",
                            ",\n"
                        ),
                        weight=ft.FontWeight.BOLD,
                        style=ft.TextStyle(
                            height=1.1
                        ),
                        expand=True
                    )
                ]
            )

            tile = surface_card(
                ft.ListTile(
                    leading=ft.Icon(
                        ft.Icons.POINT_OF_SALE,
                        color=ft.Colors.PRIMARY,
                    ),
                    title=title_content,
                    subtitle=ft.Text(
                        f"Datum: {expense.date}",
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    trailing=ft.Text(
                        f"-{expense.amount:.2f} €",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.RED_400,
                        text_align=ft.TextAlign.RIGHT
                    ),
                    content_padding=ft.Padding.symmetric(horizontal=8),
                    on_click=(
                        lambda e, exp=expense:
                        self.show_expense_details(exp)
                    )
                    if has_receipt
                    else None
                ),
                padding=4,
            )

            gesture = ft.GestureDetector(
                content=tile,
                on_long_press=(
                    lambda e, exp=expense:
                    self.confirm_delete_expense(exp)
                )
            )

            self.expense_list.controls.append(
                gesture
            )

        self.app.page.update()

    # =========================================================
    # AUSGABE DETAILS / BELEG ANZEIGEN
    # =========================================================

    def show_expense_details(self, expense):

        receipt_data = read_receipt(
            expense.receipt
        )

        if not receipt_data:
            self.show_message(
                "Der Beleg konnte nicht gefunden werden."
            )
            return

        image = ft.Image(
            src=receipt_data,
            fit=ft.BoxFit.CONTAIN,
            width=320,
            height=480
        )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Beleg"
            ),
            content=ft.Column(
                tight=True,
                horizontal_alignment=(
                    ft.CrossAxisAlignment.CENTER
                ),
                controls=[
                    ft.Text(
                        expense.title,
                        weight=ft.FontWeight.BOLD
                    ),
                    ft.Text(
                        f"{expense.amount:.2f} €"
                    ),
                    ft.Divider(),
                    image
                ]
            ),
            actions=[
                ft.TextButton(
                    "Schließen",
                    on_click=lambda e:
                    self.app.page.pop_dialog()
                )
            ]
        )

        self.app.page.show_dialog(
            dialog
        )

    # =========================================================
    # AUSGABE LÖSCHEN
    # =========================================================

    def confirm_delete_expense(self, expense):

        def delete_action(e):

            # -------------------------------------------------
            # 1. Getränkezähler zurücksetzen
            # -------------------------------------------------

            if (
                hasattr(expense, "items")
                and expense.items
            ):

                for beverage, count in (
                    expense.items.items()
                ):

                    beverage.count = max(
                        0,
                        beverage.count - count
                    )

            # -------------------------------------------------
            # 2. Beleg löschen
            # -------------------------------------------------

            if getattr(
                expense,
                "receipt",
                None
            ):

                delete_receipt(
                    expense.receipt
                )

            # -------------------------------------------------
            # 3. Ausgabe entfernen
            # -------------------------------------------------

            if expense in self.app.expense_objects:

                self.app.expense_objects.remove(
                    expense
                )

            # -------------------------------------------------
            # 4. Daten speichern
            # -------------------------------------------------

            self.app.save_data()

            self.update_overview()

            # -------------------------------------------------
            # 5. Getränkeliste aktualisieren
            # -------------------------------------------------

            if "beverage_main" in self.app.screens:

                self.app.screens[
                    "beverage_main"
                ].update_list()

            # -------------------------------------------------
            # 6. Animation
            # -------------------------------------------------

            asyncio.create_task(
                booking_animation(
                    self.app.page,
                    animation="delete"
                )
            )

            self.app.page.pop_dialog()
            self.app.page.update()

        show_confirmation_dialog(
            self.app.page,
            "Ausgabe löschen",
            f'Möchtest du die Ausgabe "{expense.title}" '
            f"({expense.amount:.2f} €) wirklich löschen?\n\n"
            "Die gebuchten Getränke werden vom Gesamtzähler abgezogen.",
            "Löschen",
            delete_action,
        )

    # =========================================================
    # KAMERA-BERECHTIGUNG
    # =========================================================

    # REFRESH
    # =========================================================

    def refresh(self):
        self.update_overview()
