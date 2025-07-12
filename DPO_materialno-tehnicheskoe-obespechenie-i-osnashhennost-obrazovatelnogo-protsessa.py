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
    "main_title": (By.CSS_SELECTOR, "h1.page__content-title"),
    "meta_title": (By.TAG_NAME, "title"),
    "meta_description": (By.XPATH, "//meta[@name='description']"),
    "content_desc": (By.CSS_SELECTOR, "div.page__content-desc"),
    "ordered_lists": (By.CSS_SELECTOR, "div.page__content-desc ol"),
    "unordered_lists": (By.CSS_SELECTOR, "div.page__content-desc ul")
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
    metadata["categories"] = ["Материально-техническое обеспечение", "Образование"]
    metadata["tags"] = ["ДПО", "материально-техническое обеспечение", "дистанционное обучение"]

    return metadata

# Функция для парсинга страницы
def parse_page(driver, url):
    driver.get(url)
    try:
        # Ожидание загрузки заголовка (15 секунд)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["main_title"])
        )
    except Exception as e:
        print(f"Ошибка загрузки страницы: {str(e)}")
        return [], url, {}

    metadata = extract_metadata(driver, url)
    result = []

    # Извлечение заголовка
    try:
        main_title = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["main_title"])
        ).text.strip()
        result.append(("title", main_title))
        print(f"Заголовок страницы: {main_title}")
    except Exception as e:
        print(f"Ошибка при парсинге заголовка: {str(e)}")

    # Извлечение содержимого div.page__content-desc
    try:
        content_desc = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["content_desc"])
        )
        content_elements = content_desc.find_elements(By.XPATH, "./*")  # Все дочерние элементы
        content_blocks = []

        for elem in content_elements:
            if elem.tag_name == "p":
                text = elem.text.strip()
                if not text:
                    continue
                # Форматирование в зависимости от стиля
                if elem.find_elements(By.TAG_NAME, "strong") and elem.find_elements(By.TAG_NAME, "u"):
                    content_blocks.append(f"### {text}")
                elif elem.find_elements(By.TAG_NAME, "strong"):
                    content_blocks.append(f"**{text}**")
                elif elem.find_elements(By.TAG_NAME, "em"):
                    content_blocks.append(f"*{text}*")
                else:
                    content_blocks.append(text)

            elif elem.tag_name == "ol":
                # Обработка упорядоченного списка
                try:
                    items = elem.find_elements(By.TAG_NAME, "li")
                    list_items = [f"{idx + 1}. {item.text.strip()}" for idx, item in enumerate(items) if item.text.strip()]
                    if list_items:
                        content_blocks.append("\n".join(list_items))
                except Exception as e:
                    print(f"Ошибка при парсинге упорядоченного списка: {str(e)}")

            elif elem.tag_name == "ul":
                # Обработка неупорядоченного списка
                try:
                    items = elem.find_elements(By.TAG_NAME, "li")
                    list_items = [f"• {item.text.strip()}" for item in items if item.text.strip()]
                    if list_items:
                        content_blocks.append("\n".join(list_items))
                except Exception as e:
                    print(f"Ошибка при парсинге неупорядоченного списка: {str(e)}")

        if content_blocks:
            result.append(("content", content_blocks))
            print(f"Содержимое: {content_blocks}")
    except Exception as e:
        print(f"Ошибка при парсинге содержимого: {str(e)}")

    print(f"Итоговые данные: {result}")
    return result, url, metadata

# Функция для сохранения данных в Markdown-файл
def save_to_markdown(data, url, metadata, filename="DPO_materialno-tehnicheskoe-obespechenie-i-osnashhennost-obrazovatelnogo-protsessa.md"):
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

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"Контент записан в файл: {filename}")
    return filename

# Основной блок программы
if __name__ == "__main__":
    TARGET_URL = "https://academydpo.org/materialno-tehnicheskoe-obespechenie-i-osnashhennost-obrazovatelnogo-protsessa"
    driver = get_driver()
    try:
        parsed_data, page_url, metadata = parse_page(driver, TARGET_URL)
        output_file = save_to_markdown(parsed_data, page_url, metadata)
        print(f"Файл {output_file} успешно сохранен!")
    except Exception as e:
        print(f"Ошибка при парсинге: {str(e)}")
    finally:
        driver.quit()