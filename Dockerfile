FROM pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime

# Устанавливаем зависимости для OpenCV / работы с изображениями
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ make \
    ffmpeg libsm6 libxext6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir scipy==1.15.3

RUN pip install --no-cache-dir numpy==1.26.4

COPY ./app /app

CMD ["python", "recognition_service.py"]