import json
import flet as ft
import asyncio

from Utils.classes import Person, Expense, Beverage
from Utils.updater import APP_VERSION, check_for_update, download_and_install_update
from Utils.logger import log, log_error



class SettingsScreen(ft.Column):

    def __init__(self, app):
        super().__init__(
            expand=True,
            spacing=0
        )

        self.app = app

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
            ft.Container(
                padding=16,
                content=self.settings_list
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

        return {
            "persons": [
                person.to_dict()
                for person in self.app.person_objects
            ],
            "expenses": [
                expense.to_dict()
                for expense in self.app.expense_objects
            ],
            "beverages": [
                beverage.to_dict()
                for beverage in self.app.beverage_objects
            ]
        }

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

            if not isinstance(data, dict):
                raise ValueError(
                    "Die Datei enthält keine gültige Datenstruktur."
                )

            if "persons" not in data:
                raise ValueError(
                    "Der Bereich 'persons' fehlt."
                )

            if "expenses" not in data:
                raise ValueError(
                    "Der Bereich 'expenses' fehlt."
                )

            if "beverages" not in data:
                raise ValueError(
                    "Der Bereich 'beverages' fehlt."
                )

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

                # Personen
                self.app.person_objects.clear()

                for person_data in data["persons"]:
                    person = Person.from_dict(person_data)
                    self.app.person_objects.append(person)

                # Ausgaben
                self.app.expense_objects.clear()

                for expense_data in data["expenses"]:
                    expense = Expense.from_dict(expense_data, self.app.beverage_objects)
                    self.app.expense_objects.append(expense)

                # Getränke
                self.app.beverage_objects.clear()

                for beverage_data in data["beverages"]:
                    beverage = Beverage.from_dict(beverage_data)
                    self.app.beverage_objects.append(beverage)

                # Speichern
                self.app.save_data()
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

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Daten importieren"),
            content=ft.Text(
                "Möchtest du die aktuellen Daten wirklich durch die importierten Daten ersetzen?\n\n"
                f"Personen: {person_count}\n"
                f"Ausgaben: {expense_count}\n"
                f"Getränkesorten: {beverage_count}\n\n"
                "Dieser Vorgang kann nicht rückgängig gemacht werden."
            ),
            actions=[
                ft.TextButton(
                    "Abbrechen",
                    on_click=lambda e: self.app.page.pop_dialog()
                ),
                ft.FilledButton(
                    "Importieren",
                    on_click=perform_import
                )
            ]
        )

        self.app.page.show_dialog(dialog)

    # =========================================================
    # RESET
    # =========================================================

    def confirm_reset_all(self, e=None):

        def perform_reset(_):

            # Personen-Buchungen löschen
            for person in self.app.person_objects:

                if hasattr(person, "transactions"):
                    person.transactions.clear()

            # Ausgaben löschen
            self.app.expense_objects.clear()

            # Getränkezähler zurücksetzen
            for beverage in self.app.beverage_objects:
                beverage.count = 0

            self.app.save_data()
            self.app.page.pop_dialog()
            self.app.refresh_all_screens()

            self.show_dialog(
                "Zurücksetzen erfolgreich",
                "Alle Zählerstände, Guthaben und "
                "Ausgaben wurden auf 0 zurückgesetzt."
            )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Kasse zurücksetzen"),
            content=ft.Text(
                "Möchtest du wirklich alle Guthaben, "
                "Ausgaben und gezählten Getränke auf 0 "
                "zurücksetzen?\n\n"
                "Die angelegten Personen und Getränkesorten "
                "bleiben dabei bestehen."
            ),
            actions=[
                ft.TextButton(
                    "Abbrechen",
                    on_click=lambda e: self.app.page.pop_dialog()
                ),
                ft.FilledButton(
                    "Alles zurücksetzen",
                    on_click=perform_reset
                )
            ]
        )

        self.app.page.show_dialog(dialog)

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

    async def download_update(
            self,
            download_url
    ):
        log("================================")
        log("Update-Installation gestartet")
        log(
            f"Download-URL: {download_url}"
        )

        try:

            self.app.page.pop_dialog()

            log(
                "Lade neue APK herunter..."
            )

            apk_path = (
                await download_and_install_update(
                    download_url
                )
            )

            log(
                f"APK heruntergeladen: "
                f"{apk_path}"
            )

            log(
                "Android-Installer wurde "
                "gestartet."
            )

            self.show_dialog(
                "Update wird installiert",
                "Die neue Version wurde "
                "heruntergeladen.\n\n"
                "Android öffnet jetzt den "
                "Installationsdialog.\n\n"
                "Bestätige dort die Installation."
            )

        except Exception as ex:

            log_error(
                "Update-Fehler: "
                f"{type(ex).__name__}"
            )

            log_error(
                f"Fehlermeldung: {ex}"
            )

            self.show_dialog(
                "Update fehlgeschlagen",
                "Das Update konnte nicht "
                "gestartet werden.\n\n"
                f"Fehler:\n{ex}"
            )

        log(
            "Update-Installation beendet"
        )

        log("================================")

    # =========================================================
    # ALLGEMEINER DIALOG
    # =========================================================

    def show_dialog(self, title, message):

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[
                ft.FilledButton(
                    "OK",
                    on_click=lambda e: self.app.page.pop_dialog()
                )
            ]
        )

        self.app.page.show_dialog(dialog)

    # =========================================================
    # REFRESH
    # =========================================================

    def refresh(self):
        self.update()