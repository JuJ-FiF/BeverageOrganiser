"""Gemeinsame UI-Bausteine und Farben der dunklen Oberfläche."""

import flet as ft

ACCENT_COLOR = ft.Colors.PRIMARY
ACCENT_TEXT_COLOR = ft.Colors.ON_PRIMARY


def screen_heading(title, subtitle, action=None):
    heading = ft.Column(
        [
            ft.Text(title, size=28, weight=ft.FontWeight.BOLD),
            ft.Text(subtitle, size=14, color=ft.Colors.ON_SURFACE_VARIANT),
        ],
        spacing=4,
        tight=True,
    )
    controls = [heading, action] if action else [heading]
    return ft.Row(
        controls,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        wrap=True,
        spacing=16,
    )


def surface_card(content, *, padding=14):
    return ft.Card(
        variant=ft.CardVariant.FILLED,
        elevation=0,
        content=ft.Container(
            content=content,
            padding=padding,
        ),
    )


def primary_button(label, icon, on_click):
    return ft.FilledButton(
        label,
        icon=icon,
        on_click=on_click,
    )
