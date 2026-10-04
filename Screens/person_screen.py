import asyncio

import flet as ft

from Utils.classes import Person
from Utils.animations import BUTTON_EXPAND_ON_SELECT, booking_animation

class PersonScreen(ft.Column):

    def __init__(self, app):
        super().__init__(
            expand=True,
            spacing=12
        )

        self.app = app
        self.selected_amount = 20.0

        self.btn_5 = ft.Button(
            "5 €",
            expand=True,
            on_click=lambda e: self.select_amount(5),
            animate_scale=BUTTON_EXPAND_ON_SELECT
        )

        self.btn_10 = ft.Button(
            "10 €",
            expand=True,
            on_click=lambda e: self.select_amount(10),
            animate_scale=BUTTON_EXPAND_ON_SELECT
        )

        self.btn_20 = ft.Button(
            "20 €",
            expand=True,
            on_click=lambda e: self.select_amount(20),
            animate_scale=BUTTON_EXPAND_ON_SELECT
        )

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
                content=ft.Row(
                    controls=[
                        self.btn_5,
                        self.btn_10,
                        self.btn_20
                    ],
                    spacing=16
                )
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

    def select_amount(self, amount):
        self.selected_amount = float(amount)
        self.update_button_styles()
        self.app.page.update()

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

        self.btn_5.style = (
            filled
            if self.selected_amount == 5
            else outlined
        )
        self.btn_5.scale = 1.05 if self.selected_amount == 5 else 1

        self.btn_10.style = (
            filled
            if self.selected_amount == 10
            else outlined
        )
        self.btn_10.scale = 1.05 if self.selected_amount == 10 else 1

        self.btn_20.style = (
            filled
            if self.selected_amount == 20
            else outlined
        )
        self.btn_20.scale = 1.05 if self.selected_amount == 20 else 1

    # ---------------------------------------------------------
    # PERSON ANTIPPEN
    # ---------------------------------------------------------

    def on_person_click(self, person):

        amount = self.selected_amount

        person.add_transaction(amount)

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
                                f"Datum: {transaction.date}",
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
        self.update_button_styles()
        self.update_list()
