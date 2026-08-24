FROM python:3.12-slim

WORKDIR /app

# 先装依赖，充分利用 Docker 构建缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码与静态前端
COPY . .

EXPOSE 8000

# 云托管默认监听 0.0.0.0:8000，健康检查可用 /api/v1/health
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
