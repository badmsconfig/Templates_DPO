# Импорт необходимых библиотек
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path
import yaml
from datetime import datetime
import re

# Функция для настройки и получения веб-драйвера Chrome
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

# Словарь с CSS-селекторами для извлечения данных
SELECTORS = {
    "office_position": (By.CSS_SELECTOR, "div.contact_block__position"),
    "office_address": (By.CSS_SELECTOR, "div.contact_block__name"),
    "activity_text": (By.CSS_SELECTOR, "b"),
    "table_rows": (By.CSS_SELECTOR, "table.recvisit_table tbody tr"),
    "row_title": (By.CSS_SELECTOR, "td:nth-child(1)"),
    "row_data": (By.CSS_SELECTOR, "td:nth-child(2)"),
    "meta_title": (By.TAG_NAME, "title"),
    "meta_description": (By.XPATH, "//meta[@name='description']")
}

# Функция для извлечения метаданных
def extract_metadata(driver, url):
    metadata = {}
    try:
        title_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(SELECTORS["meta_title"])
        )
        metadata["title"] = title_element.get_attribute("innerText").strip()
    except Exception as e:
        print(f"Ошибка при извлечении заголовка страницы: {str(e)}")
        metadata["title"] = "Без названия"

    try:
        desc_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(SELECTORS["meta_description"])
        )
        metadata["description"] = desc_element.get_attribute("content").strip()
    except Exception as e:
        print(f"Ошибка при извлечении meta description: {str(e)}")
        try:
            activity_text = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(SELECTORS["activity_text"])
            )
            intro_text = activity_text.text.strip()
            metadata["description"] = re.sub(r'[#*\[\]]', '', intro_text)[:160].strip() + "..."
        except:
            metadata["description"] = "Описание отсутствует"

    metadata["url"] = url
    metadata["date"] = datetime.now().strftime("%Y-%m-%d")
    metadata["categories"] = ["Контакты", "Образование"]
    metadata["tags"] = ["ДПО", "контакты", "дистанционное обучение"]

    return metadata

# Функция для парсинга страницы
def parse_page(driver, url):
    driver.get(url)
    try:
        # Ожидание загрузки таблицы (15 секунд)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["table_rows"])
        )
    except Exception as e:
        print(f"Ошибка загрузки страницы: {str(e)}")
        return [], url, {}

    metadata = extract_metadata(driver, url)
    result = []

    # Извлечение информации об офисе
    try:
        office_position = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["office_position"])
        ).text.strip()
        result.append(("office_position", office_position))
        print(f"Заголовок офиса: {office_position}")
    except Exception as e:
        print(f"Ошибка при парсинге заголовка офиса: {str(e)}")

    try:
        office_address = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["office_address"])
        ).text.strip()
        result.append(("office_address", office_address))
        print(f"Адрес офиса: {office_address}")
    except Exception as e:
        print(f"Ошибка при парсинге адреса офиса: {str(e)}")

    # Извлечение текста о деятельности
    try:
        activity_text = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["activity_text"])
        ).text.strip()
        result.append(("activity_text", activity_text))
        print(f"Текст о деятельности: {activity_text}")
    except Exception as e:
        print(f"Ошибка при парсинге текста о деятельности: {str(e)}")

    # Парсинг таблицы
    try:
        rows = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(SELECTORS["table_rows"])
        )
        table_content = []
        for row in rows:
            try:
                row_title = row.find_element(*SELECTORS["row_title"]).text.strip()
                print(f"Заголовок строки: {row_title}")
            except Exception as e:
                print(f"Ошибка при парсинге заголовка строки: {str(e)}")
                continue

            try:
                row_data = row.find_element(*SELECTORS["row_data"]).text.strip()
                print(f"Данные строки: {row_data}")
            except Exception as e:
                print(f"Ошибка при парсинге данных строки: {str(e)}")
                row_data = ""

            if row_title and row_data:
                table_content.append(f"### {row_title}\n{row_data}")

        if table_content:
            result.append(("content", table_content))
            print(f"Содержимое таблицы: {table_content}")
    except Exception as e:
        print(f"Ошибка при парсинге таблицы: {str(e)}")

    print(f"Итоговые данные: {result}")
    return result, url, metadata

# Функция для сохранения данных в Markdown-файл
def save_to_markdown(data, url, metadata, filename="DPO_kontakty.md"):
    content = []

    # Формируем YAML-метаданные
    yaml_metadata = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
    content.append(f"---\n{yaml_metadata}---")

    content.append(f"# Контакты\n[Перейти к странице]({url})")

    for item in data:
        if item[0] == "office_position":
            content.append(f"## {item[1]}")
        elif item[0] == "office_address":
            content.append(f"{item[1]}")
        elif item[0] == "activity_text":
            content.append(f"**{item[1]}**")
        elif item[0] == "content":
            content.append("## Реквизиты")
            content.extend(item[1])

    # Объединяем с одним переносом строки
    final_content = "\n".join(line for line in content if line.strip())

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"Контент записан в файл: {filename}")
    return filename

# Основной блок программы
if __name__ == "__main__":
    TARGET_URL = "https://academydpo.org/kontakty"
    driver = get_driver()
    try:
        parsed_data, page_url, metadata = parse_page(driver, TARGET_URL)
        output_file = save_to_markdown(parsed_data, page_url, metadata)
        print(f"Файл {output_file} успешно сохранен!")
    except Exception as e:
        print(f"Ошибка при парсинге: {str(e)}")
    finally:
        driver.quit()