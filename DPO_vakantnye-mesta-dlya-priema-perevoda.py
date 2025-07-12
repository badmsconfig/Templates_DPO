# Импорт необходимых библиотек
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from pathlib import Path
import yaml
from datetime import datetime

# Функция для настройки и получения веб-драйвера Chrome
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

# Словарь с CSS/XPath-селекторами для извлечения данных
SELECTORS = {
    "main_title": (By.CSS_SELECTOR, "h1.page__content-title"),
    "intro_paragraphs": (By.XPATH, "//div[contains(@class, 'page__content-desc')]//p[not(preceding-sibling::h2) and not(preceding-sibling::h3)]"),
    "sub_titles": (By.CSS_SELECTOR, "div.page__content-desc h2, div.page__content-desc h3"),
    "list_items": (By.XPATH, "./li"),
    "meta_title": (By.TAG_NAME, "title"),
    "meta_description": (By.XPATH, "//meta[@name='description']")
}

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
    metadata["categories"] = ["Образование", "Прием и перевод"]
    metadata["tags"] = ["ДПО", "вакантные места", "прием", "перевод"]

    return metadata

# Функция для парсинга одной секции
def parse_section(driver, sub_title_element):
    content = []
    try:
        title = sub_title_element.text.strip()
        tag = sub_title_element.tag_name
        print(f"Найден подзаголовок ({tag}): {title}")

        next_elements = sub_title_element.find_elements(By.XPATH, "./following-sibling::*")
        for element in next_elements:
            if element.tag_name in ["h2", "h3"]:
                break
            if element.tag_name == "p":
                element_text = normalize_text(element.get_attribute('innerText'))
                if element_text:
                    content.append(element_text)
            elif element.tag_name == "ul":
                list_items = element.find_elements(*SELECTORS["list_items"])
                for item in list_items:
                    item_text = normalize_text(item.get_attribute('innerText'))
                    if item_text:
                        content.append(f"• {item_text}")
        print(f"Найден контент для секции '{title}': {content}")
        return {"title": title, "tag": tag, "content": content} if content else None
    except Exception as e:
        print(f"Ошибка в секции '{title}': {str(e)}")
        return None

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

    try:
        main_title = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["main_title"])
        ).text.strip()
        result.append(("title", main_title))
        print(f"Основной заголовок: {main_title}")
    except Exception as e:
        print(f"Ошибка при парсинге основного заголовка: {str(e)}")

    try:
        intro_elements = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(SELECTORS["intro_paragraphs"])
        )
        intro_text = [normalize_text(elem.text) for elem in intro_elements if elem.text.strip()]
        intro_text = [text for text in intro_text if text]  # Удаление None
        if intro_text:
            result.append(("content", intro_text))
            print(f"Вводные параграфы: {intro_text}")
        else:
            print("Вводные параграфы не найдены.")
    except Exception as e:
        print(f"Ошибка при парсинге вводных параграфов: {str(e)}")

    try:
        sub_title_elements = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(SELECTORS["sub_titles"])
        )
        for sub_title_element in sub_title_elements:
            section = parse_section(driver, sub_title_element)
            if section:
                result.append(("section", section))
    except Exception as e:
        print(f"Ошибка при парсинге подзаголовков: {str(e)}")

    print(f"Итоговые данные: {result}")
    return result, url, metadata

# Функция для сохранения данных в Markdown-файл
def save_to_markdown(data, url, metadata, filename="DPO_vakantnye-mesta-dlya-priema-perevoda.md"):
    content = []

    # Формируем YAML-метаданные
    yaml_metadata = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
    content.append(f"---\n{yaml_metadata}---")

    for item in data:
        if item[0] == "title":
            content.append(f"# {item[1]}")
            content.append(f"[Перейти к странице]({url})")
        elif item[0] == "content":
            content.extend(item[1])
        elif item[0] == "section":
            section = item[1]
            if section["tag"] == "h2":
                content.append(f"## {section['title']}")
            else:
                content.append(f"### {section['title']}")
            content.extend(section["content"])

    # Фильтрация пустых строк и объединение с одним переносом строки
    final_content = "\n".join(line for line in content if line.strip())

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"Контент записан в файл: {filename}")
    return filename

# Основной блок программы
if __name__ == "__main__":
    TARGET_URL = "https://academydpo.org/vakantnye-mesta-dlya-priema-perevoda"
    driver = get_driver()
    try:
        parsed_data, page_url, metadata = parse_page(driver, TARGET_URL)
        output_file = save_to_markdown(parsed_data, page_url, metadata)
        print(f"Файл {output_file} успешно сохранен!")
    except Exception as e:
        print(f"Ошибка при парсинге: {str(e)}")
    finally:
        driver.quit()