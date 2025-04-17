import asyncio
from datetime import timedelta
from pathlib import Path
import re

from rich.prompt import Confirm
from tqdm import tqdm

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
        print(f"\n\n{f'Track {number}' if number else 'Next track'}}")
        print(f'\t{titlename}')
        print(f'\t{disk_usage}: {chaptercount} chapter(s), {duration}')

    async def display_titles(self):
        return await self.makemkv.titles.print()

    # TODO make this a proper abstract method
    def expect_rip(self, duration):
        ...

    # TODO make this a proper abstract method
    def multiselect_choice_from_track(self, track):
        ...

    async def select_titles(self):
        # TODO build a set of choices for a multiselect TUI
        for title in self.makemkv.titles:
            duration = await title.get_duration()
            await self.display_title(title, duration=duration)
            await title.set_enabled(Confirm.ask('should I rip this motherfucker?', default=self.expect_rip(duration)))

    async def confirm_and_rip(self, preconfirm=False, debug=False):
        print('\n\nTitle Tree:')
        await self.makemkv.titles.print()

        we_good = Confirm.ask('we good?')
        if we_good:
            print('\n\nSaving selected titles...')
            if debug:
                ipdb.set_trace()
            await self.makemkv.save_all_selected_to_mkv()

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
