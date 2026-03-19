import pika
import json

# ===================== CONFIG =====================
RABBITMQ_HOST = 'localhost'
CV_QUEUE = 'api_queue'

# ===================== Обработка сообщений =====================
def on_result(channel, method, properties, body):
    print("\n[<] Received message from cv_queue")
    try:
        data = json.loads(body)
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[!] Failed to parse JSON: {e}")
        print(body)
    channel.basic_ack(delivery_tag=method.delivery_tag)

# ===================== Подключение =====================
connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
channel = connection.channel()
channel.queue_declare(queue=CV_QUEUE, durable=True)

channel.basic_consume(queue=CV_QUEUE, on_message_callback=on_result)

print("[*] Listening for recognition results...")
try:
    channel.start_consuming()
except KeyboardInterrupt:
    print("Exiting...")
    channel.stop_consuming()
