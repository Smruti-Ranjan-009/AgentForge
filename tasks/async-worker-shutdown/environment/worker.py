import asyncio


async def worker() -> str:
    await asyncio.sleep(0.2)
    return "done"


async def run_worker() -> dict:
    task = asyncio.create_task(worker())
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.sleep(0)
    return {"status": "cancelled", "pending": len(asyncio.all_tasks() - {asyncio.current_task()})}


if __name__ == "__main__":
    print(asyncio.run(run_worker()))
