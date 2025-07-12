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

# Словарь с CSS-селекторами для извлечения данных
SELECTORS = {
    "main_title": (By.CSS_SELECTOR, "h1.page__content-title"),
    "meta_title": (By.TAG_NAME, "title"),
    "meta_description": (By.XPATH, "//meta[@name='description']"),
    "content_paragraphs": (By.CSS_SELECTOR, "div.page__content-desc p")
}

# Функция для настройки и получения веб-драйвера Chrome
def get_driver():
    # Настройка опций для браузера Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Запуск браузера в фоновом режиме (без GUI)
    chrome_options.add_argument("--disable-gpu")  # Отключение GPU для стабильности
    chrome_options.add_argument("--no-sandbox")  # Отключение песочницы для совместимости
    chrome_options.add_argument("--window-size=1920,1080")  # Установка размера окна браузера
    # Инициализация драйвера Chrome
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
            content_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(SELECTORS["content_paragraphs"])
            )
            intro_text = " ".join([elem.text.strip() for elem in content_elements if elem.text.strip()])
            metadata["description"] = re.sub(r'[#*\[\]]', '', intro_text)[:160].strip() + "..."
        except:
            metadata["description"] = "Описание отсутствует"

    metadata["url"] = url
    metadata["date"] = datetime.now().strftime("%Y-%m-%d")
    metadata["categories"] = ["Финансово-хозяйственная деятельность", "Образование"]
    metadata["tags"] = ["ДПО", "финансы", "дистанционное обучение"]

    return metadata

# Функция для парсинга страницы
def parse_page(driver, url):
    # Загрузка страницы по указанному URL
    driver.get(url)
    try:
        # Ожидание загрузки основного заголовка (15 секунд)
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

    # Извлечение параграфов контента
    try:
        content_elements = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(SELECTORS["content_paragraphs"])
        )
        content_text = [elem.text.strip() for elem in content_elements if elem.text.strip()]
        if content_text:
            result.append(("content", content_text))
            print(f"Параграфы контента: {content_text}")
    except Exception as e:
        print(f"Ошибка при парсинге контента: {str(e)}")

    print(f"Итоговые данные: {result}")
    return result, url, metadata

# Функция для сохранения данных в Markdown-файл
def save_to_markdown(data, url, metadata, filename="DPO_finhozdeyat.md"):
    content = []

    # Формируем YAML-метаданные
    yaml_metadata = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
    content.append(f"---\n{yaml_metadata}---")

    for item in data:
        if item[0] == "title":
            # Добавление заголовка в формате Markdown и ссылки на страницу
            content.append(f"# {item[1]}")
            content.append(f"[Перейти к странице]({url})")
        elif item[0] == "content":
            # Добавление параграфов контента
            content.extend([line for line in item[1] if line.strip()])

    # Объединяем с одним переносом строки
    final_content = "\n".join(line for line in content if line.strip())

    # Сохранение в файл с кодировкой UTF-8
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"Контент записан в файл: {filename}")
    return filename

# Основной блок программы
if __name__ == "__main__":
    # URL страницы для парсинга
    TARGET_URL = "https://academydpo.org/finansovo-hozyajstvennaya-deyatelnost"

    # Инициализация драйвера
    driver = get_driver()
    try:
        # Парсинг страницы и получение данных
        parsed_data, page_url, metadata = parse_page(driver, TARGET_URL)
        # Сохранение данных в Markdown-файл
        output_file = save_to_markdown(parsed_data, page_url, metadata)
        print(f"Файл {output_file} успешно сохранен!")
    except Exception as e:
        print(f"Ошибка при парсинге: {str(e)}")
    finally:
        # Закрытие драйвера для освобождения ресурсов
        driver.quit()