import typing as T
from contextlib import contextmanager
from edge_orm import logger

try:
    from sentry_sdk import start_span

    USE_SENTRY = True
except ModuleNotFoundError:
    logger.debug("Sentry not found, will not span.")
    USE_SENTRY = False


@contextmanager
def span(
    op: str, description: str = None, use: bool = True, **kwargs: T.Any
) -> T.Iterator[T.Any]:
    if USE_SENTRY is False or use is False:
        yield
    else:
        with start_span(op=op, description=description, **kwargs):
            yield
