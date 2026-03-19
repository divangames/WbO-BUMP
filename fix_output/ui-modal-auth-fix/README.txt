Фикс: единый стиль модальных окон, вход с подсветкой ошибки, скрытие «Выйти» для гостя.

--- Лёгкий патч (только исходники) ---
Архив WBO_Animation_ui-modal-auth_2026-03-20.zip:
  - main.py
  - ui_common.py
Установка: скопировать в корень репозитория / портативной папки с .py, где так запускают приложение.

--- GitHub / автообновление для пользователей .exe ---
Маленький ZIP с .py НЕ подходит: нужна полная сборка.
Из корня проекта после build.bat выполните:
  powershell -NoProfile -ExecutionPolicy Bypass -File .\pack_github_update.ps1
Архив для релиза появится в fix_output\github-update\ (имя update_WboBAMP_v....zip).
Подробности: fix_output\github-update\README.txt

Дата: 2026-03-20.
