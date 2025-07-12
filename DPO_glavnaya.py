# Импорт необходимых библиотек
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
from pathlib import Path
import sys
import yaml
from datetime import datetime
import re

# Настройка кодировки консоли на UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Настройка логирования только в консоль
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Функция настройки веб-драйвера
def get_driver():
    """Создает и настраивает веб-драйвер."""
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Запуск без графического интерфейса
        chrome_options.add_argument('--disable-gpu')  # Отключение GPU
        chrome_options.add_argument('--no-sandbox')  # Отключение песочницы
        chrome_options.add_argument('--window-size=1920,1080')  # Размер окна
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        logging.info("Веб-драйвер успешно создан")
        return driver
    except Exception as e:
        logging.error(f"Ошибка при настройке веб-драйвера: {e}")
        return None

# Словарь селекторов для извлечения данных
elements_to_parse = {
    "page_title": [
        {"type": "css", "value": "section.desc_page h2.desc_page-title"},
    ],
    "meta_title": [
        {"type": "css", "value": "title"},
    ],
    "meta_description": [
        {"type": "xpath", "value": "//meta[@name='description']"},
    ],
    "page_text": [
        {"type": "css", "value": "section.desc_page div.desc_page-text p"},
    ],
    "info_block_title": [
        {"type": "css", "value": "h2.info_block__images-title span"},
    ],
    "info_block_text": [
        {"type": "css", "value": "div.info_block-desc p"},
    ],
    "info_links": [
        {"type": "css", "value": "a.info_block__list-link"},
    ],
    "home_desc_section": [
        {"type": "css", "value": "section.home_desc > *"},
    ],
    "education_features": {
        "trigger_text": "Такое обучение имеет свои особенности:",
        "selector": {"type": "xpath", "value": "//p[contains(text(), 'Такое обучение имеет свои особенности:')]/following-sibling::ul[1]/li"},
    },
    "learning_forms": {
        "trigger_text": "В нашей академии дистанционное обучение проводится в разных формах:",
        "selector": {"type": "xpath", "value": "//h3[contains(text(), 'В нашей академии дистанционное обучение проводится в разных формах:')]/following-sibling::ul[1]/li"},
    },
    "medical_education": {
        "trigger_text": "Дистанционное обучение для руководящего состава здравоохранительных организаций",
        "selector": {"type": "xpath", "value": "//p[contains(., 'Дистанционное обучение для руководящего состава')]/following-sibling::ul[1]/li/a"},
    },
    "construction_courses": {
        "trigger_text": "Курсы на базе средне-специального или высшего образования",
        "selector": {"type": "xpath", "value": "//p[contains(., 'Курсы на базе средне-специального или высшего образования')]/following-sibling::ul[1]/li/a"},
    },
    "special_courses": {
        "trigger_text": "Курсы специальной переподготовки на базе среднего и/или высшего образования",
        "selector": {"type": "xpath", "value": "//p[contains(., 'Курсы специальной переподготовки на базе среднего и/или высшего образования')]/following-sibling::ul[1]/li/a"},
    },
}

# Функция для извлечения метаданных
def extract_metadata(driver, url):
    metadata = {}
    try:
        title_elements = []
        for selector in elements_to_parse["meta_title"]:
            if selector["type"] == "css":
                elements = driver.find_elements(By.CSS_SELECTOR, selector["value"])
                title_elements.extend([el.get_attribute("innerText").strip() for el in elements if el.get_attribute("innerText").strip()])
        metadata["title"] = title_elements[0] if title_elements else "Без названия"
    except Exception as e:
        logging.warning(f"Ошибка при извлечении заголовка страницы: {e}")
        metadata["title"] = "Без названия"

    try:
        desc_elements = []
        for selector in elements_to_parse["meta_description"]:
            if selector["type"] == "xpath":
                elements = driver.find_elements(By.XPATH, selector["value"])
                desc_elements.extend([el.get_attribute("content").strip() for el in elements if el.get_attribute("content").strip()])
        metadata["description"] = desc_elements[0] if desc_elements else ""
        if not metadata["description"]:
            raise Exception("Meta description отсутствует")
    except Exception as e:
        logging.warning(f"Ошибка при извлечении meta description: {e}")
        try:
            text_elements = []
            for selector in elements_to_parse["page_text"]:
                if selector["type"] == "css":
                    elements = driver.find_elements(By.CSS_SELECTOR, selector["value"])
                    text_elements.extend([el.text.strip() for el in elements if el.text.strip()])
            intro_text = " ".join(text_elements)
            metadata["description"] = re.sub(r'[#*\[\]]', '', intro_text)[:160].strip() + "..."
        except:
            metadata["description"] = "Описание отсутствует"

    metadata["url"] = url
    metadata["date"] = datetime.now().strftime("%Y-%m-%d")
    metadata["categories"] = ["Главная страница", "Образование"]
    metadata["tags"] = ["ДПО", "дистанционное обучение", "курсы"]

    return metadata

# Функция парсинга веб-страницы
def parse_website(url, driver):
    """Парсинг веб-страницы."""
    results = {
        "url": url,
        "metadata": {},
        "sections": [],  # Список для заголовков и текстов
        "links": [],  # Список для ссылок
        "education_features": [],
        "learning_forms": [],
        "medical_education": [],
        "construction_courses": [],
        "special_courses": []
    }

    try:
        driver.get(url)
        time.sleep(2)  # Ожидание загрузки
        logging.info(f"Страница загружена: {url}")

        # Извлечение метаданных
        results["metadata"] = extract_metadata(driver, url)

        # Парсинг заголовков страницы
        title_texts = []
        for selector in elements_to_parse["page_title"]:
            try:
                if selector["type"] == "css":
                    elements = driver.find_elements(By.CSS_SELECTOR, selector["value"])
                elif selector["type"] == "xpath":
                    elements = driver.find_elements(By.XPATH, selector["value"])
                title_texts.extend([el.text.strip() for el in elements if el.text.strip()])
            except Exception as e:
                logging.warning(f"Ошибка при парсинге заголовков: {e}")
                continue

        # Парсинг основного текста страницы
        body_texts = []
        for selector in elements_to_parse["page_text"]:
            try:
                if selector["type"] == "css":
                    elements = driver.find_elements(By.CSS_SELECTOR, selector["value"])
                elif selector["type"] == "xpath":
                    elements = driver.find_elements(By.XPATH, selector["value"])
                body_texts.extend([el.text.strip() for el in elements if el.text.strip()])
            except Exception as e:
                logging.warning(f"Ошибка при парсинге текста страницы: {e}")
                continue

        # Объединение заголовков и текстов в секции
        if len(title_texts) == 1 and len(body_texts) > 1:
            for i, text in enumerate(body_texts):
                results["sections"].append({
                    "title": title_texts[0] if i == 0 else "",
                    "text": text
                })
        else:
            for i in range(max(len(title_texts), len(body_texts))):
                title = title_texts[i] if i < len(title_texts) else ""
                text = body_texts[i] if i < len(body_texts) else ""
                results["sections"].append({"title": title, "text": text})

        # Парсинг заголовков информационных блоков
        info_titles = []
        for selector in elements_to_parse["info_block_title"]:
            try:
                if selector["type"] == "css":
                    elements = driver.find_elements(By.CSS_SELECTOR, selector["value"])
                elif selector["type"] == "xpath":
                    elements = driver.find_elements(By.XPATH, selector["value"])
                info_titles.extend([el.text.strip() for el in elements if el.text.strip()])
            except Exception as e:
                logging.warning(f"Ошибка при парсинге заголовков инфоблоков: {e}")
                continue

        # Парсинг текстов информационных блоков
        info_texts = []
        for selector in elements_to_parse["info_block_text"]:
            try:
                if selector["type"] == "css":
                    elements = driver.find_elements(By.CSS_SELECTOR, selector["value"])
                elif selector["type"] == "xpath":
                    elements = driver.find_elements(By.XPATH, selector["value"])
                info_texts.extend([el.text.strip() for el in elements if el.text.strip()])
            except Exception as e:
                logging.warning(f"Ошибка при парсинге текстов инфоблоков: {e}")
                continue

        # Объединение заголовков и текстов инфоблоков
        if len(info_titles) == 1 and len(info_texts) > 0:
            for i, text in enumerate(info_texts):
                results["sections"].append({
                    "title": info_titles[0] if i == 0 else "",
                    "text": text
                })
        else:
            for i in range(max(len(info_titles), len(info_texts))):
                title = info_titles[i] if i < len(info_titles) else ""
                text = info_texts[i] if i < len(info_texts) else ""
                results["sections"].append({"title": title, "text": text})

        # Парсинг ссылок
        for selector in elements_to_parse["info_links"]:
            try:
                if selector["type"] == "css":
                    elements = driver.find_elements(By.CSS_SELECTOR, selector["value"])
                elif selector["type"] == "xpath":
                    elements = driver.find_elements(By.XPATH, selector["value"])
                for el in elements:
                    if el.text.strip():
                        results["links"].append({
                            "text": el.text.strip(),
                            "url": el.get_attribute("href")
                        })
            except Exception as e:
                logging.warning(f"Ошибка при парсинге ссылок: {e}")
                continue

        # Парсинг секции home_desc
        for selector in elements_to_parse["home_desc_section"]:
            try:
                if selector["type"] == "css":
                    elements = driver.find_elements(By.CSS_SELECTOR, selector["value"])
                    for el in elements:
                        tag_name = el.tag_name.lower()
                        text = el.text.strip()
                        if not text:
                            continue
                        if tag_name in ['h2', 'h3']:
                            results["sections"].append({"title": text, "text": ""})
                        elif tag_name in ['p', 'li']:
                            if results["sections"] and not results["sections"][-1]["text"]:
                                results["sections"][-1]["text"] = text
                            else:
                                results["sections"].append({"title": "", "text": text})
            except Exception as e:
                logging.warning(f"Ошибка при парсинге home_desc: {e}")
                continue

        # Парсинг особенностей обучения
        try:
            if elements_to_parse["education_features"]["selector"]["type"] == "xpath":
                elements = driver.find_elements(By.XPATH, elements_to_parse["education_features"]["selector"]["value"])
                for el in elements:
                    text = el.text.strip()
                    if text:
                        results["education_features"].append(text)
        except Exception as e:
            logging.warning(f"Ошибка при парсинге особенностей обучения: {e}")

        # Парсинг форм обучения
        try:
            if elements_to_parse["learning_forms"]["selector"]["type"] == "xpath":
                elements = driver.find_elements(By.XPATH, elements_to_parse["learning_forms"]["selector"]["value"])
                for el in elements:
                    text = el.text.strip()
                    if text:
                        results["learning_forms"].append(text)
        except Exception as e:
            logging.warning(f"Ошибка при парсинге форм обучения: {e}")

        # Парсинг медицинского образования
        try:
            if elements_to_parse["medical_education"]["selector"]["type"] == "xpath":
                elements = driver.find_elements(By.XPATH, elements_to_parse["medical_education"]["selector"]["value"])
                for el in elements:
                    text = el.text.strip()
                    url = el.get_attribute("href")
                    if text:
                        results["medical_education"].append({"text": text, "url": url})
        except Exception as e:
            logging.warning(f"Ошибка при парсинге медицинского образования: {e}")

        # Парсинг строительных курсов
        try:
            if elements_to_parse["construction_courses"]["selector"]["type"] == "xpath":
                elements = driver.find_elements(By.XPATH, elements_to_parse["construction_courses"]["selector"]["value"])
                for el in elements:
                    text = el.text.strip()
                    url = el.get_attribute("href")
                    if text:
                        results["construction_courses"].append({"text": text, "url": url})
        except Exception as e:
            logging.warning(f"Ошибка при парсинге строительных курсов: {e}")

        # Парсинг специальных курсов
        try:
            if elements_to_parse["special_courses"]["selector"]["type"] == "xpath":
                elements = driver.find_elements(By.XPATH, elements_to_parse["special_courses"]["selector"]["value"])
                for el in elements:
                    text = el.text.strip()
                    url = el.get_attribute("href")
                    if text:
                        results["special_courses"].append({"text": text, "url": url})
        except Exception as e:
            logging.warning(f"Ошибка при парсинге специальных курсов: {e}")

        logging.info(f"Парсинг страницы {url} завершен")
        return results
    except Exception as e:
        logging.error(f"Критическая ошибка при парсинге {url}: {e}")
        return results

# Функция сохранения результатов в Markdown-файл
def save_results_to_file(results, filename="DPO_glavnaya.md"):
    """Сохраняет результаты в Markdown-файл."""
    try:
        save_path = Path(r"D:\python_work\DPO\DPO") / filename
        with open(save_path, "w", encoding="utf-8") as f:
            for res in results:
                # Формируем YAML-метаданные
                yaml_metadata = yaml.dump(res["metadata"], allow_unicode=True, sort_keys=False)
                f.write(f"---\n{yaml_metadata}---\n")

                # Заголовок страницы
                f.write(f"# Страница: {res['url']}\n")
                f.write(f"[Открыть страницу]({res['url']})\n")
                f.write(f"{'='*80}\n")

                # Секции с заголовками и текстом
                for section in res["sections"]:
                    if section["title"]:
                        f.write(f"## {section['title']}\n")
                    if section["text"]:
                        f.write(f"{section['text']}\n")

                # Ссылки
                if res["links"]:
                    f.write("## Ссылки\n")
                    for link in res["links"]:
                        f.write(f"- [{link['text']}]({link['url']})\n")

                # Особенности обучения
                if res["education_features"]:
                    f.write("## Особенности обучения\n")
                    for item in res["education_features"]:
                        f.write(f"- {item}\n")

                # Формы обучения
                if res["learning_forms"]:
                    f.write("## Формы обучения\n")
                    for item in res["learning_forms"]:
                        f.write(f"- {item}\n")

                # Медицинское образование
                if res["medical_education"]:
                    f.write("## Медицинское образование\n")
                    for item in res["medical_education"]:
                        f.write(f"- [{item['text']}]({item['url']})\n")

                # Строительные курсы
                if res["construction_courses"]:
                    f.write("## Строительные курсы\n")
                    for item in res["construction_courses"]:
                        f.write(f"- [{item['text']}]({item['url']})\n")

                # Специальные курсы
                if res["special_courses"]:
                    f.write("## Специальные курсы\n")
                    for item in res["special_courses"]:
                        f.write(f"- [{item['text']}]({item['url']})\n")

        logging.info(f"Результаты сохранены в файл: {save_path}")
        return save_path
    except Exception as e:
        logging.error(f"Ошибка при сохранении файла {filename}: {e}")
        return None

# Список URL-адресов для парсинга
urls = [
    "https://academydpo.org/",
]

# Основной блок выполнения программы
if __name__ == "__main__":
    logging.info("Запуск скрипта DPO_glavnaya.py")
    driver = get_driver()
    if driver is None:
        logging.error("Не удалось создать веб-драйвер. Завершение работы.")
        sys.exit(1)

    all_results = []
    for url in urls:
        try:
            logging.info(f"Парсинг страницы: {url}")
            data = parse_website(url, driver)
            all_results.append(data)
        except Exception as e:
            logging.error(f"Ошибка при обработке {url}: {e}")

    driver.quit()
    logging.info("Веб-драйвер закрыт")

    saved_file = save_results_to_file(all_results)
    if saved_file:
        logging.info(f"Скрипт успешно завершен, файл создан: {saved_file}")
    else:
        logging.error("Скрипт завершился с ошибкой, файл не создан")