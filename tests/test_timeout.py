import asyncio
import time

import pytest
from aiohttp.helpers import Timeout


def test_timeout(loop):
    canceled_raised = False

    @asyncio.coroutine
    def long_running_task():
        try:
            yield from asyncio.sleep(10, loop=loop)
        except asyncio.CancelledError:
            nonlocal canceled_raised
            canceled_raised = True
            raise

    @asyncio.coroutine
    def run():
        with pytest.raises(asyncio.TimeoutError):
            with Timeout(0.01, loop=loop) as t:
                yield from long_running_task()
                assert t._loop is loop
        assert canceled_raised, 'CancelledError was not raised'

    loop.run_until_complete(run())


def test_timeout_finish_in_time(loop):
    @asyncio.coroutine
    def long_running_task():
        yield from asyncio.sleep(0.01, loop=loop)
        return 'done'

    @asyncio.coroutine
    def run():
        with Timeout(0.1, loop=loop):
            resp = yield from long_running_task()
        assert resp == 'done'

    loop.run_until_complete(run())


def test_timeout_gloabal_loop(loop):
    asyncio.set_event_loop(loop)

    @asyncio.coroutine
    def run():
        with Timeout(0.1) as t:
            yield from asyncio.sleep(0.01)
            assert t._loop is loop

    loop.run_until_complete(run())


def test_timeout_not_relevant_exception(loop):
    @asyncio.coroutine
    def run():
        with pytest.raises(KeyError):
            with Timeout(0.1, loop=loop):
                raise KeyError

    loop.run_until_complete(run())


def test_timeout_canceled_error_is_converted_to_timeout(loop):
    @asyncio.coroutine
    def run():
        with pytest.raises(asyncio.CancelledError):
            with Timeout(0.001, loop=loop):
                raise asyncio.CancelledError

    loop.run_until_complete(run())


def test_timeout_blocking_loop(loop):
    @asyncio.coroutine
    def long_running_task():
        time.sleep(0.1)
        return 'done'

    @asyncio.coroutine
    def run():
        with Timeout(0.01, loop=loop):
            result = yield from long_running_task()
        assert result == 'done'

    loop.run_until_complete(run())


def test_for_race_conditions(loop):
    @asyncio.coroutine
    def run():
        fut = asyncio.Future(loop=loop)
        loop.call_later(0.1, fut.set_result('done'))
        with Timeout(0.2, loop=loop):
            resp = yield from fut
        assert resp == 'done'

    loop.run_until_complete(run())


def test_timeout_time(loop):
    @asyncio.coroutine
    def go():
        foo_running = None

        start = loop.time()
        with pytest.raises(asyncio.TimeoutError):
            with Timeout(0.1, loop=loop):
                foo_running = True
                try:
                    yield from asyncio.sleep(0.2, loop=loop)
                finally:
                    foo_running = False

        assert abs(0.1 - (loop.time() - start)) < 0.01
        assert not foo_running

    loop.run_until_complete(go())
