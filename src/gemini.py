import asyncio
import time
import traceback

from md2tgmd import escape
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    PermissionDeniedError,
    RateLimitError,
)
from telebot import TeleBot
from telebot.types import Message

from config import conf
from utils import init_user, save_turn, stream_reply

error_info              =       conf["error_info"]
before_generate_info    =       conf["before_generate_info"]
download_pic_notify     =       conf["download_pic_notify"]


def is_deleted_message_error(error: Exception) -> bool:
    error_text = str(error).lower()
    return (
        "message to edit not found" in error_text
        or "message identifier is not specified" in error_text
        or "message can't be edited" in error_text
    )


def get_user_error_message(error: Exception) -> str:
    error_text = str(error).lower()
    status_code = getattr(error, "status_code", None)

    if isinstance(error, RateLimitError) or status_code == 429:
        return conf["quota_error_info"]
    if isinstance(error, (AuthenticationError, PermissionDeniedError)) or status_code in {401, 403}:
        return conf["auth_error_info"]
    if isinstance(error, BadRequestError) or status_code == 400:
        return conf["invalid_error_info"]
    if isinstance(error, (APITimeoutError, TimeoutError)) or "timeout" in error_text or "timed out" in error_text:
        return conf["timeout_error_info"]
    if isinstance(error, APIConnectionError):
        return conf["timeout_error_info"]
    if isinstance(error, APIStatusError) and status_code and status_code >= 500:
        return conf["timeout_error_info"]
    return error_info


async def gemini_stream(bot: TeleBot, message: Message, contents: str | list) -> None:
    session = await init_user(message.from_user.id)
    model = session["model"]
    lock = session["lock"]
    if lock.locked():
        await bot.reply_to(message, conf["busy_info"])
        return

    sent_message = await bot.reply_to(message, "Generating answers...")
    if model is None:
        await bot.edit_message_text(
            "Please choose a model first with /model.",
            chat_id=sent_message.chat.id,
            message_id=sent_message.message_id
        )
        return

    async with lock:
        output_message_deleted = False
        try:
            full_response = ""
            last_update = time.time()
            update_interval = conf["streaming_update_interval"]

            async with asyncio.timeout(conf["generation_timeout_seconds"]):
                async for chunk_text in stream_reply(message.from_user.id, contents):
                    full_response += chunk_text
                    current_time = time.time()
                    if current_time - last_update < update_interval or output_message_deleted:
                        continue

                    try:
                        await bot.edit_message_text(
                            escape(full_response),
                            chat_id=sent_message.chat.id,
                            message_id=sent_message.message_id,
                            parse_mode="MarkdownV2"
                        )
                    except Exception as e:
                        if "parse markdown" in str(e).lower():
                            await bot.edit_message_text(
                                full_response,
                                chat_id=sent_message.chat.id,
                                message_id=sent_message.message_id
                            )
                        elif is_deleted_message_error(e):
                            output_message_deleted = True
                        elif "message is not modified" not in str(e).lower():
                            print(f"Error updating message: {e}")
                    last_update = current_time

            if output_message_deleted:
                await bot.reply_to(message, full_response or conf["timeout_error_info"])
            else:
                try:
                    await bot.edit_message_text(
                        escape(full_response),
                        chat_id=sent_message.chat.id,
                        message_id=sent_message.message_id,
                        parse_mode="MarkdownV2"
                    )
                except Exception as e:
                    try:
                        if "parse markdown" in str(e).lower():
                            await bot.edit_message_text(
                                full_response,
                                chat_id=sent_message.chat.id,
                                message_id=sent_message.message_id
                            )
                        elif is_deleted_message_error(e):
                            await bot.reply_to(message, full_response or conf["timeout_error_info"])
                    except Exception:
                        traceback.print_exc()

            try:
                await save_turn(message.from_user.id, contents, full_response)
            except Exception:
                traceback.print_exc()

        except Exception as e:
            traceback.print_exc()
            try:
                error_message = get_user_error_message(e)
                if output_message_deleted:
                    await bot.reply_to(message, error_message)
                else:
                    await bot.edit_message_text(
                        error_message,
                        chat_id=sent_message.chat.id,
                        message_id=sent_message.message_id
                    )
            except Exception:
                traceback.print_exc()
