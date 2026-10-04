"""
Получение токена Яндекс Музыки через официальный вход Яндекса (OAuth Device Flow).

Запуск:  yandex-music-mcp-auth
Скрипт покажет ссылку и код. Открой ссылку, войди в Яндекс и введи код.
Токен сохранится в ~/.yandex-music-mcp/token — пароль скрипт не видит.
"""

import os
import webbrowser
from pathlib import Path

from yandex_music import Client

TOKEN_FILE = Path.home() / ".yandex-music-mcp" / "token"


def on_code(code):
    print(flush=True)
    print("1) Открой страницу:", code.verification_url, flush=True)
    print("2) Войди в свой Яндекс-аккаунт и введи код:", code.user_code, flush=True)
    print("   (жду подтверждения...)", flush=True)
    try:
        webbrowser.open(code.verification_url)
    except Exception:
        pass


def main():
    c = Client()
    token = c.device_auth(on_code=on_code)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token.access_token, encoding="utf-8")
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except OSError:
        pass
    me = Client(token.access_token).init().me.account
    print(flush=True)
    print(f"Готово! Вошли как {me.login}. Токен сохранён в {TOKEN_FILE}", flush=True)
    print("Никому его не показывай — это полный доступ к аккаунту Музыки.", flush=True)


if __name__ == "__main__":
    main()
