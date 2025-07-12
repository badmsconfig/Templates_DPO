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

SELECTORS = {
    "main_title": (By.CSS_SELECTOR, "h1.page__content-title"),
    "section_titles": (By.CSS_SELECTOR, "h2"),
    "content_paragraphs": (By.CSS_SELECTOR, ".page__content-desc > *"),
    "meta_title": (By.TAG_NAME, "title"),
    "meta_description": (By.XPATH, "//meta[@name='description']"),
}

def extract_metadata(driver, url):
    """Извлекает метаданные страницы."""
    metadata = {
        "title": "",
        "description": "",
        "url": url,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "categories": ["Материально-техническое обеспечение", "Образование"],
        "tags": ["ДПО", "материально-техническое обеспечение", "дистанционное обучение"]
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
            first_paragraph = driver.find_element(By.CSS_SELECTOR, ".page__content-desc p").text.strip()
            metadata["description"] = re.sub(r'[#*\[\]]', '', first_paragraph)[:160].strip() + "..."
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
    content = []

    try:
        main_title = driver.find_element(*SELECTORS["main_title"]).text.strip()
        content.append(("title", main_title))
        logging.info(f"Найден основной заголовок: {main_title}")
    except Exception as e:
        logging.warning(f"Ошибка при парсинге заголовка: {e}")

    try:
        elements = driver.find_elements(*SELECTORS["content_paragraphs"])
        logging.info(f"Найдено {len(elements)} элементов контента")

        for el in elements:
            tag = el.tag_name
            text = el.text.strip()
            if not text:
                continue

            if tag == "h2":
                content.append(("section_title", text))
            elif tag == "ul":
                items = el.find_elements(By.TAG_NAME, "li")
                list_items = [f"• {li.text.strip().rstrip(';')}" for li in items if li.text.strip()]
                if list_items:
                    content.append(("list", "\n".join(list_items)))
            elif tag in ["p", "div"]:
                content.append(("paragraph", text))

    except Exception as e:
        logging.warning(f"Ошибка при парсинге контента: {e}")

    logging.info(f"Парсинг завершен. Получено {len(content)} элементов контента")
    return content, url, metadata

def save_to_markdown(data, url, metadata, filename="DPO_matertehnichobespechenieiosnashhennost.md"):
    """Сохраняет результаты в Markdown-файл с точным форматированием."""
    try:
        save_path = Path(r"D:\python_work\dpo\dpo") / filename
        content_blocks = []

        # Формируем YAML-метаданные
        yaml_metadata = yaml.dump(metadata, allow_unicode=True, sort_keys=False, width=float("inf"))
        content_blocks.append(f"---\n{yaml_metadata}---")

        # Заголовок страницы
        content_blocks.append(f"# {metadata['title']}\n[Перейти к странице]({url})")

        # Обрабатываем основной контент
        current_section = None
        for item_type, item_content in data:
            item_content = item_content.strip()
            if not item_content:
                continue

            if item_type == "title":
                continue  # Уже обработали в заголовке

            elif item_type == "section_title":
                if current_section:
                    content_blocks.append(current_section)
                current_section = {
                    'title': f"## {item_content}",
                    'content': []
                }

            elif item_type == "paragraph":
                if not current_section:
                    current_section = {'title': None, 'content': []}
                if current_section['content'] and current_section['content'][-1].endswith('.'):
                    # Объединяем с предыдущим абзацем
                    current_section['content'][-1] = f"{current_section['content'][-1]} {item_content}"
                else:
                    current_section['content'].append(item_content)

            elif item_type == "list":
                if not current_section:
                    current_section = {'title': None, 'content': []}
                # Убираем лишние переносы в списках
                list_items = [f"• {line.strip('• ')}" for line in item_content.split('\n') if line.strip()]
                current_section['content'].extend(list_items)

        # Добавляем последнюю секцию
        if current_section:
            content_blocks.append(current_section)

        # Формируем итоговый контент
        final_content = []
        for section in content_blocks:
            if isinstance(section, str):
                final_content.append(section)
                continue
            if section['title']:
                final_content.append(section['title'])
            for item in section['content']:
                if item.startswith('•'):
                    final_content.append(item)
                else:
                    final_content.append(item)
            # Добавляем пустую строку после секции, если она не последняя
            if section != content_blocks[-1]:
                final_content.append("")

        # Объединяем с одним переносом строки
        final_content = "\n".join(line for line in final_content if line.strip() or line == "")

        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        logging.info(f"Контент записан в файл: {save_path}")
        return save_path

    except Exception as e:
        logging.error(f"Ошибка при сохранении файла {filename}: {e}")
        return None

if __name__ == "__main__":
    TARGET_URL = "https://academydpo.org/materialno-tehnicheskoe-obespechenie-i-osnashhennost"
    logging.info("Запуск скрипта DPO_matertehnichobespechenieiosnashhennost.py")
    driver = get_driver()
    if driver is None:
        logging.error("Не удалось создать веб-драйвер. Завершение работы.")
        sys.exit(1)
    try:
        parsed_content, page_url, metadata = parse_page(driver, TARGET_URL)
        if not parsed_content:
            logging.error("Ошибка: не удалось получить контент со страницы")
            sys.exit(1)
        output_file = save_to_markdown(parsed_content, page_url, metadata)
        if output_file:
            logging.info(f"Парсинг завершен успешно. Результат сохранен в: {output_file}")
        else:
            logging.error("Ошибка при сохранении файла")
            sys.exit(1)
    except Exception as e:
        logging.error(f"Критическая ошибка при парсинге: {e}")
        sys.exit(1)
    finally:
        driver.quit()
        logging.info("Веб-драйвер закрыт")