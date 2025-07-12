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

# Словарь с CSS/XPath-селекторами для извлечения данных
SELECTORS = {
    "main_title": (By.CSS_SELECTOR, "h1.page__content-title"),
    "section_titles": (By.CSS_SELECTOR, "h2"),
    "section_content": (By.XPATH, "./following-sibling::*[self::p or self::h3][preceding-sibling::h2[1][contains(., '{current_title}')]][following-sibling::h2[1][contains(., '{next_title}')]] | ./following-sibling::*[self::p or self::h3][preceding-sibling::h2[1][contains(., '{current_title}')]][not(following-sibling::h2)]"),
    "meta_title": (By.TAG_NAME, "title"),
    "meta_description": (By.XPATH, "//meta[@name='description']")
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
    metadata = {
        "title": "",
        "description": "",
        "url": url,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "categories": ["Оплата образовательных услуг", "Образование"],
        "tags": ["ДПО", "оплата обучения", "дистанционное обучение"]
    }

    try:
        title_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(SELECTORS["meta_title"])
        )
        metadata["title"] = title_element.get_attribute("innerText").strip()
    except Exception as e:
        logging.warning(f"Ошибка при извлечении заголовка страницы: {e}")
        try:
            main_title = driver.find_element(*SELECTORS["main_title"]).text.strip()
            metadata["title"] = main_title
        except:
            metadata["title"] = "Без названия"

    try:
        desc_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(SELECTORS["meta_description"])
        )
        metadata["description"] = desc_element.get_attribute("content").strip()
    except Exception as e:
        logging.warning(f"Ошибка при извлечении meta description: {e}")
        try:
            first_paragraph = driver.find_element(By.CSS_SELECTOR, "div.page__content-desc > p").text.strip()
            metadata["description"] = re.sub(r'[#*\[\]]', '', first_paragraph)[:160].strip() + "..."
        except:
            metadata["description"] = "Описание отсутствует"

    return metadata

def parse_section(driver, section_element, current_title, next_title=None):
    """Парсит одну секцию."""
    content = []
    try:
        # Извлечение заголовка секции
        title = section_element.text.strip()
        logging.info(f"Найден заголовок секции: {title}")

        # Формирование селектора для контента секции
        if next_title:
            content_selector = (By.XPATH, SELECTORS["section_content"][1].format(current_title=title, next_title=next_title))
        else:
            content_selector = (By.XPATH, SELECTORS["section_content"][1].format(current_title=title, next_title=""))

        # Извлечение контента секции (<p> и <h3> в порядке появления)
        content_elements = section_element.find_elements(*content_selector)
        for element in content_elements:
            element_text = element.get_attribute('innerText').strip()
            if element_text:
                # Если элемент — <h3>, добавляем как подзаголовок
                if element.tag_name == "h3":
                    content.append(f"### {element_text}")
                else:
                    # Разбиваем текст <p> на строки, учитывая <br> и списки с •
                    lines = element_text.replace("\n", " ").split("  ")
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        if "•" in line:
                            # Разбиваем по • для обработки элементов списка
                            sub_lines = line.split("•")
                            for sub_line in sub_lines:
                                sub_line = sub_line.strip()
                                if sub_line:
                                    # Удаляем точку с запятой в конце, если есть
                                    sub_line = sub_line.rstrip(";")
                                    content.append(f"• {sub_line}")
                        else:
                            content.append(line)
        logging.info(f"Найден контент для секции '{title}': {content}")
        return {"title": title, "content": content}
    except Exception as e:
        logging.warning(f"Общая ошибка в секции {title}: {e}")
        return None

def parse_page(driver, url):
    """Парсит страницу и возвращает данные."""
    logging.info(f"Начинаем парсинг страницы: {url}")
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["main_title"])
        )
    except Exception as e:
        logging.error(f"Ошибка загрузки страницы: {e}")
        return [], url, {}

    metadata = extract_metadata(driver, url)
    result = []

    # Извлечение основного заголовка
    try:
        main_title = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["main_title"])
        ).text.strip()
        result.append(("title", main_title))
        logging.info(f"Основной заголовок: {main_title}")
    except Exception as e:
        logging.warning(f"Ошибка при парсинге основного заголовка: {e}")

    # Парсинг секций
    try:
        section_elements = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(SELECTORS["section_titles"])
        )
        section_titles = [elem.text.strip() for elem in section_elements]

        for i, section_element in enumerate(section_elements):
            # Определение следующего заголовка (если есть)
            next_title = section_titles[i + 1] if i + 1 < len(section_titles) else None
            section = parse_section(driver, section_element, section_titles[i], next_title)
            if section:
                result.append(("section", section))
    except Exception as e:
        logging.warning(f"Ошибка при парсинге секций: {e}")

    logging.info(f"Парсинг завершен. Получено {len(result)} элементов контента")
    return result, url, metadata

def save_to_markdown(data, url, metadata, filename="DPO_oplata-obrazovatelnyh-uslug.md"):
    """Сохраняет данные в Markdown-файл."""
    try:
        save_path = Path(r"D:\python_work\dpo\dpo") / filename
        content = []

        # Формируем YAML-метаданные
        yaml_metadata = yaml.dump(metadata, allow_unicode=True, sort_keys=False, width=float("inf"))
        content.append(f"---\n{yaml_metadata}---")

        # Формируем контент в логическом порядке
        for item in data:
            if item[0] == "title":
                content.append(f"# {item[1]}")
                content.append(f"[Перейти к странице]({url})")
            elif item[0] == "section":
                section = item[1]
                content.append(f"## {section['title']}")
                content.extend(section['content'])

        # Объединяем с одним переносом строки
        final_content = "\n".join(line for line in content if line.strip())

        # Создаём директорию, если она не существует
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        logging.info(f"Контент записан в файл: {save_path}")
        return save_path
    except Exception as e:
        logging.error(f"Ошибка при сохранении файла {filename}: {e}")
        return None

# Основной блок программы
if __name__ == "__main__":
    TARGET_URL = "https://academydpo.org/oplata-obrazovatelnyh-uslug"
    logging.info("Запуск скрипта DPO_oplata-obrazovatelnyh-uslug.py")
    driver = get_driver()
    if driver is None:
        logging.error("Не удалось создать веб-драйвер. Завершение работы.")
        sys.exit(1)
    try:
        parsed_data, page_url, metadata = parse_page(driver, TARGET_URL)
        if not parsed_data:
            logging.error("Ошибка: не удалось получить контент со страницы")
            sys.exit(1)
        output_file = save_to_markdown(parsed_data, page_url, metadata)
        if output_file:
            logging.info(f"Файл {output_file} успешно сохранен!")
        else:
            logging.error("Ошибка при сохранении файла")
            sys.exit(1)
    except Exception as e:
        logging.error(f"Критическая ошибка при парсинге: {e}")
        sys.exit(1)
    finally:
        driver.quit()
        logging.info("Веб-драйвер закрыт")