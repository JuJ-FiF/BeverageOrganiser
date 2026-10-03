import asyncio
import sys
from pathlib import Path

import flet as ft

from Utils.classes import Expense
from Utils.animations import booking_animation
from Utils.receipts import (
    save_receipt,
    read_receipt,
    delete_receipt,
    receipt_exists,
    get_receipt_path
)
from Utils.receipt_ocr import recognize_receipt_text
from Utils.receipt_parser import parse_receipt


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

            title = (
                expense.merchant
                if getattr(expense, "merchant", None)
                else expense.title
            )

            if not title:
                title = "Ausgabe"

            title_content = ft.Row(
                spacing=8,
                controls=[
                    ft.Text(
                        title.replace(
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

            # -------------------------------------------------
            # DATUM
            # -------------------------------------------------

            receipt_date = getattr(
                expense,
                "receipt_date",
                None
            )

            if receipt_date:

                subtitle_text = (
                    f"Belegdatum: {receipt_date}"
                )

            else:

                subtitle_text = (
                    f"Datum: {expense.date}"
                )

            # -------------------------------------------------
            # GETRÄNKE
            # -------------------------------------------------

            if expense.title:

                subtitle_text += (
                    f"\n{expense.title}"
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
                        subtitle_text,
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

        merchant = getattr(
            expense,
            "merchant",
            None
        )

        receipt_date = getattr(
            expense,
            "receipt_date",
            None
        )

        info_controls = []

        if merchant:

            info_controls.append(
                ft.Text(
                    merchant,
                    size=18,
                    weight=ft.FontWeight.BOLD
                )
            )

        if receipt_date:

            info_controls.append(
                ft.Text(
                    f"Belegdatum: {receipt_date}"
                )
            )

        info_controls.append(
            ft.Text(
                f"{expense.amount:.2f} €"
            )
        )

        if expense.title:

            info_controls.append(
                ft.Text(
                    expense.title,
                    size=13
                )
            )

        info_controls.extend(
            [
                ft.Divider(),
                image
            ]
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
                controls=info_controls
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
            # 1. GETRÄNKEZÄHLER VERRINGERN
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
            # 2. BELEG LÖSCHEN
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
            # 3. AUSGABE ENTFERNEN
            # -------------------------------------------------

            if expense in self.app.expense_objects:

                self.app.expense_objects.remove(
                    expense
                )

            # -------------------------------------------------
            # 4. SPEICHERN
            # -------------------------------------------------

            self.app.save_data()

            self.update_overview()

            # -------------------------------------------------
            # 5. GETRÄNKELISTE AKTUALISIEREN
            # -------------------------------------------------

            if "beverage_main" in self.app.screens:

                self.app.screens[
                    "beverage_main"
                ].update_list()

            # -------------------------------------------------
            # 6. ANIMATION
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

        # -----------------------------------------------------
        # FELDER
        # -----------------------------------------------------

        market_field = ft.TextField(
            label="Markt",
            hint_text="z.B. REWE, Kaufland, EDEKA"
        )

        date_field = ft.TextField(
            label="Belegdatum",
            hint_text="TT.MM.JJJJ"
        )

        amount_field = ft.TextField(
            label="Endsumme in €",
            hint_text="z.B. 74,09",
            keyboard_type=ft.KeyboardType.NUMBER
        )

        # -----------------------------------------------------
        # GETRÄNKE
        # -----------------------------------------------------

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
        # OCR-STATUS
        # -----------------------------------------------------

        ocr_status = ft.Text(
            "",
            size=12,
            color=ft.Colors.GREY_600
        )

        ocr_button = ft.FilledTonalButton(
            "Beleg automatisch auslesen",
            icon=ft.Icons.DOCUMENT_SCANNER,
        )

        # -----------------------------------------------------
        # BELEG-STATUS
        # -----------------------------------------------------

        receipt_data = {
            "bytes": None,
            "extension": ".jpg",
            "name": None,
            "path": None
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

        # =====================================================
        # HILFSFUNKTIONEN
        # =====================================================

        def clear_error(field):

            if field.error_text:

                field.error_text = None

        # =====================================================
        # GETRÄNKEZÄHLER AKTUALISIEREN
        # =====================================================

        def update_count_label(beverage):

            count_labels[
                beverage
            ].value = (
                f"{session_counts[beverage]}x"
            )

        # =====================================================
        # BELEG-VORSCHAU
        # =====================================================

        def update_receipt_preview():

            data = receipt_data["bytes"]

            if not data:

                receipt_preview.visible = False
                receipt_preview.content = None

                receipt_status.value = (
                    "Kein Beleg ausgewählt."
                )

                remove_receipt_button.visible = False

                ocr_button.disabled = True

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

            ocr_button.disabled = False

            self.app.page.update()

        # =====================================================
        # BELEG ENTFERNEN
        # =====================================================

        def remove_receipt(e=None):

            if receipt_data["path"]:

                delete_receipt(
                    receipt_data["path"]
                )

            receipt_data["bytes"] = None
            receipt_data["name"] = None
            receipt_data["extension"] = ".jpg"
            receipt_data["path"] = None

            ocr_status.value = ""

            update_receipt_preview()

        remove_receipt_button.on_click = remove_receipt

        # =====================================================
        # TEMPORÄREN BELEG SPEICHERN
        # =====================================================

        def save_receipt_for_ocr():

            if not receipt_data["bytes"]:
                return False

            # Bereits gespeichert
            if receipt_data["path"]:

                return True

            try:

                receipt_data["path"] = save_receipt(
                    receipt_data["bytes"],
                    receipt_data["extension"]
                )

                return True

            except Exception as ex:

                print(
                    "Temporary receipt save error:",
                    ex
                )

                return False

        # =====================================================
        # BILD AUSWÄHLEN
        # =====================================================

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

                # Alten temporären Beleg löschen
                if receipt_data["path"]:

                    delete_receipt(
                        receipt_data["path"]
                    )

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

                receipt_data["path"] = None

                ocr_status.value = ""

                update_receipt_preview()

            except Exception as ex:

                self.show_message(
                    "Bild konnte nicht ausgewählt werden."
                )

                print(
                    "Receipt picker error:",
                    ex
                )

        # =====================================================
        # FOTO AUFNEHMEN
        # =====================================================

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

                        # Alten Beleg löschen
                        if receipt_data["path"]:

                            delete_receipt(
                                receipt_data["path"]
                            )

                        receipt_data["bytes"] = data
                        receipt_data["extension"] = ".jpg"
                        receipt_data["name"] = (
                            "Aufgenommenes Foto"
                        )
                        receipt_data["path"] = None

                        ocr_status.value = ""

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

        # =====================================================
        # GETRÄNK HINZUFÜGEN
        # =====================================================

        def increment_beverage(beverage):

            session_counts[beverage] += 1

            update_count_label(
                beverage
            )

            self.app.page.update()

        # =====================================================
        # AUSWAHL ZURÜCKSETZEN
        # =====================================================

        def reset_counts(e=None):

            for beverage in session_counts:

                session_counts[beverage] = 0

                update_count_label(
                    beverage
                )

            self.app.page.update()

        # =====================================================
        # GETRÄNKELISTE
        # =====================================================

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

        # =====================================================
        # OCR
        # =====================================================

        async def run_ocr(e=None):

            if not receipt_data["bytes"]:

                self.show_message(
                    "Bitte zuerst einen Beleg auswählen "
                    "oder fotografieren."
                )

                return

            if not save_receipt_for_ocr():

                self.show_message(
                    "Der Beleg konnte für die "
                    "Texterkennung nicht gespeichert werden."
                )

                return

            ocr_button.disabled = True

            ocr_status.value = (
                "Beleg wird automatisch ausgelesen …"
            )

            self.app.page.update()

            try:

                receipt_path = get_receipt_path(
                    receipt_data["path"]
                )

                if not receipt_path:

                    raise RuntimeError(
                        "Der Pfad zum Beleg konnte nicht ermittelt werden."
                    )

                # OCR nicht auf dem UI-Thread ausführen.
                raw_text = await asyncio.to_thread(
                    recognize_receipt_text,
                    str(receipt_path)
                )

                if not raw_text:

                    raise RuntimeError(
                        "Auf dem Beleg wurde kein Text erkannt."
                    )

                # -------------------------------------------------
                # OCR-TEXT AUSWERTEN
                # -------------------------------------------------

                result = parse_receipt(
                    raw_text,
                    self.app.beverage_objects
                )

                self._last_ocr_matches = result.get(
                    "matches",
                    []
                )

                # -------------------------------------------------
                # DATUM
                # -------------------------------------------------

                detected_date = result.get(
                    "date"
                )

                if detected_date:

                    date_field.value = (
                        detected_date
                    )

                # -------------------------------------------------
                # MARKT
                # -------------------------------------------------

                detected_market = result.get(
                    "market"
                )

                if detected_market:

                    market_field.value = (
                        detected_market
                    )

                # -------------------------------------------------
                # ENDSUMME
                # -------------------------------------------------

                detected_total = result.get(
                    "total"
                )

                if detected_total is not None:

                    amount_field.value = (
                        f"{detected_total:.2f}"
                    )

                # -------------------------------------------------
                # ERKANNTE GETRÄNKE
                # -------------------------------------------------

                detected_items = result.get(
                    "items",
                    {}
                )

                # Erst aktuelle Auswahl löschen
                for beverage in session_counts:

                    session_counts[
                        beverage
                    ] = 0

                    update_count_label(
                        beverage
                    )

                # Dann OCR-Ergebnis übernehmen
                for beverage, count in (
                    detected_items.items()
                ):

                    if beverage not in session_counts:
                        continue

                    session_counts[
                        beverage
                    ] = int(count)

                    update_count_label(
                        beverage
                    )

                # -------------------------------------------------
                # ERGEBNIS
                # -------------------------------------------------

                matched_count = len(
                    detected_items
                )

                unmatched = result.get(
                    "unmatched",
                    []
                )

                if unmatched:

                    ocr_status.value = (
                        f"{matched_count} Getränkesorten erkannt. "
                        f"{len(unmatched)} Position(en) "
                        f"nicht eindeutig erkannt."
                    )

                else:

                    ocr_status.value = (
                        f"Beleg erkannt: "
                        f"{matched_count} Getränkesorten."
                    )

                self.app.page.update()

            except Exception as ex:

                print(
                    "OCR error:",
                    ex
                )

                ocr_status.value = (
                    "Beleg konnte nicht automatisch "
                    "ausgelesen werden."
                )

                self.show_message(
                    "Die automatische Belegerkennung "
                    "konnte nicht durchgeführt werden.\n\n"
                    f"Fehler:\n{ex}"
                )

            finally:

                ocr_button.disabled = False

                self.app.page.update()

        ocr_button.on_click = run_ocr

        # =====================================================
        # BELEG-BEREICH
        # =====================================================

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
                            ),

                            ocr_button
                        ]
                    ),

                    ocr_status,

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

        # =====================================================
        # SPEICHERN
        # =====================================================

        def save(e):

            # -------------------------------------------------
            # FELD-FEHLER ZURÜCKSETZEN
            # -------------------------------------------------

            clear_error(
                amount_field
            )

            clear_error(
                market_field
            )

            clear_error(
                date_field
            )

            # -------------------------------------------------
            # GETRÄNKE
            # -------------------------------------------------

            selected_items = [
                f"{count}x {beverage.name}"
                for beverage, count
                in session_counts.items()
                if count > 0
            ]

            title = ", ".join(
                selected_items
            )

            # -------------------------------------------------
            # BETRAG
            # -------------------------------------------------

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

                if "," in amount_raw:

                    amount = float(
                        amount_raw.replace(
                            ".",
                            ""
                        ).replace(
                            ",",
                            "."
                        )
                    )

                else:

                    amount = float(
                        amount_raw
                    )

            except ValueError:

                amount_field.error_text = (
                    "Bitte einen gültigen Betrag eingeben."
                )

                amount_field.update()

                return

            if amount < 0:

                amount_field.error_text = (
                    "Der Betrag darf nicht negativ sein."
                )

                amount_field.update()

                return

            # -------------------------------------------------
            # GEKAUFTE GETRÄNKE
            # -------------------------------------------------

            purchased_items = {
                beverage: count
                for beverage, count
                in session_counts.items()
                if count > 0
            }

            # -------------------------------------------------
            # MARKT
            # -------------------------------------------------

            merchant = (
                market_field.value.strip()
                if market_field.value
                else None
            )

            if not merchant:
                merchant = None

            # -------------------------------------------------
            # DATUM
            # -------------------------------------------------

            receipt_date = (
                date_field.value.strip()
                if date_field.value
                else None
            )

            if not receipt_date:
                receipt_date = None

            # -------------------------------------------------
            # BELEG
            # -------------------------------------------------

            receipt_path = receipt_data["path"]

            if receipt_data["bytes"] and not receipt_path:

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
            # EXPENSE ERSTELLEN
            # -------------------------------------------------

            new_expense = Expense(
                title=title,
                amount=amount,
                items=purchased_items,
                receipt=receipt_path,
                merchant=merchant,
                receipt_date=receipt_date
            )

            self.app.expense_objects.append(
                new_expense
            )

            # -------------------------------------------------
            # GETRÄNKEZÄHLER ERHÖHEN
            # -------------------------------------------------

            for beverage, added_count in (
                purchased_items.items()
            ):

                beverage.count += added_count

            # -------------------------------------------------
            # OCR-ALIASE LERNEN
            #
            # Die Parser-Ergebnisse enthalten die ursprünglich
            # erkannten Bezeichnungen.
            #
            # Beispiel:
            #
            # REWE-Beleg:
            # "UR KROE 20X0,5"
            #
            # -> Ur-Krostitzer
            #
            # Dieser Name kann anschließend als
            # Markt-Alias gespeichert werden.
            # -------------------------------------------------

            # Die Alias-Übernahme erfolgt über das Ergebnis,
            # das während der OCR gespeichert wurde.
            #
            # Falls receipt_parser eine Liste "matches"
            # liefert, werden die bestätigten Zuordnungen
            # hier übernommen.

            ocr_matches = getattr(
                self,
                "_last_ocr_matches",
                []
            )

            for match in ocr_matches:

                beverage = match.get(
                    "beverage"
                )

                raw_name = match.get(
                    "raw_name"
                )

                if not beverage or not raw_name:
                    continue

                if beverage not in purchased_items:
                    continue

                if hasattr(
                    beverage,
                    "add_alias"
                ):

                    beverage.add_alias(
                        raw_name,
                        merchant
                    )

            # -------------------------------------------------
            # SPEICHERN
            # -------------------------------------------------

            self.app.save_data()

            self.update_overview()

            if "beverage_main" in self.app.screens:

                self.app.screens[
                    "beverage_main"
                ].update_list()

            # -------------------------------------------------
            # ANIMATION
            # -------------------------------------------------

            asyncio.create_task(
                booking_animation(
                    self.app.page,
                    animation="success"
                )
            )

            self.app.page.pop_dialog()

            self.app.page.update()

        # =====================================================
        # DIALOG
        # =====================================================

        dialog = ft.AlertDialog(
            modal=True,

            title=ft.Text(
                "Ausgabe buchen"
            ),

            content=ft.Container(
                width=420,

                content=ft.Column(
                    controls=[

                        market_field,

                        date_field,

                        amount_field,

                        ft.Divider(),

                        ft.Text(
                            "Getränke",
                            weight=ft.FontWeight.BOLD
                        ),

                        beverage_list,

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

        # -----------------------------------------------------
        # BELEG ZUM OCR-PARSER ÜBERGEBEN
        # -----------------------------------------------------
        #
        # Wir überschreiben run_ocr mit einer kleinen Erweiterung,
        # damit die gefundenen Alias-Zuordnungen für save()
        # verfügbar bleiben.
        #
        # Die eigentliche OCR-Funktion bleibt oben.
        #

        original_run_ocr = run_ocr

        async def run_ocr_with_matches(e=None):

            self._last_ocr_matches = []

            await original_run_ocr(
                e
            )

        ocr_button.on_click = run_ocr_with_matches

        # =====================================================
        # DIALOG ANZEIGEN
        # =====================================================

        self.app.page.show_dialog(
            dialog
        )

        update_receipt_preview()

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