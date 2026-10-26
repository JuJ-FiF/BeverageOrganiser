"""Reusable message and simple confirmation dialogs for app screens."""

import flet as ft

from Screens.ui_components import ACCENT_COLOR, ACCENT_TEXT_COLOR

_BUTTON_SHAPE = ft.RoundedRectangleBorder(radius=24)


def show_message_dialog(page, title, message, *, filled_button=True):
    button = ft.FilledButton if filled_button else ft.TextButton
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.Text(message),
        actions=[
            button(
                "OK",
                on_click=lambda _: page.pop_dialog(),
                style=ft.ButtonStyle(shape=_BUTTON_SHAPE),
            )
        ],
    )
    page.show_dialog(dialog)


def show_confirmation_dialog(page, title, message, confirm_label, on_confirm):
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.Text(message),
        actions=[
            ft.OutlinedButton(
                "Abbrechen",
                on_click=lambda _: page.pop_dialog(),
                style=ft.ButtonStyle(
                    color=ACCENT_COLOR,
                    side=ft.BorderSide(1, ACCENT_COLOR),
                    shape=_BUTTON_SHAPE,
                ),
            ),
            ft.FilledButton(
                confirm_label,
                on_click=on_confirm,
                style=ft.ButtonStyle(
                    bgcolor=ACCENT_COLOR,
                    color=ACCENT_TEXT_COLOR,
                    shape=_BUTTON_SHAPE,
                ),
            ),
        ],
    )
    page.show_dialog(dialog)
