import asyncio
import os

from contextlib import asynccontextmanager

from TeraTTS import TTS
from ruaccent import RUAccent

from fastapi import FastAPI
from pydantic import BaseModel

from hypercorn.asyncio import serve
from hypercorn.config import Config


# Set path for script.
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

# Global phrases queue.
fifo_queue = asyncio.Queue()

accentizer = RUAccent()
accentizer.load(
    workdir="./models/accents",
    omograph_model_size='big_poetry',
    use_dictionary=True
)
tts = TTS(
    # "TeraTTS/glados2-g2p-vits",
    "TeraTTS/natasha-g2p-vits",
    save_path="./models/voices",
    add_time_to_end=1.0,
    tokenizer_load_dict=False
)


class SayRequest(BaseModel):
    phrase: str
    lenght_scale: float | None = None


async def bg_worker():
    while True:
        say_request = await fifo_queue.get()
        
        if isinstance(say_request, SayRequest):
            phrase = accentizer.process_all(say_request.phrase)
            tts(phrase, play=True, lenght_scale=1.2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(bg_worker())

    yield


app = FastAPI(lifespan=lifespan)
app_config = Config()
app_config.bind = ["localhost:8000"]


@app.post("/say")
async def say(say_request: SayRequest):
    await fifo_queue.put(say_request)

    return {"status": "ok"}


if __name__ == "__main__":
    asyncio.run(serve(app, app_config))