import asyncio

from app.core.queue import Job, JobQueue
from app.utils.dedup import Deduplicator
from app.utils.stats import StatsCollector


def test_queue_enqueue_dequeue() -> None:
    async def _run() -> None:
        stats = StatsCollector()
        queue = JobQueue(max_size=10, deduplicator=Deduplicator(60), stats=stats)
        job = Job.build("job-1", chat_id="c1", message_id="m1", sender_id="s1", update_type="message", text="hi")
        decision = await queue.enqueue(job)
        assert decision == "enqueued"
        fetched = await queue.get()
        assert fetched is not None
        assert fetched.job_id == "job-1"
        queue.task_done()

    asyncio.run(_run())


def test_queue_task_done_defaults_to_high_queue() -> None:
    async def _run() -> None:
        queue = JobQueue(max_size=10, deduplicator=Deduplicator(60))
        await queue.put_raw(None)
        await queue.get()
        queue.task_done()

    asyncio.run(_run())
