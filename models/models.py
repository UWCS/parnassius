from sqlalchemy.orm import declarative_base

from utils.logging import get_representation

__all__ = ["Base", "model_repr"]

Base = declarative_base()


def model_repr(cls):
    def __repr__(self):
        values = ", ".join(
            f"{k}={get_representation(v)}" for k, v in vars(self).items()
        )
        return f"<{type(self).__name__} {values}>"

    cls.__repr__ = __repr__
    return cls
