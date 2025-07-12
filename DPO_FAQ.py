# Импорт необходимых библиотек
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from pathlib import Path
import yaml
from datetime import datetime
import re

# Словарь с CSS/XPath-селекторами для извлечения данных со страницы
SELECTORS = {
    "main_title": (By.CSS_SELECTOR, "h1.page__content-title"),
    "meta_title": (By.TAG_NAME, "title"),
    "meta_description": (By.XPATH, "//meta[@name='description']"),
    "section_titles": (By.CSS_SELECTOR, "h2.page_faq__item-title"),
    "section_content": (By.XPATH, "./following-sibling::div[contains(@class, 'page_faq__item-desc')][1]//*[self::p or self::li]")
}

# Функция для настройки и получения веб-драйвера Chrome
def get_driver():
    # Настройка опций для браузера Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Запуск браузера в фоновом режиме (без GUI)
    chrome_options.add_argument("--disable-gpu")  # Отключение GPU для стабильности в headless-режиме
    chrome_options.add_argument("--no-sandbox")  # Отключение песочницы для совместимости
    chrome_options.add_argument("--window-size=1920,1080")  # Установка размера окна браузера
    # Инициализация драйвера Chrome с заданными опциями
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
            section_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(SELECTORS["section_content"])
            )
            intro_text = " ".join([elem.text.strip() for elem in section_elements if elem.text.strip()])
            metadata["description"] = re.sub(r'[#*\[\]]', '', intro_text)[:160].strip() + "..."
        except:
            metadata["description"] = "Описание отсутствует"

    metadata["url"] = url
    metadata["date"] = datetime.now().strftime("%Y-%m-%d")
    metadata["categories"] = ["FAQ", "Образование"]
    metadata["tags"] = ["ДПО", "вопросы и ответы", "дистанционное обучение"]

    return metadata

# Функция для парсинга одной секции страницы
def parse_section(driver, section_element):
    content = []
    try:
        # Извлечение текста заголовка секции
        title = section_element.text.strip()
        # Удаление текста вложенного элемента toggle, если он присутствует
        toggle_div = section_element.find_elements(By.CSS_SELECTOR, "div.page_faq__item-toggle")
        if toggle_div:
            toggle_text = toggle_div[0].text.strip()
            title = title.replace(toggle_text, "").strip()
        print(f"Найден заголовок секции: {title}")

        # Извлечение контента секции (параграфы <p> и элементы списка <li>)
        content_elements = section_element.find_elements(*SELECTORS["section_content"])
        for element in content_elements:
            element_text = element.get_attribute('innerText').strip()
            if element_text:
                # Добавление символа • для элементов списка
                if element.tag_name == "li":
                    content.append(f"• {element_text}")
                else:
                    content.append(element_text)
        print(f"Найден контент для секции '{title}': {content}")

        # Возвращаем словарь с заголовком и контентом секции
        return {"title": title, "content": content}
    except Exception as e:
        print(f"Ошибка при парсинге секции: {str(e)}")
        return None

# Функция для парсинга всей страницы
def parse_page(driver, url):
    # Загрузка страницы по указанному URL
    driver.get(url)
    try:
        # Ожидание загрузки основного заголовка (максимум 15 секунд)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["main_title"])
        )
    except Exception as e:
        print(f"Ошибка загрузки страницы: {str(e)}")
        return [], url, {}

    metadata = extract_metadata(driver, url)
    result = []

    # Извлечение основного заголовка страницы
    try:
        main_title = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["main_title"])
        ).text.strip()
        result.append(("title", main_title))
        print(f"Основной заголовок: {main_title}")
    except Exception as e:
        print(f"Ошибка при парсинге основного заголовка: {str(e)}")

    # Парсинг всех секций страницы
    try:
        section_elements = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(SELECTORS["section_titles"])
        )
        for section_element in section_elements:
            section = parse_section(driver, section_element)
            if section:
                result.append(("section", section))
    except Exception as e:
        print(f"Ошибка при парсинге секций: {str(e)}")

    print(f"Итоговые данные: {result}")
    return result, url, metadata

# Функция для сохранения данных в Markdown-файл
def save_to_markdown(data, url, metadata, filename="DPO_FAQ.md"):
    content = []

    # Формируем YAML-метаданные
    yaml_metadata = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
    content.append(f"---\n{yaml_metadata}---")

    for item in data:
        if item[0] == "title":
            content.append(f"# {item[1]}")
            content.append(f"[Перейти к странице]({url})")
        elif item[0] == "section":
            section = item[1]
            content.append(f"## {section['title']}")
            content.extend([line for line in section['content'] if line.strip()])

    # Объединяем с одним переносом строки
    final_content = "\n".join(line for line in content if line.strip())

    # Сохранение результата в Markdown-файл
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"Контент записан в файл: {filename}")
    return filename

# Основной блок программы
if __name__ == "__main__":
    # URL страницы для парсинга
    TARGET_URL = "https://academydpo.org/faq"

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