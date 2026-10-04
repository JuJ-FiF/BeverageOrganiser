import copy
import json
import flet as ft

from Utils.data_transfer import (
    build_import_data,
    create_export_data,
    validate_import_data,
)
from Screens.dialogs import show_confirmation_dialog, show_message_dialog
from Utils.updater import check_for_update, download_and_install_update
from Utils.version import APP_VERSION

class SettingsScreen(ft.Column):

    def __init__(self, app):
        super().__init__(
            expand=True,
            spacing=0
        )

        self.app = app

        # -----------------------------------------------------
        # UPDATE ANZEIGE
        # -----------------------------------------------------

        self.update_status = ft.Container(
            visible=False,
            bgcolor=ft.Colors.GREEN,
            padding=ft.Padding(
                left=16,
                right=16,
                top=10,
                bottom=10
            ),
            content=ft.Row(
                [
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE,
                        color=ft.Colors.WHITE
                    ),
                    ft.Text(
                        "Update wird vorbereitet …",
                        color=ft.Colors.WHITE,
                        weight=ft.FontWeight.BOLD
                    )
                ],
                spacing=10
            )
        )

        # -----------------------------------------------------
        # FILE PICKER
        # -----------------------------------------------------

        self.file_picker = ft.FilePicker()
        self.settings_list = ft.ListView(
            expand=True,
            spacing=0
        )

        # -----------------------------------------------------
        # 1. EXPORT
        # -----------------------------------------------------

        self.settings_list.controls.append(
            ft.ListTile(
                leading=ft.Icon(ft.Icons.DOWNLOAD),
                title=ft.Text(
                    "Daten exportieren",
                    weight=ft.FontWeight.BOLD
                ),
                subtitle=ft.Text(
                    "Sichert die aktuellen Daten (Personen, "
                    "Ausgaben und Getränke) als JSON-Datei."
                ),
                on_click=self.export_data
            )
        )

        self.settings_list.controls.append(ft.Divider())

        # -----------------------------------------------------
        # 2. IMPORT
        # -----------------------------------------------------

        self.settings_list.controls.append(
            ft.ListTile(
                leading=ft.Icon(ft.Icons.UPLOAD_FILE),
                title=ft.Text(
                    "Daten importieren",
                    weight=ft.FontWeight.BOLD
                ),
                subtitle=ft.Text(
                    "Lädt eine zuvor exportierte JSON-Datei "
                    "und stellt die Daten wieder her."
                ),
                on_click=self.import_data
            )
        )

        self.settings_list.controls.append(
            ft.Divider()
        )

        # -----------------------------------------------------
        # 3. RESET
        # -----------------------------------------------------

        self.settings_list.controls.append(
            ft.ListTile(
                leading=ft.Icon(ft.Icons.RESTART_ALT),
                title=ft.Text(
                    "Kasse & Zähler zurücksetzen",
                    weight=ft.FontWeight.BOLD
                ),
                subtitle=ft.Text(
                    "Setzt Budgets, Ausgaben und "
                    "Getränkezähler auf 0. "
                    "Personen und Sorten bleiben erhalten."
                ),
                on_click=self.confirm_reset_all
            )
        )

        self.controls = [
            self.update_status,

            ft.Container(
                padding=16,
                content=self.settings_list,
                expand=True
            )
        ]

        # -----------------------------------------------------
        # 4. NACH UPDATES SUCHEN
        # -----------------------------------------------------

        self.settings_list.controls.append(
            ft.Divider()
        )

        self.settings_list.controls.append(
            ft.ListTile(
                leading=ft.Icon(ft.Icons.SYSTEM_UPDATE),
                title=ft.Text(
                    "Nach Updates suchen",
                    weight=ft.FontWeight.BOLD
                ),
                subtitle=ft.Text(
                    f"Aktuelle Version: {APP_VERSION}"
                ),
                on_click=self.check_updates
            )
        )

    # =========================================================
    # DATEN FÜR EXPORT ERSTELLEN
    # =========================================================

    def create_export_data(self):
        return create_export_data(
            self.app.person_objects,
            self.app.expense_objects,
            self.app.beverage_objects,
        )

    # =========================================================
    # EXPORT
    # =========================================================

    async def export_data(self, e=None):

        try:

            data = self.create_export_data()
            json_data = json.dumps(data, ensure_ascii=False, indent=4)
            file_bytes = json_data.encode("utf-8")

            result = await self.file_picker.save_file(
                dialog_title="Daten sichern",
                file_name="kassenstand_export.json",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["json"],
                src_bytes=file_bytes
            )

            if not result:
                return

            self.show_dialog(
                "Export erfolgreich",
                "Die Daten wurden erfolgreich exportiert."
            )

        except Exception as ex:

            self.show_dialog(
                "Export fehlgeschlagen",
                f"Fehler beim Export:\n{ex}"
            )

    # =========================================================
    # IMPORT
    # =========================================================

    async def import_data(self, e=None):

        try:

            files = await self.file_picker.pick_files(
                dialog_title="Daten importieren",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["json"],
                allow_multiple=False,
                with_data=True
            )

            if not files:
                return

            selected_file = files[0]

            if not selected_file.bytes:
                self.show_dialog(
                    "Import fehlgeschlagen",
                    "Die ausgewählte Datei konnte nicht gelesen werden."
                )
                return

            data = json.loads(
                selected_file.bytes.decode("utf-8")
            )

            validate_import_data(data)

            self.confirm_import(data)

        except json.JSONDecodeError:

            self.show_dialog(
                "Import fehlgeschlagen",
                "Die ausgewählte Datei ist keine gültige JSON-Datei."
            )

        except Exception as ex:

            self.show_dialog(
                "Import fehlgeschlagen",
                f"Fehler beim Import:\n{ex}"
            )

    # =========================================================
    # IMPORT BESTÄTIGEN
    # =========================================================

    def confirm_import(self, data):

        person_count = len(data.get("persons", []))
        expense_count = len(data.get("expenses", []))
        beverage_count = len(data.get("beverages", []))

        def perform_import(e):

            try:
                previous_state = (
                    self.app.person_objects,
                    self.app.expense_objects,
                    self.app.beverage_objects,
                )
                persons, expenses, beverages = build_import_data(data)
                self.app.person_objects = persons
                self.app.expense_objects = expenses
                self.app.beverage_objects = beverages

                if not self.app.save_data():
                    (
                        self.app.person_objects,
                        self.app.expense_objects,
                        self.app.beverage_objects,
                    ) = previous_state
                    self.app.page.pop_dialog()
                    self.app.refresh_all_screens()
                    self.show_dialog(
                        "Speichern fehlgeschlagen",
                        "Der Import wurde nicht übernommen. "
                        "Die bisherigen Daten bleiben erhalten.",
                    )
                    return

                self.app.page.pop_dialog()
                self.app.refresh_all_screens()

                self.show_dialog(
                    "Import erfolgreich",
                    f"Die Daten wurden erfolgreich importiert.\n\n"
                    f"Personen: {person_count}\n"
                    f"Ausgaben: {expense_count}\n"
                    f"Getränkesorten: {beverage_count}"
                )

            except Exception as ex:

                self.app.page.pop_dialog()

                self.show_dialog(
                    "Import fehlgeschlagen",
                    f"Fehler beim Übernehmen der Daten:\n{ex}"
                )

        show_confirmation_dialog(
            self.app.page,
            "Daten importieren",
            "Möchtest du die aktuellen Daten wirklich durch die "
            "importierten Daten ersetzen?\n\n"
            f"Personen: {person_count}\n"
            f"Ausgaben: {expense_count}\n"
            f"Getränkesorten: {beverage_count}\n\n"
            "Dieser Vorgang kann nicht rückgängig gemacht werden.",
            "Importieren",
            perform_import,
        )

    # =========================================================
    # RESET
    # =========================================================

    def confirm_reset_all(self, e=None):

        def perform_reset(_):
            previous_state = copy.deepcopy((
                self.app.person_objects,
                self.app.expense_objects,
                self.app.beverage_objects,
            ))

            # Personen-Buchungen löschen
            for person in self.app.person_objects:

                if hasattr(person, "transactions"):
                    person.transactions.clear()

            # Ausgaben löschen
            self.app.expense_objects.clear()

            # Getränkezähler zurücksetzen
            for beverage in self.app.beverage_objects:
                beverage.count = 0

            if not self.app.save_data():
                (
                    self.app.person_objects,
                    self.app.expense_objects,
                    self.app.beverage_objects,
                ) = previous_state
                self.app.page.pop_dialog()
                self.app.refresh_all_screens()
                self.show_dialog(
                    "Speichern fehlgeschlagen",
                    "Das Zurücksetzen wurde nicht übernommen. "
                    "Die bisherigen Daten bleiben erhalten.",
                )
                return

            self.app.page.pop_dialog()
            self.app.refresh_all_screens()

            self.show_dialog(
                "Zurücksetzen erfolgreich",
                "Alle Zählerstände, Guthaben und "
                "Ausgaben wurden auf 0 zurückgesetzt."
            )

        show_confirmation_dialog(
            self.app.page,
            "Kasse zurücksetzen",
            "Möchtest du wirklich alle Guthaben, Ausgaben und "
            "gezählten Getränke auf 0 zurücksetzen?\n\n"
            "Die angelegten Personen und Getränkesorten "
            "bleiben dabei bestehen.",
            "Alles zurücksetzen",
            perform_reset,
        )

    # =========================================================
    # CHECK NACH UPDATES
    # =========================================================

    async def check_updates(self, e=None):

        # Button während der Prüfung deaktivieren
        if e is not None and hasattr(e, "control"):
            e.control.disabled = True
            e.control.update()

        try:

            update = await check_for_update()

            if update is None:
                self.show_dialog(
                    "Keine Updates",
                    (
                        "Du verwendest bereits die "
                        f"aktuelle Version {APP_VERSION}."
                    )
                )

                return

            self.show_update_dialog(update)

        except Exception as ex:

            self.show_dialog(
                "Updateprüfung fehlgeschlagen",
                (
                    "Die Suche nach Updates konnte "
                    "nicht durchgeführt werden.\n\n"
                    f"Fehler:\n{ex}"
                )
            )

        finally:

            if e is not None and hasattr(e, "control"):
                e.control.disabled = False
                e.control.update()

    def show_update_dialog(self, update):

        async def on_download_click(e):
            await self.download_update(
                update["download_url"]
            )

        dialog = ft.AlertDialog(
            modal=True,

            title=ft.Text(
                f"Update verfügbar: v{update['version']}"
            ),

            content=ft.Column(
                [
                    ft.Text(
                        update["changelog"]
                        or "Keine Änderungen angegeben."
                    ),
                ],
                tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),

            actions=[
                ft.TextButton(
                    "Später",
                    on_click=lambda e:
                    self.app.page.pop_dialog(),
                ),

                ft.FilledButton(
                    "Update installieren",
                    icon=ft.Icons.SYSTEM_UPDATE,
                    on_click=on_download_click,
                ),
            ],
        )

        self.app.page.show_dialog(
            dialog
        )

    def show_update_status(self):

        self.update_status.visible = True

        self.update_status.content = ft.Row(
            [
                ft.Icon(
                    ft.Icons.CHECK_CIRCLE,
                    color=ft.Colors.WHITE
                ),
                ft.Text(
                    "Update wird vorbereitet …",
                    color=ft.Colors.WHITE,
                    weight=ft.FontWeight.BOLD
                )
            ],
            spacing=10
        )

        self.update_status.update()

    def hide_update_status(self):

        self.update_status.visible = False
        self.update_status.update()

    async def download_update(
            self,
            download_url
    ):

        try:

            # ---------------------------------------------
            # Update-Dialog schließen
            # ---------------------------------------------

            self.app.page.pop_dialog()

            # ---------------------------------------------
            # Grünen Status-Balken anzeigen
            # ---------------------------------------------

            self.show_update_status()

            # ---------------------------------------------
            # APK herunterladen und Installer starten
            # ---------------------------------------------

            apk_path = (
                await download_and_install_update(
                    download_url
                )
            )

            if apk_path is None:
                self.hide_update_status()
                self.show_dialog(
                    "Installation erlauben",
                    "Android hat die Einstellung für diese Quelle geöffnet. "
                    "Erlaube dort die Installation unbekannter Apps und "
                    "starte das Update anschließend erneut. Die APK wurde "
                    "noch nicht heruntergeladen.",
                )
                return

            # ---------------------------------------------
            # Status aktualisieren
            # ---------------------------------------------

            self.update_status.content = ft.Row(
                [
                    ft.Icon(
                        ft.Icons.SYSTEM_UPDATE,
                        color=ft.Colors.WHITE
                    ),
                    ft.Text(
                        "Update wird installiert …",
                        color=ft.Colors.WHITE,
                        weight=ft.FontWeight.BOLD
                    )
                ],
                spacing=10
            )

            self.update_status.update()

            # ---------------------------------------------
            # KEIN weiterer Dialog
            #
            # Android zeigt jetzt seinen eigenen
            # Installationsdialog.
            # ---------------------------------------------

        except Exception as ex:

            self.hide_update_status()

            self.show_dialog(
                "Update fehlgeschlagen",
                "Das Update konnte nicht "
                "gestartet werden.\n\n"
                f"Fehler:\n{ex}"
            )

    # =========================================================
    # ALLGEMEINER DIALOG
    # =========================================================

    def show_dialog(self, title, message):
        show_message_dialog(
            self.app.page,
            title,
            message,
        )

    # =========================================================
    # REFRESH
    # =========================================================

    def refresh(self):
        self.update()
