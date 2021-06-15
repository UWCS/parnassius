import logging

from utils.logging import log_func

logger = logging.getLogger("parnassius.utils.utils")
log = log_func(logger)


@log
def comma_separate(el: list, /):
    if len(el) == 1:
        return f"{el[0]}"
    elif len(el) == 2:
        return f"{el[0]} and {el[1]}"
    else:
        return f'{", ".join(el[:-1])}, and {el[-1]}'


@log
def format_list_of_members(members, /, *, ping=True):
    if ping:
        el = [member.mention for member in members]
    else:
        el = [str(member) for member in members]
    return comma_separate(el)
