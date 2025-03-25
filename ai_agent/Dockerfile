FROM python:3.11.9-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 安裝 poetry
RUN pip install poetry==1.7.1

# 複製 poetry 相關文件
COPY pyproject.toml poetry.lock ./

# 配置 poetry 不創建虛擬環境（因為我們在容器中）
RUN poetry config virtualenvs.create false

# 安裝依賴
RUN poetry install --no-interaction --no-ansi

# 複製應用程序代碼
COPY . .

# 暴露 Streamlit 默認端口
EXPOSE 8501

# 啟動 Streamlit 應用
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"] 