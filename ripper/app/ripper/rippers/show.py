from datetime import timedelta

from rich.console import Console
from rich.prompt import Prompt

from ripper.cli import *

from .ripper import Ripper

class Show(Ripper):
    @classmethod
    async def new(cls, console=Console(), title=None, year=None, season=None, starts_at_episode=None):
        if all(arg is None for arg in [title, year, season]):
            if await confirm("Are there already episodes of this show in the media library?"):
                media_dir = Path("/media/shows")
                showdir = await select_subdir(media_dir, console=console)
                title, year = Ripper.parse_title_and_year(showdir)
                if await confirm("Are there already episodes of this season in the media library?"):
                    seasondir = await select_subdir(media_dir / showdir, console=console)
                    season = seasondir.split().pop()
                else:
                    season = await text("season, as a two-digit number (enter '00' for unseasoned eps and specials)")

        title = title or await text("What's the show's title?")
        year = year or await text('What year was it released?')
        season = season or await text('What season? e.g. 01, 02, or 00 for special eps')
        starts_at_episode = starts_at_episode or await text("episode number of this disc's first track", default="1")

        return cls(
            console=console,
            title=title,
            year=year,
            season=season,
            starts_at_episode=int(starts_at_episode),
        )

    def __init__(self, console=Console(), title=str, year=str, season=str, starts_at_episode=1):
        self._media_subdir = "shows"
        self._console = console

        self.title = title
        self.season = season
        self.year = year
        self.starts_at_episode = starts_at_episode

    def expect_rip(self, duration) -> bool:
        return duration > self.episode_lower_bound and duration < self.episode_upper_bound

    def multiselect_choice_from_track(self, track):
        # TODO do? use self.expect_rip to set preselect state, return some kinda id
        ...

    async def display_title(self, title, duration=None, number=1):
        return await super().display_title(title, duration=duration, number=number)

    async def rename_ripped_files(self):
        title = Prompt.ask("What's the show's title?")
        # TODO look up year etc in some movie db API?
        year = Prompt.ask('What year was it released?')
        season = Prompt.ask('What season? e.g. 01, 02, or 00 for special eps')
        first_episode = Prompt.ask('What is the episode number of the first track on this disk?', default=1)

        show_dir = f'{title} ({year})'
        season_dir = f'Season {season}'
        if Confirm.ask(f'You good moving ahead and importing ep(s) to `{show_dir}/{season_dir}`?'):
            # get
            old_filename = Path(makemkv.current_info[4])
            if not old_filename.suffix('.mkv'):
                candidate_files = [f for f in media.iterdir() if f.suffix == '.mkv']
                if len(candidate_files) == 1:
                    old_filename = candidate_files[0]
                else:
                    # TODO ls /media/inbox, ask user to pick file themselves
                    ...

            media.mkdir(f"shows/{show_dir}/{season_dir}", parents=True, exist_ok=True)
            if cli.debug:
                ipdb.set_trace()
            # TODO sanity check! count # of tracks selected? before/after dir listings of /media/inbox? idk.
            # for i, file in enumerate(/media/inbox/*.mkv):
            #     mv $file /media/shows/{show_dir}/{season_dir}/
            # new_file = old_filename.rename('/media/shows/{show_dir}/{season_dir}/{title} S{season}E{0 if i < 9 else ""}{first_episode + i}.mkv')

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
