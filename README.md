# yandex-music-mcp

Неофициальный [MCP](https://modelcontextprotocol.io)-сервер для **Яндекс Музыки**. Подключается к Claude Desktop, Claude Code и другим MCP-клиентам и даёт ассистенту доступ к вашей библиотеке: лайкам, истории, «Моей волне», плейлистам.

Работает локально на вашем компьютере (stdio). Токен хранится только у вас, никуда не отправляется.
Подходит для Windows, macOS и Linux.

> ⚠️ **Неофициальный проект.** Не связан с ООО «Яндекс» и не одобрен им. Использует неофициальную библиотеку [yandex-music](https://github.com/MarshalX/yandex-music-api); если Яндекс изменит API, сервер может временно перестать работать. Сервер **не скачивает** аудио: он работает только с метаданными, лайками и плейлистами вашего аккаунта.

[English below ↓](#english)

---

## Что умеет

| Чтение | Изменения |
|---|---|
| `account_info` — проверка подключения | `create_playlist` — новый плейлист (по умолчанию приватный) |
| `search` — поиск треков, альбомов, артистов, плейлистов | `add_tracks_to_playlist` |
| `get_liked_tracks` — «Мне нравится» | `remove_tracks_from_playlist` |
| `get_listening_history` — история по дням | `like_tracks` / `unlike_tracks` |
| `list_my_playlists`, `get_playlist_tracks` | `export_tracks_to_file` — выгрузка лайков или плейлиста в `.txt` и `.csv` |
| `get_album_tracks`, `get_artist_tracks` | |
| `get_similar_tracks`, `get_my_wave`, `get_chart` | |

Воспроизведением сервер не управляет: слушаете, как обычно, в приложении Яндекс Музыки, а созданные плейлисты и лайки появляются там сразу.

### Примеры запросов

- «Проанализируй мои последние 300 лайков: какие жанры и десятилетия я слушаю?»
- «Что я слушал на этой неделе?»
- «Собери приватный плейлист "Осень" из 25 треков, похожих на мои последние лайки»
- «Выгрузи все мои лайки в файл»

---

## Установка

Понадобятся [uv](https://docs.astral.sh/uv/) и аккаунт Яндекса. Для части функций (например, «Моя волна») может требоваться подписка Плюс.

### 1. Установите uv

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Перезапустите терминал и проверьте: `uv --version`.

### 2. Скачайте проект

```bash
git clone https://github.com/<user>/yandex-music-mcp.git
```
или скачайте ZIP со страницы репозитория и распакуйте.

### 3. Получите токен (один раз)

```bash
cd yandex-music-mcp
uv run yandex-music-mcp-auth
```

Откроется страница входа Яндекса (`ya.ru/device`), а в терминале появится код. Войдите в аккаунт, введите код и дождитесь строки «Готово!». Токен сохранится в `~/.yandex-music-mcp/token`. Скрипт использует официальный OAuth-вход Яндекса и не видит ваш пароль.

> **Windows:** запускайте в обычном **Windows PowerShell** или Терминале, **не в PowerShell ISE**: ISE не показывает вывод программы, и код не появится.

### 4. Подключите к Claude Desktop

**Settings → Developer → Edit Config** откроет `claude_desktop_config.json`. Добавьте в него на верхний уровень:

```json
{
  "mcpServers": {
    "yandex-music": {
      "command": "uv",
      "args": ["--directory", "/ПОЛНЫЙ/ПУТЬ/К/yandex-music-mcp", "run", "yandex-music-mcp"]
    }
  }
}
```

- На Windows путь пишется с двойными слэшами: `"C:\\Users\\ИМЯ\\yandex-music-mcp"`.
- Если Claude не находит `uv`, укажите полный путь. Его покажет команда `where.exe uv` (Windows) или `which uv` (macOS/Linux). Обычно это `C:\\Users\\ИМЯ\\.local\\bin\\uv.exe` или `~/.local/bin/uv`.
- Если в файле уже есть другие настройки, не удаляйте их, а добавьте блок `"mcpServers"` рядом с ними, через запятую.

Полностью закройте Claude (на Windows: через значок в трее → Quit) и откройте снова. Проверка: «проверь подключение к Яндекс Музыке».

### Claude Code

```bash
claude mcp add yandex-music -- uv --directory /ПОЛНЫЙ/ПУТЬ/К/yandex-music-mcp run yandex-music-mcp
```

---

## Настройки

| Переменная | Назначение |
|---|---|
| `YANDEX_MUSIC_TOKEN` | Токен напрямую (вместо файла) |
| `YANDEX_MUSIC_TOKEN_FILE` | Путь к файлу с токеном |
| `YANDEX_MUSIC_EXPORT_DIR` | Куда сохранять выгрузки (по умолчанию `Документы/Yandex Music exports`) |

## Безопасность и приватность

- Токен даёт полный доступ к вашему аккаунту Музыки. Не публикуйте его и не коммитьте: `.gitignore` уже исключает файлы токена и выгрузки.
- Отозвать доступ можно на [id.yandex.ru](https://id.yandex.ru) в разделе устройств и сервисов.
- Все инструменты, которые что-то меняют, помечены для MCP-клиента как изменяющие, и Claude по умолчанию спрашивает подтверждение перед их вызовом.

## Решение проблем

- **Сервер не появился в Claude.** Проверьте JSON на лишние или пропущенные запятые и путь к `uv`. Логи: `%APPDATA%\Claude\logs\mcp-server-yandex-music.log` (Windows) или `~/Library/Logs/Claude/` (macOS).
- **«Нет токена».** Выполните `uv run yandex-music-mcp-auth` и дождитесь «Готово!». В сообщении об ошибке перечислены пути, где сервер искал токен.
- **Новые инструменты не видны** после обновления. Перезапустите Claude и откройте новый чат.

---

<a id="english"></a>
## English

Unofficial MCP server for **Yandex Music**. Lets Claude (or any MCP client) search the catalog, read your likes, listening history, My Wave and playlists, create and edit playlists, like tracks, and export your library to `.txt`/`.csv`. It runs locally over stdio, and your token stays on your machine. It does **not** download audio. Not affiliated with Yandex.

**Quick start:** install [uv](https://docs.astral.sh/uv/), clone the repo, run `uv run yandex-music-mcp-auth` (OAuth device flow; on Windows use regular PowerShell, not ISE), then add the following to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "yandex-music": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/yandex-music-mcp", "run", "yandex-music-mcp"]
    }
  }
}
```

Restart Claude Desktop fully. Environment variables: `YANDEX_MUSIC_TOKEN`, `YANDEX_MUSIC_TOKEN_FILE`, `YANDEX_MUSIC_EXPORT_DIR`.

## License

MIT. See [LICENSE](LICENSE). Built on top of [yandex-music](https://github.com/MarshalX/yandex-music-api) (LGPL-3.0), which is used as an unmodified dependency.
