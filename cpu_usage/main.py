import psutil
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import time
import statistics

app = FastAPI()

cpu_history = {"mongod": [], "redis": []}
HISTORY_DURATION = 2.5  # 2500 milliseconds


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


@app.get("/cpu_usage")
async def cpu_usage():
    current_time = time.time()
    mongod_cpu_percent = get_process_cpu_percent("mongod", "mongod")
    redis_cpu_percent = get_process_cpu_percent("redis-server", "redis")

    result = {}

    for process, cpu_percent in [
        ("mongod", mongod_cpu_percent),
        ("redis", redis_cpu_percent),
    ]:
        if cpu_percent is not None:
            cpu_history[process].append((current_time, cpu_percent))

            # Remove old entries
            while (
                cpu_history[process]
                and current_time - cpu_history[process][0][0] > HISTORY_DURATION
            ):
                cpu_history[process].pop(0)

            cpu_values = [cpu for _, cpu in cpu_history[process]]
            stats = get_cpu_stats(cpu_values) or {
                "high": cpu_percent,
                "average": cpu_percent,
                "low": cpu_percent,
                "median": cpu_percent,
            }

            result[f"{process}_cpu_percent"] = stats
        else:
            result[f"{process}_cpu_percent"] = {
                "error": f"{process.capitalize()} process not found"
            }

    return JSONResponse(content=result)


if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=4302)