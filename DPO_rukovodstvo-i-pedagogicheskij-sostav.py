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
    "paragraphs": (By.CSS_SELECTOR, "div.page__content-desc > p"),
    "underline_text": (By.CSS_SELECTOR, "div.page__content-desc > u"),
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
        "categories": ["Руководство", "Педагогический состав", "Образование"],
        "tags": ["ДПО", "руководство", "преподаватели", "администрация"]
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
            first_paragraph = driver.find_element(*SELECTORS["paragraphs"]).text.strip()
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

    # Извлечение подзаголовка (underline)
    try:
        underline_text = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["underline_text"])
        ).text.strip()
        result.append(("subtitle", underline_text))
        logging.info(f"Подзаголовок: {underline_text}")
    except Exception as e:
        logging.warning(f"Ошибка при парсинге подзаголовка: {e}")

    # Извлечение параграфов
    try:
        paragraphs = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(SELECTORS["paragraphs"])
        )
        paragraph_texts = []
        current_person = None
        for p in paragraphs:
            p_text = p.text.strip()
            if p_text:
                # Проверяем, является ли параграф началом описания новой персоны
                if p_text.startswith("Генеральный директор:") or p_text.startswith("Заведующий учебной частью"):
                    if current_person:
                        paragraph_texts.append(current_person)
                    current_person = {"title": p_text}
                elif current_person:
                    # Добавляем информацию к текущей персоне
                    if "Уровень образования:" in p_text:
                        current_person["education"] = p_text
                    elif "Общий стаж работы:" in p_text:
                        current_person["total_experience"] = p_text
                    elif "Стаж работы в должности:" in p_text:
                        current_person["position_experience"] = p_text
                    elif "Окончил:" in p_text or "Окончил (а):" in p_text:
                        current_person["graduated"] = p_text
                    elif "Дополнительное профессиональное образование:" in p_text:
                        current_person["additional_education"] = p_text
                    elif "Контактный телефон:" in p_text:
                        current_person["phone"] = p_text
                    elif "Электронная почта:" in p_text:
                        current_person["email"] = p_text
        # Добавляем последнюю персону, если она есть
        if current_person:
            paragraph_texts.append(current_person)
        if paragraph_texts:
            result.append(("content", paragraph_texts))
            logging.info(f"Параграфы: {paragraph_texts}")
    except Exception as e:
        logging.warning(f"Ошибка при парсинге параграфов: {e}")

    logging.info(f"Парсинг завершен. Получено {len(result)} элементов контента")
    return result, url, metadata

def save_to_markdown(data, url, metadata, filename="DPO_rukovodstvo-i-pedagogicheskij-sostav.md"):
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
            elif item[0] == "subtitle":
                content.append(f"## {item[1]}")
            elif item[0] == "content":
                for person in item[1]:
                    if isinstance(person, dict):
                        content.append(f"## {person.get('title', '')}")
                        if "education" in person:
                            content.append(f"- {person['education']}")
                        if "total_experience" in person:
                            content.append(f"- {person['total_experience']}")
                        if "position_experience" in person:
                            content.append(f"- {person['position_experience']}")
                        if "graduated" in person:
                            content.append(f"- {person['graduated']}")
                        if "additional_education" in person:
                            content.append(f"- {person['additional_education']}")
                        if "phone" in person:
                            content.append(f"- {person['phone']}")
                        if "email" in person:
                            content.append(f"- {person['email']}")
                        content.append("")  # Пустая строка для разделения персон

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
    TARGET_URL = "https://academydpo.org/rukovodstvo-i-pedagogicheskij-sostav"
    logging.info("Запуск скрипта DPO_rukovodstvo-i-pedagogicheskij-sostav.py")
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