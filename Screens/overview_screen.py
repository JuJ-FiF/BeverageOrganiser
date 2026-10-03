import asyncio
import sys
from pathlib import Path

import flet as ft

from Utils.classes import Expense
from Utils.animations import booking_animation
from Utils.receipts import save_receipt, read_receipt, delete_receipt, receipt_exists


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

            receipt_icon = (
                ft.Icons.RECEIPT_LONG
                if has_receipt
                else None
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
                        color=ft.Colors.BLACK,
                        style=ft.TextStyle(
                            height=1.1
                        ),
                        expand=True
                    )
                ]
            )

            if has_receipt:

                title_content.controls.append(
                    ft.Icon(
                        ft.Icons.RECEIPT_LONG,
                        color=ft.Colors.BLACK,
                        size=22
                    )
                )

            tile = ft.Container(
                bgcolor="#D7C9A8",
                border_radius=10,
                padding=ft.Padding.only(
                    left=16,
                    bottom=4
                ),
                content=ft.ListTile(
                    title=title_content,
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
                    content_padding=ft.Padding.only(
                        right=16
                    ),
                    on_click=(
                        lambda e, exp=expense:
                        self.show_expense_details(exp)
                    )
                    if has_receipt
                    else None
                )
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

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Ausgabe löschen"
            ),
            content=ft.Text(
                f'Möchtest du die Ausgabe '
                f'"{expense.title}" '
                f'({expense.amount:.2f} €) '
                f'wirklich löschen?\n\n'
                f'Die gebuchten Getränke werden '
                f'vom Gesamtzähler abgezogen.'
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

        self.app.page.show_dialog(
            dialog
        )

    # =========================================================
    # AUSGABE HINZUFÜGEN
    # =========================================================

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

        # -----------------------------------------------------
        # BELEG-STATUS
        # -----------------------------------------------------

        receipt_data = {
            "bytes": None,
            "extension": ".jpg",
            "name": None
        }

        receipt_preview = ft.Container(
            visible=False,
            width=120,
            height=150,
            border_radius=8,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=None
        )

        receipt_status = ft.Text(
            "Kein Beleg ausgewählt.",
            size=12,
            color=ft.Colors.GREY_600
        )

        remove_receipt_button = ft.TextButton(
            "Beleg entfernen",
            icon=ft.Icons.DELETE_OUTLINE,
            visible=False
        )

        # -----------------------------------------------------
        # BELEG-VORSCHAU AKTUALISIEREN
        # -----------------------------------------------------

        def update_receipt_preview():

            data = receipt_data["bytes"]

            if not data:

                receipt_preview.visible = False
                receipt_preview.content = None

                receipt_status.value = (
                    "Kein Beleg ausgewählt."
                )

                remove_receipt_button.visible = False

                self.app.page.update()
                return

            receipt_preview.content = ft.Image(
                src=data,
                fit=ft.BoxFit.CONTAIN,
                width=120,
                height=150
            )

            receipt_preview.visible = True

            if receipt_data["name"]:
                receipt_status.value = (
                    f"Beleg: {receipt_data['name']}"
                )
            else:
                receipt_status.value = (
                    "Foto aufgenommen"
                )

            remove_receipt_button.visible = True

            self.app.page.update()

        # -----------------------------------------------------
        # BELEG ENTFERNEN
        # -----------------------------------------------------

        def remove_receipt(e=None):

            receipt_data["bytes"] = None
            receipt_data["name"] = None
            receipt_data["extension"] = ".jpg"

            update_receipt_preview()

        remove_receipt_button.on_click = remove_receipt

        # -----------------------------------------------------
        # BILD AUS GALERIE / DATEI AUSWÄHLEN
        # -----------------------------------------------------

        async def pick_receipt(e=None):

            try:

                picker = ft.FilePicker()

                files = await picker.pick_files(
                    dialog_title="Beleg auswählen",
                    allow_multiple=False,
                    with_data=True,
                    file_type=(
                        ft.FilePickerFileType.CUSTOM
                    ),
                    allowed_extensions=[
                        "jpg",
                        "jpeg",
                        "png",
                        "webp"
                    ]
                )

                if not files:
                    return

                selected = files[0]

                if not selected.bytes:
                    self.show_message(
                        "Das Bild konnte nicht gelesen werden."
                    )
                    return

                extension = Path(
                    selected.name
                ).suffix.lower()

                if extension not in [
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp"
                ]:
                    extension = ".jpg"

                receipt_data["bytes"] = (
                    selected.bytes
                )

                receipt_data["extension"] = (
                    extension
                )

                receipt_data["name"] = (
                    selected.name
                )

                update_receipt_preview()

            except Exception as ex:

                self.show_message(
                    "Bild konnte nicht ausgewählt werden."
                )

                print(
                    "Receipt picker error:",
                    ex
                )

        # -----------------------------------------------------
        # FOTO AUFNEHMEN
        # -----------------------------------------------------

        async def take_receipt_photo(e=None):

            if sys.platform == "win32":

                self.show_message(
                    "Die Kamera ist unter Windows "
                    "in der App nicht verfügbar.\n\n"
                    "Bitte benutze dort 'Bild auswählen'."
                )

                return

            try:

                import flet_camera as fc

            except ImportError:

                self.show_message(
                    "Das Kamera-Modul ist nicht installiert."
                )

                return

            try:

                camera = fc.Camera(
                    expand=True,
                    preview_enabled=True
                )

                cameras = (
                    await camera.get_available_cameras()
                )

                if not cameras:

                    self.show_message(
                        "Keine Kamera gefunden."
                    )

                    return

                # Bevorzugt die Rückkamera.
                selected_camera = next(
                    (
                        item
                        for item in cameras
                        if item.lens_direction
                        == fc.CameraLensDirection.BACK
                    ),
                    cameras[0]
                )

                await camera.initialize(
                    description=selected_camera,
                    resolution_preset=(
                        fc.ResolutionPreset.MEDIUM
                    ),
                    enable_audio=False,
                    image_format_group=(
                        fc.ImageFormatGroup.JPEG
                    )
                )

                async def capture_photo(e=None):

                    try:

                        data = (
                            await camera.take_picture()
                        )

                        if not data:

                            self.show_message(
                                "Foto konnte nicht aufgenommen werden."
                            )

                            return

                        receipt_data["bytes"] = data
                        receipt_data["extension"] = ".jpg"
                        receipt_data["name"] = (
                            "Aufgenommenes Foto"
                        )

                        self.app.page.pop_dialog()

                        update_receipt_preview()

                    except Exception as ex:

                        self.show_message(
                            "Foto konnte nicht aufgenommen werden."
                        )

                        print(
                            "Camera capture error:",
                            ex
                        )

                camera_dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text(
                        "Beleg fotografieren"
                    ),
                    content=ft.Container(
                        width=320,
                        height=420,
                        content=camera
                    ),
                    actions=[
                        ft.TextButton(
                            "Abbrechen",
                            on_click=lambda e:
                            self.app.page.pop_dialog()
                        ),
                        ft.FilledButton(
                            "Foto aufnehmen",
                            icon=ft.Icons.PHOTO_CAMERA,
                            on_click=capture_photo
                        )
                    ]
                )

                self.app.page.show_dialog(
                    camera_dialog
                )

                self.app.page.update()

            except Exception as ex:

                print(
                    "Camera error:",
                    ex
                )

                self.show_message(
                    "Kamera konnte nicht gestartet werden."
                )

        # -----------------------------------------------------
        # GETRÄNKE
        # -----------------------------------------------------

        def increment_beverage(beverage):

            session_counts[beverage] += 1

            count_labels[
                beverage
            ].value = (
                f"{session_counts[beverage]}x"
            )

            self.app.page.update()

        def reset_counts(e=None):

            for beverage in session_counts:

                session_counts[beverage] = 0

                count_labels[
                    beverage
                ].value = "0x"

            self.app.page.update()

        for beverage in self.app.beverage_objects:

            count_label = ft.Text(
                "0x",
                width=40,
                text_align=ft.TextAlign.RIGHT
            )

            count_labels[
                beverage
            ] = count_label

            tile = ft.ListTile(
                title=ft.Text(
                    f"{beverage.name} "
                    f"(Gesamt: {beverage.count})"
                ),
                trailing=count_label,
                on_click=(
                    lambda e, b=beverage:
                    increment_beverage(b)
                )
            )

            beverage_list.controls.append(
                tile
            )

        beverage_list.controls.append(
            ft.ListTile(
                title=ft.Text(
                    "Auswahl leeren"
                ),
                leading=ft.Icon(
                    ft.Icons.CLEAR
                ),
                on_click=reset_counts
            )
        )

        # -----------------------------------------------------
        # BELEG-BEREICH
        # -----------------------------------------------------

        receipt_section = ft.Container(
            padding=10,
            border_radius=10,
            bgcolor=ft.Colors.with_opacity(
                0.05,
                ft.Colors.ON_SURFACE
            ),
            content=ft.Column(
                spacing=8,
                controls=[

                    ft.Text(
                        "Rechnung / Beleg",
                        weight=ft.FontWeight.BOLD
                    ),

                    ft.Row(
                        wrap=True,
                        spacing=8,
                        controls=[

                            ft.OutlinedButton(
                                "Bild auswählen",
                                icon=ft.Icons.IMAGE,
                                on_click=pick_receipt
                            ),

                            ft.FilledTonalButton(
                                "Foto aufnehmen",
                                icon=ft.Icons.PHOTO_CAMERA,
                                on_click=take_receipt_photo
                            )
                        ]
                    ),

                    ft.Row(
                        spacing=12,
                        vertical_alignment=(
                            ft.CrossAxisAlignment.CENTER
                        ),
                        controls=[
                            receipt_preview,
                            ft.Column(
                                tight=True,
                                spacing=4,
                                controls=[
                                    receipt_status,
                                    remove_receipt_button
                                ]
                            )
                        ]
                    )
                ]
            )
        )

        # -----------------------------------------------------
        # SPEICHERN
        # -----------------------------------------------------

        def save(e):

            selected_items = [
                f"{count}x {beverage.name}"
                for beverage, count
                in session_counts.items()
                if count > 0
            ]

            title = ", ".join(
                selected_items
            )

            amount_raw = (
                amount_field.value.strip()
                if amount_field.value
                else ""
            )

            if not title:

                amount_field.error_text = (
                    "Bitte mindestens ein Getränk auswählen."
                )

                amount_field.update()

                return

            if not amount_raw:

                amount_field.error_text = (
                    "Bitte einen Betrag eingeben."
                )

                amount_field.update()

                return

            try:

                amount = float(
                    amount_raw.replace(
                        ",",
                        "."
                    )
                )

            except ValueError:

                amount_field.error_text = (
                    "Bitte einen gültigen Betrag eingeben."
                )

                amount_field.update()

                return

            # -------------------------------------------------
            # Gekaufte Getränke
            # -------------------------------------------------

            purchased_items = {
                beverage: count
                for beverage, count
                in session_counts.items()
                if count > 0
            }

            # -------------------------------------------------
            # Beleg dauerhaft speichern
            # -------------------------------------------------

            receipt_path = None

            if receipt_data["bytes"]:

                try:

                    receipt_path = save_receipt(
                        receipt_data["bytes"],
                        receipt_data["extension"]
                    )

                except Exception as ex:

                    print(
                        "Receipt save error:",
                        ex
                    )

                    amount_field.error_text = (
                        "Der Beleg konnte nicht gespeichert werden."
                    )

                    amount_field.update()

                    return

            # -------------------------------------------------
            # Expense erstellen
            # -------------------------------------------------

            new_expense = Expense(
                title=title,
                amount=amount,
                items=purchased_items,
                receipt=receipt_path
            )

            self.app.expense_objects.append(
                new_expense
            )

            # -------------------------------------------------
            # Getränkezähler erhöhen
            # -------------------------------------------------

            for beverage, added_count in (
                purchased_items.items()
            ):

                beverage.count += added_count

            # -------------------------------------------------
            # Speichern
            # -------------------------------------------------

            self.app.save_data()

            self.update_overview()

            if "beverage_main" in self.app.screens:

                self.app.screens[
                    "beverage_main"
                ].update_list()

            # -------------------------------------------------
            # Animation
            # -------------------------------------------------

            asyncio.create_task(
                booking_animation(
                    self.app.page,
                    animation="success"
                )
            )

            self.app.page.pop_dialog()
            self.app.page.update()

        # -----------------------------------------------------
        # DIALOG
        # -----------------------------------------------------

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Ausgabe buchen"
            ),
            content=ft.Container(
                width=420,
                content=ft.Column(
                    controls=[
                        beverage_list,
                        amount_field,
                        receipt_section
                    ],
                    tight=True,
                    spacing=12,
                    scroll=ft.ScrollMode.AUTO
                )
            ),
            actions=[
                ft.TextButton(
                    "Abbrechen",
                    on_click=lambda e:
                    self.app.page.pop_dialog()
                ),
                ft.FilledButton(
                    "Buchen",
                    icon=ft.Icons.SAVE,
                    on_click=save
                )
            ]
        )

        self.app.page.show_dialog(
            dialog
        )

    # =========================================================
    # NACHRICHT
    # =========================================================

    def show_message(self, message):

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(
                "Hinweis"
            ),
            content=ft.Text(
                message
            ),
            actions=[
                ft.TextButton(
                    "OK",
                    on_click=lambda e:
                    self.app.page.pop_dialog()
                )
            ]
        )

        self.app.page.show_dialog(
            dialog
        )

    # =========================================================
    # REFRESH
    # =========================================================

    def refresh(self):
        self.update_overview()