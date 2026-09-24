# utf8-search 服务镜像
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# pip 镜像源：国内服务器构建时可通过
#   docker compose build --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
# 或直接在 docker-compose.yml 的 build.args 中指定，避免访问 pypi.org 超时。
ARG PIP_INDEX_URL=https://pypi.org/simple
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 先装依赖，利用镜像层缓存
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
 && pip install --no-cache-dir .

# 缓存目录（compose 中挂载为卷）
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "utf8_search.server.http_api:app", "--host", "0.0.0.0", "--port", "8000"]