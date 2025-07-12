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

# Словарь селекторов для страницы
SELECTORS = {
    "main_title": (By.CSS_SELECTOR, "h1.valid_doc__title"),
    "desc_paragraphs": (By.CSS_SELECTOR, "div.valid_doc__desc > p:not(.wp-block-heading ~ p)"),
    "sub_title": (By.CSS_SELECTOR, "h1.wp-block-heading"),
    "registry_paragraphs": (By.CSS_SELECTOR, "div.valid_doc__desc > h1.wp-block-heading ~ p"),
    "list_items": (By.CSS_SELECTOR, "div.valid_doc__desc > ul > li"),
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
        "categories": ["Сервис проверки документов", "Образование"],
        "tags": ["ДПО", "проверка документов", "реестр", "образовательные услуги"]
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
            first_paragraph = driver.find_element(*SELECTORS["desc_paragraphs"]).text.strip()
            metadata["description"] = first_paragraph[:160].strip() + "..."
        except:
            metadata["description"] = "Описание отсутствует"

    return metadata

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

    # Извлечение параграфов описания (до подзаголовка)
    try:
        desc_paragraphs = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(SELECTORS["desc_paragraphs"])
        )
        desc_texts = [p.text.strip() for p in desc_paragraphs if p.text.strip()]
        if desc_texts:
            result.append(("desc_content", desc_texts))
            logging.info(f"Параграфы описания: {desc_texts}")
    except Exception as e:
        logging.warning(f"Ошибка при парсинге параграфов описания: {e}")

    # Извлечение подзаголовка
    try:
        sub_title = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["sub_title"])
        ).text.strip()
        result.append(("sub_title", sub_title))
        logging.info(f"Подзаголовок: {sub_title}")
    except Exception as e:
        logging.warning(f"Ошибка при парсинге подзаголовка: {e}")

    # Извлечение параграфов реестра (после подзаголовка) и списка целей
    try:
        registry_paragraphs = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(SELECTORS["registry_paragraphs"])
        )
        registry_texts = []
        for i, p in enumerate(registry_paragraphs):
            p_text = p.text.strip()
            # Обработка параграфа с целями реестра
            if "Целями создания Федерального реестра являются" in p_text:
                try:
                    ul = p.find_element(By.XPATH, "./following-sibling::ul")
                    li_elements = ul.find_elements(By.CSS_SELECTOR, "li")
                    measures = [li.text.strip() for li in li_elements if li.text.strip()]
                    p_text = f"{p_text}\n" + "\n".join(f"- {m}" for m in measures)
                except:
                    logging.warning("Не удалось найти список целей реестра")
            registry_texts.append(p_text)
        if registry_texts:
            result.append(("registry_content", registry_texts))
            logging.info(f"Параграфы реестра: {registry_texts}")
    except Exception as e:
        logging.warning(f"Ошибка при парсинге параграфов реестра: {e}")

    logging.info(f"Парсинг завершен. Получено {len(result)} элементов контента")
    return result, url, metadata

def save_to_markdown(data, url, metadata, filename="DPO_servis-proverki-dokumentov.md"):
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
            elif item[0] == "desc_content":
                content.extend(item[1])
            elif item[0] == "sub_title":
                content.append(f"## {item[1]}")
            elif item[0] == "registry_content":
                content.extend(item[1])

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
    TARGET_URL = "https://academydpo.org/servis-proverki-dokumentov"
    logging.info("Запуск скрипта DPO_servis-proverki-dokumentov.py")
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