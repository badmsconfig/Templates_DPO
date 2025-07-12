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
    "meta_title": (By.TAG_NAME, "title"),
    "meta_description": (By.XPATH, "//meta[@name='description']"),
    "image_links": (By.CSS_SELECTOR, "a[href*='.jpg']"),
    "document_links": (By.CSS_SELECTOR, "a.file_link")
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
            document_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(SELECTORS["document_links"])
            )
            intro_text = " ".join([elem.text.strip() for elem in document_elements if elem.text.strip()])
            metadata["description"] = re.sub(r'[#*\[\]]', '', intro_text)[:160].strip() + "..."
        except:
            metadata["description"] = "Описание отсутствует"

    metadata["url"] = url
    metadata["date"] = datetime.now().strftime("%Y-%m-%d")
    metadata["categories"] = ["Документы", "Образование"]
    metadata["tags"] = ["ДПО", "документы", "дистанционное обучение"]

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

    # Извлечение ссылок на изображения
    try:
        image_links = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(SELECTORS["image_links"])
        )
        images = []
        for link in image_links:
            img_url = link.get_attribute("href")
            img_alt = link.find_element(By.TAG_NAME, "img").get_attribute("alt")
            images.append(f"[{img_alt}]({img_url})")
        if images:
            result.append(("images", images))
            print(f"Изображения: {images}")
    except Exception as e:
        print(f"Ошибка при парсинге изображений: {str(e)}")

    # Извлечение списка документов
    try:
        document_links = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(SELECTORS["document_links"])
        )
        documents = []
        for link in document_links:
            doc_text = link.text.strip()
            doc_url = link.get_attribute("href")
            documents.append(f"[{doc_text}]({doc_url})")
        if documents:
            result.append(("content", documents))
            print(f"Документы: {documents}")
    except Exception as e:
        print(f"Ошибка при парсинге списка документов: {str(e)}")

    return result, url, metadata

# Функция для сохранения данных в Markdown-файл
def save_to_markdown(data, url, metadata, filename="DPO_dokumenty.md"):
    content = []

    # Формируем YAML-метаданные
    yaml_metadata = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
    content.append(f"---\n{yaml_metadata}---")

    for item in data:
        if item[0] == "title":
            content.append(f"# {item[1]}")
            content.append(f"[Перейти к странице]({url})")
        elif item[0] == "images":
            content.append("## Изображения")
            content.extend([f"- {img}" for img in item[1] if img.strip()])
        elif item[0] == "content":
            content.append("## Список документов")
            content.extend([f"- {doc}" for doc in item[1] if doc.strip()])

    # Объединяем с одним переносом строки
    final_content = "\n".join(line for line in content if line.strip())

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(final_content)
    print(f"Контент записан в файл: {filename}")
    print(f"Абсолютный путь к файлу: {Path(filename).resolve()}")
    return filename

# Основной блок программы
if __name__ == "__main__":
    TARGET_URL = "https://academydpo.org/dokumenty"
    driver = get_driver()
    try:
        parsed_data, page_url, metadata = parse_page(driver, TARGET_URL)
        output_file = save_to_markdown(parsed_data, page_url, metadata)
        print(f"Файл {output_file} успешно сохранен!")
    except Exception as e:
        print(f"Ошибка при парсинге: {str(e)}")
    finally:
        driver.quit()