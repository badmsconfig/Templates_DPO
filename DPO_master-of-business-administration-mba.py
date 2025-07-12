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

# Словарь селекторов для страницы MBA
SELECTORS = {
    "main_title": (By.CSS_SELECTOR, "h1.category__title"),
    "meta_title": (By.TAG_NAME, "title"),
    "meta_description": (By.XPATH, "//meta[@name='description']"),
    "features_list": (By.CSS_SELECTOR, "ul"),
    "description_paragraphs": (By.CSS_SELECTOR, "div.category__info-body > p"),
    "course_subtitle": (By.CSS_SELECTOR, "h2.category__title"),
    "course_details_titles": (By.CSS_SELECTOR, "h3.category_info__item-title"),
    "course_details_paragraphs": (By.CSS_SELECTOR, "div.category_info__item-desc > p"),
    "faq_title": (By.CSS_SELECTOR, "div.faq_block_title"),
    "faq_text": (By.CSS_SELECTOR, "div.faq_block_text")
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
            paragraphs = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(SELECTORS["description_paragraphs"])
            )
            intro_text = " ".join([p.text.strip() for p in paragraphs if p.text.strip()])
            metadata["description"] = re.sub(r'[#*\[\]]', '', intro_text)[:160].strip() + "..."
        except:
            metadata["description"] = "Описание отсутствует"

    metadata["url"] = url
    metadata["date"] = datetime.now().strftime("%Y-%m-%d")
    metadata["categories"] = ["MBA", "Образование"]
    metadata["tags"] = ["ДПО", "MBA", "дистанционное обучение"]

    return metadata

# Функция для парсинга страницы
def parse_page(driver, url):
    driver.get(url)
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(SELECTORS["main_title"])
        )
    except Exception as e:
        print(f"Ошибка загрузки страницы: {str(e)}")
        return [], url, {}

    metadata = extract_metadata(driver, url)
    result = []

    # Извлечение основного заголовка
    try:
        main_title = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(SELECTORS["main_title"])
        ).text.strip()
        result.append(("title", main_title))
        print(f"Основной заголовок: {main_title}")
    except Exception as e:
        print(f"Ошибка при парсинге заголовка: {str(e)}")

    # Извлечение списка особенностей
    try:
        features = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located(SELECTORS["features_list"])
        )
        feature_texts = []
        for ul in features:
            li_elements = ul.find_elements(By.TAG_NAME, "li")
            feature_texts.extend([f"• {li.text.strip()}" for li in li_elements if li.text.strip()])
        if feature_texts:
            result.append(("features", feature_texts))
            print(f"Особенности: {feature_texts}")
        else:
            print("Список особенностей пуст или не найден")
    except Exception as e:
        print(f"Ошибка при парсинге списка особенностей: {str(e)}")

    # Извлечение параграфов описания
    try:
        paragraphs = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located(SELECTORS["description_paragraphs"])
        )
        paragraph_texts = [p.text.strip() for p in paragraphs if p.text.strip()]
        if paragraph_texts:
            result.append(("description", paragraph_texts))
            print(f"Параграфы описания: {paragraph_texts}")
        else:
            print("Параграфы описания пусты или не найдены")
    except Exception as e:
        print(f"Ошибка при парсинге параграфов: {str(e)}")

    # Извлечение подзаголовка курса
    try:
        course_subtitle = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(SELECTORS["course_subtitle"])
        ).text.strip()
        result.append(("course_subtitle", course_subtitle))
        print(f"Подзаголовок курса: {course_subtitle}")
    except Exception as e:
        print(f"Ошибка при парсинге подзаголовка курса: {str(e)}")

    # Извлечение заголовков и текста деталей курса
    try:
        detail_titles = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located(SELECTORS["course_details_titles"])
        )
        detail_paragraphs = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located(SELECTORS["course_details_paragraphs"])
        )
        detail_texts = []
        for title, paragraph in zip(detail_titles, detail_paragraphs):
            title_text = title.text.strip()
            paragraph_text = paragraph.text.strip()
            if title_text != "Объем программы":  # Исключаем пункт "Объем программы"
                detail_texts.append((title_text, paragraph_text))
        if detail_texts:
            result.append(("course_details", detail_texts))
            print(f"Детали курса: {detail_texts}")
        else:
            print("Детали курса пусты или не найдены")
    except Exception as e:
        print(f"Ошибка при парсинге деталей курса: {str(e)}")

    # Извлечение FAQ
    try:
        faq_title = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(SELECTORS["faq_title"])
        ).text.strip()
        faq_text = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(SELECTORS["faq_text"])
        ).text.strip()
        faq_combined = [f"• {faq_title}:\n{faq_text}"]
        result.append(("faq", faq_combined))
        print(f"FAQ: {faq_combined}")
    except Exception as e:
        print(f"Ошибка при парсинге FAQ: {str(e)}")

    return result, url, metadata

# Функция для сохранения данных в Markdown-файл
def save_to_markdown(data, url, metadata, filename="DPO_master-of-business-administration-mba.md"):
    content = []

    # Формируем YAML-метаданные
    yaml_metadata = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
    content.append(f"---\n{yaml_metadata}---")

    for item in data:
        if item[0] == "title":
            content.append(f"# {item[1]}")
            content.append(f"[Перейти к странице]({url})")
        elif item[0] == "features":
            content.append("## Особенности")
            content.extend(item[1])
        elif item[0] == "description":
            content.append("## Описание")
            content.extend(item[1])
        elif item[0] == "course_subtitle":
            content.append(f"## {item[1]}")
        elif item[0] == "course_details":
            content.append("## Детали курса")
            for title, text in item[1]:
                content.append(f"### {title}\n{text}")
        elif item[0] == "faq":
            content.append("## FAQ")
            content.extend(item[1])

    # Объединяем с одним переносом строки
    final_content = "\n".join(line for line in content if line.strip())

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(final_content)
    print(f"Контент записан в файл: {filename}")
    return filename

# Основной блок программы
if __name__ == "__main__":
    TARGET_URL = "https://academydpo.org/master-of-business-administration-mba"
    driver = get_driver()
    try:
        parsed_data, page_url, metadata = parse_page(driver, TARGET_URL)
        output_file = save_to_markdown(parsed_data, page_url, metadata)
        print(f"Файл {output_file} успешно сохранен!")
    except Exception as e:
        print(f"Ошибка при парсинге: {str(e)}")
    finally:
        driver.quit()