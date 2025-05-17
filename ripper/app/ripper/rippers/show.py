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
        self.show_dir = self.media_dir / f'{self.title} ({self.year})'
        self.season_dir = self.show_dir / f'Season {season}'

    def expect_rip(self, duration) -> bool:
        return duration > self.episode_lower_bound and duration < self.episode_upper_bound

    async def display_title(self, title, duration=None, number=1):
        return await super().display_title(title, duration=duration, number=number)

    async def rename_ripped_files(self):
        """Move ripped episode files from `/media/inbox/*.mkv` to
        `/media/shows/<title>/Season <season>/<title> S<season>E<episode>.mkv`
        based on the order of selected tracks and assumed episode sequence.
        """
        media = Path("/media")
        inbox = media / "inbox"
        cli = get_cli_args()

        if not await confirm(f'You good moving ahead and importing ep(s) to `{self.season_dir}`?'):
            return

        # Gather all MKV files in /media/inbox
        ripped_files = sorted(f for f in inbox.iterdir() if f.suffix == '.mkv')
        track_count = len(self.selected_tracks)
        file_count = len(ripped_files)

        if file_count != track_count:
            self._console.print(
                f"[yellow]⚠️ Found {file_count} ripped .mkv files, "
                f"but you selected {track_count} tracks.[/yellow]"
            )

            # FIXME if there was an issue ripping one or more tracks, there will be fewer
            # selectable files than selections and this instruction will frustrate more
            # than help.
            # - minimal: rephrase
            # - ideal: compare size and/or runtimes of ripped mkv files to selected tracks to try to match them automatically
            self._console.print(f"[green]Please select all files for the {track_count} tracks you ripped[/green]")
            selected_files = await select_file(inbox, self._console, multiple=True)
            ripped_files = [inbox / filename for filename in selected_files]

        self.season_dir.mkdir(parents=True, exist_ok=True)

        for i, ripped_file in enumerate(ripped_files):
            episode = self.starts_at_episode + i
            new_name = f"{self.title} S{self.season}E{episode:02d}.mkv"
            destination = self.season_dir / new_name

            if cli.debug:
                print(f"Moving: {ripped_file} → {destination}")

            ripped_file.rename(destination)

        print(f"✅ Imported {len(ripped_files)} episode(s) to `{self.season_dir}`.")
