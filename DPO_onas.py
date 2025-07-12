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
    "intro_paragraph": (By.XPATH, "//div[contains(@class, 'page__content-desc')]/p[1]"),
    "school_programs": (By.XPATH, "//div[contains(@class, 'wp-block-group-is-layout-flow')]//p[not(contains(text(), 'Академия также оказывает широкий спектр консалтинговых услуг'))]"),
    "consulting": {
        "title": (By.XPATH, "//h2[contains(., 'Консалтинговые услуги')]"),
        "content": (By.XPATH, "//h2[contains(., 'Консалтинговые услуги')]/following-sibling::*[self::p or self::ul/li][preceding-sibling::h2[1][contains(., 'Консалтинговые услуги')]][not(following-sibling::h2)] | //h2[contains(., 'Консалтинговые услуги')]/following-sibling::*[self::p or self::ul/li][following-sibling::h2[1][contains(., 'Виды обучения')]]")
    },
    "education_types": {
        "title": (By.XPATH, "//h2[contains(., 'Виды обучения')]"),
        "content": (By.XPATH, "//h2[contains(., 'Виды обучения')]/following-sibling::*[self::p or self::ul/li][preceding-sibling::h2[1][contains(., 'Виды обучения')]][not(following-sibling::h2)] | //h2[contains(., 'Виды обучения')]/following-sibling::*[self::p or self::ul/li][following-sibling::h2[1][contains(., 'Курсы профессиональной переподготовки в Академии ДПО')]]")
    },
    "retraining": {
        "title": (By.XPATH, "//h2[contains(., 'Курсы профессиональной переподготовки в Академии ДПО')]"),
        "content": (By.XPATH, "//h2[contains(., 'Курсы профессиональной переподготовки в Академии ДПО')]/following-sibling::*[self::p or self::ul/li][preceding-sibling::h2[1][contains(., 'Курсы профессиональной переподготовки в Академии ДПО')]][not(following-sibling::h2)] | //h2[contains(., 'Курсы профессиональной переподготовки в Академии ДПО')]/following-sibling::*[self::p or self::ul/li][following-sibling::h2[1][contains(., 'Курсы повышения квалификации в Академии ДПО')]]")
    },
    "qualification": {
        "title": (By.XPATH, "//h2[contains(., 'Курсы повышения квалификации в Академии ДПО')]"),
        "content": (By.XPATH, "//h2[contains(., 'Курсы повышения квалификации в Академии ДПО')]/following-sibling::*[self::p or self::ul/li][preceding-sibling::h2[1][contains(., 'Курсы повышения квалификации в Академии ДПО')]][not(following-sibling::h2)] | //h2[contains(., 'Курсы повышения квалификации в Академии ДПО')]/following-sibling::*[self::p or self::ul/li][following-sibling::h2[1][contains(., 'Стоимость курсов')]]")
    },
    "pricing": {
        "title": (By.XPATH, "//h2[contains(., 'Стоимость курсов')]"),
        "content": (By.XPATH, "//h2[contains(., 'Стоимость курсов')]/following-sibling::*[self::p or self::ul/li][preceding-sibling::h2[1][contains(., 'Стоимость курсов')]][not(following-sibling::h2)]")
    },
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
        "categories": ["О нас", "Образование"],
        "tags": ["ДПО", "консалтинговые услуги", "виды обучения", "профессиональная переподготовка", "повышение квалификации"]
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
            metadata["description"] = re.sub(r'[#*\[\]]', '', first_paragraph)[:160].strip() + "..."
        except:
            metadata["description"] = "Описание отсутствует"

    return metadata

def parse_section(driver, title_locator, content_locator):
    """Парсит одну секцию."""
    content = []
    try:
        # Извлечение заголовка секции
        try:
            title = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(title_locator)
            ).text.strip()
            logging.info(f"Найден заголовок секции: {title}")
        except Exception as e:
            logging.warning(f"Не удалось найти заголовок секции {title_locator}: {e}")
            return None

        # Извлечение контента секции (параграфы и списки)
        try:
            elements = WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located(content_locator)
            )
            seen_texts = set()  # Для предотвращения дублирования текста
            for element in elements:
                element_text = element.get_attribute('innerText').strip()
                if element_text and element_text not in seen_texts:
                    if element.tag_name == "li":
                        content.append(f"• {element_text}")
                    else:
                        content.append(element_text)
                    seen_texts.add(element_text)
            logging.info(f"Найден контент для секции '{title}': {content}")
        except Exception as e:
            logging.warning(f"Не удалось найти контент для секции '{title}': {e}")

        return {"title": title, "content": content}
    except Exception as e:
        logging.warning(f"Общая ошибка в секции {title_locator}: {e}")
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

    # Извлечение программ для школьников
    try:
        school_elements = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(SELECTORS["school_programs"])
        )
        school_text = [p.text.strip() for p in school_elements if p.text.strip()]
        if school_text:
            result.append(("content", school_text))
            logging.info(f"Программы для школьников: {school_text}")
    except Exception as e:
        logging.warning(f"Ошибка при парсинге программ для школьников: {e}")

    # Парсинг секции "Консалтинговые услуги"
    consulting = parse_section(driver, SELECTORS["consulting"]["title"], SELECTORS["consulting"]["content"])
    if consulting:
        result.append(("section", consulting))

    # Парсинг секции "Виды обучения"
    education_types = parse_section(driver, SELECTORS["education_types"]["title"], SELECTORS["education_types"]["content"])
    if education_types:
        result.append(("section", education_types))

    # Парсинг секции "Курсы профессиональной переподготовки"
    retraining = parse_section(driver, SELECTORS["retraining"]["title"], SELECTORS["retraining"]["content"])
    if retraining:
        result.append(("section", retraining))

    # Парсинг секции "Курсы повышения квалификации"
    qualification = parse_section(driver, SELECTORS["qualification"]["title"], SELECTORS["qualification"]["content"])
    if qualification:
        result.append(("section", qualification))

    # Парсинг секции "Стоимость курсов"
    pricing = parse_section(driver, SELECTORS["pricing"]["title"], SELECTORS["pricing"]["content"])
    if pricing:
        result.append(("section", pricing))

    logging.info(f"Парсинг завершен. Получено {len(result)} элементов контента")
    return result, url, metadata

def save_to_markdown(data, url, metadata, filename="DPO_onas.md"):
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
            elif item[0] == "content":
                content.extend(item[1])  # Убрано добавление заголовка "## Описание"
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
    TARGET_URL = "https://academydpo.org/o-nas"
    logging.info("Запуск скрипта DPO_onas.py")
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