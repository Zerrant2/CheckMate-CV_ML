import pika
import json
import sys
import os
import uuid
from dotenv import load_dotenv
load_dotenv()
# параметры подключения
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "root")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "root")

CV_QUEUE = os.getenv("CV_QUEUE", "cv_queue")

def send_task(image_path: str):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue=CV_QUEUE, durable=True)

    # Уникальный ID для задачи
    receipt_id = str(uuid.uuid4())

    message = {
        "ReceiptId": receipt_id,
        "Path": image_path
    }

    props = pika.BasicProperties(type="ReceiptRecognitionRequest")

    channel.basic_publish(
        exchange="",
        routing_key=CV_QUEUE,
        body=json.dumps(message),
        properties=props
    )

    print(f"[>] Sent task: {receipt_id} for {image_path}")
    connection.close()
    return receipt_id

if __name__ == "__main__":

    send_task(r"default_shadows.jpg")
