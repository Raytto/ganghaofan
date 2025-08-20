# 罡好饭后端服务 Docker 镜像

FROM continuumio/miniconda3:latest

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CONDA_AUTO_UPDATE_CONDA=false \
    PATH="/opt/conda/envs/ghf-server/bin:$PATH"

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制环境配置文件
COPY server/environment.yml /tmp/environment.yml

# 创建conda环境
RUN conda env create -f /tmp/environment.yml && \
    conda clean -afy

# 复制应用代码
COPY server/ /app/

# 创建必要的目录
RUN mkdir -p /app/data /app/config /app/logs

# 创建非root用户
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["conda", "run", "-n", "ghf-server", "python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]