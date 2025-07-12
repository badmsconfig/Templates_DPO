import os
import subprocess
import glob
import datetime
import sys
import logging
from pathlib import Path

# Настройка кодировки консоли на UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Настройка логирования
LOG_FILE = Path(r"D:\python_work\dpo\dpo") / f"parser_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s',
                    handlers=[logging.FileHandler(LOG_FILE, encoding='utf-8'), logging.StreamHandler(sys.stdout)])

BASE_DIR = Path(r"D:\python_work\dpo\dpo")
SCRIPTS = [
    "DPO_aktsii.py", "DPO_dokument-company.py", "DPO_dokumenty.py",
    "DPO_dostupnaya-sreda-v-ooo-akademiya-dpo.py", "DPO_FAQ.py", "DPO_finhozdeyat.py",
    "DPO_glavnaya.py", "DPO_kontakty.py", "DPO_master-of-business-administration-mba.py",
    "DPO_materialno-tehnicheskoe-obespechenie-i-osnashhennost-obrazovatelnogo-protsessa.py",
    "DPO_materialno-tehnicheskoe-obespechenie-i-osnashhennost-obrazovatelnogo-protsessa-dostupnaya-sreda.py",
    "DPO_matertehnichobespechenieiosnashhennost.py", "DPO_mezhdunarodnoe-sotrudnichestvo.py",
    "DPO_napravleniya-main.py", "DPO_obrazovanie.py", "DPO_onas.py",
    "DPO_oplata-obrazovatelnyh-uslug.py", "DPO_organizatsiya-pitaniya.py",
    "DPO_osnovnye-svedeniya.py", "DPO_partnery.py", "DPO_pedagogicheskij-sostav.py",
    "DPO_platnye-obrazovatelnye-uslugi.py", "DPO_politika-konfidentsialnosti-personalnyh-dannyh.py",
    "DPO_rukovodstvo.py", "DPO_rukovodstvo-i-pedagogicheskij-sostav.py",
    "DPO_servis-proverki-dokumentov.py", "DPO_sotrudnichestvo.py", "DPO_stipendii.py",
    "DPO_stipendii-i-inye-vidy-materialnoj-podderzhki.py", "DPO_struktura-i-organy-upravleniya.py",
    "DPO_vakantnye-mesta-dlya-priema-perevoda.py", "DPO_vakantnye-mesta-dlya-priema-perevoda1.py"
]
TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = BASE_DIR / f"Раздел_1_{TIMESTAMP}.md"


def run_scripts():
    """Запускает скрипты и проверяет создание Markdown-файлов."""
    successful_scripts, missing_files = [], []
    python_exe = BASE_DIR.parent / "venv" / "Scripts" / "python.exe"

    if not python_exe.exists():
        logging.error(f"Python из виртуального окружения не найден: {python_exe}")
        return successful_scripts, missing_files

    available_scripts = {f.name.lower(): f for f in BASE_DIR.glob("*.py")}
    logging.info(f"Найдено Python-скриптов: {len(available_scripts)}")

    for script in SCRIPTS:
        script_path = BASE_DIR / script
        expected_md = BASE_DIR / script.replace(".py", ".md")

        if not script_path.exists():
            script_lower = script.lower()
            if script_lower in available_scripts:
                logging.warning(
                    f"Скрипт {script} не найден, но найден {available_scripts[script_lower]}. Исправьте регистр.")
                script_path = available_scripts[script_lower]
            else:
                logging.error(f"Скрипт {script} не найден")
                missing_files.append(expected_md)
                continue

        logging.info(f"Запуск скрипта: {script}")
        try:
            result = subprocess.run([str(python_exe), str(script_path)], capture_output=True, text=True,
                                    timeout=300, encoding='utf-8', errors='replace')
            if result.returncode == 0:
                logging.info(f"Скрипт {script} успешно выполнен")
                successful_scripts.append(script)
                if expected_md.exists():
                    logging.info(f"Создан файл: {expected_md}")
                else:
                    logging.error(f"Файл {expected_md} не создан")
                    missing_files.append(expected_md)
            else:
                logging.error(f"Ошибка при выполнении {script}: {result.stderr}")
                missing_files.append(expected_md)
        except subprocess.TimeoutExpired:
            logging.error(f"Скрипт {script} превысил время выполнения (5 минут)")
            missing_files.append(expected_md)
        except Exception as e:
            logging.error(f"Исключение при выполнении {script}: {str(e)}")
            missing_files.append(expected_md)

    return successful_scripts, missing_files


def clean_markdown_content(content):
    """Очищает содержимое Markdown, убирая лишние пустые строки и объединяя переносы."""
    lines = content.splitlines()
    cleaned_lines = []
    prev_line_empty = False

    for line in lines:
        line = line.rstrip()
        if not line:
            if not prev_line_empty:
                cleaned_lines.append("")
                prev_line_empty = True
            continue
        prev_line_empty = False
        cleaned_lines.append(line)

    # Удаляем лишние пустые строки в конце
    while cleaned_lines and not cleaned_lines[-1]:
        cleaned_lines.pop()

    # Объединяем строки, которые должны быть вместе (например, текст в абзацах)
    result = []
    i = 0
    while i < len(cleaned_lines):
        line = cleaned_lines[i]
        if line.startswith('#') or line.startswith('-') or not line:
            result.append(line)
        else:
            # Объединяем строки абзаца
            paragraph = [line]
            j = i + 1
            while j < len(cleaned_lines) and cleaned_lines[j] and not cleaned_lines[j].startswith(('#', '-')):
                paragraph.append(cleaned_lines[j])
                j += 1
            result.append(' '.join(paragraph))
            i = j - 1
        i += 1

    return '\n'.join(result)


def combine_markdown_files(missing_files):
    """Объединяет Markdown-файлы в один с улучшенной читаемостью."""
    markdown_files = sorted([f for f in BASE_DIR.glob("*.md") if f != OUTPUT_FILE])
    logging.info(f"Найдено Markdown-файлов: {len(markdown_files)}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
        outfile.write(f"# Раздел 1\nДата создания: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        if not markdown_files:
            outfile.write("Ошибка: Markdown-файлы не найдены.\n")
            logging.error("Markdown-файлы не найдены")
            return

        added_files = []
        for md_file in markdown_files:
            try:
                with open(md_file, "r", encoding="utf-8") as infile:
                    content = clean_markdown_content(infile.read())
                    outfile.write(f"\n## {md_file.name.replace('.md', '')}\n{content}\n---\n")
                logging.info(f"Файл {md_file} добавлен")
                added_files.append(md_file)
            except Exception as e:
                logging.error(f"Ошибка при обработке {md_file}: {str(e)}")
                outfile.write(f"\n## Ошибка: {md_file.name}\nПричина: {str(e)}\n---\n")

        if missing_files or any(
                md_file.name not in [script.replace(".py", ".md") for script in SCRIPTS] for md_file in markdown_files):
            outfile.write("\n## Пропущенные или неожидаемые файлы\n")
            for missing_file in missing_files:
                if missing_file not in added_files:
                    outfile.write(f"- {missing_file.name}: не создан или не добавлен\n")
            for md_file in markdown_files:
                expected_mds = [script.replace(".py", ".md") for script in SCRIPTS]
                if md_file.name not in expected_mds:
                    outfile.write(f"- {md_file.name}: найден, но не ожидался\n")


def main():
    logging.info("Запуск обработки скриптов...")
    successful_scripts, missing_files = run_scripts()
    logging.info(f"Успешно выполнено скриптов: {len(successful_scripts)} из {len(SCRIPTS)}")
    logging.info(f"Пропущенные файлы: {len(missing_files)}")
    logging.info("Объединение Markdown-файлов...")
    combine_markdown_files(missing_files)
    logging.info(f"Итоговый файл создан: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()