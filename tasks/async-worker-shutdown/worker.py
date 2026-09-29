import asyncio


async def worker() -> str:
    try:
        await asyncio.sleep(1)
        return "done"
    except asyncio.CancelledError:
        await asyncio.sleep(1)
        raise


async def run_worker() -> dict:
    task = asyncio.create_task(worker())
    await asyncio.sleep(0.05)
    task.cancel()
    pending = len(asyncio.all_tasks() - {asyncio.current_task()})
    return {"status": "cancelled", "pending": pending}


if __name__ == "__main__":
    print(asyncio.run(run_worker()))
