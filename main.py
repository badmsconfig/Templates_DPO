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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)

BASE_DIR = Path(r"D:\python_work\dpo\dpo")
SCRIPTS = [
    "DPO_aktsii.py",
    "DPO_dokument-company.py",
    "DPO_dokumenty.py",
    "DPO_dostupnaya-sreda-v-ooo-akademiya-dpo.py",
    "DPO_FAQ.py",
    "DPO_finhozdeyat.py",
    "DPO_glavnaya.py",
    "DPO_kontakty.py",
    "DPO_master-of-business-administration-mba.py",
    "DPO_materialno-tehnicheskoe-obespechenie-i-osnashhennost-obrazovatelnogo-protsessa.py",
    "DPO_materialno-tehnicheskoe-obespechenie-i-osnashhennost-obrazovatelnogo-protsessa-dostupnaya-sreda.py",
    "DPO_matertehnichobespechenieiosnashhennost.py",
    "DPO_mezhdunarodnoe-sotrudnichestvo.py",
    "DPO_napravleniya-main.py",
    "DPO_obrazovanie.py",
    "DPO_onas.py",
    "DPO_oplata-obrazovatelnyh-uslug.py",
    "DPO_organizatsiya-pitaniya.py",
    "DPO_osnovnye-svedeniya.py",
    "DPO_partnery.py",
    "DPO_pedagogicheskij-sostav.py",
    "DPO_platnye-obrazovatelnye-uslugi.py",
    "DPO_politika-konfidentsialnosti-personalnyh-dannyh.py",
    "DPO_rukovodstvo.py",
    "DPO_rukovodstvo-i-pedagogicheskij-sostav.py",
    "DPO_servis-proverki-dokumentov.py",
    "DPO_sotrudnichestvo.py",
    "DPO_stipendii.py",
    "DPO_stipendii-i-inye-vidy-materialnoj-podderzhki.py",
    "DPO_struktura-i-organy-upravleniya.py",
    "DPO_vakantnye-mesta-dlya-priema-perevoda.py",
    "DPO_vakantnye-mesta-dlya-priema-perevoda1.py",

]
TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = BASE_DIR / f"Раздел_1_{TIMESTAMP}.md"


def run_scripts():
    """Запускает все скрипты из списка и проверяет создание Markdown-файлов."""
    successful_scripts = []
    missing_files = []

    # Проверка пути к Python из виртуального окружения
    python_exe = BASE_DIR.parent / "venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        logging.error(f"Python из виртуального окружения не найден: {python_exe}")
        return successful_scripts, missing_files

    # Проверка существующих файлов
    available_scripts = {f.name.lower(): f for f in BASE_DIR.glob("*.py")}
    logging.info(f"Найдено Python-скриптов в {BASE_DIR}: {len(available_scripts)}")

    for script in SCRIPTS:
        script_path = BASE_DIR / script
        expected_md = BASE_DIR / script.replace(".py", ".md")

        # Проверка наличия скрипта
        if not script_path.exists():
            # Проверяем с учетом регистра
            script_lower = script.lower()
            if script_lower in available_scripts:
                logging.warning(f"Скрипт {script} не найден, но найден {available_scripts[script_lower]}. Исправьте регистр в SCRIPTS.")
                script_path = available_scripts[script_lower]
            else:
                logging.error(f"Скрипт {script} не найден в {BASE_DIR}")
                missing_files.append(expected_md)
                continue

        logging.info(f"Запуск скрипта: {script}")
        try:
            result = subprocess.run(
                [str(python_exe), str(script_path)],
                capture_output=True,
                text=True,
                timeout=300,
                encoding='utf-8',
                errors='replace',
            )
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


def combine_markdown_files(missing_files):
    """Объединяет все Markdown-файлы в один и записывает информацию о пропущенных файлах."""
    markdown_files = list(BASE_DIR.glob("*.md"))
    logging.info(f"Найдено Markdown-файлов: {len(markdown_files)}")
    logging.info(f"Список файлов: {[str(f) for f in markdown_files]}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
        outfile.write("# Раздел 1\n\n")
        outfile.write(f"Дата создания: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        if not markdown_files:
            outfile.write("Ошибка: Markdown-файлы не найдены.\n")
            logging.error("Markdown-файлы не найдены")
            return

        added_files = []
        for md_file in sorted(markdown_files):
            if md_file == OUTPUT_FILE:
                continue
            try:
                with open(md_file, "r", encoding="utf-8") as infile:
                    outfile.write(f"## Данные из файла: {md_file.name}\n\n")
                    outfile.write(infile.read())
                    outfile.write("\n\n---\n\n")
                logging.info(f"Файл {md_file} добавлен в итоговый отчет")
                added_files.append(md_file)
            except Exception as e:
                logging.error(f"Ошибка при обработке {md_file}: {str(e)}")
                outfile.write(f"## Ошибка: файл {md_file.name} не добавлен\n\n")
                outfile.write(f"Причина: {str(e)}\n\n---\n\n")

        if missing_files:
            outfile.write("## Пропущенные или не созданные файлы\n\n")
            for missing_file in missing_files:
                if missing_file not in added_files:
                    outfile.write(f"- {missing_file.name}: не создан или не добавлен\n")
                    logging.error(f"Файл {missing_file} не был создан или добавлен")
            for md_file in markdown_files:
                expected_mds = [script.replace(".py", ".md") for script in SCRIPTS]
                if md_file.name not in expected_mds and md_file != OUTPUT_FILE:
                    outfile.write(f"- {md_file.name}: найден, но не ожидался\n")
                    logging.warning(f"Файл {md_file} найден, но не ожидался")


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