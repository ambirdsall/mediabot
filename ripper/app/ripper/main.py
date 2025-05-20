import asyncio
from datetime import timedelta
import logging
from logging import getLogger, StreamHandler
from pathlib import Path
import sys

import ipdb
import nest_asyncio
from rich.console import Console
from rich.prompt import Confirm, Prompt
from tqdm import tqdm
from dotenv import load_dotenv


from ripper.cli import *
from ripper.mmkv_abi.drive_info.drive_state import DriveState
from ripper.mmkv_abi.mmkv import MakeMKV
from ripper.mmkv_abi.app_string import AppString

from ripper.rippers import Movie, Music, Show

load_dotenv()

async def main():
    media = Path('/media')
    cli = get_cli_args()
    console = Console()
    if not cli.media_type:
        cli.media_type = await select(
            "What type of media is on this disk?",
            choices=[
                choice("Film", "f", value="movie"),
                choice("TV Show", "s", value="show"),
                choice("Music", "m", value="music")
            ],
        )

    match cli.media_type:
        case 'movie':
            ripper = await Movie.new(
                console=console,
                title=cli.title,
                year=cli.year,
            )
        case 'show':
            ripper = await Show.new(
                console=console,
                title=cli.title,
                year=cli.year,
            )
        case 'music':
            ripper = Music(
                title=cli.title or Prompt.ask("title of music album:"),
                year=cli.year or Prompt.ask("year released:")
            )
        case _:
            raise Error(f'what the hell kind of media type is {cli.media_type}')

    with console.status("Reading disc...", spinner="moon"):
        await ripper.init_makemkv()

    await ripper.multiselect_titles()

    # TODO decouple confirm and rip
    if not await ripper.confirm_and_rip():
        print('aight, nvm')
        # TODO any cleanup needed?
        return

    match cli.media_type:
        case 'movie' | 'show':
            try:
                await ripper.rename_ripped_files()
            except Exception as err:
                def reraise(err):
                    raise err

                if cli.debug:
                    import ipdb; ipdb.set_trace()
                else:
                    raise err
        case 'music':
            pass
        case _:
            print('the fuck')
            import ipdb; ipdb.set_trace()


def cli():
    evloop = asyncio.get_event_loop()
    nest_asyncio.apply(evloop)
    evloop.run_until_complete(main())


if __name__ == '__main__':
    cli()
