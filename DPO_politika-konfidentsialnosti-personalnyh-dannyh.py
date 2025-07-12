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

# Настройка кодировки консоли на UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Словарь селекторов
SELECTORS = {
    "main_title": (By.CSS_SELECTOR, "h1.page__content-title"),
    "intro_paragraph": (By.CSS_SELECTOR, "div.page__content-desc > p:first-child"),
    "meta_title": (By.TAG_NAME, "title"),
    "meta_description": (By.XPATH, "//meta[@name='description']"),
    "sections": {
        "terms": {
            "title": (By.XPATH, "//h2[contains(., '1. Определение терминов')]"),
            "content": (By.XPATH, "//h2[contains(., '1. Определение терминов')]/following-sibling::p[preceding-sibling::h2[1][contains(., '1. Определение терминов')]][following-sibling::h2[1][contains(., '2. Общие положения')]]")
        },
        "general_provisions": {
            "title": (By.XPATH, "//h2[contains(., '2. Общие положения')]"),
            "content": (By.XPATH, "//h2[contains(., '2. Общие положения')]/following-sibling::p[preceding-sibling::h2[1][contains(., '2. Общие положения')]][following-sibling::h2[1][contains(., '3. Предмет политики конфиденциальности')]]")
        },
        "subject": {
            "title": (By.XPATH, "//h2[contains(., '3. Предмет политики конфиденциальности')]"),
            "content": (By.XPATH, "//h2[contains(., '3. Предмет политики конфиденциальности')]/following-sibling::p[preceding-sibling::h2[1][contains(., '3. Предмет политики конфиденциальности')]][following-sibling::h2[1][contains(., '4. Цели сбора персональной информации пользователя')]]")
        },
        "purposes": {
            "title": (By.XPATH, "//h2[contains(., '4. Цели сбора персональной информации пользователя')]"),
            "content": (By.XPATH, "//h2[contains(., '4. Цели сбора персональной информации пользователя')]/following-sibling::p[preceding-sibling::h2[1][contains(., '4. Цели сбора персональной информации пользователя')]][following-sibling::h2[1][contains(., '5. Способы и сроки обработки персональной информации')]]")
        },
        "processing_methods": {
            "title": (By.XPATH, "//h2[contains(., '5. Способы и сроки обработки персональной информации')]"),
            "content": (By.XPATH, "//h2[contains(., '5. Способы и сроки обработки персональной информации')]/following-sibling::p[preceding-sibling::h2[1][contains(., '5. Способы и сроки обработки персональной информации')]][following-sibling::h2[1][contains(., '6. Права и обязанности сторон')]]")
        },
        "rights_obligations": {
            "title": (By.XPATH, "//h2[contains(., '6. Права и обязанности сторон')]"),
            "content": (By.XPATH, "//h2[contains(., '6. Права и обязанности сторон')]/following-sibling::p[preceding-sibling::h2[1][contains(., '6. Права и обязанности сторон')]][following-sibling::h2[1][contains(., '7. Ответственность сторон')]]")
        },
        "responsibility": {
            "title": (By.XPATH, "//h2[contains(., '7. Ответственность сторон')]"),
            "content": (By.XPATH, "//h2[contains(., '7. Ответственность сторон')]/following-sibling::p[preceding-sibling::h2[1][contains(., '7. Ответственность сторон')]][following-sibling::h2[1][contains(., '8. Разрешение споров')]]")
        },
        "dispute_resolution": {
            "title": (By.XPATH, "//h2[contains(., '8. Разрешение споров')]"),
            "content": (By.XPATH, "//h2[contains(., '8. Разрешение споров')]/following-sibling::p[preceding-sibling::h2[1][contains(., '8. Разрешение споров')]][following-sibling::h2[1][contains(., '9. Дополнительные условия')]]")
        },
        "additional_conditions": {
            "title": (By.XPATH, "//h2[contains(., '9. Дополнительные условия')]"),
            "content": (By.XPATH, "//h2[contains(., '9. Дополнительные условия')]/following-sibling::p[preceding-sibling::h2[1][contains(., '9. Дополнительные условия')]]")
        }
    },
    "footer_paragraphs": (By.XPATH, "//div[contains(@class, 'page__content-desc')]/p[position() > last()-3 and position() <= last()-1]")
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
        "categories": ["Политика конфиденциальности", "Образование"],
        "tags": ["ДПО", "конфиденциальность", "персональные данные", "политика"]
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
            first_paragraph = driver.find_element(*SELECTORS["intro_paragraph"]).text.strip()
            metadata["description"] = first_paragraph[:160].strip() + "..."
        except:
            metadata["description"] = "Описание отсутствует"

    return metadata

def parse_section(driver, title_locator, content_locator, section_name):
    """Парсит секцию страницы."""
    content = []
    try:
        title = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(title_locator)
        ).text.strip()
        logging.info(f"Найден заголовок секции: {title}")
    except Exception as e:
        logging.warning(f"Не удалось найти заголовок секции {section_name}: {e}")
        return None

    try:
        elements = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(content_locator)
        )
        seen_texts = set()
        for element in elements:
            element_text = element.get_attribute('innerText').strip()
            if element_text and element_text not in seen_texts:
                content.append(element_text)
                seen_texts.add(element_text)
        logging.info(f"Найден контент для секции '{title}': {content}")
    except Exception as e:
        logging.warning(f"Не удалось найти контент для секции '{title}': {e}")

    return {"title": title, "content": content}

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
        logging.warning(f"Ошибка при парсинге заголовка: {e}")

    # Извлечение вводного параграфа
    try:
        intro_text = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["intro_paragraph"])
        ).text.strip()
        if intro_text:
            result.append(("content", [intro_text]))
            logging.info(f"Вводный параграф: {intro_text}")
    except Exception as e:
        logging.warning(f"Ошибка при парсинге вводного параграфа: {e}")

    # Парсинг секций
    for section_key, section_data in SELECTORS["sections"].items():
        section = parse_section(driver, section_data["title"], section_data["content"], section_key)
        if section:
            result.append(("section", section))

    # Извлечение завершающих параграфов
    try:
        footer_paragraphs = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(SELECTORS["footer_paragraphs"])
        )
        footer_texts = [p.text.strip() for p in footer_paragraphs if p.text.strip()]
        if footer_texts:
            result.append(("content", footer_texts))
            logging.info(f"Завершающие параграфы: {footer_texts}")
    except Exception as e:
        logging.warning(f"Ошибка при парсинге завершающих параграфов: {e}")

    logging.info(f"Парсинг завершен. Получено {len(result)} элементов контента")
    return result, url, metadata

def save_to_markdown(data, url, metadata, filename="DPO_politika-konfidentsialnosti-personalnyh-dannyh.md"):
    """Сохраняет данные в Markdown-файл."""
    try:
        save_path = Path(r"D:\python_work\dpo\dpo") / filename
        content = []

        # Формируем YAML-метаданные
        yaml_metadata = yaml.dump(metadata, allow_unicode=True, sort_keys=False, width=float("inf"))
        content.append(f"---\n{yaml_metadata}---")

        # Формируем контент
        for item in data:
            if item[0] == "title":
                content.append(f"# {item[1]}")
                content.append(f"[Перейти к странице]({url})")
            elif item[0] == "content":
                content.extend(item[1])
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
    TARGET_URL = "https://academydpo.org/politika-konfidentsialnosti-personalnyh-dannyh"
    logging.info("Запуск скрипта DPO_politika-konfidentsialnosti-personalnyh-dannyh.py")
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