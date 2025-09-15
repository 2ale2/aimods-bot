# stress_persistence.py
import asyncio, os, random, time
from aimods_bot.src.core.async_persistence import AsyncPostgresPersistence
from dotenv import load_dotenv


async def main():
    p = AsyncPostgresPersistence(
        url=os.getenv("POSTGRES_CONNECTION_URL"),
        on_flush=False,        # coalescing attivo
        coalesce_delay=0.05,   # alza/abbassa per test
        update_interval=0,     # parametro PTB ignorato qui, ma lo lasciamo
    )
    await p.initialize()

    N_TASKS = 50          # numero di coroutine concorrenti
    OPS_PER_TASK = 1000   # update per ciascuna coroutine

    async def worker(tid: int):
        for i in range(OPS_PER_TASK):
            uid = random.randint(1, 100)
            # simula uno user_data che cambia
            data = {"count": i, "tid": tid}
            await p.update_user_data(uid, data)
            # jitter minimo
            await asyncio.sleep(random.random() * 0.002)

    t0 = time.perf_counter()
    await asyncio.gather(*[worker(t) for t in range(N_TASKS)])
    # forza l’ultimo flush
    await p.flush()
    dt = time.perf_counter() - t0
    print(f"Done {N_TASKS*OPS_PER_TASK} updates in {dt:.2f}s")

    await p.aclose()

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
