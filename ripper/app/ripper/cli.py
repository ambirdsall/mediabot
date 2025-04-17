import asyncio
from pathlib import Path
from pprint import pprint

import questionary
from rich.console import Console
from rich.table import Table

HOUSE_STYLE = questionary.Style([
    ("question", "bold fg:#bfa76f"),     # warm tan
    ("answer", "bold fg:#6d9773"),       # muted sage green
    ("pointer", "fg:#bfa76f bold"),      # same warm tan as question
    ("highlighted", "fg:#bfa76f bold"),  # highlight match
    ("selected", "fg:#6d9773"),          # selected item color
    ("separator", "fg:#867666"),         # cool taupe
])

def choice(title, shortcut_key=None, **kwargs) -> questionary.Choice:
    return questionary.Choice(title, shortcut_key=shortcut_key, **kwargs)

async def select(prompt: str, choices: list[str | questionary.Choice], **kwargs) -> str:
    return await questionary.select(
        prompt,
        choices=choices,
        use_shortcuts=True,
        style=HOUSE_STYLE,
        **kwargs,
    ).ask_async()

async def multiselect(prompt: str, choices: list[str | questionary.Choice], **kwargs) -> str:
    return await questionary.checkbox(
        prompt,
        choices=choices,
        style=HOUSE_STYLE,
        **kwargs,
    ).ask_async()

async def text(prompt: str, **kwargs) -> str:
    return await questionary.text(prompt, style=HOUSE_STYLE, **kwargs).ask_async()

async def confirm(prompt: str, default=True, **kwargs) -> bool:
    return await questionary.confirm(
        prompt,
        default=default,
        style=HOUSE_STYLE,
        **kwargs,
    ).ask_async()

async def select_subdir(parent_dir: Path, console: Console) -> str:
    table = Table()
    table.add_column("Show", style="cyan", no_wrap=True)

    subdirs = sorted([p.name for p in parent_dir.iterdir() if p.is_dir()])
    for name in subdirs:
        table.add_row(name)

    console.print(table)

    return await questionary.autocomplete(
        "Which one?",
        choices=subdirs,
        validate=lambda show: show in subdirs,
        ignore_case=True,
        style=HOUSE_STYLE,
    ).ask_async()


if __name__ == '__main__':
    # let's go hog fucking wild testing this shit
    MUSIC_DIR = Path("/media/music")
    SHOWS_DIR = Path("/media/shows")

    async def test():
        if await confirm("Are there already episodes of this show in the media library?"):
            console = Console()
            fake_eps = [
                choice()
            ]
            # showdir = await select_subdir(SHOWS_DIR, console=console)

            # if await confirm("Are there already episodes from this season in [ibid]?"):
            #     pprint(f'{showdir}/' + await select_subdir(SHOWS_DIR / showdir, console=console))

    asyncio.run(test())
