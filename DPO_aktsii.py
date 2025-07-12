# Импорт библиотек для работы с Selenium, управления ChromeDriver и работы с файлами
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from pathlib import Path
import yaml
from datetime import datetime
import re


# 🔧 Функция настройки веб-драйвера в headless-режиме
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver


# 📄 Словарь селекторов для парсинга страницы акций
SELECTORS = {
    "main_title": (By.CSS_SELECTOR, "h1.stock__title"),
    "meta_title": (By.TAG_NAME, "title"),
    "meta_description": (By.XPATH, "//meta[@name='description']"),
    "intro_paragraph": (By.XPATH, "(//div[contains(@class, 'stock__desc')])[1]//p"),
    "section_titles": (By.CSS_SELECTOR, "h2.stock__block-title"),
    "toggle_button": (By.XPATH,
                      "./following-sibling::div[contains(@class, 'stock__block-info')]//button[contains(@class, 'stock_info_btn')]"),
    "section_info": (By.XPATH,
                     "./following-sibling::div[contains(@class, 'stock__block-info')]//*[self::div[contains(@class, 'stock__block-cat')] or self::div[contains(@class, 'stock__block-text')]]"),
    "section_desc_container": (By.XPATH, "./following-sibling::div[contains(@class, 'stock__block-desc')]"),
    "section_desc": (By.XPATH, "./following-sibling::div[contains(@class, 'stock__block-desc')]//p"),
    "final_paragraph": (By.XPATH, "(//div[contains(@class, 'stock__desc')])[last()]//p")
}


# 🧠 Функция для извлечения метаданных
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
            intro_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located(SELECTORS["intro_paragraph"])
            )
            intro_text = " ".join([elem.text.strip() for elem in intro_elements if elem.text.strip()])
            metadata["description"] = re.sub(r'[#*\[\]]', '', intro_text)[:160].strip() + "..."
        except:
            metadata["description"] = "Описание отсутствует"

    metadata["url"] = url
    metadata["date"] = datetime.now().strftime("%Y-%m-%d")
    metadata["categories"] = ["Акции", "Образование"]
    metadata["tags"] = ["ДПО", "дистанционное обучение", "акции"]

    return metadata


# 🧠 Функция парсинга одной секции акции
def parse_section(driver, section_element):
    content = []
    try:
        title = section_element.text.strip()
        print(f"Найден заголовок секции: {title}")

        try:
            toggle_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(section_element.find_element(*SELECTORS["toggle_button"]))
            )
            print(f"Найдена кнопка для секции: {title}")
            driver.execute_script("arguments[0].click();", toggle_button)
            print(f"Клик по кнопке для секции: {title}")
            desc_container = WebDriverWait(driver, 10).until(
                EC.visibility_of(section_element.find_element(*SELECTORS["section_desc_container"]))
            )
            print(f"Контейнер описания виден для секции: {title}")
        except Exception as e:
            print(f"Не удалось найти или кликнуть на кнопку для раскрытия в секции {title}: {str(e)}")

        try:
            info_elements = section_element.find_elements(*SELECTORS["section_info"])
            for elem in info_elements:
                elem_text = elem.get_attribute('innerText').strip()
                if elem_text:
                    content.append(elem_text)
            print(f"Найдена информация для {title}: {content}")
        except Exception as e:
            print(f"Нет информации stock__block-info в секции {title}: {str(e)}")

        try:
            desc_elements = WebDriverWait(driver, 10).until(
                EC.visibility_of_all_elements_located(section_element.find_elements(*SELECTORS["section_desc"]))
            )
            for elem in desc_elements:
                elem_text = elem.get_attribute('innerText').strip()
                if elem_text:
                    lines = elem_text.split("\n")
                    content.extend(lines)
            print(f"Найдено описание для {title}: {content}")
        except Exception as e:
            print(f"Ошибка при извлечении stock__block-desc в секции {title}: {str(e)}")
            try:
                desc_elements = section_element.find_elements(*SELECTORS["section_desc"])
                for elem in desc_elements:
                    elem_text = driver.execute_script("return arguments[0].innerText;", elem).strip()
                    if elem_text:
                        lines = elem_text.split("\n")
                        content.extend(lines)
                print(f"Найдено описание через JavaScript для {title}: {content}")
            except Exception as e:
                print(f"Ошибка при извлечении stock__block-desc через JavaScript в секции {title}: {str(e)}")

        print(f"Спарсена секция: {title}, контент: {content}")
        return {"title": title, "content": content}
    except Exception as e:
        print(f"Общая ошибка в секции {title}: {str(e)}")
        return None


# 🧠 Функция парсинга страницы
def parse_page(driver, url):
    driver.get(url)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["main_title"])
        )
    except Exception as e:
        print(f"Ошибка загрузки страницы: {str(e)}")
        return [], {}

    metadata = extract_metadata(driver, url)
    result = []

    try:
        main_title = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(SELECTORS["main_title"])
        ).text.strip()
        result.append(("title", main_title))
        print(f"Основной заголовок: {main_title}")
    except Exception as e:
        print(f"Ошибка при парсинге основного заголовка: {str(e)}")

    try:
        intro_elements = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(SELECTORS["intro_paragraph"])
        )
        intro_text = [elem.text.strip() for elem in intro_elements if elem.text.strip()]
        if intro_text:
            result.append(("content", intro_text))
            print(f"Вводный параграф: {intro_text}")
    except Exception as e:
        print(f"Ошибка при парсинге вводного параграфа: {str(e)}")

    try:
        section_elements = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(SELECTORS["section_titles"])
        )
        for section_element in section_elements:
            section = parse_section(driver, section_element)
            if section:
                result.append(("section", section))
    except Exception as e:
        print(f"Ошибка при парсинге секций: {str(e)}")

    try:
        final_elements = WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located(SELECTORS["final_paragraph"])
        )
        final_text = [elem.text.strip() for elem in final_elements if elem.text.strip()]
        if final_text:
            final_content = []
            for text in final_text:
                lines = text.split("\n")
                final_content.extend(lines)
            result.append(("content", final_content))
            print(f"Заключительный параграф: {final_content}")
    except Exception as e:
        print(f"Ошибка при парсинге заключительного параграфа: {str(e)}")

    print(f"Итоговые данные: {result}")
    return result, metadata


# 💾 Функция сохранения результатов в Markdown-файл
def save_to_txt(data, metadata, filename="DPO_aktsii.md"):
    save_path = Path.cwd() / filename
    content = []

    # Формируем YAML-метаданные
    yaml_metadata = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
    content.append(f"---\n{yaml_metadata}---")

    for item in data:
        if item[0] == "title":
            content.append(f"# {item[1]}")
            content.append(f"[Открыть страницу]({metadata['url']})")
        elif item[0] == "content":
            content.extend([line.strip() for line in item[1] if line.strip()])
        elif item[0] == "section":
            section = item[1]
            content.append(f"## {section['title']}")
            content.extend([line.strip() for line in section['content'] if line.strip()])

    # Объединяем с одним переносом строки
    final_content = "\n".join(line for line in content if line.strip())

    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print(f"✅ Результаты сохранены в файл: {save_path}")
    return save_path


# 🚀 Запуск парсера
if __name__ == "__main__":
    TARGET_URL = "https://academydpo.org/aktsii"

    driver = get_driver()
    try:
        parsed_data, metadata = parse_page(driver, TARGET_URL)
        save_to_txt(parsed_data, metadata)
    except Exception as e:
        print(f"Ошибка при парсинге: {str(e)}")
    finally:
        driver.quit()