# De-identification

Локальное macOS/Windows-приложение для маскировки персональных данных перед отправкой документов в облачные нейросети.

De-identification работает локально: исходный файл не изменяется, рядом создаётся копия с токенами вида `[PHONE_1]`, а файл `*_keys.json` остаётся на компьютере пользователя.

## Что поддерживается

- `.docx`, `.xlsx`, `.pptx`, `.pdf`, `.txt`, `.md`, `.csv`;
- добавление файлов и папок через Finder или drag-and-drop;
- фоновая обработка очереди;
- отдельный `_clean`-файл для каждого исходного документа;
- локальный JSON-ключ с исходными значениями.

Перед отправкой очищенного файла обязательно проверьте его содержимое вручную. Файлы `*_keys.json` содержат реальные персональные данные: их нельзя отправлять в нейросеть или публиковать в GitHub.

## Запуск из исходников на macOS

Нужен Python 3.13.

```bash
/opt/homebrew/bin/python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run_app.py
```

Тесты:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Установка готовой версии

Готовые установщики публикуются на странице **GitHub Releases**:

- macOS: `De-identification.dmg`;
- Windows 10/11 x64: `De-identification-Setup.exe`.

На macOS откройте DMG и перетащите `De-identification` на ярлык `Applications`. На Windows запустите installer и откройте De-identification из меню Start или с рабочего стола.
