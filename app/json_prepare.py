import json
import re
import os
import uuid

# CONFIG

OPERATION_MAP = {
    "Приход": "Income",
    "Возврат прихода": "ReturnIncome",
    "Расход": "Expense",
    "Возврат расхода": "ReturnExpense"
}

def remove_trailing_commas(text):
    lines = text.splitlines()
    cleaned_lines = []
    skip_block = False

    for line in lines:
        stripped_line = line.rstrip()  # убираем пробелы справа

        # проверяем, начинаем ли блок "Предметы"
        if '"Предметы": [' in stripped_line:
            skip_block = True

        # если не внутри блока "Предметы", убираем запятую в конце
        if not skip_block:
            stripped_line = stripped_line.rstrip(',')

        # проверяем, конец блока "Предметы"
        if skip_block and ']' in stripped_line:
            skip_block = False

        cleaned_lines.append(stripped_line)

    return "\n".join(cleaned_lines)


# Пример использования:

def parse_items(text: str):
    # 1) Вырезаем блок с предметами (нежадно)
    m = re.search(r"Предметы\s*:\s*\[(.*?)\]", text, re.S)
    if not m:
        return []

    raw = m.group(1)

    # 2) Нормализация "почти JSON" → валидный JSON
    block = raw

    # 2.1 между объектами вставляем запятые: } {  →  },{
    block = re.sub(r'}\s*{', '},{', block)

    # 2.2 у ключей (name, quantity, unit, price_per_unit) добавляем кавычки, если их нет
    def quote_keys(mo):
        prefix, key = mo.group(1), mo.group(2)
        return f'{prefix}"{key}":'
    block = re.sub(r'(?m)(^|[{,\s])\s*(name|quantity|unit|price_per_unit)\s*:', quote_keys, block)

    # 2.3 убираем хвостовые запятые перед } или ]
    block = re.sub(r',\s*([}\]])', r'\1', block)

    # ВАЖНО: не заменяем «типографские» кавычки на " — это как раз часто ломает JSON.
    # Если вдруг в значениях есть неэкранированные двойные кавычки, json всё равно может упасть.
    # Тогда перейдём на «план Б».

    json_str = "[" + block.strip() + "]"

    try:
        return json.loads(json_str)
    except Exception:
        # 3) План Б — максимально терпимый построчный парсер
        items = []
        # берём каждый объект { ... }
        for obj in re.findall(r'\{(.*?)\}', raw, re.S):
            fields = {}
            # берём непустые строки внутри объекта
            for line in re.findall(r'.+', obj):
                line = line.strip().rstrip(',')
                if ':' not in line:
                    continue
                key, val = line.split(':', 1)
                key = key.strip().strip('"\'“”«»').lower()
                val = val.strip().rstrip(',').strip()

                # удаляем внешние кавычки любого типа
                pairs = [('"', '"'), ("'", "'"), ('«', '»'), ('“', '”')]
                for lq, rq in pairs:
                    if len(val) >= 2 and val[0] == lq and val[-1] == rq:
                        val = val[1:-1].strip()
                        break

                fields[key] = val

            items.append({
                "Name": fields.get("name"),
                "Quantity": fields.get("quantity"),
                "Unit": fields.get("unit"),
                "PricePerUnit": fields.get("price_per_unit") or fields.get("price") or fields.get("sum"),
            })
        return items

def extract_store_name(text: str) -> str:
    if text != None:
        text = text.lower()
        name = re.sub(r"[\"'«»“”„]", "", text)
        return name.strip()
    else:
        return "Unknown"

def categorize_price(total: float) -> str:
    if total < 500:
        return "Under500"
    elif 500 <= total < 1000:
        return "From500To1000"
    elif 1000 <= total < 5000:
        return "From1000To5000"
    else:
        return "Over5000"

# Load store categories
def load_store_categories(path="store_categories.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_category_by_store(store_name: str, categories: dict) -> str:
    new_store_name = store_name.replace('ё', 'е')
    for category, stores in categories.items():
        store_words = new_store_name.split()
        for name in store_words:
                if name in stores:
                    return category
    return "Other"

# Main parser
def parse_receipt_from_image(text: str, store_map: dict, receipt_id) -> dict:

    #fix ,
    text = remove_trailing_commas(text)


    patterns = {
        "operation_type": r"Тип операции:\s*(.*)",
        "date": r"Дата:\s*(.*)",
        "time": r"Время:\s*(.*)",
        "total": r"Итоговая сумма:\s*([\d.,]+)",
        "fiscal_number": r"Цифры после ФН:\s*(\d+)",
        "fiscal_document": r"Цифры после ФД:\s*(\d+)",
        "fiscal_sign": r"Цифры после ФП:\s*(\d+)",
        "inn": r"Цифры после ИНН:\s*(\d+)",
        "receipt_number": r"Номер чека:\s*(\d+)",
        "store_name": r"Название магазина:\s*(.+)",
        "vat_amount": r"Цифры после суммы НДС:\s*([\d.,]+)",
    }

    data = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text,re.MULTILINE)
        if match:
            data[key] = match.group(1).strip()


    # value processing
    op_type = OPERATION_MAP.get(data.get("operation_type", ""), "Unknown")
    total_value = float(data.get("total", "0").replace(",", "."))
    price_category = categorize_price(total_value)
    store_name = extract_store_name(data.get("store_name"))

    category_by_store = get_category_by_store(store_name, store_map)


    # parse items
    items = parse_items(text)
    if not items:
        print("Предметы не найдены")
    else:
        print(items)
    # final
    State = ""
    if (data.get("total") or store_name or items) == None:
        State = "NotRecognized"
    else:
        State = "Recognized"
    result = {
        "ReceiptId": receipt_id,
        "OperationType": op_type,
        "CategoryByStore": category_by_store,
        "CategoryByPrice": price_category,
        "State": State,
        "Date": data.get("date"),
        "Time": data.get("time"),
        "Total": data.get("total"),
        "FiscalNumber": data.get("fiscal_number"),
        "FiscalDocument": data.get("fiscal_document"),
        "FiscalSign": data.get("fiscal_sign"),
        "INN": data.get("inn"),
        "ReceiptNumber": data.get("receipt_number"),
        "StoreName": store_name,
        "Items": items,
        "VatAmount": data.get("vat_amount")
    }

    return result

def main_text_parser(text: str, receipt_id, input_type):
    store_categories = os.getenv("STORE_CATEGORIES")
    store_map = load_store_categories(store_categories)


    if input_type == "image":
        parsed = parse_receipt_from_image(text, store_map, receipt_id)
        return parsed

