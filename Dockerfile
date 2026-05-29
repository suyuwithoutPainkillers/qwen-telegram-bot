FROM python:3.14.0-slim-bookworm

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./src/ .

ENV TELEGRAM_BOT_API_KEY=""
ENV QWEN_API_KEY=""
ENV DASHSCOPE_API_KEY=""
ENV QWEN_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
ENV QWEN_MODELS="qwen-turbo,qwen-plus,qwen-max,qwen-long,qwen-vl-plus,qwen-vl-max"
ENV ADMIN_USER_IDS=""

CMD ["python", "-u", "main.py"]
