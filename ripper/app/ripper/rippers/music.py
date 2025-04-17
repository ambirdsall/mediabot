from .ripper import Ripper

from rich.prompt import Prompt

class Music(Ripper):
    def __init__(self, title=None, year=None):
        self._media_subdir = "music"
        self.title = title or Prompt.ask("What's the title of this music collection?")
        self.year = year or Prompt.ask("What year was it released?")

    def expect_rip(self, duration) -> bool:
        return True

    async def display_title(self, title, duration=None, number=1):
        return await super().display_title(title, duration=duration, number=number)

    async def rename_ripped_files(self):
        ...
