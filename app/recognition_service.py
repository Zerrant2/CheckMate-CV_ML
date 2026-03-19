import pika
import logging
import threading
import json
import time
from queue import Queue
import os
import sys
from dotenv import load_dotenv
from InternVL3.model_load import load_model, model_inference
from api_recognition_service import api_recognition, api_recognition_document
from json_prepare import main_text_parser
from cv_text_preprocess import cv_preprecess
from pdf_extractor import get_pdf_info
import subprocess

# ===================== CONFIG =====================
load_dotenv()
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "root")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "root")
API_QUEUE = os.getenv("API_QUEUE", "api_queue")
CV_QUEUE = os.getenv("CV_QUEUE", "cv_queue")

RECOGNITION_MODE = os.getenv("RECOGNITION_MODE")
PREPROCESS_MODE = os.getenv("PREPROCESSING")
ROOT_FOLDER = os.getenv("ROOT_FOLDER", "/app")
STORAGE_DIR = os.getenv("RECEIPTS_DIR", "receipts")

# ===================== LOGGER =====================
logger = logging.getLogger("recognition_service")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# ===================== STATE =====================
task_queue = Queue()
cancelled_tasks = set()
cancelled_lock = threading.Lock()

# ===================== UTILS =====================
def safe_publish(channel, exchange, routing_key, body, properties, retries=3, delay=2):
    retries = int(retries)
    for attempt in range(retries):
        try:
            channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=body,
                properties=properties
            )
            return
        except pika.exceptions.StreamLostError as e:
            logger.warning(f"StreamLostError, retry {attempt+1}/{retries}")
            time.sleep(delay)
    logger.error("Failed to publish message after retries")


def get_file_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"]:
        return "image"
    elif ext in [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".odt"]:
        return "document"
    return "unknown"

# ===================== RECOGNITION =====================
def recognize_receipt(receipt_id, path):
    document_type = get_file_type(path)
    if document_type == "image":
        if PREPROCESS_MODE == "docres":
            subprocess.run([
                sys.executable, "inference.py", "--im_path", path, "--task", "end2end", "--save_dtsprompt", "0"
            ], cwd=f"{ROOT_FOLDER}/DocRes")
            logger.info("DocRes recognition ready")
        elif PREPROCESS_MODE == "cv":
            cv_preprecess(path)
            logger.info("CV recognition ready")

        if RECOGNITION_MODE == "api":
            return api_recognition(f"{ROOT_FOLDER}/DocRes/restored/current_check.jpg")
        elif RECOGNITION_MODE == "local":
            local_model_name = os.getenv("DEVICE_MODEL")
            local_model_cache_dir = os.getenv("CACHE_DIR")
            prompt_file = os.getenv("SYSTEM_PROMPT")
            with open(prompt_file, "r", encoding="utf-8") as f:
                system_prompt = f.read()
            model = load_model(model_name=local_model_name, cache_dir=local_model_cache_dir)
            return model_inference(local_model_name, f"{ROOT_FOLDER}/DocRes/restored/current_check.jpg", system_prompt, model)

    elif document_type == "document":
        document_text = get_pdf_info(path)
        return api_recognition_document(document_text)

# ===================== WORKER THREAD =====================
def worker_thread():
    conn_params = pika.ConnectionParameters(
        heartbeat=0,
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=pika.PlainCredentials(username=RABBITMQ_USER, password=RABBITMQ_PASS)
    )
    connection = pika.BlockingConnection(conn_params)
    channel = connection.channel()
    channel.queue_declare(queue=API_QUEUE, durable=True)

    while True:
        receipt = task_queue.get()
        receipt_id = receipt["ReceiptId"]
        path = os.path.join(STORAGE_DIR, receipt["Path"])

        with cancelled_lock:
            if receipt_id in cancelled_tasks:
                logger.info(f"Task {receipt_id} cancelled before start")
                cancelled_tasks.discard(receipt_id)
                continue

        # Send recognition started
        started_msg = {"ReceiptId": receipt_id}
        props = pika.BasicProperties(type="Infrustructure.Handlers.Receipts.ReceiptRecognitionStarted.ReceiptRecognitionStartedResponse")
        safe_publish(channel, "", API_QUEUE, json.dumps(started_msg), props)

        logger.info(f"Processing receipt {receipt_id}")

        try:
            result = recognize_receipt(receipt_id, path)
            result = main_text_parser(result, receipt_id, "image")
            logger.info(json.dumps(result, ensure_ascii=False, indent=4))
        except Exception as e:
            logger.error(f"Error processing receipt {receipt_id}: {e}")
            continue

        with cancelled_lock:
            if receipt_id in cancelled_tasks:
                logger.info(f"Task {receipt_id} cancelled before sending result")
                cancelled_tasks.discard(receipt_id)
                continue

        # Send result
        props = pika.BasicProperties(type="Infrustructure.Handlers.Receipts.ReceiptRecognition.ReceiptRecognitionResponse")
        safe_publish(channel, "", API_QUEUE, json.dumps(result, indent=4), props)
        logger.info(f"Sent result for receipt {receipt_id}")

# ===================== CALLBACK =====================
def on_message(channel, method, properties, body):
    msg_type = properties.type if properties else None
    try:
        data = json.loads(body)
    except Exception:
        logger.error("Invalid JSON")
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    if msg_type == "ReceiptRecognitionRequest":
        task_queue.put(data)
        logger.info(f"Received task: {data['ReceiptId']}")
    elif msg_type == "ReceiptRecognitionCancelRequest":
        receipt_id = data.get("ReceiptId")
        if receipt_id:
            with cancelled_lock:
                cancelled_tasks.add(receipt_id)
                logger.info(f"Cancelled task: {receipt_id}")
    else:
        logger.warning(f"Unknown message type: {msg_type}")

    channel.basic_ack(delivery_tag=method.delivery_tag)

# ===================== MAIN =====================
def main():
    conn_params = pika.ConnectionParameters(
        heartbeat=0,
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=pika.PlainCredentials(username=RABBITMQ_USER, password=RABBITMQ_PASS)
    )
    connection = pika.BlockingConnection(conn_params)
    channel = connection.channel()
    channel.queue_declare(queue=API_QUEUE, durable=True)
    channel.queue_declare(queue=CV_QUEUE, durable=True)

    # Start worker thread
    threading.Thread(target=worker_thread, daemon=True).start()

    # Start consuming messages
    channel.basic_consume(queue=CV_QUEUE, on_message_callback=on_message)
    logger.info("Waiting for messages.")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Exiting...")

if __name__ == "__main__":
    main()
