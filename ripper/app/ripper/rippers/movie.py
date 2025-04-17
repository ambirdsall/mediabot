from .ripper import Ripper

from rich.prompt import Prompt

class Movie(Ripper):
    def __init__(self, title, year):
        self._media_subdir = "movies"
        self.title = title or Prompt.ask("What's the movie's title?")
        self.year = year or Prompt.ask('What year was it released?', validate)
        self.basename = f'{title} ({year})'

    def expect_rip(self, duration):
        return duration > self.episode_upper_bound

    async def display_title(self, title, duration=None):
        return await super().display_title(title, duration=duration)

    async def rename_ripped_files(self):
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
