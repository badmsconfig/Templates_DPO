# Импорт необходимых библиотек
import requests
import pdfplumber
import re
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
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

def remove_accents(text):
    """Удаляет ударения из текста."""
    accents = {
        'а́': 'а', 'е́': 'е', 'и́': 'и', 'о́': 'о', 'у́': 'у', 'ы́': 'ы', 'э́': 'э', 'ю́': 'ю', 'я́': 'я',
        'А́': 'А', 'Е́': 'Е', 'И́': 'И', 'О́': 'О', 'У́': 'У', 'Ы́': 'Ы', 'Э́': 'Э', 'Ю́': 'Ю', 'Я́': 'Я',
        'ё': 'е', 'Ё': 'Е'
    }
    for accented, plain in accents.items():
        text = text.replace(accented, plain)
    return text

def is_text_valid(text):
    """Проверяет текст на наличие бессмысленных символов или 'белиберды'."""
    garbage_pattern = r'[^a-zA-Zа-яА-Я0-9\s.,;:!?-]'
    garbage_count = len(re.findall(garbage_pattern, text))
    total_length = len(text)

    if total_length == 0 or (garbage_count / total_length > 0.3):
        return False

    word_pattern = r'[а-яА-Я]{3,}'
    words = re.findall(word_pattern, text)
    return len(words) > 2

def clean_text(text):
    """Очищает текст от лишних пробелов, сохраняя структуру строк."""
    lines = [re.sub(r'\s+', ' ', line).strip() for line in text.splitlines() if line.strip()]
    return '\n'.join(lines)

def extract_metadata(driver, url):
    """Извлекает метаданные страницы."""
    metadata = {
        "title": "",
        "description": "",
        "url": url,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "categories": ["Педагогический состав", "Образование"],
        "tags": ["ДПО", "преподаватели", "образовательные услуги"]
    }

    try:
        title_element = driver.find_element(By.TAG_NAME, "title")
        metadata["title"] = remove_accents(title_element.get_attribute("innerText").strip())
    except Exception as e:
        logging.warning(f"Ошибка при извлечении заголовка страницы: {e}")
        try:
            main_title = driver.find_element(By.CSS_SELECTOR, "article.page__content h1.page__content-title").text.strip()
            metadata["title"] = remove_accents(main_title)
        except:
            metadata["title"] = "Без названия"

    try:
        desc_element = driver.find_element(By.XPATH, "//meta[@name='description']")
        metadata["description"] = remove_accents(desc_element.get_attribute("content").strip())
    except Exception as e:
        logging.warning(f"Ошибка при извлечении meta description: {e}")
        try:
            first_paragraph = driver.find_element(By.CSS_SELECTOR, "article.page__content div.page__content-desc > p").text.strip()
            metadata["description"] = remove_accents(re.sub(r'[#*\[\]]', '', first_paragraph)[:160].strip()) + "..."
        except:
            metadata["description"] = "Описание отсутствует"

    return metadata

def parse_page(url):
    """Парсит страницу с помощью Selenium и извлекает заголовок, ссылку на PDF и метаданные."""
    try:
        # Настройка Selenium
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--enable-unsafe-swiftshader")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

        # Загружаем страницу
        driver.get(url)
        logging.info(f"Начинаем парсинг страницы: {url}")

        # Извлекаем метаданные
        metadata = extract_metadata(driver, url)

        # Извлекаем заголовок
        title_element = driver.find_element(By.CSS_SELECTOR, 'article.page__content h1.page__content-title')
        title_text = clean_text(title_element.text) if title_element else "Без заголовка"
        title_text = remove_accents(title_text)
        logging.info(f"Основной заголовок: {title_text}")

        # Извлекаем ссылку на PDF
        pdf_link = driver.find_element(By.CSS_SELECTOR, 'article.page__content div.page__content-desc a')
        pdf_url = urljoin(url, pdf_link.get_attribute('href')) if pdf_link else None
        logging.info(f"Ссылка на PDF: {pdf_url}")

        driver.quit()
        return title_text, pdf_url, metadata
    except Exception as e:
        logging.error(f"Ошибка при парсинге страницы: {e}")
        return None, None, {}

def parse_pdf(pdf_url):
    """Парсит PDF и извлекает текст, сохраняя читабельную структуру."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        }
        response = requests.get(pdf_url, headers=headers)
        response.raise_for_status()

        temp_pdf_path = Path(r"D:\python_work\dpo\dpo\temp.pdf")
        temp_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_pdf_path, 'wb') as f:
            f.write(response.content)

        text_content = []
        with pdfplumber.open(temp_pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text and is_text_valid(page_text):
                    cleaned_text = clean_text(page_text)
                    if cleaned_text:
                        text_content.append(cleaned_text)

        temp_pdf_path.unlink(missing_ok=True)
        logging.info(f"Извлечено {len(text_content)} страниц из PDF")
        return '\n\n'.join(text_content) if text_content else ""
    except requests.exceptions.HTTPError as e:
        logging.error(f"Ошибка HTTP при загрузке PDF: {e}")
        return ""
    except Exception as e:
        logging.error(f"Ошибка при парсинге PDF: {e}")
        return ""

def save_to_markdown(title, page_url, pdf_text, metadata, filename="DPO_pedagogicheskij-sostav.md"):
    """Сохраняет текст в формате Markdown, форматируя имена как заголовки второго уровня и объединяя строки."""
    try:
        save_path = Path(r"D:\python_work\dpo\dpo") / filename
        content = []

        # Формируем YAML-метаданные
        yaml_metadata = yaml.dump(metadata, allow_unicode=True, sort_keys=False, width=float("inf"))
        content.append(f"---\n{yaml_metadata}---")

        # Формируем контент
        content.append(f"# {title}")
        content.append(f"[Ссылка на страницу]({page_url})")

        # Обрабатываем текст PDF
        names = ["Лукашевич Елена Алексеевна", "Ростовцева Елена Юрьевна"]
        pdf_lines = pdf_text.split('\n')
        formatted_pdf_lines = []
        current_line = ""
        current_name = None

        for i, line in enumerate(pdf_lines):
            line = remove_accents(line.strip())
            if not line:
                continue

            # Проверяем, является ли строка одним из указанных имён
            if line in names:
                if current_line:
                    formatted_pdf_lines.append(current_line)
                current_name = line
                formatted_pdf_lines.append(f"## {line}")  # Изменено на заголовок второго уровня
                current_line = ""
                continue

            # Проверяем, начинается ли строка с маленькой буквы
            is_lowercase_start = line and line[0].islower() and not line.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'))

            if is_lowercase_start and current_line:
                # Объединяем с предыдущей строкой
                current_line += " " + line
            else:
                # Сохраняем предыдущую строку, если она есть
                if current_line:
                    formatted_pdf_lines.append(current_line)
                current_line = line

        # Добавляем последнюю строку, если она есть
        if current_line:
            formatted_pdf_lines.append(current_line)

        content.append('\n'.join(formatted_pdf_lines))

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

def main():
    url = "https://academydpo.org/pedagogicheskij-sostav"
    logging.info("Запуск скрипта DPO_pedagogicheskij-sostav.py")

    title, pdf_url, metadata = parse_page(url)
    if not title or not pdf_url:
        logging.error("Не удалось извлечь заголовок или ссылку на PDF")
        return

    pdf_text = parse_pdf(pdf_url)
    if not pdf_text:
        logging.error("Не удалось извлечь текст из PDF. Проверьте доступ к файлу или защиту от ботов.")
        return

    output_file = save_to_markdown(title, url, pdf_text, metadata)
    if output_file:
        logging.info(f"Файл {output_file} успешно сохранен!")
    else:
        logging.error("Ошибка при сохранении файла")

if __name__ == "__main__":
    main()