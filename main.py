import flet as ft

from Screens.beverage_screen import BeverageScreen
from Screens.overview_screen import OverviewScreen
from Screens.person_screen import PersonScreen
from Screens.settings_screen import SettingsScreen
from Utils.data_store import (
    get_data_file_path,
    has_saved_data_file,
    load_deposit_amounts,
    load_data,
    save_data,
)

class DrinkCashApp:
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
        self.data_file_path = get_data_file_path(__file__)
        self.deposit_amounts = load_deposit_amounts(self.data_file_path)

        self.load_data()
        self.setup_page()
        self.create_screens()
        self.create_navigation_drawer()

    # ---------------------------------------------------------
    # FLET GRUNDEINSTELLUNGEN
    # ---------------------------------------------------------

    def setup_page(self):
        self.page.title = "BeverageOrganiser"
        self.page.theme_mode = ft.ThemeMode.DARK
        theme = ft.Theme(
            color_scheme_seed=ft.Colors.AMBER,
            dialog_theme=ft.DialogTheme(
                shape=ft.RoundedRectangleBorder(radius=20),
            ),
        )
        self.page.theme = theme
        self.page.dark_theme = theme
        self.page.padding = 0
        self.wide_layout = (self.page.width or 0) >= 720

        self.page.appbar = ft.AppBar(
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.LOCAL_BAR, color=ft.Colors.PRIMARY),
                    ft.Text("BeverageOrganiser", weight=ft.FontWeight.BOLD),
                ],
                spacing=10,
            ),
            leading=ft.IconButton(
                icon=ft.Icons.MENU,
                tooltip="Navigation",
                on_click=self.open_drawer,
            ),
            bgcolor=ft.Colors.SURFACE,
            elevation=0,
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
                    padding=20,
                    content=ft.Text(
                        "BeverageOrganiser",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                    ),
                ),
                ft.Divider(),
                ft.NavigationDrawerDestination(
                    icon=ft.Icons.PEOPLE_OUTLINE,
                    selected_icon=ft.Icons.PEOPLE,
                    label="Personen & Budget",
                ),
                ft.NavigationDrawerDestination(
                    icon=ft.Icons.POINT_OF_SALE_OUTLINED,
                    selected_icon=ft.Icons.POINT_OF_SALE,
                    label="Kassenübersicht",
                ),
                ft.NavigationDrawerDestination(
                    icon=ft.Icons.LOCAL_BAR_OUTLINED,
                    selected_icon=ft.Icons.LOCAL_BAR,
                    label="Getränke",
                ),
                ft.NavigationDrawerDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="Einstellungen",
                ),
            ],
        )

        self.page.drawer = self.navigation_drawer
        self.content_panel = ft.Container(
            expand=True,
            padding=28,
            bgcolor=ft.Colors.SURFACE,
        )
        self.navigation = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.SELECTED,
            min_width=84,
            bgcolor=ft.Colors.SURFACE,
            on_change=self.navigation_change,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.PEOPLE_OUTLINE,
                    selected_icon=ft.Icons.PEOPLE,
                    label="Personen",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.POINT_OF_SALE_OUTLINED,
                    selected_icon=ft.Icons.POINT_OF_SALE,
                    label="Kasse",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.LOCAL_BAR_OUTLINED,
                    selected_icon=ft.Icons.LOCAL_BAR,
                    label="Getränke",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="Einstellungen",
                ),
            ],
        )
        self.body = ft.Container(expand=True)
        self.page.add(self.body)
        self.page.on_resize = self.on_page_resize
        self.render()

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

    def navigation_change(self, e):
        destinations = [
            "person_main",
            "overview_main",
            "beverage_main",
            "settings_main",
        ]
        index = e.control.selected_index
        if index is not None and 0 <= index < len(destinations):
            self.change_screen(destinations[index])

    def on_page_resize(self, e):
        wide_layout = (self.page.width or 0) >= 720
        if wide_layout != self.wide_layout:
            self.wide_layout = wide_layout
            self.render()

    def render(self):
        destinations = [
            "person_main",
            "overview_main",
            "beverage_main",
            "settings_main",
        ]
        index = destinations.index(self.current_screen)
        self.navigation.selected_index = index
        self.navigation_drawer.selected_index = index
        self.content_panel.content = self.screens[self.current_screen]
        self.content_panel.padding = 28 if self.wide_layout else 16
        self.body.content = (
            ft.Row(
                [
                    self.navigation,
                    ft.VerticalDivider(width=1, thickness=1),
                    self.content_panel,
                ],
                expand=True,
                spacing=0,
            )
            if self.wide_layout
            else self.content_panel
        )
        self.page.update()

    def change_screen(self, screen_name):
        if screen_name not in self.screens:
            return

        self.current_screen = screen_name

        self.render()

    # ---------------------------------------------------------
    # DATEN LADEN
    # ---------------------------------------------------------

    def load_data(self):
        if not has_saved_data_file(self.data_file_path):
            return

        try:
            print(self.data_file_path)
            (
                self.person_objects,
                self.expense_objects,
                self.beverage_objects,
            ) = load_data(self.data_file_path)

        except Exception as e:
            print(f"Fehler beim Laden: {e}")

    # ---------------------------------------------------------
    # DATEN SPEICHERN
    # ---------------------------------------------------------

    def save_data(self):
        try:
            print(self.data_file_path)
            save_data(
                self.data_file_path,
                self.person_objects,
                self.expense_objects,
                self.beverage_objects,
            )
            return True

        except Exception as e:
            print(f"Fehler beim Speichern: {e}")
            return False

    # ---------------------------------------------------------
    # HILFSFUNKTION
    # ---------------------------------------------------------

    def refresh_all_screens(self):
        for screen in self.screens.values():
            screen.refresh()

        self.page.update()

def main(page: ft.Page):
    DrinkCashApp(page)

if __name__ == "__main__":
    ft.run(main)
