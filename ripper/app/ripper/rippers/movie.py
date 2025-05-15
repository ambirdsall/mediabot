from .ripper import Ripper

from ripper.cli import *

from os import getenv

import requests
from rich.console import Console
from rich.prompt import Confirm, Prompt

def search_movies(title):
    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": getenv("TMDB_API_KEY"),
        "query": title,
    }
    res = requests.get(url, params=params)
    films = [(m["title"], m["release_date"]) for m in res.json().get("results", [])]
    return [(title, date[:4] if date else None) for title, date in films]

async def find_movie_and_year_from_search():
    title = await text("Let's find your movie! Please enter the title (or enough for a search engine, at least):")
    # TODO basic error handling for `requests.get`, either here or inside `search_movies`
    candidates = search_movies(title)

    if len(candidates) == 0:
        print("No results! let's try again:")
        return await find_movie_and_year_from_search()

    choices = [choice(title=f"{c_year} :: {c_title}", value=(c_title, c_year)) for c_title, c_year in candidates]

    selection = await select(
        prompt="Choose from results",
        choices=choices,
    )

    if selection is None and await confirm("Hmm. Do you want to try again?"):
        return await find_movie_and_year_from_search()
    elif selection is None:
        return None, None

    return selection


class Movie(Ripper):
    @classmethod
    async def new(cls, console=Console(), title=None, year=None):
        title, year = await find_movie_and_year_from_search()

        return cls(
            title=title,
            year=year,
            console=console,
        )

    def __init__(self, title, year, console=Console()):
        self.title = title or Prompt.ask("What's the movie's title?")
        self.year = year or Prompt.ask('What year was it released?', validate)

        self.basename = f'{title} ({year})'
        self._media_subdir = "movies"
        self.directory = self.media_dir / self.basename

    def expect_rip(self, duration):
        return duration > self.episode_upper_bound

    async def display_title(self, title, duration=None):
        return await super().display_title(title, duration=duration)

    async def rename_ripped_files(self):
        """Move a ripped movie file from `/media/inbox/<possibly gibberish>.mkv` to
        `/media/movies/<title> (<year>)/<title> (<year>).mkv`."""
        old_filename = Path(self.makemkv.current_info[4])
        if await confirm(f"You good renaming `{old_filename}` to `{self.directory / f'{self.basename}.mkv'}`?"):

            # FIXME THIS IS ALL UNTESTED BC IT AIN'T HAPPENED YET
            # and it's ~definitely~ maybe not correct lol
            if not old_filename.suffix == '.mkv':
                candidate_files = [f for f in self.media_dir.iterdir() if f.suffix == '.mkv']
                if len(candidate_files) == 1:
                    old_filename = Path(candidate_files[0])
                else:
                    old_filename = Path(await select_file(self.media_dir, self.console))

            self.directory.mkdir(exist_ok=True)
            new_file = old_filename.rename(self.directory / f'{self.basename}.mkv')

            if new_file.is_file():
                print(f'lo it is ript to {new_file}')
                # TODO back up and preprocess (mp4?)
            else:
                print(f"I thought I was saving the video as {new_file}, but that seems to not be a file??")
