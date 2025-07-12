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
    "main_title": (By.CSS_SELECTOR, "h1"),
    "intro_paragraph": (By.CSS_SELECTOR, "h1 + p"),
    "advantages_block": (By.CSS_SELECTOR, "div.preim_block > div.item"),
    "partnership_conditions": {
        "title": (By.XPATH, "//h2[contains(text(), 'Сотрудничество на выгодных для вас условиях')]"),
        "content": (By.CSS_SELECTOR, "div.item")
    },
    "partnership_steps": {
        "title": (By.XPATH, "//h2[contains(text(), 'Станьте нашим партнером за 3 простых шага')]"),
        "content": (By.CSS_SELECTOR, "div.name, div.desc")
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
        "categories": ["Сотрудничество", "Образование"],
        "tags": ["ДПО", "партнерство", "образовательные услуги", "бизнес"]
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
        title = WebDriverWait(driver, 40).until(
            EC.visibility_of_element_located(title_locator)
        ).text.strip()
        logging.info(f"Найден заголовок секции '{section_name}': {title}")
    except Exception as e:
        logging.warning(f"Не удалось найти заголовок секции '{section_name}' {title_locator}: {e}")
        return None

    try:
        elements = WebDriverWait(driver, 40).until(
            EC.presence_of_all_elements_located(content_locator)
        )
        logging.info(f"Найдено {len(elements)} элементов в секции '{section_name}'")
        seen_texts = set()
        if section_name == "Сотрудничество на выгодных для вас условиях":
            for element in elements:
                try:
                    name = element.find_element(By.CSS_SELECTOR, "div.name").text.strip().rstrip(',')
                    span = element.find_element(By.CSS_SELECTOR, "span").text.strip()
                    paragraph = element.find_element(By.CSS_SELECTOR, "p").text.strip()
                    bold = element.find_element(By.CSS_SELECTOR, "b").text.strip()
                    price = element.find_element(By.CSS_SELECTOR, "div.price").text.strip()
                    # Объединяем в читаемый текст, удаляя лишние переносы
                    item_text = f"{name}: {span}. {paragraph} {bold} {price}"
                    logging.info(f"Обработан элемент item: {item_text}")
                    if item_text not in seen_texts:
                        content.append(item_text)
                        seen_texts.add(item_text)
                except Exception as e:
                    logging.warning(f"Ошибка при парсинге элемента item в секции '{section_name}': {e}")
                    try:
                        logging.debug(f"HTML элемента: {element.get_attribute('outerHTML')[:200]}...")
                    except:
                        pass
        else:  # Для секции шагов
            step_texts = []
            current_step = None
            for element in elements:
                try:
                    element_text = element.get_attribute('innerText').strip()
                    if element.get_attribute('class') == 'name':
                        if current_step:
                            # Объединяем название и описание шага в читаемый текст
                            content.append(f"{current_step['name']}: {current_step['desc']}")
                        current_step = {"name": element_text, "desc": ""}
                    elif element.get_attribute('class') == 'desc':
                        if current_step:
                            if 'связаться с нами' in element_text:
                                try:
                                    link = element.find_element(By.CSS_SELECTOR, "a")
                                    link_text = link.text.strip()
                                    link_href = link.get_attribute("href")
                                    element_text = element_text.replace(link_text, f"[{link_text}]({link_href})")
                                except Exception as e:
                                    logging.warning(f"Ошибка при обработке ссылки в секции '{section_name}': {e}")
                            current_step["desc"] = element_text
                    if element_text and element_text not in seen_texts:
                        seen_texts.add(element_text)
                except Exception as e:
                    logging.warning(f"Ошибка при парсинге элемента name/desc в секции '{section_name}': {e}")
                    try:
                        logging.debug(f"HTML элемента: {element.get_attribute('outerHTML')[:200]}...")
                    except:
                        pass
            if current_step and current_step["desc"]:
                content.append(f"{current_step['name']}: {current_step['desc']}")
            logging.info(f"Найден контент для секции '{section_name}': {content}")
    except Exception as e:
        logging.warning(f"Не удалось найти контент для секции '{section_name}' {content_locator}: {e}")
        try:
            items = driver.find_elements(By.CSS_SELECTOR, "div.item")
            names_descs = driver.find_elements(By.CSS_SELECTOR, "div.name, div.desc")
            logging.debug(f"Найдено div.item на странице: {len(items)}")
            logging.debug(f"Найдено div.name/desc на странице: {len(names_descs)}")
            if items:
                logging.debug(f"HTML первого div.item: {items[0].get_attribute('outerHTML')[:200]}...")
            if names_descs:
                logging.debug(f"HTML первого div.name/desc: {names_descs[0].get_attribute('outerHTML')[:200]}...")
        except:
            pass
        try:
            body = driver.find_element(By.TAG_NAME, "body").get_attribute('outerHTML')[:500]
            logging.debug(f"HTML страницы (первые 500 символов): {body}...")
        except:
            pass

    return {"title": title, "content": content}

def parse_page(driver, url):
    """Парсит страницу и возвращает данные."""
    logging.info(f"Начинаем парсинг страницы: {url}")
    try:
        driver.get(url)
        WebDriverWait(driver, 40).until(
            EC.visibility_of_element_located(SELECTORS["main_title"])
        )
    except Exception as e:
        logging.error(f"Ошибка загрузки страницы: {e}")
        return [], url, {}

    metadata = extract_metadata(driver, url)
    result = []

    # Извлечение основного заголовка
    try:
        main_title = WebDriverWait(driver, 40).until(
            EC.visibility_of_element_located(SELECTORS["main_title"])
        ).text.strip()
        result.append(("title", main_title))
        logging.info(f"Основной заголовок: {main_title}")
    except Exception as e:
        logging.warning(f"Ошибка при парсинге заголовка: {e}")

    # Извлечение вводного параграфа
    try:
        intro_text = WebDriverWait(driver, 40).until(
            EC.visibility_of_element_located(SELECTORS["intro_paragraph"])
        ).text.strip()
        if intro_text:
            result.append(("content", [intro_text]))
            logging.info(f"Вводный параграф: {intro_text}")
    except Exception as e:
        logging.warning(f"Ошибка при парсинге вводного параграфа: {e}")

    # Извлечение блока преимуществ
    try:
        advantages = WebDriverWait(driver, 40).until(
            EC.visibility_of_all_elements_located(SELECTORS["advantages_block"])
        )
        advantages_texts = []
        for item in advantages:
            name = item.find_element(By.CSS_SELECTOR, "div.name").text.strip().rstrip(',')
            desc = item.find_element(By.CSS_SELECTOR, "div.desc").text.strip()
            advantages_texts.append(f"{name}: {desc}")
        if advantages_texts:
            result.append(("section", {"title": "Преимущества сотрудничества", "content": advantages_texts}))
            logging.info(f"Блок преимуществ: {advantages_texts}")
    except Exception as e:
        logging.warning(f"Ошибка при парсинге блока преимуществ: {e}")

    # Парсинг секции условий сотрудничества
    conditions = parse_section(driver, SELECTORS["partnership_conditions"]["title"],
                            SELECTORS["partnership_conditions"]["content"],
                            "Сотрудничество на выгодных для вас условиях")
    if conditions:
        result.append(("section", conditions))

    # Парсинг секции шагов сотрудничества
    steps = parse_section(driver, SELECTORS["partnership_steps"]["title"],
                        SELECTORS["partnership_steps"]["content"],
                        "Станьте нашим партнером за 3 простых шага")
    if steps:
        result.append(("section", steps))

    logging.info(f"Парсинг завершен. Получено {len(result)} элементов контента")
    return result, url, metadata

def save_to_markdown(data, url, metadata, filename="DPO_sotrudnichestvo.md"):
    """Сохраняет данные в Markdown-файл."""
    try:
        save_path = Path(r"D:\python_work\dpo\dpo") / filename
        content = []

        # Формируем YAML-метаданные
        yaml_metadata = yaml.dump(metadata, allow_unicode=True, sort_keys=False, width=float("inf"))
        content.append(f"---\n{yaml_metadata}---")

        # Обработка элементов для форматирования в Markdown
        for item in data:
            if item[0] == "title":
                content.append(f"# {item[1]}")
                content.append(f"[Перейти к странице]({url})")
            elif item[0] == "content":
                content.extend(item[1])
            elif item[0] == "section":
                section = item[1]
                content.append(f"## {section['title']}")
                for text in section['content']:
                    content.append(f"- {text}")

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
    TARGET_URL = "https://academydpo.org/sotrudnichestvo"
    logging.info("Запуск скрипта DPO_sotrudnichestvo.py")
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