import asyncio
from datetime import timedelta
import logging
from logging import getLogger, StreamHandler
from pathlib import Path
import re
import sys

from tqdm import tqdm

from ripper.cli import choice, confirm, multiselect, get_cli_args
from ripper.mmkv_abi.drive_info.drive_state import DriveState
from ripper.mmkv_abi.mmkv import MakeMKV
from ripper.mmkv_abi.app_string import AppString

class Ripper:
    # verbose = False
    verbose = True
    episode_lower_bound = timedelta(minutes=20)
    episode_upper_bound = timedelta(minutes=50)
    # subclasses must define their own media_subdir property
    media_subdir: str

    def use(self, makemkv):
        self.makemkv = makemkv

    def verbose(self, turnt_up=True):
        self.verbose = turnt_up

    @property
    def media_dir(self):
        return Path("/media") / self._media_subdir

    # override me, pls
    # TODO define as proper abstract method
    def format_track_name(self, name):
        return name

    @staticmethod
    def parse_title_and_year(subdir: str) -> tuple[str, str | None]:
        """Given a known media subdir in the expected "$TITLE ($YEAR)" format, extract its
        title and year and return `(title, year)`. Returns `(subdir, None)` if parsing is unsuccessful."""
        match = re.match(r"^(.*?)(?: \((\d{4})\))?$", subdir)
        if match:
            title, year = match.groups()
            return title.strip(), year
        return subdir, None

    async def display_title(self, title, duration=None, number=None):
        duration = duration or await title.get_duration()
        titlename = await title.get_name()
        chaptercount = await title.get_chapter_count()
        disk_usage = await title.get_disc_size()
        print(f"\n\n{f'Track {number}' if number else 'Next track'}")
        print(f'\t{titlename}')
        print(f'\t{disk_usage}: {chaptercount} chapter(s), {duration}')

    async def display_titles(self):
        return await self.makemkv.titles.print()

    # TODO make this a proper abstract method
    def expect_rip(self, duration):
        ...

    async def init_makemkv(self):
        makemkv = MakeMKV(self.setup_logger(logging.INFO))
        cli = get_cli_args()
        await makemkv.init()

        if cli.debug:
            print(f'MakeMKV version: {await makemkv.get_app_string(AppString.Version)}')
            print(f'MakeMKV platform: {await makemkv.get_app_string(AppString.Platform)}')
            print(f'MakeMKV build: {await makemkv.get_app_string(AppString.Build)}')
            print(f'Interface language: {await makemkv.get_app_string(AppString.InterfaceLanguage)}')

        await makemkv.set_output_folder('/media/inbox')
        await makemkv.update_avalible_drives()

        self.makemkv = makemkv
        self.selected_tracks = []

        if cli.debug:
            print('Waiting for disc...')
        await self._wait_for_disc_inserted()

        if cli.debug:
            print('Waiting for titles...')
        await self._wait_for_titles_populated()


    async def _select_track(self, track):
        self.selected_tracks.append(track)
        await track.set_enabled(True)

    # TODO encapsulate mmkv setup shenanigans
    def setup_logger(self, log_level):
        logger = getLogger(__name__)
        logger.setLevel(log_level)

        handler = StreamHandler(sys.stdout)
        handler.setLevel(log_level)

        logger.addHandler(handler)
        return logger

    async def _wait_for_disc_inserted(self):
        # TODO print a "plx insert disc and close drive" msg after appropriate timeout
        while True:
            drives = [v for v in self.makemkv.drives.values() if v.drive_state is DriveState.Inserted]
            if len(drives) > 0:
                drive = drives[0]
                await self.makemkv.open_cd_disk(drive.drive_id)
                break

            await self.makemkv.idle()
            await asyncio.sleep(0.25)

    # TODO encapsulate mmkv setup shenanigans
    async def _wait_for_titles_populated(self):
        while self.makemkv.titles is None:
            await self.makemkv.idle()
            await asyncio.sleep(0.25)

    async def _multiselect_choice_from_title(self, title, value):
        duration = await title.get_duration()
        titlename = await title.get_name()
        chaptercount = await title.get_chapter_count()
        disk_usage = await title.get_disc_size()
        return choice(
            f'{titlename}: {disk_usage}, {chaptercount} chapter(s), {duration}',
            checked=self.expect_rip(duration),
            value=value
        )

    async def multiselect_titles(self):
        titles = list(self.makemkv.titles)
        choices = []
        for i, title in enumerate(titles):
            await title.set_enabled(False)
            choices.append(
                await self._multiselect_choice_from_title(title, i)
            )
        selected_title_idxs = await multiselect(
            "Please select all tracks you'd like to rip",
            choices
        )

        for idx in selected_title_idxs:
             await self._select_track(titles[idx])


    async def confirm_and_rip(self, preconfirm=False, debug=False):
        print('\n\nTitle Tree:')
        await self.makemkv.titles.print()

        we_good = await confirm('we good?')
        if we_good:
            print('\n\nSaving selected titles...')
            if debug:
                ipdb.set_trace()
            await self.makemkv.save_all_selected_to_mkv()

            # TODO use cool emoji moon spinner for progress here, too
            with tqdm(total=65536) as pbar:
                while self.makemkv.job_mode:
                    if pbar.n > self.makemkv.total_bar:
                        pbar.reset()
                        pbar.update(self.makemkv.total_bar)
                    else:
                        pbar.update(self.makemkv.total_bar - pbar.n)

                    pbar.set_description(self.makemkv.current_info[4])
                    pbar.set_postfix_str(self.makemkv.current_info[3])

                    await self.makemkv.idle()
                    await asyncio.sleep(0.25)
                # TODO can I detect failure (e.g. due to insufficient disk space) post-`makemkv.job_mode`?
                # if so, should return `False`
            return True
