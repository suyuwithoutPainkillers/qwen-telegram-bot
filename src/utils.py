import base64
import io
import os
from asyncio import Lock, to_thread
from typing import Any, AsyncIterator, TypedDict

from openai import AsyncOpenAI
from PIL import Image

from config import conf
from storage import (
    append_turn,
    clear_user_history,
    get_user_model,
    load_history,
    set_user_model,
)

DEFAULT_QWEN_MODELS = (
    "qwen-turbo",
    "qwen-plus",
    "qwen-max",
    "qwen-long",
    "qwen-vl-plus",
    "qwen-vl-max",
)

QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"


class UserSession(TypedDict):
    lock: Lock
    model: str | None


chat_dict: dict[int, UserSession] = {}
client: AsyncOpenAI | None = None
available_models: list[str] = list(DEFAULT_QWEN_MODELS)


def init_client(api_key: str, base_url: str | None = None, models: str | None = None) -> None:
    """Initialize the OpenAI-compatible Qwen client once during startup."""
    global client, available_models
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url or QWEN_BASE_URL,
        timeout=120.0,
        max_retries=1,
    )

    if models:
        configured = [model.strip() for model in models.split(",") if model.strip()]
        if configured:
            available_models = configured


def get_client() -> AsyncOpenAI:
    if client is None:
        raise RuntimeError("Qwen client is not initialized")
    return client


async def list_available_models(force_refresh: bool = False) -> list[str]:
    return available_models


def get_default_model() -> str:
    return available_models[0]


async def init_user(user_id: int) -> UserSession:
    if user_id not in chat_dict:
        lock = Lock()
        model = await to_thread(get_user_model, user_id)
        if not model or model.startswith("gemini-"):
            model = get_default_model()
            await to_thread(set_user_model, user_id, model)
        chat_dict[user_id] = {
            "lock": lock,
            "model": model,
        }
    return chat_dict[user_id]


async def select_model(user_id: int, new_model: str) -> str:
    session = await init_user(user_id)
    lock = session["lock"]

    async with lock:
        await to_thread(set_user_model, user_id, new_model)
        session["model"] = new_model
        return new_model


async def get_current_model(user_id: int) -> str | None:
    session = await init_user(user_id)
    return session["model"]


async def clear_history(user_id: int) -> None:
    await init_user(user_id)
    await to_thread(clear_user_history, user_id)


def _image_to_data_url(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=90)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _contents_to_openai_content(contents: str | list[Any]) -> str | list[dict[str, object]]:
    if isinstance(contents, str):
        return contents

    parts: list[dict[str, object]] = []
    for item in contents:
        if isinstance(item, str) and item.strip():
            parts.append({"type": "text", "text": item.strip()})
        elif isinstance(item, Image.Image):
            parts.append({
                "type": "image_url",
                "image_url": {"url": _image_to_data_url(item)},
            })

    if not parts:
        return ""
    if len(parts) == 1 and parts[0].get("type") == "text":
        return str(parts[0]["text"])
    return parts


def _normalize_contents_for_history(contents: str | list[Any]) -> str:
    if isinstance(contents, str):
        return contents

    caption = ""
    has_image = False
    for item in contents:
        if isinstance(item, str):
            caption = item.strip()
        elif isinstance(item, Image.Image):
            has_image = True

    if has_image and caption:
        return f"[Image] {caption}"
    if has_image:
        return "[Image]"
    return caption


def _model_for_contents(model: str, contents: str | list[Any]) -> str:
    if isinstance(contents, list) and any(isinstance(item, Image.Image) for item in contents):
        if "vl" not in model:
            return os.getenv("QWEN_VISION_MODEL", "qwen-vl-plus")
    return model


async def stream_reply(user_id: int, contents: str | list[Any]) -> AsyncIterator[str]:
    session = await init_user(user_id)
    model = session["model"] or get_default_model()
    history = await to_thread(load_history, user_id, conf["max_history_turns"])
    messages: list[dict[str, object]] = [
        *history,
        {
            "role": "user",
            "content": _contents_to_openai_content(contents),
        },
    ]
    response = await get_client().chat.completions.create(
        model=_model_for_contents(model, contents),
        messages=messages,
        stream=True,
    )
    async for chunk in response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        text = getattr(delta, "content", None)
        if text:
            yield text


async def save_turn(user_id: int, contents: str | list[Any], model_text: str) -> None:
    if not model_text.strip():
        return

    session = await init_user(user_id)
    model = session["model"]
    if model is None:
        return

    user_text = _normalize_contents_for_history(contents)
    await to_thread(append_turn, user_id, model, user_text, model_text, conf["max_history_turns"])
