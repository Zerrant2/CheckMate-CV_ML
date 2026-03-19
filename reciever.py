import pika
import json
import os
from dotenv import load_dotenv

load_dotenv()
# параметры подключения
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "root")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "root")

API_QUEUE = os.getenv("API_QUEUE", "api_queue")

def on_message(channel, method, properties, body):
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        print("[!] Invalid JSON")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    print(f"[<] Received message of type {properties.type}")
    print(json.dumps(data, ensure_ascii=False, indent=4))

    channel.basic_ack(delivery_tag=method.delivery_tag)

def consume_results():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue=API_QUEUE, durable=True)

    print("[*] Waiting for results...")
    channel.basic_consume(queue=API_QUEUE, on_message_callback=on_message)
    channel.start_consuming()

if __name__ == "__main__":
    consume_results()
