# Hunyuan3D-2 FastAPI Asset Server
# Build on a CUDA base image. Adjust for your server's GPU architecture.

FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV H3D_OUTPUT_DIR=/app/generated_assets

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    python3-pip \
    python3-dev \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install PyTorch matching CUDA 12.1
RUN pip3 install --no-cache-dir torch==2.4.0 torchvision --index-url https://download.pytorch.org/whl/cu121

# Install Hunyuan3D-2 from GitHub (shape + texture)
RUN git clone https://github.com/Tencent-Hunyuan/Hunyuan3D-2.git /tmp/hunyuan3d2 && \
    cd /tmp/hunyuan3d2 && \
    pip3 install -r requirements.txt && \
    pip3 install -e . && \
    cd hy3dgen/texgen/custom_rasterizer && \
    python3 setup.py install && \
    cd ../../differentiable_renderer && \
    python3 setup.py install

# Copy server requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# Copy server code
COPY main.py /app/main.py

# Create output directory
RUN mkdir -p /app/generated_assets

EXPOSE 8080

CMD ["python3", "-u", "main.py"]
