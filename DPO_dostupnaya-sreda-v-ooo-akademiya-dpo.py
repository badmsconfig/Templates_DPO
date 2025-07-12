from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path
import yaml
from datetime import datetime
import re

# Словарь селекторов для страницы https://academydpo.org/dostupnaya-sreda-v-ooo-akademiya-dpo
SELECTORS = {
    "main_title": (By.CSS_SELECTOR, "h1.page__content-title"),
    "meta_title": (By.TAG_NAME, "title"),
    "meta_description": (By.XPATH, "//meta[@name='description']"),
    "table_rows": (By.CSS_SELECTOR, "div.page__content-desc > div.table > table > tbody > tr")
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
            table_rows = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(SELECTORS["table_rows"])
            )
            intro_text = " ".join([row.text.strip() for row in table_rows[1:] if row.text.strip()])
            metadata["description"] = re.sub(r'[#*\[\]]', '', intro_text)[:160].strip() + "..."
        except:
            metadata["description"] = "Описание отсутствует"

    metadata["url"] = url
    metadata["date"] = datetime.now().strftime("%Y-%m-%d")
    metadata["categories"] = ["Доступная среда", "Образование"]
    metadata["tags"] = ["ДПО", "доступная среда", "дистанционное обучение"]

    return metadata

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

    # Извлечение данных таблицы
    try:
        table_rows = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(SELECTORS["table_rows"])
        )
        table_data = []
        for row in table_rows[1:]:  # Пропускаем заголовок таблицы
            cells = row.find_elements(By.CSS_SELECTOR, "td")
            if len(cells) == 2:
                condition = cells[0].text.strip()
                availability = cells[1].text.strip()
                # Разделение текста в ячейке на строки для пунктов (например, для "Специальные условия охраны здоровья")
                availability_lines = availability.split('\n')
                if len(availability_lines) > 1:
                    availability = '\n' + '\n'.join(f"- {line.strip()}" for line in availability_lines if line.strip())
                table_data.append((condition, availability))
        if table_data:
            result.append(("table", table_data))
            print(f"Данные таблицы: {table_data}")
    except Exception as e:
        print(f"Ошибка при парсинге таблицы: {str(e)}")

    return result, url, metadata

# Функция для сохранения данных в Markdown-файл
def save_to_markdown(data, url, metadata, filename="DPO_dostupnaya-sreda-v-ooo-akademiya-dpo.md"):
    content = []

    # Формируем YAML-метаданные
    yaml_metadata = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
    content.append(f"---\n{yaml_metadata}---")

    # Формируем контент в логическом порядке
    for item in data:
        if item[0] == "title":
            content.append(f"# {item[1]}")
            content.append(f"[Перейти к странице]({url})")
        elif item[0] == "table":
            content.append("## Условия доступной среды")
            content.append("| Условия доступной среды | Наличие |")
            content.append("|------------------------|---------|")
            for condition, availability in item[1]:
                # Экранируем символы | в тексте, если они есть
                condition = condition.replace("|", "\\|")
                availability = availability.replace("|", "\\|")
                content.append(f"| {condition} | {availability} |")

    # Объединяем с одним переносом строки
    final_content = "\n".join(line for line in content if line.strip())

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(final_content)
    print(f"Контент записан в файл: {filename}")
    return filename

# Основной блок программы
if __name__ == "__main__":
    TARGET_URL = "https://academydpo.org/dostupnaya-sreda-v-ooo-akademiya-dpo"
    driver = get_driver()
    try:
        parsed_data, page_url, metadata = parse_page(driver, TARGET_URL)
        output_file = save_to_markdown(parsed_data, page_url, metadata)
        print(f"Файл {output_file} успешно сохранен!")
    except Exception as e:
        print(f"Ошибка при парсинге: {str(e)}")
    finally:
        driver.quit()