# Импорт необходимых библиотек
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from pathlib import Path
import sys
import logging
import yaml
from datetime import datetime
import re

# Настройка кодировки консоли на UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Словарь с CSS-селекторами
SELECTORS = {
    "main_title": (By.CSS_SELECTOR, "h1.page__content-title"),
    "meta_title": (By.TAG_NAME, "title"),
    "meta_description": (By.XPATH, "//meta[@name='description']"),
    "content_desc": (By.CSS_SELECTOR, "div.page__content-desc"),
    "table_rows": (By.CSS_SELECTOR, "div.table table tbody tr"),
    "row_title": (By.CSS_SELECTOR, "td:nth-child(1)"),
    "row_data": (By.CSS_SELECTOR, "td:nth-child(2)"),
    "ordered_lists": (By.CSS_SELECTOR, "div.page__content-desc ol"),
    "unordered_lists": (By.CSS_SELECTOR, "div.page__content-desc ul")
}

def get_driver():
    """Создает и настраивает веб-драйвер."""
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1920,1080")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        logging.info("Веб-драйвер успешно создан")
        return driver
    except Exception as e:
        logging.error(f"Ошибка при настройке веб-драйвера: {e}")
        return None

def extract_metadata(driver, url):
    """Извлекает метаданные страницы."""
    metadata = {}
    try:
        title_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(SELECTORS["meta_title"])
        )
        metadata["title"] = title_element.get_attribute("innerText").strip()
    except Exception as e:
        logging.warning(f"Ошибка при извлечении заголовка страницы: {e}")
        metadata["title"] = "Без названия"

    try:
        desc_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(SELECTORS["meta_description"])
        )
        metadata["description"] = desc_element.get_attribute("content").strip()
    except Exception as e:
        logging.warning(f"Ошибка при извлечении meta description: {e}")
        try:
            content_desc = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(SELECTORS["content_desc"])
            )
            content_elements = content_desc.find_elements(By.TAG_NAME, "p")
            intro_text = " ".join([elem.text.strip() for elem in content_elements if elem.text.strip()])
            metadata["description"] = re.sub(r'[#*\[\]]', '', intro_text)[:160].strip() + "..."
        except:
            metadata["description"] = "Описание отсутствует"

    metadata["url"] = url
    metadata["date"] = datetime.now().strftime("%Y-%m-%d")
    metadata["categories"] = ["Доступная среда", "Образование"]
    metadata["tags"] = ["ДПО", "доступная среда", "дистанционное обучение"]

    return metadata

def parse_page(driver, url):
    """Парсит страницу и возвращает данные."""
    try:
        driver.get(url)
        logging.info(f"Загрузка страницы: {url}")
        WebDriverWait(driver, 30).until(EC.presence_of_element_located(SELECTORS["main_title"]))
    except Exception as e:
        logging.error(f"Ошибка загрузки страницы: {e}")
        return [], url, {}

    metadata = extract_metadata(driver, url)
    result = []

    # Извлечение заголовка
    try:
        main_title = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(SELECTORS["main_title"])
        ).text.strip()
        result.append(("title", main_title))
        logging.info(f"Заголовок страницы: {main_title}")
    except Exception as e:
        logging.warning(f"Ошибка при парсинге заголовка: {e}")

    # Извлечение содержимого
    try:
        content_desc = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(SELECTORS["content_desc"])
        )
        content_elements = content_desc.find_elements(By.XPATH, "./*")
        content_blocks = []

        for elem in content_elements:
            if elem.tag_name == "p":
                text = elem.text.strip()
                if not text:
                    continue
                if elem.find_elements(By.TAG_NAME, "strong") and elem.find_elements(By.TAG_NAME, "u"):
                    content_blocks.append(f"### {text}")
                elif elem.find_elements(By.TAG_NAME, "strong"):
                    content_blocks.append(f"**{text}**")
                else:
                    content_blocks.append(text)

            elif elem.tag_name == "div" and "table" in elem.get_attribute("class"):
                try:
                    rows = elem.find_elements(*SELECTORS["table_rows"])
                    table_content = ["Условия доступной среды\tНаличие"]
                    for row in rows:
                        try:
                            row_title = row.find_element(*SELECTORS["row_title"]).text.strip()
                            row_data = row.find_element(*SELECTORS["row_data"]).text.strip()
                            if row_title and row_data:
                                table_content.append(f"{row_title}\t{row_data}")
                            logging.info(f"Строка таблицы: {row_title} - {row_data}")
                        except Exception as e:
                            logging.warning(f"Ошибка при парсинге строки таблицы: {e}")
                    content_blocks.append("\n".join(table_content))
                except Exception as e:
                    logging.warning(f"Ошибка при парсинге таблицы: {e}")

            elif elem.tag_name == "ol":
                try:
                    items = elem.find_elements(By.TAG_NAME, "li")
                    list_items = [f"{idx + 1}. {item.text.strip()}" for idx, item in enumerate(items) if item.text.strip()]
                    if list_items:
                        content_blocks.append("\n".join(list_items))
                except Exception as e:
                    logging.warning(f"Ошибка при парсинге упорядоченного списка: {e}")

            elif elem.tag_name == "ul":
                try:
                    items = elem.find_elements(By.TAG_NAME, "li")
                    list_items = [f"• {item.text.strip()}" for item in items if item.text.strip()]
                    if list_items:
                        content_blocks.append("\n".join(list_items))
                except Exception as e:
                    logging.warning(f"Ошибка при парсинге неупорядоченного списка: {e}")

        if content_blocks:
            result.append(("content", content_blocks))
            logging.info(f"Содержимое: {content_blocks}")
    except Exception as e:
        logging.warning(f"Ошибка при парсинге содержимого: {e}")

    logging.info(f"Итоговые данные: {result}")
    return result, url, metadata

def save_to_markdown(data, url, metadata, filename="DPO_materialno-tehnicheskoe-obespechenie-i-osnashhennost-obrazovatelnogo-protsessa-dostupnaya-sreda.md"):
    """Сохраняет данные в Markdown-файл."""
    try:
        save_path = Path(r"D:\python_work\dpo\dpo") / filename
        content = []

        # Формируем YAML-метаданные
        yaml_metadata = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
        content.append(f"---\n{yaml_metadata}---")

        # Добавление заголовка и ссылки
        for item in data:
            if item[0] == "title":
                content.append(f"# {item[1]}\n[Перейти к странице]({url})")
                break
        else:
            content.append(f"# Материально-техническое обеспечение\n[Перейти к странице]({url})")

        # Добавление содержимого
        for item in data:
            if item[0] == "content":
                content.extend(item[1])

        # Объединяем с одним переносом строки
        final_content = "\n".join(line for line in content if line.strip())

        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        logging.info(f"Контент записан в файл: {save_path}")
        return save_path
    except Exception as e:
        logging.error(f"Ошибка при сохранении файла {filename}: {e}")
        return None

if __name__ == "__main__":
    TARGET_URL = "https://academydpo.org/materialno-tehnicheskoe-obespechenie-i-osnashhennost-obrazovatelnogo-protsessa-dostupnaya-sreda"
    logging.info("Запуск скрипта PDO_materialno_tehnicheskoe_obespechenie_i_osnashhennost_obrazovatelnogo_protsessa_dostupnaya_sreda.py")
    driver = get_driver()
    if driver is None:
        logging.error("Не удалось создать веб-драйвер. Завершение работы.")
        sys.exit(1)
    try:
        parsed_data, page_url, metadata = parse_page(driver, TARGET_URL)
        output_file = save_to_markdown(parsed_data, page_url, metadata)
        if output_file:
            logging.info(f"Файл {output_file} успешно сохранен!")
        else:
            logging.error("Файл не сохранен из-за ошибки")
            sys.exit(1)
    except Exception as e:
        logging.error(f"Критическая ошибка при обработке: {e}")
        sys.exit(1)
    finally:
        driver.quit()
        logging.info("Веб-драйвер закрыт")