import psutil
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
import time
import statistics

app = FastAPI()

cpu_history = {"mongod": [], "redis": []}


def get_process_cpu_percent(process_name, username):
    for proc in psutil.process_iter(["name", "cmdline", "username", "cpu_percent"]):
        try:
            cmdline = proc.info["cmdline"]
            if (
                cmdline
                and process_name in cmdline[0]
                and proc.info["username"] == username
            ):
                return proc.info["cpu_percent"]
        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
            IndexError,
        ):
            pass
    return None


def get_cpu_stats(cpu_values):
    if cpu_values:
        return {
            "high": max(cpu_values),
            "average": statistics.mean(cpu_values),
            "low": min(cpu_values),
            "median": statistics.median(cpu_values),
        }
    return None


HISTORY_DURATION = 30  # 30 seconds
SAMPLE_INTERVAL = 1  # 1 second

@app.get("/cpu_usage")
async def cpu_usage():
    samples = []
    start_time = time.time()

    while time.time() - start_time < HISTORY_DURATION:
        mongod_cpu_percent = get_process_cpu_percent("mongod", "mongod")
        #mongod_cpu_percent = get_process_cpu_percent("mongod", "mongodb")
        redis_cpu_percent = get_process_cpu_percent("redis-server", "redis")
        
        samples.append({
            "timestamp": time.time(),
            "mongod": mongod_cpu_percent,
            "redis": redis_cpu_percent
        })
        
        await asyncio.sleep(SAMPLE_INTERVAL)

    result = {}
    for process in ["mongod", "redis"]:
        cpu_values = [sample[process] for sample in samples if sample[process] is not None]
        if cpu_values:
            stats = get_cpu_stats(cpu_values)
            result[f"{process}_cpu_percent"] = stats
        else:
            result[f"{process}_cpu_percent"] = {
                "error": f"{process.capitalize()} process not found"
            }

    return JSONResponse(content=result)


if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=4302)