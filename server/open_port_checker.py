import asyncio
import sys

import stamina
import structlog

logger = structlog.get_logger()

# Per-process global limit on the number of concurrent port checks to avoid
# being too noisy.
PORT_CHECK_CONCURRENCY_LIMIT = 100 if sys.platform == "darwin" else 2500


def limit_concurrency(max_concurrency: int):
    sema = asyncio.Semaphore(max_concurrency)

    def decorator(func):
        async def wrapper(*args, **kwargs):
            async with sema:
                return await func(*args, **kwargs)

        return wrapper

    return decorator


@limit_concurrency(PORT_CHECK_CONCURRENCY_LIMIT)
@stamina.retry(on=OSError, attempts=5)
async def tcp_open_port_check(host: str, port: int, timeout: int = 5) -> tuple:
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return (port, True)
    except asyncio.TimeoutError:
        logger.debug(f"Timeout connecting to {host!r}:{port!r}")
    except (ConnectionRefusedError, ConnectionResetError):
        logger.debug(f"Connection refused by {host!r}:{port!r}")
    except Exception as e:
        logger.exception("Unknown exception during connection", host=host, port=port)
        raise e

    return (port, False)
