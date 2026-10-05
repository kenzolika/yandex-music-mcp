# yandex-music-mcp

<!-- mcp-name: io.github.kenzolika/yandex-music-mcp -->

Неофициальный [MCP](https://modelcontextprotocol.io)-сервер для **Яндекс Музыки**. Подключается к Claude Desktop, Claude Code и другим MCP-клиентам и даёт ассистенту доступ к вашей библиотеке: лайкам, истории прослушиваний, «Моей волне» и плейлистам.

Сервер работает локально на вашем компьютере (stdio). Токен хранится только у вас и никуда не передаётся. Поддерживаются Windows, macOS и Linux.

> ⚠️ **Неофициальный проект.** Не связан с ООО «Яндекс» и не одобрен им. Использует неофициальную библиотеку [yandex-music](https://github.com/MarshalX/yandex-music-api): если Яндекс изменит API, сервер может временно перестать работать. Аудио сервер **не скачивает** — только работает с метаданными, лайками и плейлистами вашего аккаунта.

[English version below ↓](#english)

---

## Что умеет

| Чтение | Изменения |
|---|---|
| `account_info` — проверка подключения | `create_playlist` — новый плейлист (по умолчанию приватный) |
| `search` — поиск треков, альбомов, артистов и плейлистов | `add_tracks_to_playlist` — добавить треки |
| `get_liked_tracks` — «Мне нравится» | `remove_tracks_from_playlist` — убрать треки |
| `get_listening_history` — история прослушиваний по дням | `delete_playlist` — удалить плейлист (с проверкой названия) |
| `list_my_playlists`, `get_playlist_tracks` — ваши плейлисты | `like_tracks` / `unlike_tracks` — лайки |
| `get_playlist_by_url` — любой публичный плейлист или альбом по ссылке | `export_tracks_to_file` — выгрузка лайков или плейлиста в `.txt` и `.csv` |
| `get_album_tracks`, `get_artist_tracks` — альбомы и артисты | |
| `get_similar_tracks`, `get_my_wave`, `get_chart` — рекомендации и чарт | |

Воспроизведением сервер не управляет: музыку вы слушаете, как обычно, в приложении Яндекс Музыки, а новые плейлисты и лайки появляются там сразу.

### Примеры запросов

- «Проанализируй мои последние 300 лайков: какие жанры и десятилетия я слушаю?»
- «Что я слушал на этой неделе?»
- «Собери приватный плейлист "Осень" из 25 треков, похожих на мои последние лайки»
- «Вот плейлист друга: <ссылка>. Что из него уже есть в моих лайках?»
- «Выгрузи все мои лайки в файл»

---

## Быстрая установка

**1. Установите [uv](https://docs.astral.sh/uv/)** — он скачает и запустит коннектор:

- Windows (PowerShell):
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- macOS / Linux:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

Закройте терминал, откройте заново и проверьте: `uv --version`.

**2. Войдите в Яндекс (один раз):**

```bash
uvx --from yandex-music-mcp yandex-music-mcp-auth
```

**3. Подключите к клиенту:**

- **Claude Code** — одна команда:
  ```bash
  claude mcp add yandex-music -- uvx yandex-music-mcp
  ```
- **Claude Desktop** — откройте **Settings → Developer → Edit Config** и добавьте в файл `claude_desktop_config.json`:
  ```json
  {
    "mcpServers": {
      "yandex-music": {
        "command": "uvx",
        "args": ["yandex-music-mcp"]
      }
    }
  }
  ```

Если что-то не получилось, ниже — пошаговая установка из исходников с подробностями.

---

## Установка из исходников

Понадобятся [uv](https://docs.astral.sh/uv/) и аккаунт Яндекса. Для части функций (например, «Моей волны») может понадобиться подписка Плюс.

### 1. Установите uv

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
Закройте терминал, откройте заново и проверьте: `uv --version`.

### 2. Скачайте проект

```bash
git clone https://github.com/kenzolika/yandex-music-mcp.git
```
Или нажмите **Code → Download ZIP** на странице репозитория и распакуйте архив.

### 3. Получите токен (один раз)

```bash
cd yandex-music-mcp
uv run yandex-music-mcp-auth
```

Откроется страница входа Яндекса (`ya.ru/device`), а в терминале появится код. Войдите в аккаунт, введите код и дождитесь в терминале строки «Готово!». Токен сохранится в `~/.yandex-music-mcp/token`. Скрипт использует официальный вход Яндекса и вашего пароля не видит.

### 4. Узнайте полный путь к папке проекта

Клиенту нужно знать, где лежит проект. Самый простой способ — в терминале, в папке проекта (после шага 3 вы уже в ней):

- **Windows (PowerShell):** `(Get-Location).Path` → например, `C:\Users\Ivan\Documents\yandex-music-mcp`
- **macOS / Linux:** `pwd` → например, `/Users/ivan/yandex-music-mcp`

На Windows можно и мышкой: в Проводнике зажмите **Shift**, щёлкните по папке правой кнопкой и выберите **«Копировать как путь»**.

> **Важно для Windows:** в JSON-конфиге обратный слэш нужно удваивать: `C:\\Users\\Ivan\\Documents\\yandex-music-mcp`. Можно вместо этого писать прямые слэши — Windows их понимает: `C:/Users/Ivan/Documents/yandex-music-mcp`.

### 5а. Подключите к Claude Desktop

В Claude Desktop откройте **Settings → Developer → Edit Config** — откроется файл `claude_desktop_config.json`. Добавьте в него блок `mcpServers`, подставив свой путь из шага 4:

```json
{
  "mcpServers": {
    "yandex-music": {
      "command": "uv",
      "args": ["--directory", "C:/Users/Ivan/Documents/yandex-music-mcp", "run", "yandex-music-mcp"]
    }
  }
}
```

- **В файле уже есть другие настройки?** Не удаляйте их: добавьте `"mcpServers": { ... }` на верхний уровень рядом с ними, отделив запятой.
- **Claude не находит `uv`?** Укажите в `"command"` полный путь к нему. Его покажет `where.exe uv` (Windows) или `which uv` (macOS/Linux) — обычно это `C:/Users/Ivan/.local/bin/uv.exe` или `~/.local/bin/uv`.

Полностью закройте Claude Desktop (на Windows — через значок в трее → **Quit**, крестика окна недостаточно) и откройте снова.

### 5б. Или подключите к Claude Code

Вместо шага 5а — одна команда с путём из шага 4:

```bash
claude mcp add yandex-music -- uv --directory "C:/Users/Ivan/Documents/yandex-music-mcp" run yandex-music-mcp
```

### 6. Проверьте

Напишите в новом чате: «Проверь подключение к Яндекс Музыке». Если в ответе ваш логин — всё работает.

---

## Настройки

| Переменная | Назначение |
|---|---|
| `YANDEX_MUSIC_TOKEN` | Токен напрямую (вместо файла) |
| `YANDEX_MUSIC_TOKEN_FILE` | Путь к файлу с токеном |
| `YANDEX_MUSIC_EXPORT_DIR` | Куда сохранять выгрузки (по умолчанию `Документы/Yandex Music exports`) |

## Безопасность и приватность

- Токен даёт полный доступ к вашему аккаунту Музыки. Не публикуйте его и не добавляйте в git — `.gitignore` уже исключает файлы токена и выгрузки.
- Отозвать доступ можно на [id.yandex.ru](https://id.yandex.ru) в разделе устройств и сервисов.
- Все инструменты, которые что-то меняют, помечены для MCP-клиента как изменяющие, и Claude по умолчанию спрашивает подтверждение перед их вызовом. `delete_playlist` дополнительно требует точное название плейлиста.

## Решение проблем

- **Сервер не появился в Claude.** Проверьте JSON на лишние или пропущенные запятые, путь к проекту и путь к `uv`. Логи: `%APPDATA%\Claude\logs\mcp-server-yandex-music.log` (Windows) или `~/Library/Logs/Claude/` (macOS).
- **«Нет токена».** Выполните шаг 3 ещё раз и не закрывайте терминал, пока не появится «Готово!». В сообщении об ошибке перечислены пути, где сервер искал токен.
- **Не видно новых инструментов после обновления.** Перезапустите Claude и откройте новый чат.

---

<a id="english"></a>
## English

Unofficial [MCP](https://modelcontextprotocol.io) server for **Yandex Music**. It connects Claude Desktop, Claude Code and other MCP clients to your Yandex Music library: likes, listening history, My Wave and playlists.

The server runs locally on your machine (stdio). Your token is stored only on your computer and is never sent anywhere else. Works on Windows, macOS and Linux.

> ⚠️ **Unofficial project.** Not affiliated with or endorsed by Yandex. Built on the unofficial [yandex-music](https://github.com/MarshalX/yandex-music-api) library, so it may break temporarily if Yandex changes its API. The server does **not** download audio; it only works with metadata, likes and playlists in your account.

### Tools

| Read | Write |
|---|---|
| `account_info` — check the connection | `create_playlist` — new playlist (private by default) |
| `search` — tracks, albums, artists, playlists | `add_tracks_to_playlist` |
| `get_liked_tracks` — your liked tracks | `remove_tracks_from_playlist` |
| `get_listening_history` — history by day | `delete_playlist` — delete a playlist (requires its exact title) |
| `list_my_playlists`, `get_playlist_tracks` — your playlists | `like_tracks` / `unlike_tracks` |
| `get_playlist_by_url` — any public playlist or album by link | `export_tracks_to_file` — export likes or a playlist to `.txt` and `.csv` |
| `get_album_tracks`, `get_artist_tracks` | |
| `get_similar_tracks`, `get_my_wave`, `get_chart` — recommendations and charts | |

The server does not control playback: listen in the Yandex Music app as usual; new playlists and likes show up there immediately.

**Example prompts:** "Analyze my last 300 likes: which genres and decades do I listen to?" · "What did I listen to this week?" · "Build a private playlist 'Autumn' with 25 tracks similar to my recent likes" · "Here's my friend's playlist: <link>. Which of these tracks are already in my likes?" · "Export all my likes to a file"

### Quick install

1. Install [uv](https://docs.astral.sh/uv/). Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`; macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`. Reopen the terminal and check `uv --version`.
2. Sign in to Yandex (once): `uvx --from yandex-music-mcp yandex-music-mcp-auth`
3. Connect a client:
   - **Claude Code:** `claude mcp add yandex-music -- uvx yandex-music-mcp`
   - **Claude Desktop:** open **Settings → Developer → Edit Config** and add to `claude_desktop_config.json`:
     ```json
     {
       "mcpServers": {
         "yandex-music": { "command": "uvx", "args": ["yandex-music-mcp"] }
       }
     }
     ```

### Install from source

1. **Install uv.** Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`; macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`. Reopen the terminal and check `uv --version`.
2. **Get the code:** `git clone https://github.com/kenzolika/yandex-music-mcp.git`, or **Code → Download ZIP** on the repository page.
3. **Get a token (once):** `cd yandex-music-mcp`, then `uv run yandex-music-mcp-auth`. A Yandex sign-in page (`ya.ru/device`) opens and a code appears in the terminal. Sign in, enter the code and wait for the "Готово!" ("Done!") line. The token is saved to `~/.yandex-music-mcp/token`. This is Yandex's official OAuth device flow; the script never sees your password.
4. **Find the full path to the project folder.** In the project folder run `(Get-Location).Path` (Windows PowerShell) or `pwd` (macOS/Linux). On Windows you can also Shift + right-click the folder in Explorer → **Copy as path**. In JSON, either double the backslashes (`C:\\Users\\Ivan\\yandex-music-mcp`) or use forward slashes (`C:/Users/Ivan/yandex-music-mcp`).
5. **Connect a client.**
   - **Claude Desktop:** Settings → Developer → Edit Config opens `claude_desktop_config.json`. Add:
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
     Keep any existing settings and add `"mcpServers"` next to them, separated by a comma. If Claude can't find `uv`, put its full path in `"command"` (`where.exe uv` on Windows, `which uv` on macOS/Linux). Then fully quit Claude Desktop (on Windows: tray icon → Quit) and start it again.
   - **Claude Code:** `claude mcp add yandex-music -- uv --directory /absolute/path/to/yandex-music-mcp run yandex-music-mcp`
6. **Check:** in a new chat ask "Check my Yandex Music connection". If the answer shows your login, you're all set.

### Configuration

| Variable | Purpose |
|---|---|
| `YANDEX_MUSIC_TOKEN` | Pass the token directly instead of a file |
| `YANDEX_MUSIC_TOKEN_FILE` | Path to the token file |
| `YANDEX_MUSIC_EXPORT_DIR` | Where exports are saved (default: `Documents/Yandex Music exports`) |

### Security and privacy

- The token gives full access to your Yandex Music account. Never publish or commit it; `.gitignore` already excludes token files and exports.
- You can revoke access at [id.yandex.ru](https://id.yandex.ru) under devices and services.
- Every tool that changes something is marked as such for the MCP client, so Claude asks for confirmation before calling it. `delete_playlist` also requires the playlist's exact title.

### Troubleshooting

- **The server doesn't show up in Claude.** Check the JSON for missing or extra commas, the project path and the path to `uv`. Logs: `%APPDATA%\Claude\logs\mcp-server-yandex-music.log` (Windows) or `~/Library/Logs/Claude/` (macOS).
- **"No token" error.** Run step 3 again and keep the terminal open until "Готово!" appears. The error message lists every path where the server looked for the token.
- **New tools are missing after an update.** Restart Claude and open a new chat.

---

## Авторы · Authors

Сделано **Kenzolika & Claudiea** 🎧 — человеком и его ИИ-напарницей (Claude) за один осенний вечер.
Made by **Kenzolika & Claudiea**, a human and his AI sidekick (Claude), in one autumn evening.

## Лицензия · License

MIT, см. [LICENSE](LICENSE). Использует библиотеку [yandex-music](https://github.com/MarshalX/yandex-music-api) (LGPL-3.0) как зависимость, без изменений.
MIT, see [LICENSE](LICENSE). Uses [yandex-music](https://github.com/MarshalX/yandex-music-api) (LGPL-3.0) as an unmodified dependency.
