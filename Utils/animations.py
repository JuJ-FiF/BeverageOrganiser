import asyncio
from pathlib import Path

import flet as ft
import flet_lottie as ftl


BUTTON_EXPAND_ON_SELECT = ft.Animation(
                duration=500,
                curve=ft.AnimationCurve.EASE_OUT
            )


SUCCESS_ANIMATION = "animations/success.json"
DELETE_ANIMATION = "animations/delete.json"


async def booking_animation(page, animation:str=""):
    """
    Spielt die Buchungsanimation einmalig
    unten mittig auf dem Bildschirm ab.

    animation : str = success | delete
    """

    animation = ftl.Lottie(
        src=SUCCESS_ANIMATION if animation == "success" else DELETE_ANIMATION,
        width=200 if animation == "success" else 110,
        height=200 if animation == "success" else 110,

        # Animation automatisch starten
        animate=True,

        # NICHT wiederholen
        repeat=False,
        reverse=False,

        # Position im Overlay
        bottom=0 if animation == "success" else 45,
        left=0,
        right=0,
    )

    page.overlay.append(animation)
    page.update()

    # Die Lottie-Datei läuft selbstständig einmal durch.
    # Danach entfernen wir sie wieder.
    await asyncio.sleep(2.5 if animation == "success" else 3.5)

    if animation in page.overlay:
        page.overlay.remove(animation)
        page.update()