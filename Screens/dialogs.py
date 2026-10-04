"""Reusable message and simple confirmation dialogs for app screens."""

import flet as ft


def show_message_dialog(page, title, message, *, filled_button=True):
    button = ft.FilledButton if filled_button else ft.TextButton
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.Text(message),
        actions=[
            button("OK", on_click=lambda _: page.pop_dialog())
        ],
    )
    page.show_dialog(dialog)


def show_confirmation_dialog(page, title, message, confirm_label, on_confirm):
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.Text(message),
        actions=[
            ft.TextButton(
                "Abbrechen",
                on_click=lambda _: page.pop_dialog(),
            ),
            ft.FilledButton(confirm_label, on_click=on_confirm),
        ],
    )
    page.show_dialog(dialog)
