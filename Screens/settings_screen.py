import asyncio
import copy
import json
import sys
import flet as ft

from Utils.data_transfer import (
    build_import_data,
    create_export_data,
    validate_import_data,
)
from Screens.dialogs import show_confirmation_dialog, show_message_dialog
from Utils.updater import (
    check_for_update,
    download_apk,
    open_security_settings as open_android_security_settings,
    request_install_permission,
    start_android_update,
)
from Utils.version import APP_VERSION
from Utils.data_store import (
    format_euro_amount,
    save_deposit_amounts as persist_deposit_amounts,
    validate_deposit_amounts,
)
from Screens.ui_components import screen_heading

class SettingsScreen(ft.Column):

    def __init__(self, app):
        super().__init__(
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            spacing=0,
        )

        self.app = app

        # -----------------------------------------------------
        # UPDATE ANZEIGE
        # -----------------------------------------------------

        self.update_status = self.app.update_status_banner

        # -----------------------------------------------------
        # FILE PICKER
        # -----------------------------------------------------

        self.file_picker = ft.FilePicker()
        if self.file_picker not in self.app.page.services:
            self.app.page.services.append(self.file_picker)
        self.deposit_amount_summary = ft.Text(
            self.format_deposit_summary(self.app.deposit_amounts)
        )
        settings_cards = [
            self.settings_card(
                title="Einzahlungsbeträge",
                description=self.deposit_amount_summary,
                actions=[
                    self.action_button(
                        "Beträge anpassen",
                        ft.Icons.EDIT_OUTLINED,
                        self.open_deposit_amount_dialog,
                    )
                ],
                action_alignment=ft.MainAxisAlignment.END,
            ),
            self.settings_card(
                title="Datenverwaltung",
                icon=ft.Icons.SWAP_HORIZ,
                description=(
                    "Personen, Buchungen, Ausgaben und Getränke als JSON sichern "
                    "oder aus einem Export wiederherstellen."
                ),
                actions=[
                    self.action_button(
                        "Daten importieren",
                        ft.Icons.UPLOAD_FILE,
                        self.import_data,
                    ),
                    self.action_button(
                        "Daten exportieren",
                        ft.Icons.DOWNLOAD,
                        self.export_data,
                        primary=True,
                    ),
                ],
                action_alignment=ft.MainAxisAlignment.END,
            ),
            self.settings_card(
                title="Einstellungen sichern",
                icon=ft.Icons.SETTINGS_BACKUP_RESTORE,
                description=(
                    "Schnellbeträge als JSON-Datei sichern oder aus einem Export "
                    "wiederherstellen."
                ),
                actions=[
                    self.action_button(
                        "Einstellungen importieren",
                        ft.Icons.UPLOAD_FILE,
                        self.import_settings,
                    ),
                    self.action_button(
                        "Einstellungen exportieren",
                        ft.Icons.DOWNLOAD,
                        self.export_settings,
                        primary=True,
                    ),
                ],
                action_alignment=ft.MainAxisAlignment.END,
            ),
            self.settings_card(
                title="App-Updates",
                icon=ft.Icons.SYSTEM_UPDATE,
                description=(
                    "Updates werden geprüft und als Android-App installiert."
                ),
                details=ft.Text(f"Installierte Version: {APP_VERSION}"),
                actions=[
                    self.action_button(
                        "Nach Updates suchen",
                        ft.Icons.SYSTEM_UPDATE,
                        self.check_updates,
                    )
                ],
                action_alignment=ft.MainAxisAlignment.END,
            ),
            self.settings_card(
                title="Kassenverwaltung",
                icon=ft.Icons.RESTART_ALT,
                description=(
                    "Setzt Budgets, Ausgaben und Getränkezähler zurück. "
                    "Personen und Sorten bleiben erhalten."
                ),
                actions=[
                    self.action_button(
                        "Kasse & Zähler zurücksetzen",
                        ft.Icons.RESTART_ALT,
                        self.confirm_reset_all,
                        color=ft.Colors.ERROR,
                    )
                ],
                action_alignment=ft.MainAxisAlignment.END,
            ),
        ]

        self.settings_content = ft.Column(
            controls=[
                screen_heading(
                    "Einstellungen",
                    "Einzahlungen, Daten und App verwalten.",
                ),
                *settings_cards,
            ],
            expand=True,
            spacing=20,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        self.controls = [self.settings_content]


    # =========================================================
    # DATEN FÜR EXPORT ERSTELLEN
    # =========================================================

    def settings_card(
        self,
        title,
        description,
        actions,
        icon=None,
        details=None,
        action_alignment=ft.MainAxisAlignment.END,
    ):
        heading = ft.Text(title, size=18, weight=ft.FontWeight.W_600)
        if icon is not None:
            heading = ft.Row(
                [
                    ft.Icon(icon, color=ft.Colors.PRIMARY),
                    heading,
                ],
                spacing=10,
            )
        content = [heading]
        if details is not None:
            content.append(details)
        content.extend(
            [
                description
                if isinstance(description, ft.Control)
                else ft.Text(
                    description,
                    size=14,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.Row(
                    actions,
                    spacing=10,
                    wrap=True,
                    alignment=action_alignment,
                ),
            ]
        )
        return ft.Card(
            variant=ft.CardVariant.OUTLINED,
            elevation=0,
            content=ft.Container(
                padding=20,
                content=ft.Column(content, spacing=12),
            ),
        )

    @staticmethod
    def action_button(label, icon, on_click, primary=False, color=None):
        if primary:
            return ft.FilledButton(
                label,
                icon=icon,
                on_click=on_click,
            )
        if color:
            return ft.OutlinedButton(
                label,
                icon=icon,
                on_click=on_click,
                style=ft.ButtonStyle(
                    color=color,
                    side=ft.BorderSide(1, color),
                ),
            )
        return ft.OutlinedButton(
            label,
            icon=icon,
            on_click=on_click,
        )

    def create_export_data(self):
        return create_export_data(
            self.app.person_objects,
            self.app.expense_objects,
            self.app.beverage_objects,
        )

    @staticmethod
    def format_deposit_summary(amounts):
        values = " · ".join(f"{format_euro_amount(amount)} €" for amount in amounts)
        return f"Schnellbeträge für Einzahlungen · {values}"

    def open_deposit_amount_dialog(self, e=None):
        fields = [
            ft.TextField(
                label=f"Schnellbetrag {index + 1} (€)",
                value=format_euro_amount(amount),
                expand=True,
                keyboard_type=ft.KeyboardType.TEXT,
            )
            for index, amount in enumerate(self.app.deposit_amounts)
        ]
        error_text = ft.Text(
            color=ft.Colors.ERROR,
            size=13,
            visible=False,
        )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Schnellbeträge anpassen"),
            content=ft.Container(
                width=420,
                content=ft.Column(
                    [
                        ft.Text(
                            "Lege die drei Beträge für schnelle Einzahlungen fest. "
                            "Sie müssen positiv und unterschiedlich sein.",
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Column(fields, spacing=8),
                        error_text,
                    ],
                    tight=True,
                    spacing=14,
                ),
            ),
            actions=[
                ft.TextButton(
                    "Abbrechen",
                    on_click=lambda _: self.app.page.pop_dialog(),
                ),
                ft.FilledButton(
                    "Speichern",
                    icon=ft.Icons.SAVE_OUTLINED,
                    on_click=lambda _: self.save_deposit_amounts(fields, error_text),
                ),
            ],
        )
        self.app.page.show_dialog(dialog)

    def save_deposit_amounts(self, fields, error_text):
        try:
            amounts = validate_deposit_amounts([field.value for field in fields])
            self.app.deposit_amounts = persist_deposit_amounts(
                self.app.data_file_path,
                amounts,
            )
        except ValueError as ex:
            error_text.value = str(ex)
            error_text.visible = True
            self.app.page.update()
            return
        except OSError as ex:
            error_text.value = f"Speichern fehlgeschlagen: {ex}"
            error_text.visible = True
            self.app.page.update()
            return

        self.deposit_amount_summary.value = self.format_deposit_summary(
            self.app.deposit_amounts
        )
        self.app.page.pop_dialog()
        self.app.refresh_all_screens()
        self.show_dialog(
            "Einzahlungsbeträge gespeichert",
            "Die neuen Schnellbeträge werden ab sofort verwendet.",
        )

    async def export_settings(self, e=None):
        try:
            settings = {"deposit_amounts": self.app.deposit_amounts}
            file_bytes = json.dumps(
                settings,
                ensure_ascii=False,
                indent=4,
            ).encode("utf-8")
            result = await self.file_picker.save_file(
                dialog_title="Einstellungen sichern",
                file_name="beverageorganiser_einstellungen.json",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["json"],
                src_bytes=file_bytes,
            )
            if result:
                self.show_dialog(
                    "Einstellungen exportiert",
                    "Die Schnellbeträge wurden exportiert.",
                )
        except Exception as ex:
            self.show_dialog(
                "Export fehlgeschlagen",
                f"Einstellungen konnten nicht exportiert werden:\n{ex}",
            )

    async def import_settings(self, e=None):
        try:
            files = await self.file_picker.pick_files(
                dialog_title="Einstellungen importieren",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["json"],
                allow_multiple=False,
                with_data=True,
            )
            if not files:
                return
            if not files[0].bytes:
                raise ValueError("Die ausgewählte Datei konnte nicht gelesen werden.")

            data = json.loads(files[0].bytes.decode("utf-8"))
            if isinstance(data, dict) and isinstance(data.get("settings"), dict):
                data = data["settings"]
            if not isinstance(data, dict):
                raise ValueError("Die Datei enthält keine gültigen Einstellungen.")
            amounts = validate_deposit_amounts(data.get("deposit_amounts"))
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as ex:
            self.show_dialog("Import fehlgeschlagen", str(ex))
            return
        except Exception as ex:
            self.show_dialog(
                "Import fehlgeschlagen",
                f"Einstellungen konnten nicht importiert werden:\n{ex}",
            )
            return

        formatted = " · ".join(
            f"{format_euro_amount(amount)} €" for amount in amounts
        )

        def apply_settings(_):
            try:
                self.app.deposit_amounts = persist_deposit_amounts(
                    self.app.data_file_path,
                    amounts,
                )
            except (OSError, ValueError) as ex:
                self.app.page.pop_dialog()
                self.show_dialog(
                    "Import fehlgeschlagen",
                    f"Die Einstellungen konnten nicht gespeichert werden:\n{ex}",
                )
                return

            self.deposit_amount_summary.value = self.format_deposit_summary(
                self.app.deposit_amounts
            )
            self.app.page.pop_dialog()
            self.app.refresh_all_screens()
            self.show_dialog(
                "Einstellungen importiert",
                "Die Schnellbeträge wurden übernommen.",
            )

        show_confirmation_dialog(
            self.app.page,
            "Einstellungen importieren",
            f"Die aktuellen Schnellbeträge werden ersetzt durch:\n{formatted}",
            "Importieren",
            apply_settings,
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

        self.set_update_status("Suche nach Updates …")
        try:
            update = await check_for_update()

            if update is None:
                if sys.platform == "win32":
                    await self.simulate_update_process()
                else:
                    self.hide_update_status()
                    self.show_dialog(
                        "Keine Updates",
                        (
                            "Du verwendest bereits die "
                            f"aktuelle Version {APP_VERSION}."
                        )
                    )

                return

            self.hide_update_status()
            self.show_update_dialog(update)

        except Exception as ex:
            self.hide_update_status()
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
                f"Update verfügbar: {update['version']}"
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

    def set_update_status(self, message, icon=None):
        indicator = (
            ft.Icon(icon, color=ft.Colors.WHITE)
            if icon
            else ft.ProgressRing(
                width=20,
                height=20,
                stroke_width=2,
                color=ft.Colors.WHITE,
            )
        )
        self.update_status.content = ft.Row(
            [
                indicator,
                ft.Text(
                    message,
                    color=ft.Colors.WHITE,
                    weight=ft.FontWeight.BOLD,
                ),
            ],
            spacing=10,
        )
        self.update_status.visible = True
        self.update_status.update()

    def hide_update_status(self):
        self.update_status.visible = False
        self.update_status.update()

    async def simulate_update_process(self):
        steps = [
            ("Updatevorgang wird unter Windows simuliert …", None),
            ("Download wird simuliert …", None),
            ("Installationsdialog wird simuliert …", ft.Icons.SYSTEM_UPDATE),
        ]
        for message, icon in steps:
            self.set_update_status(message, icon)
            await asyncio.sleep(0.7)
        self.set_update_status(
            f"Simulation abgeschlossen · Version {APP_VERSION} bleibt installiert.",
            ft.Icons.CHECK_CIRCLE,
        )
        await asyncio.sleep(2)
        self.hide_update_status()

    def show_update_safety_dialog(self, download_url):
        async def open_settings(_):
            try:
                await asyncio.to_thread(open_android_security_settings)
            except Exception as error:
                self.show_dialog(
                    "Sicherheitseinstellungen konnten nicht geöffnet werden",
                    str(error),
                )

        async def continue_update(_):
            self.app.page.pop_dialog()
            await self.download_update(download_url, safety_confirmed=True)

        self.app.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Automatischen Schutz prüfen"),
                content=ft.Column(
                    [
                        ft.Text(
                            "Auf einigen neueren Android-Geräten, besonders "
                            "Samsung Galaxy, kann der Automatische Schutz "
                            "(Automatische Sperre) die Installation dieses "
                            "Updates blockieren. Falls nötig, öffne Sicherheit "
                            "und Datenschutz → Automatische Sperre und deaktiviere "
                            "den Schutz vorübergehend. Aktiviere ihn nach dem "
                            "Update wieder."
                        ),
                        ft.OutlinedButton(
                            "Sicherheitseinstellungen öffnen",
                            icon=ft.Icons.SECURITY,
                            on_click=open_settings,
                        ),
                    ],
                    tight=True,
                    spacing=14,
                ),
                actions=[
                    ft.TextButton(
                        "Abbrechen",
                        on_click=lambda _: self.app.page.pop_dialog(),
                    ),
                    ft.FilledButton(
                        "Weiter",
                        icon=ft.Icons.ARROW_FORWARD,
                        on_click=continue_update,
                    ),
                ],
            )
        )

    async def download_update(self, download_url, safety_confirmed=False):
        try:
            if sys.platform == "win32":
                self.app.page.pop_dialog()
                await self.simulate_update_process()
                return

            if not safety_confirmed:
                self.app.page.pop_dialog()
                self.show_update_safety_dialog(download_url)
                return

            self.set_update_status("Installationsberechtigung wird geprüft …")
            can_install = await asyncio.to_thread(request_install_permission)
            if not can_install:
                self.hide_update_status()
                self.show_dialog(
                    "Installation erlauben",
                    "Android hat die Einstellung für diese Quelle geöffnet. "
                    "Erlaube dort die Installation unbekannter Apps und "
                    "starte das Update anschließend erneut. Die APK wurde "
                    "noch nicht heruntergeladen.",
                )
                return

            self.set_update_status("Update wird heruntergeladen …")
            apk_path = await asyncio.to_thread(download_apk, download_url)
            self.set_update_status("Installationsdialog wird geöffnet …")
            await asyncio.to_thread(start_android_update, apk_path)
            self.set_update_status(
                "Bitte das Update im Android-Installationsdialog bestätigen.",
                ft.Icons.SYSTEM_UPDATE,
            )
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


