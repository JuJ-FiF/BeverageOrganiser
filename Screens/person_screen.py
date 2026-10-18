import asyncio

import flet as ft

from Utils.classes import Person
from Utils.animations import BUTTON_EXPAND_ON_SELECT, booking_animation
from Utils.data_store import format_euro_amount, parse_euro_amount

class PersonScreen(ft.Column):

    def __init__(self, app):
        super().__init__(
            expand=True,
            spacing=12
        )

        self.app = app
        self.selected_amount = self.app.deposit_amounts[-1]
        self.custom_amount_selected = False
        self.selected_note = ""
        self.amount_buttons = []
        self.amount_row = ft.Column(spacing=4)
        self.build_amount_controls()

        self.person_list = ft.ListView(
            expand=True,
            spacing=4,
            padding=ft.Padding.only(
                right=10
            ),
            auto_scroll=False
        )

        self.controls = [
            ft.Container(
                padding=ft.Padding.only(left=26,
                                        right=36,
                                        top=8),
                content=self.amount_row,
            ),

            ft.Container(
                expand=True,
                padding=16,
                content=ft.Stack(
                    controls=[
                        ft.Column(
                            controls=[self.person_list,
                                ft.Row()]
                        ),

                        ft.FloatingActionButton(
                            icon=ft.Icons.PERSON_ADD,
                            on_click=self.open_add_person_dialog
                        )
                    ],
                    alignment=ft.Alignment.BOTTOM_RIGHT
                )
            )
        ]

        self.update_button_styles()
        self.update_list()

    # ---------------------------------------------------------
    # BETRAG AUSWÄHLEN
    # ---------------------------------------------------------

    @staticmethod
    def format_amount(amount):
        return format_euro_amount(amount)

    def build_amount_controls(self):
        self.amount_buttons = [
            ft.Button(
                f"{self.format_amount(amount)} €",
                expand=True,
                on_click=lambda e, value=amount: self.select_amount(value),
                animate_scale=BUTTON_EXPAND_ON_SELECT,
            )
            for amount in self.app.deposit_amounts
        ]
        self.custom_amount_button = ft.Button(
            self.custom_amount_label(),
            icon=ft.Icons.EDIT_OUTLINED,
            on_click=self.open_custom_amount_dialog,
        )
        self.amount_row.controls = [
            ft.Row(controls=self.amount_buttons, spacing=16),
            ft.Row(
                [self.custom_amount_button],
                alignment=ft.MainAxisAlignment.END,
            ),
        ]
        self.update_button_styles()

    def custom_amount_label(self):
        if not self.custom_amount_selected:
            return "Eigener Betrag"
        return f"Eigener Betrag · {self.format_amount(self.selected_amount)} €"

    def select_amount(self, amount):
        self.selected_amount = float(amount)
        self.custom_amount_selected = False
        self.selected_note = ""
        self.update_button_styles()
        self.app.page.update()

    def open_custom_amount_dialog(self, e=None):
        amount_field = ft.TextField(
            label="Betrag (€)",
            hint_text="z. B. 7,50",
            keyboard_type=ft.KeyboardType.TEXT,
            autofocus=True,
        )
        note_field = ft.TextField(
            label="Vermerk (optional)",
            hint_text="z. B. Gast oder Pfandrückgeld",
        )

        def save_custom_amount(_):
            try:
                amount = parse_euro_amount(amount_field.value)
            except ValueError as error:
                amount_field.error_text = str(error)
                self.app.page.update()
                return

            self.selected_amount = amount
            self.selected_note = note_field.value.strip() or "Eigener Betrag"
            self.custom_amount_selected = True
            self.app.page.pop_dialog()
            self.update_button_styles()
            self.app.page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Eigenen Betrag festlegen"),
            content=ft.Column(
                [amount_field, note_field],
                tight=True,
                spacing=12,
            ),
            actions=[
                ft.TextButton(
                    "Abbrechen",
                    on_click=lambda _: self.app.page.pop_dialog(),
                ),
                ft.FilledButton("Übernehmen", on_click=save_custom_amount),
            ],
        )
        self.app.page.show_dialog(dialog)

    def update_button_styles(self):
        filled = ft.ButtonStyle(
            bgcolor=ft.Colors.AMBER,
            color=ft.Colors.BLACK
        )

        outlined = ft.ButtonStyle(
            bgcolor=ft.Colors.TRANSPARENT,
            color=ft.Colors.AMBER,
            side=ft.BorderSide(
                1,
                ft.Colors.AMBER
            )
        )

        for button, amount in zip(self.amount_buttons, self.app.deposit_amounts):
            selected = (
                not self.custom_amount_selected
                and self.selected_amount == amount
            )
            button.style = filled if selected else outlined
            button.scale = 1.05 if selected else 1

        self.custom_amount_button.content = self.custom_amount_label()
        self.custom_amount_button.style = (
            filled if self.custom_amount_selected else outlined
        )

    # ---------------------------------------------------------
    # PERSON ANTIPPEN
    # ---------------------------------------------------------

    def on_person_click(self, person):

        amount = self.selected_amount

        person.add_transaction(amount, self.selected_note)

        self.app.save_data()
        self.update_list()
        self.app.page.update()

        self.app.screens["overview_main"].update_overview()

        asyncio.create_task(booking_animation(self.app.page, animation="success"))

    # ---------------------------------------------------------
    # PERSONENLISTE
    # ---------------------------------------------------------

    def update_list(self):
        self.person_list.controls.clear()

        for person in self.app.person_objects:
            tile = ft.Container(
                bgcolor="#D7C9A8",
                border_radius=10,
                padding=ft.Padding.symmetric(
                    horizontal=16,
                    vertical=10
                ),
                content=ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(
                            person.name,
                            size=16,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLACK
                        ),
                        ft.Text(
                            f"Budget: {person.budget:.2f} €",
                            size=13,
                            color=ft.Colors.BLACK_87
                        )
                    ]
                )
            )

            gesture = ft.GestureDetector(
                content=tile,
                on_tap=lambda _, p=person:
                self.on_person_click(p),
                on_long_press=lambda _, p=person:
                self.open_person_history_dialog(p)
            )

            self.person_list.controls.append(gesture)

    def update_all(self):
        self.app.save_data()
        self.update_list()
        self.app.page.update()
        self.app.screens["overview_main"].update_overview()

    # ---------------------------------------------------------
    # PERSON HINZUFÜGEN
    # ---------------------------------------------------------

    def open_add_person_dialog(self, _):
        field = ft.TextField(
            label="Name der Person",
            autofocus=True
        )

        def save(_):
            name = field.value.strip()

            if not name:
                field.error_text = "Bitte einen Namen eingeben."
                self.app.page.update()
                return

            # Prüfen, ob der Name bereits existiert
            if any(
                person.name.strip().lower() == name.lower()
                for person in self.app.person_objects
            ):
                field.error_text = "Diese Person existiert bereits."
                self.app.page.update()
                return

            # Person hinzufügen
            self.app.person_objects.append(Person(name=name))

            # Daten speichern, alles neu laden
            self.app.page.pop_dialog()
            self.update_all()
            asyncio.create_task(booking_animation(self.app.page, animation="success"))

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Person hinzufügen"),
            content=field,
            actions=[
                ft.TextButton(
                    "Abbrechen",
                    on_click=lambda _: self.app.page.pop_dialog()
                ),
                ft.FilledButton(
                    "Speichern",
                    on_click=save
                )
            ]
        )

        self.app.page.show_dialog(dialog)

    # ---------------------------------------------------------
    # PERSONENVERLAUF
    # ---------------------------------------------------------

    def open_person_history_dialog(self, person):
        history_list = ft.ListView(
            height=250,
            spacing=4
        )

        def refresh_dialog_list():
            history_list.controls.clear()

            if not person.transactions:
                history_list.controls.append(
                    ft.ListTile(
                        title=ft.Text(
                            "Keine Buchungen vorhanden."
                        )
                    )
                )
            else:
                for transaction in reversed(
                    person.transactions
                ):
                    prefix = (
                        "+"
                        if transaction.amount > 0
                        else ""
                    )

                    subtitle = f"Datum: {transaction.date}"
                    if transaction.note:
                        subtitle += f" · {transaction.note}"

                    tile = ft.Container(
                        bgcolor="#D7C9A8",
                        border_radius=10,
                        padding=ft.Padding.only(
                            left=4,
                            bottom=4
                        ),
                        content =ft.ListTile(
                            title=ft.Text(
                                f"{prefix}{transaction.amount:.2f} €",
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLACK
                            ),
                            subtitle=ft.Text(
                                subtitle,
                                color=ft.Colors.BLACK_87
                            ),
                            bgcolor="#D7C9A8"
                        )
                    )

                    gesture = ft.GestureDetector(
                        content=tile,
                        on_long_press=lambda e, t=transaction:
                            confirm_delete_transaction(t)
                    )

                    history_list.controls.append(gesture)

        def confirm_delete_transaction(transaction):
            person.remove_transaction(transaction)

            refresh_dialog_list()
            self.update_all()

        def delete_person(_):
            if person in self.app.person_objects:
                self.app.person_objects.remove(person)

            self.update_all()
            self.app.page.pop_dialog()

            asyncio.create_task(booking_animation(self.app.page, animation="delete"))

        refresh_dialog_list()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                f"Verlauf: {person.name}"
            ),
            content=ft.Column(
                controls=[
                    ft.Text(
                        "Buchungen löschen: gedrückt halten"
                    ),
                    history_list
                ],
                tight=True
            ),
            actions=[
                ft.TextButton(
                    "Person löschen",
                    on_click=delete_person
                ),
                ft.FilledButton(
                    "Schließen",
                    on_click=lambda e:
                        self.app.page.pop_dialog()
                )
            ]
        )

        self.app.page.show_dialog(dialog)

    # ---------------------------------------------------------
    # REFRESH
    # ---------------------------------------------------------

    def refresh(self):
        if (
            not self.custom_amount_selected
            and self.selected_amount not in self.app.deposit_amounts
        ):
            self.selected_amount = self.app.deposit_amounts[-1]
        self.build_amount_controls()
        self.update_list()
