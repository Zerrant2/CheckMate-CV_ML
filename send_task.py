import pika
import json

# ===================== CONFIG =====================
RABBITMQ_HOST = 'localhost'
API_QUEUE = 'cv_queue'

# ===================== Настройки задачи =====================
SEND_CANCELLATION = False  # ← переключай True / False

receipt_id = "check7"  # Можно менять ID
image_path = r"/mnt/test_files/1 (1).jpg" # Можно менять путь (не используется)
conn_params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=5672,
        credentials=pika.PlainCredentials(username="root", password="root")
    )

# ===================== Подключение =====================
connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
channel = connection.channel()

channel.queue_declare(queue=API_QUEUE, durable=True)

# ===================== Сообщение =====================
if SEND_CANCELLATION:
    message_type = 'cancel_receipt_recognition'
    body = {"receipt_id": receipt_id}
else:
    message_type = 'receipt_recognition_request'
    body = {"receipt_id": receipt_id, "path": image_path}

properties = pika.BasicProperties(headers={'type': message_type})
print(body)
channel.basic_publish(
    exchange='',
    routing_key=API_QUEUE,
    body=json.dumps(body),
    properties=properties
)

print(f"[>] Sent message of type '{message_type}' with receipt_id = {receipt_id}")
connection.close()
