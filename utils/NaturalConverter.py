from discord.ext.commands import BadArgument, Converter

__all__ = ["NaturalConverter"]


class NaturalConverter(Converter):
    def __init__(self, *, include_zero: bool = False):
        self.lower_bound = 0 if include_zero else 1

    async def convert(self, ctx, argument):
        try:
            i = int(argument)
            if i < self.lower_bound:
                raise BadArgument
            return i
        except ValueError:
            raise BadArgument
