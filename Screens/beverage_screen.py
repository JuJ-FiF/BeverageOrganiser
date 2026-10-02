import flet as ft

from Utils.classes import Beverage


class BeverageScreen(ft.Column):

    def __init__(self, app):
        super().__init__(
            expand=True,
            spacing=12
        )

        self.app = app

        self.beverage_list = ft.ListView(
            expand=True,
            spacing=8
        )

        self.controls = [
            ft.Container(
                padding=16,
                content=ft.Text(
                    "Getränkearten & Sorten",
                    size=22,
                    weight=ft.FontWeight.BOLD
                )
            ),

            ft.Container(
                padding=ft.Padding.symmetric(
                    horizontal=16
                ),
                content=ft.Row(
                    controls=[
                        ft.Text(
                            "Gedrückt halten zum Löschen",
                            size=13,
                            expand=True
                        ),

                        ft.FilledButton(
                            "Sorte hinzufügen",
                            icon=ft.Icons.ADD,
                            on_click=self.open_add_beverage_dialog
                        )
                    ]
                )
            ),

            ft.Container(
                expand=True,
                padding=ft.Padding.symmetric(
                    horizontal=16
                ),
                content=self.beverage_list
            )
        ]

        self.update_list()

    # ---------------------------------------------------------
    # LISTE
    # ---------------------------------------------------------

    def update_list(self):
        self.beverage_list.controls.clear()

        for beverage in self.app.beverage_objects:
            tile = ft.Container(
                bgcolor="#D7C9A8",
                border_radius=10,
                padding=ft.Padding.only(
                    left=16,
                    bottom=4
                ),
                content=ft.ListTile(
                    title=ft.Text(
                        beverage.name,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLACK,
                    ),
                    subtitle=ft.Text(
                        f"Gesamt gekauft: {beverage.count}x",
                        color=ft.Colors.BLACK_87
                    ),
                    content_padding=ft.Padding.zero()
                )
            )

            gesture = ft.GestureDetector(
                content=tile,
                on_long_press=lambda e, b=beverage:
                    self.confirm_delete_beverage(b)
            )

            self.beverage_list.controls.append(
                gesture
            )

        self.app.page.update()

    # ---------------------------------------------------------
    # GETRÄNK HINZUFÜGEN
    # ---------------------------------------------------------

    def open_add_beverage_dialog(self, e=None):

        field = ft.TextField(
            label="Getränkesorte",
            hint_text="z.B. Cola, Bockbier, Apfelschorle",
            autofocus=True
        )

        def save(e):
            new_name = field.value.strip()

            existing_names = [
                beverage.name.lower()
                for beverage
                in self.app.beverage_objects
            ]

            if not new_name:
                return

            if new_name.lower() in existing_names:
                field.error_text = (
                    "Diese Sorte existiert bereits."
                )
                field.update()
                return

            new_beverage = Beverage(
                name=new_name,
                count=0
            )

            self.app.beverage_objects.append(
                new_beverage
            )

            self.app.save_data()
            self.update_list()

            self.app.page.pop_dialog()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Sorte hinzufügen"),
            content=field,
            actions=[
                ft.TextButton(
                    "Abbrechen",
                    on_click=lambda e:
                        self.app.page.pop_dialog()
                ),
                ft.FilledButton(
                    "Hinzufügen",
                    on_click=save
                )
            ]
        )

        self.app.page.show_dialog(dialog)

    # ---------------------------------------------------------
    # GETRÄNK LÖSCHEN
    # ---------------------------------------------------------

    def confirm_delete_beverage(self, beverage):

        def delete_action(e):

            if beverage in self.app.beverage_objects:
                self.app.beverage_objects.remove(
                    beverage
                )

            self.app.save_data()
            self.update_list()

            self.app.page.pop_dialog()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Sorte löschen"),
            content=ft.Text(
                f'Möchtest du "{beverage.name}" '
                f'wirklich aus der Sortenauswahl entfernen?'
            ),
            actions=[
                ft.TextButton(
                    "Abbrechen",
                    on_click=lambda e:
                        self.app.page.pop_dialog()
                ),
                ft.FilledButton(
                    "Löschen",
                    on_click=delete_action
                )
            ]
        )

        self.app.page.show_dialog(dialog)

    # ---------------------------------------------------------
    # REFRESH
    # ---------------------------------------------------------

    def refresh(self):
        self.update_list()