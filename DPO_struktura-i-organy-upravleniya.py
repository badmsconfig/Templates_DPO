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

# Словарь селекторов
SELECTORS = {
    "main_title": (By.CSS_SELECTOR, "h1.page__content-title"),
    "structure_table": (By.CSS_SELECTOR, "div.page__content-desc > div.table > table > tbody > tr"),
    "meta_title": (By.TAG_NAME, "title"),
    "meta_description": (By.XPATH, "//meta[@name='description']"),
    "intro_paragraphs": (By.XPATH, "//div[contains(@class, 'page__content-desc')]//p[not(preceding-sibling::h2) and not(preceding-sibling::h3)]")
}

# Функция для настройки и получения веб-драйвера Chrome
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

# Функция для нормализации текста
def normalize_text(text):
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\s*,\s*', ', ', text)
    return text if text else None

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
            intro_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(SELECTORS["intro_paragraphs"])
            )
            intro_text = " ".join([elem.text.strip() for elem in intro_elements if elem.text.strip()])
            metadata["description"] = re.sub(r'[#*\[\]]', '', intro_text)[:160].strip() + "..."
        except:
            metadata["description"] = "Описание отсутствует"

    metadata["url"] = url
    metadata["date"] = datetime.now().strftime("%Y-%m-%d")
    metadata["categories"] = ["Образование", "Управление"]
    metadata["tags"] = ["ДПО", "структура", "органы управления"]

    return metadata

# Функция для парсинга таблицы
def parse_table(driver, table_locator):
    try:
        rows = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(table_locator)
        )
        table_data = []
        for row in rows:
            cells = row.find_elements(By.CSS_SELECTOR, "td")
            row_data = []
            for cell in cells:
                paragraphs = cell.find_elements(By.CSS_SELECTOR, "p")
                cell_text = "\n".join(p.text.strip() for p in paragraphs if p.text.strip())
                cell_text = normalize_text(cell_text) or "—"
                row_data.append(cell_text)
            if any(cell != "—" for cell in row_data):  # Пропускаем строки, где все ячейки пустые
                table_data.append(" | ".join(row_data))
        return table_data
    except Exception as e:
        print(f"Ошибка при парсинге таблицы: {str(e)}")
        return []

# Функция для парсинга страницы
def parse_page(driver, url):
    driver.get(url)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["main_title"])
        )
    except Exception as e:
        print(f"Ошибка загрузки страницы: {str(e)}")
        return [], url, {}

    metadata = extract_metadata(driver, url)
    result = []

    # Извлечение основного заголовка
    try:
        main_title = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["main_title"])
        ).text.strip()
        result.append(("title", main_title))
        print(f"Основной заголовок: {main_title}")
    except Exception as e:
        print(f"Ошибка при парсинге заголовка: {str(e)}")

    # Извлечение таблицы структуры и органов управления
    try:
        structure_table = parse_table(driver, SELECTORS["structure_table"])
        if structure_table:
            result.append(("table", {"title": "Структура и органы управления", "content": structure_table}))
            print(f"Таблица структуры и органов управления: {structure_table}")
    except Exception as e:
        print(f"Ошибка при парсинге таблицы: {str(e)}")

    return result, url, metadata

# Функция для сохранения данных в Markdown-файл
def save_to_markdown(data, url, metadata, filename="DPO_struktura-i-organy-upravleniya.md"):
    content = []

    # Формируем YAML-метаданные
    yaml_metadata = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
    content.append(f"---\n{yaml_metadata}---")

    for item in data:
        if item[0] == "title":
            content.append(f"# {item[1]}")
            content.append(f"[Перейти к странице]({url})")
        elif item[0] == "table":
            content.append(f"## {item[1]['title']}")
            content.extend(item[1]["content"])

    # Фильтрация пустых строк и объединение с одним переносом строки
    final_content = "\n".join(line for line in content if line.strip())

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(final_content)
    print(f"Контент записан в файл: {filename}")
    return filename

# Основной блок программы
if __name__ == "__main__":
    TARGET_URL = "https://academydpo.org/struktura-i-organy-upravleniya"
    driver = get_driver()
    try:
        parsed_data, page_url, metadata = parse_page(driver, TARGET_URL)
        output_file = save_to_markdown(parsed_data, page_url, metadata)
        print(f"Файл {output_file} успешно сохранен!")
    except Exception as e:
        print(f"Ошибка при парсинге: {str(e)}")
    finally:
        driver.quit()