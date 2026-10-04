"""Camera, receipt, and expense-entry workflows for the overview screen."""

import asyncio
import sys
from pathlib import Path

import flet as ft
import flet_permission_handler as fph

from Utils.animations import booking_animation
from Utils.classes import Expense
from Utils.receipts import save_receipt
from Screens.dialogs import show_message_dialog


class ExpenseWorkflowMixin:
    async def request_camera_permission(self):
        """
        Prüft die Kamera-Berechtigung und fordert sie bei Bedarf an.

        Rückgabe:
            True  = Kamera darf verwendet werden
            False = Kamera darf nicht verwendet werden
        """

        try:

            status = await self.permission_handler.get_status(
                fph.Permission.CAMERA
            )

            print(
                "Camera permission status:",
                status
            )

            # -------------------------------------------------
            # Bereits erlaubt
            # -------------------------------------------------

            if status == fph.PermissionStatus.GRANTED:
                return True

            # -------------------------------------------------
            # Berechtigung noch nicht erteilt
            # -------------------------------------------------

            status = await self.permission_handler.request(
                fph.Permission.CAMERA
            )

            print(
                "Camera permission request result:",
                status
            )

            if status == fph.PermissionStatus.GRANTED:
                return True

            # -------------------------------------------------
            # Dauerhaft verweigert
            # -------------------------------------------------

            if status == (
                fph.PermissionStatus.PERMANENTLY_DENIED
            ):

                await self.show_camera_permission_dialog(
                    permanently_denied=True
                )

                return False

            # -------------------------------------------------
            # Normal abgelehnt
            # -------------------------------------------------

            if status == fph.PermissionStatus.DENIED:

                await self.show_camera_permission_dialog(
                    permanently_denied=False
                )

                return False

            # -------------------------------------------------
            # Sonstige Zustände
            # -------------------------------------------------

            self.show_message(
                "Der Zugriff auf die Kamera wurde "
                "vom System nicht freigegeben."
            )

            return False

        except Exception as ex:

            print(
                "Camera permission error:",
                type(ex).__name__,
                ex
            )

            self.show_message(
                "Die Kamera-Berechtigung konnte nicht "
                "angefragt werden.\n\n"
                f"Fehler: {type(ex).__name__}: {ex}"
            )

            return False

    # =========================================================
    # KAMERA-BERECHTIGUNG DIALOG
    # =========================================================

    async def show_camera_permission_dialog(
        self,
        permanently_denied=False
    ):
        """
        Zeigt eine verständliche Meldung an,
        wenn der Kamerazugriff verweigert wurde.
        """

        if permanently_denied:

            async def open_settings(e=None):

                self.app.page.pop_dialog()

                try:

                    opened = (
                        await self.permission_handler
                        .open_app_settings()
                    )

                    if not opened:

                        self.show_message(
                            "Die Android-Einstellungen "
                            "konnten nicht geöffnet werden.\n\n"
                            "Bitte öffne die App-Einstellungen "
                            "manuell und erlaube den Zugriff "
                            "auf die Kamera."
                        )

                except Exception as ex:

                    print(
                        "Open app settings error:",
                        type(ex).__name__,
                        ex
                    )

                    self.show_message(
                        "Die App-Einstellungen konnten "
                        "nicht geöffnet werden.\n\n"
                        "Bitte öffne die Einstellungen von "
                        "BeverageOrganiser manuell und "
                        "erlaube den Kamerazugriff."
                    )

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "Kamerazugriff benötigt"
                ),
                content=ft.Text(
                    "Der Zugriff auf die Kamera wurde "
                    "dauerhaft verweigert.\n\n"
                    "Damit du Belege fotografieren kannst, "
                    "muss der Kamerazugriff in den "
                    "Android-App-Einstellungen aktiviert werden."
                ),
                actions=[
                    ft.TextButton(
                        "Abbrechen",
                        on_click=lambda e:
                        self.app.page.pop_dialog()
                    ),
                    ft.FilledButton(
                        "Einstellungen öffnen",
                        icon=ft.Icons.SETTINGS,
                        on_click=open_settings
                    )
                ]
            )

        else:

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text(
                    "Kamerazugriff benötigt"
                ),
                content=ft.Text(
                    "BeverageOrganiser benötigt Zugriff "
                    "auf die Kamera, um einen Beleg zu "
                    "fotografieren.\n\n"
                    "Du kannst den Kamerazugriff erlauben "
                    "oder weiterhin ein Bild aus der Galerie "
                    "auswählen."
                ),
                actions=[
                    ft.TextButton(
                        "Abbrechen",
                        on_click=lambda e:
                        self.app.page.pop_dialog()
                    )
                ]
            )

        self.app.page.show_dialog(
            dialog
        )

        self.app.page.update()

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
                    type(ex).__name__,
                    ex
                )

        # -----------------------------------------------------
        # FOTO AUFNEHMEN
        # -----------------------------------------------------

        async def take_receipt_photo(e=None):

            # -------------------------------------------------
            # Windows
            # -------------------------------------------------

            if sys.platform == "win32":

                self.show_message(
                    "Die Kamera ist unter Windows "
                    "in der App nicht verfügbar.\n\n"
                    "Bitte benutze dort "
                    "'Bild auswählen'."
                )

                return

            # -------------------------------------------------
            # KAMERA-BERECHTIGUNG
            # -------------------------------------------------

            permission_granted = (
                await self.request_camera_permission()
            )

            if not permission_granted:

                return

            # -------------------------------------------------
            # CAMERA PLUGIN LADEN
            # -------------------------------------------------

            try:

                import flet_camera as fc

            except ImportError as ex:

                print(
                    "Camera import error:",
                    type(ex).__name__,
                    ex
                )

                self.show_message(
                    "Das Kamera-Modul ist nicht installiert.\n\n"
                    "Bitte installiere "
                    "'flet-camera==1.0.3'."
                )

                return

            # -------------------------------------------------
            # KAMERA ERSTELLEN
            # -------------------------------------------------

            camera = None
            camera_dialog = None

            try:

                camera = fc.Camera(
                    expand=True,
                    preview_enabled=True
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

                        receipt_data["extension"] = (
                            ".jpg"
                        )

                        receipt_data["name"] = (
                            "Aufgenommenes Foto"
                        )

                        self.app.page.pop_dialog()

                        update_receipt_preview()

                    except Exception as ex:

                        print(
                            "Camera capture error:",
                            type(ex).__name__,
                            ex
                        )

                        self.show_message(
                            "Foto konnte nicht aufgenommen werden.\n\n"
                            f"Fehler: {type(ex).__name__}: {ex}"
                        )

                def close_camera_dialog(e=None):

                    try:
                        self.app.page.pop_dialog()
                    except Exception:
                        pass

                # -------------------------------------------------
                # KAMERA-DIALOG
                # -------------------------------------------------

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
                            on_click=close_camera_dialog
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

                # -------------------------------------------------
                # JETZT darf die Camera verwendet werden.
                # -------------------------------------------------

                cameras = (
                    await camera.get_available_cameras()
                )

                if not cameras:

                    self.app.page.pop_dialog()

                    self.show_message(
                        "Es wurde keine Kamera gefunden.\n\n"
                        "Bitte überprüfe, ob dein Android-Gerät "
                        "über eine funktionierende Kamera verfügt."
                    )

                    return

                # -------------------------------------------------
                # Rückkamera bevorzugen
                # -------------------------------------------------

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

                self.app.page.update()

            except Exception as ex:

                print(
                    "Camera error:",
                    type(ex).__name__,
                    ex
                )

                # Wenn der Kamera-Dialog bereits geöffnet wurde,
                # schließen wir ihn vor der Fehlermeldung.
                try:
                    if camera_dialog is not None:
                        self.app.page.pop_dialog()
                except Exception:
                    pass

                self.show_message(
                    "Die Kamera konnte nicht gestartet werden.\n\n"
                    f"Fehler: {type(ex).__name__}: {ex}"
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
                        type(ex).__name__,
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
        show_message_dialog(
            self.app.page,
            "Hinweis",
            message,
            filled_button=False,
        )

    # =========================================================
