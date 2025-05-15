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
        case 'movie':
            await ripper.rename_ripped_files()
        case 'show':
            # TODO ask if the series/season already exists in media library
            # else: seed with title from dvd? autocomplete from some API?
            if Confirm.ask("Are there already episodes of this show in the media library?"):
                title = Prompt.ask("What's the show's title?")
                year = Prompt.ask('What year was it released?')
                season = Prompt.ask('What season? e.g. 01, 02, or 00 for special eps')
                first_episode = Prompt.ask('What is the episode number of the first track on this disk?', default=1)

                show_basename = f'{title} ({year})'
                season_dir = f'Season {season}'
            else:
                title = Prompt.ask("What's the show's title?")
                # TODO look up year etc in some movie db API?
                year = Prompt.ask('What year was it released?')
                season = Prompt.ask('What season? e.g. 01, 02, or 00 for special eps')
                first_episode = Prompt.ask('What is the episode number of the first track on this disk?', default=1)

                show_basename = f'{title} ({year})'
                season_dir = f'Season {season}'
            if Confirm.ask(f'You good moving ahead and importing ep(s) to `{show_basename}/{season_dir}`?'):
                # get
                old_filename = Path(makemkv.current_info[4])
                if not old_filename.suffix('.mkv'):
                    candidate_files = [f for f in media.iterdir() if f.suffix == '.mkv']
                    if len(candidate_files) == 1:
                        old_filename = candidate_files[0]
                    else:
                        # TODO ls /media/inbox, ask user to pick file themselves
                        ...

                media.mkdir(f"shows/{show_basename}/{season_dir}", parents=True, exist_ok=True)
                if cli.debug:
                    ipdb.set_trace()
                # TODO sanity check! count # of tracks selected? before/after dir listings of /media/inbox? idk.
                # for i, file in enumerate(/media/inbox/*.mkv):
                #     mv $file /media/shows/{show_basename}/{season_dir}/
                # new_file = old_filename.rename('/media/shows/{show_basename}/{season_dir}/{show_basename} S{season}E{first_episode + i}')

                # if new_file.is_file():
                #     print(f'lo it is ript to {new_file}')
                #     convert_it_pls = Confirm.ask("should I convert it to .mp4 too?")
                #     if convert_it_pls:
                #         # run shell command like:
                #         # f"ffmpeg -i {new_file_dot_mkv} -c copy {new_file_dot_mp4}"
                #         # (may need to use /tmp/ffmpeg/bin/ffmpeg)
                #         print(f"pretend I'm converting '{new_file}' to '{new_file.with_suffix(".mp4")}' here:")
                #         print(f"\t$ ffmpeg -i {new_file} -c copy {new_file.with_suffix(".mp4")}")
                # else:
                #     print(f"I thought I was saving the video as {new_file}, but that seems to not be a file??")

        case 'music':
            pass


def cli():
    evloop = asyncio.get_event_loop()
    nest_asyncio.apply(evloop)
    evloop.run_until_complete(main())


if __name__ == '__main__':
    cli()
