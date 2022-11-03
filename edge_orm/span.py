import time
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
def timer(*, op: str, description: str = None, use: bool) -> T.Iterator[T.Any]:
    if use:
        start = time.time()
        yield
        took_ms = round((time.time() - start) * 1000, 2)
        logger.debug(f"{op=}, {description} took {took_ms} ms")
    else:
        yield


@contextmanager
def span(
    op: str,
    description: str = None,
    use: bool = True,
    log_time: bool = False,
    **kwargs: T.Any,
) -> T.Iterator[T.Any]:
    if USE_SENTRY is False or use is False:
        yield
    else:
        with timer(op=op, description=description, use=log_time):
            with start_span(op=op, description=description, **kwargs):
                yield
