import asyncio
from datetime import timedelta
import logging
from logging import getLogger, StreamHandler
from pathlib import Path
import sys

import ipdb
from rich.console import Console
from rich.prompt import Confirm, Prompt
from tqdm import tqdm

from ripper.cli import *
from ripper.mmkv_abi.drive_info.drive_state import DriveState
from ripper.mmkv_abi.mmkv import MakeMKV
from ripper.mmkv_abi.app_string import AppString

from ripper.rippers import Movie, Music, Show

async def main():
    media = Path('/media')
    cli = get_cli_args()
    console = Console()
    # examples:
    #
    # with console.status(msg, spinner='moon'):
    #     do_stuff()
    #
    # console.rule("[bold red]Example title for horizontal rule")
    #
    # console.log("message with timestamp, optional debugging info")
    #
    # console.print(
    #   "Unike justify=None, justify='left' will ' '-pad right of message str until it's console width",
    #   style="bold white on blue",
    #   justify="left|center|right"
    # )

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
            ripper = Movie(
                title=cli.title or Prompt.ask("title of film?"),
                year=cli.year or Prompt.ask("year released?")
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

    makemkv = await init_makemkv()
    ripper.use(makemkv)

    await ripper.select_titles()

    # TODO decouple confirm and rip
    if not await ripper.confirm_and_rip():
        print('aight, nvm')
        # TODO any cleanup needed?
        return

    match cli.media_type:
        case 'movie':
            # TODO seed with title from dvd? autocomplete from movie db API?
            title = Prompt.ask("What's the movie's title?")
            # TODO look up year etc in some movie db API?
            year = Prompt.ask("What year was it released?")

            movie_basename = f'{title} ({year})'
            if Confirm.ask(f"You good moving ahead with the name `{filename}`?"):
                # get
                old_filename = Path(makemkv.current_info[4])
                if not old_filename.suffix('.mkv'):
                    candidate_files = [f for f in media.iterdir() if f.suffix == '.mkv']
                    if len(candidate_files) == 1:
                        old_filename = candidate_files[0]

                media.mkdir("movies/{movie_basename}", exist_ok=True)
                # TODO move this file somewhere in `/media/rips` after converting
                new_file = old_filename.rename('/media/movies/{movie_basename}/{movie_basename} - original.mkv')

                if new_file.is_file():
                    print(f'lo it is ript to {new_file}')
                    convert_it_pls = Confirm.ask("should I convert it to .mp4 too?")
                    if convert_it_pls:
                        # run shell command like:
                        # f"ffmpeg -i {new_file_dot_mkv} -c copy {new_file_dot_mp4}"
                        # (may need to use /tmp/ffmpeg/bin/ffmpeg)
                        print(f"pretend I'm converting '{new_file}' to '{new_file.with_suffix(".mp4")}' here:")
                        print(f"\t$ ffmpeg -i {new_file} -c copy {new_file.with_suffix(".mp4")}")
                else:
                    print(f"I thought I was saving the video as {new_file}, but that seems to not be a file??")
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

async def confirm_and_rip(preconfirm=False, debug=False):
    print('\n\nTitle Tree:')
    await makemkv.titles.print()

    we_good = Confirm.ask('we good?')
    if we_good:
        print('\n\nSaving selected titles...')
        if debug:
            ipdb.set_trace()
        await makemkv.save_all_selected_to_mkv()

        with tqdm(total=65536) as pbar:
            while makemkv.job_mode:
                if pbar.n > makemkv.total_bar:
                    pbar.reset()
                    pbar.update(makemkv.total_bar)
                else:
                    pbar.update(makemkv.total_bar - pbar.n)

                pbar.set_description(makemkv.current_info[4])
                pbar.set_postfix_str(makemkv.current_info[3])

                await makemkv.idle()
                await asyncio.sleep(0.25)
            # TODO can I detect failure (e.g. due to insufficient disk space) post-`makemkv.job_mode`?
            # if so, should return `False`
        return True

async def init_makemkv():
    makemkv = MakeMKV(setup_logger(logging.INFO))
    cli = get_cli_args()
    await makemkv.init()

    if cli.debug:
        print(f'MakeMKV version: {await makemkv.get_app_string(AppString.Version)}')
        print(f'MakeMKV platform: {await makemkv.get_app_string(AppString.Platform)}')
        print(f'MakeMKV build: {await makemkv.get_app_string(AppString.Build)}')
        print(f'Interface language: {await makemkv.get_app_string(AppString.InterfaceLanguage)}')

    await makemkv.set_output_folder('/media/inbox')
    await makemkv.update_avalible_drives()

    print('Waiting for disc...')
    await wait_for_disc_inserted(makemkv)

    print('Waiting for titles...')
    await wait_for_titles_populated(makemkv)

    return makemkv

def setup_logger(log_level):
    logger = getLogger(__name__)
    logger.setLevel(log_level)

    handler = StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    logger.addHandler(handler)
    return logger

async def wait_for_disc_inserted(makemkv):
    while True:
        drives = [v for v in makemkv.drives.values() if v.drive_state is DriveState.Inserted]
        if len(drives) > 0:
            drive = drives[0]
            await makemkv.open_cd_disk(drive.drive_id)
            break

        await makemkv.idle()
        await asyncio.sleep(0.25)

async def wait_for_titles_populated(makemkv):
    while makemkv.titles is None:
        await makemkv.idle()
        await asyncio.sleep(0.25)

def cli():
    asyncio.run(main())

if __name__ == '__main__':
    cli()
