# Changelog

## Unreleased

### Новое · Added
- `get_liked_tracks` отдаёт `liked_at` — дату и время лайка; в CSV-выгрузке лайков `export_tracks_to_file` появилась колонка «Дата лайка».
  `get_liked_tracks` now returns `liked_at` (when the track was liked); likes CSV export gets a "liked date" column.

## 0.2.0 — 2026-10-05

### Новое · Added
- `get_playlist_by_url` — треки любого публичного плейлиста или альбома по ссылке: `/users/<логин>/playlists/<номер>`, `/playlists/<uuid>` (включая `lk.…`), `/album/<id>`, любой домен Яндекс Музыки.
  Tracks of any public playlist or album by its link, any Yandex Music domain.
- `delete_playlist` — удаление своего плейлиста. Помечен как необратимый и требует точное название плейлиста (`confirm_title`), чтобы не удалить не тот.
  Delete your own playlist; marked destructive and requires the exact playlist title.
- Установка из PyPI через `uvx`: `uvx yandex-music-mcp`, вход — `uvx --from yandex-music-mcp yandex-music-mcp-auth`.
  Install from PyPI with `uvx`.

### Изменено · Changed
- README: блок «Быстрая установка», подробный шаг про путь к папке проекта, отдельные шаги для Claude Desktop и Claude Code, полноценная английская версия.
  README: quick install, detailed project-path step, separate Claude Desktop / Claude Code steps, full English section.
- Зависимость `yandex-music` ограничена версиями `>=3.0,<4` — защита от ломающих обновлений библиотеки.
  `yandex-music` pinned to `>=3.0,<4`.
- Метаданные пакета: ссылки на репозиторий, поддерживаемые версии Python 3.10–3.13.
  Package metadata: project URLs, Python 3.10–3.13 classifiers.

## 0.1.0 — 2026-10-04

Первая публичная версия: поиск, лайки, история, «Моя волна», похожие треки, чарт, альбомы и артисты, создание и редактирование плейлистов, выгрузка в `.txt` / `.csv`.
First public version.
