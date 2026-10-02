import json
import os
from pathlib import Path

import flet as ft

from Utils.classes import Person, Expense, Beverage
from Screens.person_screen import PersonScreen
from Screens.overview_screen import OverviewScreen
from Screens.beverage_screen import BeverageScreen
from Screens.settings_screen import SettingsScreen


class DrinkCashApp:
    DATA_FILE_NAME = "data.json"

    def __init__(self, page: ft.Page):
        self.page = page

        # Daten
        self.person_objects = []
        self.expense_objects = []
        self.beverage_objects = []

        # Aktueller Screen
        self.current_screen = "person_main"

        # Flet-Screens
        self.screens = {}

        # Speicherpfad
        if os.getenv("FLET_APP_STORAGE_DATA"):
            DATA_FILE = Path(os.getenv("FLET_APP_STORAGE_DATA")) / "data.json"
        else:
            DATA_FILE = Path(__file__).resolve().parent / "data.json"

        self.data_file_path = DATA_FILE

        self.load_data()
        self.setup_page()
        self.create_screens()
        self.create_navigation_drawer()

        # Hauptbereich der App
        self.content_area = ft.Container(expand=True)

        self.page.add(self.content_area)

    # ---------------------------------------------------------
    # FLET GRUNDEINSTELLUNGEN
    # ---------------------------------------------------------

    def setup_page(self):
        self.page.title = "Getränkekasse"
        self.page.theme_mode = ft.ThemeMode.DARK

        self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.AMBER)
        self.page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.AMBER)

        self.page.padding = 0

        self.page.appbar = ft.AppBar(
            title=ft.Text("Getränkekasse"),
            leading=ft.IconButton(
                icon=ft.Icons.MENU,
                on_click=self.open_drawer
            ),
        )

    # ---------------------------------------------------------
    # SCREENS
    # ---------------------------------------------------------

    def create_screens(self):
        self.screens["person_main"] = PersonScreen(self)
        self.screens["overview_main"] = OverviewScreen(self)
        self.screens["beverage_main"] = BeverageScreen(self)
        self.screens["settings_main"] = SettingsScreen(self)

    # ---------------------------------------------------------
    # NAVIGATION
    # ---------------------------------------------------------

    def create_navigation_drawer(self):
        self.navigation_drawer = ft.NavigationDrawer(
            width=280,
            on_change=self.on_drawer_change,
            controls=[
                ft.Container(
                    padding=ft.Padding.only(
                        left=20,
                        top=20,
                        bottom=10
                    ),
                    content=ft.Text(
                        "Getränkekasse",
                        size=20,
                        weight=ft.FontWeight.BOLD
                    )
                ),

                ft.Divider(),

                ft.NavigationDrawerDestination(
                    icon=ft.Icons.PEOPLE_OUTLINE,
                    selected_icon=ft.Icons.PEOPLE,
                    label="Personen & Budget"
                ),

                ft.NavigationDrawerDestination(
                    icon=ft.Icons.POINT_OF_SALE_OUTLINED,
                    selected_icon=ft.Icons.POINT_OF_SALE,
                    label="Kassenübersicht"
                ),

                ft.NavigationDrawerDestination(
                    icon=ft.Icons.LOCAL_BAR_OUTLINED,
                    selected_icon=ft.Icons.LOCAL_BAR,
                    label="Sorten"
                ),

                ft.NavigationDrawerDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="Einstellungen"
                ),
            ]
        )

        self.page.drawer = self.navigation_drawer

    async def open_drawer(self, e):
        await self.page.show_drawer()

    async def on_drawer_change(self, e):
        destinations = [
            "person_main",
            "overview_main",
            "beverage_main",
            "settings_main"
        ]

        index = e.control.selected_index

        if index is not None and 0 <= index < len(destinations):
            self.change_screen(destinations[index])

        await self.page.close_drawer()

    def change_screen(self, screen_name):
        if screen_name not in self.screens:
            return

        self.current_screen = screen_name

        screen = self.screens[screen_name]

        # Screen zuerst in den festen Hauptbereich setzen
        self.content_area.content = screen

        # Drawer-Auswahl setzen
        drawer_indices = {
            "person_main": 0,
            "overview_main": 1,
            "beverage_main": 2,
            "settings_main": 3
        }

        self.navigation_drawer.selected_index = drawer_indices.get(screen_name,0)

        self.page.update()

    # ---------------------------------------------------------
    # DATEN LADEN
    # ---------------------------------------------------------

    def load_data(self):
        if not os.path.exists(self.data_file_path):
            return

        try:
            print(self.data_file_path)
            with open(self.data_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.person_objects = [
                Person.from_dict(data=person) for person in data.get("persons", [])
            ]

            # 1. ZUERST die Getränke laden
            self.beverage_objects = [
                Beverage.from_dict(data=beverage) for beverage in data.get("beverages", [])
            ]

            # 2. DANACH die Ausgaben laden und beverage_objects übergeben
            self.expense_objects = [
                Expense.from_dict(data=expense, beverage_objects=self.beverage_objects) for expense in data.get("expenses", [])
            ]

        except Exception as e:
            print(f"Fehler beim Laden: {e}")

    # ---------------------------------------------------------
    # DATEN SPEICHERN
    # ---------------------------------------------------------

    def save_data(self):
        try:
            data = {"persons": [person.to_dict() for person in self.person_objects],
                    "expenses": [expense.to_dict() for expense in self.expense_objects],
                    "beverages": [beverage.to_dict() for beverage in self.beverage_objects]
            }

            os.makedirs(os.path.dirname(self.data_file_path), exist_ok=True)

            print(self.data_file_path)
            with open(self.data_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

        except Exception as e:
            print(f"Fehler beim Speichern: {e}")

    # ---------------------------------------------------------
    # HILFSFUNKTION
    # ---------------------------------------------------------

    def refresh_all_screens(self):
        for screen in self.screens.values():
            screen.refresh()

        self.page.update()


def main(page: ft.Page):
    app = DrinkCashApp(page)
    app.content_area.content = app.screens["person_main"]
    page.update()


if __name__ == "__main__":
    ft.run(main)