"""
Yandex Music MCP server — личный коннектор Claude к Яндекс Музыке.

Работает локально через stdio. Токен берётся из переменной окружения
YANDEX_MUSIC_TOKEN или из файла ~/.yandex-music-mcp/token (его создаёт команда yandex-music-mcp-auth).
Использует неофициальную библиотеку yandex-music (MarshalX).
Неофициальный проект, не связан с ООО «Яндекс».
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from yandex_music import Client
from yandex_music.exceptions import UnauthorizedError, YandexMusicError

# stdout занят протоколом MCP — все логи только в stderr
logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
log = logging.getLogger("yandex-music-mcp")


mcp = FastMCP("yandex-music")

READ = ToolAnnotations(readOnlyHint=True, openWorldHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True)
DELETE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=True)

_client: Client | None = None


# ---------------------------------------------------------------- helpers


def _token_candidates() -> list[Path]:
    """Где искать файл токена. Claude Desktop может запускать сервер с урезанным
    окружением, поэтому кроме Path.home() проверяем USERPROFILE и папки выше server.py."""
    cands: list[Path] = []
    if os.environ.get("YANDEX_MUSIC_TOKEN_FILE"):
        cands.append(Path(os.environ["YANDEX_MUSIC_TOKEN_FILE"]))
    for base in (os.environ.get("USERPROFILE"), os.environ.get("HOME")):
        if base:
            cands.append(Path(base) / ".yandex-music-mcp" / "token")
    try:
        cands.append(Path.home() / ".yandex-music-mcp" / "token")
    except RuntimeError:
        pass
    for parent in Path(__file__).resolve().parents:
        cands.append(parent / ".yandex-music-mcp" / "token")
    seen, out = set(), []
    for c in cands:
        if str(c) not in seen:
            seen.add(str(c))
            out.append(c)
    return out


def _load_token() -> str:
    token = os.environ.get("YANDEX_MUSIC_TOKEN", "").strip()
    checked = []
    if not token:
        for path in _token_candidates():
            checked.append(str(path))
            try:
                if path.is_file():
                    token = path.read_text(encoding="utf-8").strip()
                    if token:
                        break
            except OSError:
                continue
    if not token:
        raise RuntimeError(
            "Нет токена Яндекс Музыки. Запусти `yandex-music-mcp-auth` "
            "или задай переменную YANDEX_MUSIC_TOKEN. Проверены пути: " + "; ".join(checked)
        )
    return token


def client() -> Client:
    global _client
    if _client is None:
        try:
            _client = Client(_load_token()).init()
        except UnauthorizedError as e:
            raise RuntimeError(
                "Токен недействителен или истёк. Перезапусти `yandex-music-mcp-auth`."
            ) from e
    return _client


def _uid() -> int:
    return client().me.account.uid


def _artists(obj: Any) -> list[str]:
    return [a.name for a in (getattr(obj, "artists", None) or []) if getattr(a, "name", None)]


def fmt_track(t: Any) -> dict[str, Any] | None:
    if t is None:
        return None
    album = (t.albums or [None])[0]
    return {
        "id": t.track_id,  # формат "trackId:albumId"
        "title": t.title + (f" ({t.version})" if getattr(t, "version", None) else ""),
        "artists": _artists(t),
        "album": album.title if album else None,
        "year": getattr(album, "year", None) if album else None,
        "genre": getattr(album, "genre", None) if album else None,
        "duration": _dur(t.duration_ms),
        "available": t.available,
    }


def fmt_album(a: Any) -> dict[str, Any]:
    return {
        "id": a.id,
        "title": a.title,
        "artists": _artists(a),
        "year": a.year,
        "genre": a.genre,
        "track_count": a.track_count,
    }


def fmt_artist(a: Any) -> dict[str, Any]:
    return {
        "id": a.id,
        "name": a.name,
        "genres": a.genres or [],
    }


def fmt_playlist(p: Any) -> dict[str, Any]:
    owner = getattr(p, "owner", None)
    return {
        "kind": p.kind,
        "owner_uid": getattr(owner, "uid", None),
        "owner": getattr(owner, "login", None) or getattr(owner, "name", None),
        "title": p.title,
        "track_count": p.track_count,
        "visibility": p.visibility,
        "description": p.description,
    }


def _dur(ms: int | None) -> str | None:
    if not ms:
        return None
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


def _fetch_tracks(ids: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i in range(0, len(ids), 100):
        chunk = ids[i : i + 100]
        if chunk:
            out += [x for x in (fmt_track(t) for t in client().tracks(chunk)) if x]
    return out


def _shorts_to_tracks(shorts: list[Any]) -> list[dict[str, Any]]:
    """TrackShort → полные треки; дотягивает недостающие одним батчем."""
    missing = [s.track_id for s in shorts if s.track is None]
    fetched = {t["id"].split(":")[0]: t for t in _fetch_tracks(missing)} if missing else {}
    out = []
    for s in shorts:
        if s.track is not None:
            out.append(fmt_track(s.track))
        else:
            t = fetched.get(str(s.track_id).split(":")[0])
            if t:
                out.append(t)
    return out


def _with_liked_at(shorts: list[Any]) -> list[dict[str, Any]]:
    """TrackShort из лайков → полные треки + liked_at (когда поставлен лайк, ISO-время)."""
    when = {str(s.track_id).split(":")[0]: getattr(s, "timestamp", None) for s in shorts}
    out = _fetch_tracks([s.track_id for s in shorts])
    for t in out:
        t["liked_at"] = when.get(str(t["id"]).split(":")[0])
    return out


def _split_id(track_id: str) -> tuple[str, str | None]:
    tid, _, aid = str(track_id).partition(":")
    return tid, aid or None


def _with_album(track_ids: list[str]) -> list[tuple[str, str]]:
    """Гарантирует пары (trackId, albumId) — без альбома плейлист трек не примет."""
    pairs, need = [], []
    for raw in track_ids:
        tid, aid = _split_id(raw)
        if aid:
            pairs.append((tid, aid))
        else:
            need.append(tid)
    if need:
        for t in client().tracks(need):
            if t and t.albums:
                pairs.append((str(t.id), str(t.albums[0].id)))
            else:
                raise ValueError(f"Не нашла альбом для трека {getattr(t, 'id', '?')}")
    return pairs


def guard(fn):
    """Переводит ошибки библиотеки в понятный текст для Claude."""
    import functools

    @functools.wraps(fn)
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except YandexMusicError as e:
            raise RuntimeError(f"Яндекс Музыка вернула ошибку: {e}") from e

    return wrapper


# ---------------------------------------------------------------- tools: чтение


@mcp.tool(annotations=READ)
@guard
def account_info() -> dict[str, Any]:
    """Проверка подключения: логин, имя и статус подписки Плюс."""
    st = client().account_status()
    acc = st.account
    return {
        "login": acc.login,
        "name": acc.full_name or acc.display_name,
        "uid": acc.uid,
        "plus": bool(st.plus and st.plus.has_plus),
    }


@mcp.tool(annotations=READ)
@guard
def search(
    query: str,
    type: Literal["all", "track", "album", "artist", "playlist"] = "all",
    limit: int = 10,
) -> dict[str, Any]:
    """Поиск по каталогу Яндекс Музыки. type сужает поиск; limit — сколько результатов в каждой категории."""
    r = client().search(query, type_=type)
    if r is None:
        return {"query": query, "results": {}}
    out: dict[str, Any] = {"query": query}
    if r.misspell_corrected:
        out["corrected_to"] = r.text
    if r.best and r.best.result is not None and type == "all":
        b = r.best.result
        conv = {"track": fmt_track, "album": fmt_album, "artist": fmt_artist, "playlist": fmt_playlist}
        if r.best.type in conv:
            out["best"] = {"type": r.best.type, **conv[r.best.type](b)}
    if r.tracks:
        out["tracks"] = [fmt_track(t) for t in r.tracks.results[:limit]]
    if r.albums:
        out["albums"] = [fmt_album(a) for a in r.albums.results[:limit]]
    if r.artists:
        out["artists"] = [fmt_artist(a) for a in r.artists.results[:limit]]
    if r.playlists:
        out["playlists"] = [fmt_playlist(p) for p in r.playlists.results[:limit]]
    return out


@mcp.tool(annotations=READ)
@guard
def get_liked_tracks(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """Треки из «Мне нравится», от последних лайков к старым, с датой лайка (liked_at). Для анализа вкуса бери limit побольше (до 500)."""
    likes = client().users_likes_tracks()
    shorts = likes.tracks if likes else []
    page = shorts[offset : offset + limit]
    return {
        "total_liked": len(shorts),
        "offset": offset,
        "tracks": _with_liked_at(page),
    }


@mcp.tool(annotations=READ)
@guard
def get_listening_history(limit: int = 50) -> dict[str, Any]:
    """Недавно прослушанные треки (история прослушиваний), сгруппированные по дням."""
    h = client().music_history(full_models_count=limit)
    days: list[dict[str, Any]] = []
    seen = 0
    for tab in (h.history_tabs if h else None) or []:
        ids: list[str] = []
        for group in tab.items or []:
            for item in group.tracks or []:
                data = item.data
                if not data or not data.item_id:
                    continue
                iid = data.item_id
                tid = iid.track_id or iid.id
                if tid:
                    ids.append(f"{tid}:{iid.album_id}" if iid.album_id else str(tid))
        ids = ids[: max(0, limit - seen)]
        if ids:
            days.append({"date": tab.date, "tracks": _fetch_tracks(ids)})
            seen += len(ids)
        if seen >= limit:
            break
    return {"days": days}


@mcp.tool(annotations=READ)
@guard
def list_my_playlists() -> list[dict[str, Any]]:
    """Все мои плейлисты (kind — идентификатор плейлиста для других инструментов)."""
    return [fmt_playlist(p) for p in client().users_playlists_list()]


@mcp.tool(annotations=READ)
@guard
def get_playlist_tracks(kind: int, owner_uid: int | None = None, limit: int = 200) -> dict[str, Any]:
    """Треки плейлиста. По умолчанию — мой плейлист; owner_uid — для чужого публичного."""
    p = client().users_playlists(kind, owner_uid)
    if p is None:
        raise ValueError(f"Плейлист {kind} не найден")
    shorts = (p.tracks or [])[:limit]
    return {"playlist": fmt_playlist(p), "tracks": _shorts_to_tracks(shorts)}


@mcp.tool(annotations=READ)
@guard
def get_album_tracks(album_id: int) -> dict[str, Any]:
    """Информация об альбоме и его треклист."""
    a = client().albums_with_tracks(album_id)
    tracks = [fmt_track(t) for vol in (a.volumes or []) for t in vol]
    return {"album": fmt_album(a), "tracks": tracks}


_PL_USER = re.compile(r"/users/([^/?#]+)/playlists/(\d+)")
_PL_UUID = re.compile(r"/playlists?/((?:lk\.)?[0-9a-fA-F-]{8,}|lk\.[^/?#]+)")
_ALBUM = re.compile(r"/album/(\d+)")


@mcp.tool(annotations=READ)
@guard
def get_playlist_by_url(url: str, limit: int = 300) -> dict[str, Any]:
    """Треки по ссылке на Яндекс Музыку — в том числе чужого публичного плейлиста.
    Понимает ссылки вида music.yandex.ru/users/<логин>/playlists/<номер>,
    music.yandex.ru/playlists/<uuid> (новый формат, в т.ч. lk.…) и ссылки на альбом /album/<id>.
    Подходит любой домен Яндекс Музыки (.ru, .com, .by, .kz и т.д.)."""
    url = url.strip()
    m = _PL_USER.search(url)
    if m:
        owner, kind = m.group(1), int(m.group(2))
        p = client().users_playlists(kind, owner)
    else:
        m = _PL_UUID.search(url)
        if m:
            p = client().playlist(m.group(1))
        else:
            m = _ALBUM.search(url)
            if m:
                return get_album_tracks(int(m.group(1)))
            raise ValueError(
                "Не узнала ссылку. Нужна ссылка на плейлист или альбом Яндекс Музыки, "
                "например music.yandex.ru/users/<логин>/playlists/1005 или music.yandex.ru/playlists/<uuid>."
            )
    if p is None:
        raise ValueError("Плейлист не найден или он приватный.")
    shorts = (p.tracks or [])[:limit]
    if not shorts and p.track_count:
        try:
            shorts = (p.fetch_tracks() or [])[:limit]
        except Exception:
            pass
    return {"playlist": fmt_playlist(p), "tracks": _shorts_to_tracks(shorts)}


@mcp.tool(annotations=READ)
@guard
def get_artist_tracks(artist_id: int, limit: int = 20) -> dict[str, Any]:
    """Популярные треки артиста."""
    r = client().artists_tracks(artist_id, page_size=limit)
    return {"artist_id": artist_id, "tracks": [fmt_track(t) for t in (r.tracks if r else [])]}


@mcp.tool(annotations=READ)
@guard
def get_similar_tracks(track_id: str) -> dict[str, Any]:
    """Похожие треки по версии Яндекса (track_id в формате "123" или "123:456")."""
    r = client().tracks_similar(_split_id(track_id)[0])
    return {
        "seed": fmt_track(r.track) if r else None,
        "similar": [fmt_track(t) for t in (r.similar_tracks if r else [])],
    }


@mcp.tool(annotations=READ)
@guard
def get_my_wave(batches: int = 1) -> dict[str, Any]:
    """Порция треков из «Моей волны» — персональных рекомендаций. batches — сколько порций (≈5 треков каждая)."""
    out: list[dict[str, Any]] = []
    queue = None
    for _ in range(max(1, min(batches, 5))):
        r = client().rotor_station_tracks("user:onyourwave", queue=queue)
        if not r or not r.sequence:
            break
        for s in r.sequence:
            if s.track:
                out.append(fmt_track(s.track))
        queue = r.sequence[-1].track.id if r.sequence[-1].track else None
    return {"tracks": out}


@mcp.tool(annotations=READ)
@guard
def get_chart(limit: int = 50) -> dict[str, Any]:
    """Текущий чарт Яндекс Музыки."""
    c = client().chart()
    shorts = (c.chart.tracks or [])[:limit] if c and c.chart else []
    tracks = _shorts_to_tracks(shorts)
    for i, (s, t) in enumerate(zip(shorts, tracks), 1):
        if t is not None:
            t["position"] = getattr(getattr(s, "chart", None), "position", None) or i
    return {"title": c.chart.title if c and c.chart else None, "tracks": tracks}


def _export_dir() -> Path:
    env = os.environ.get("YANDEX_MUSIC_EXPORT_DIR")
    if env:
        return Path(env)
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    docs = home / "Documents"
    return (docs if docs.is_dir() else home) / "Yandex Music exports"


def _safe_name(name: str) -> str:
    bad = '<>:"/\\|?*'
    name = "".join("_" if ch in bad else ch for ch in name).strip(" .")
    return name or "playlist"


@mcp.tool(annotations=WRITE)
@guard
def export_tracks_to_file(
    source: Literal["likes", "playlist"] = "likes",
    kind: int | None = None,
    owner_uid: int | None = None,
    file_name: str | None = None,
) -> dict[str, Any]:
    """Выгружает ВСЕ треки (лайки или плейлист) в текстовые файлы на компьютер, не загружая их в чат:
    .txt («Исполнитель — Название», по строке) и .csv (с альбомом, годом, жанром, id; для лайков — дата лайка).
    Файлы кладутся в «Документы/Yandex Music exports» (или в YANDEX_MUSIC_EXPORT_DIR). Для source="playlist" нужен kind."""
    if source == "likes":
        likes = client().users_likes_tracks()
        tracks = _with_liked_at(likes.tracks if likes else [])
        default = "Мне нравится"
    else:
        if kind is None:
            raise ValueError("Для source='playlist' укажи kind")
        p = client().users_playlists(kind, owner_uid)
        if p is None:
            raise ValueError(f"Плейлист {kind} не найден")
        tracks = _fetch_tracks([s.track_id for s in (p.tracks or [])])
        default = p.title or f"playlist_{kind}"

    import csv
    from datetime import date

    export_dir = _export_dir()
    export_dir.mkdir(parents=True, exist_ok=True)
    base = _safe_name(file_name or f"{default} {date.today().isoformat()}")
    txt, csv_path = export_dir / f"{base}.txt", export_dir / f"{base}.csv"

    with txt.open("w", encoding="utf-8-sig") as f:
        for t in tracks:
            f.write(f"{', '.join(t['artists'])} — {t['title']}\n")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["№", "Исполнитель", "Название", "Альбом", "Год", "Жанр", "Длительность", "Доступен", "ID", "Дата лайка"])
        for i, t in enumerate(tracks, 1):
            w.writerow([i, ", ".join(t["artists"]), t["title"], t["album"], t["year"], t["genre"],
                        t["duration"], "да" if t["available"] else "нет", t["id"],
                        (t.get("liked_at") or "")[:10]])
    return {"count": len(tracks), "txt": str(txt), "csv": str(csv_path)}


# ---------------------------------------------------------------- tools: изменения


@mcp.tool(annotations=WRITE)
@guard
def create_playlist(
    title: str, visibility: Literal["private", "public"] = "private"
) -> dict[str, Any]:
    """Создаёт новый плейлист (по умолчанию приватный). Возвращает его kind."""
    return fmt_playlist(client().users_playlists_create(title, visibility=visibility))


@mcp.tool(annotations=WRITE)
@guard
def add_tracks_to_playlist(kind: int, track_ids: list[str], at_start: bool = False) -> dict[str, Any]:
    """Добавляет треки в мой плейлист. track_ids — id из других инструментов ("123:456" или "123")."""
    pairs = _with_album(track_ids)
    p = client().users_playlists(kind)
    at = 0 if at_start else (p.track_count or 0)
    diff = json.dumps(
        [{"op": "insert", "at": at, "tracks": [{"id": t, "albumId": a} for t, a in pairs]}]
    )
    p = client().users_playlists_change(kind, diff, revision=p.revision)
    return {"added": len(pairs), "playlist": fmt_playlist(p)}


@mcp.tool(annotations=DELETE)
@guard
def remove_tracks_from_playlist(kind: int, track_ids: list[str]) -> dict[str, Any]:
    """Удаляет указанные треки из моего плейлиста."""
    want = {_split_id(t)[0] for t in track_ids}
    p = client().users_playlists(kind)
    idx = [i for i, s in enumerate(p.tracks or []) if _split_id(s.track_id)[0] in want]
    revision = p.revision
    for i in sorted(idx, reverse=True):  # с конца, чтобы индексы не съезжали
        p = client().users_playlists_delete_track(kind, i, i + 1, revision=revision)
        revision = p.revision
    return {"removed": len(idx), "playlist": fmt_playlist(p)}


@mcp.tool(annotations=DELETE)
@guard
def delete_playlist(kind: int, confirm_title: str) -> dict[str, Any]:
    """НЕОБРАТИМО удаляет мой плейлист целиком. Перед вызовом обязательно спроси пользователя.
    confirm_title — точное название удаляемого плейлиста (защита от удаления не того плейлиста)."""
    p = client().users_playlists(kind)
    if p is None:
        raise ValueError(f"Плейлист {kind} не найден")
    if (p.title or "").strip() != confirm_title.strip():
        raise ValueError(
            f"Название не совпало: у плейлиста {kind} название «{p.title}», а передано «{confirm_title}». Ничего не удалено."
        )
    ok = client().users_playlists_delete(kind)
    return {"deleted": bool(ok), "kind": kind, "title": p.title}


@mcp.tool(annotations=WRITE)
@guard
def like_tracks(track_ids: list[str]) -> dict[str, Any]:
    """Ставит лайк («Мне нравится») трекам."""
    ok = client().users_likes_tracks_add([_split_id(t)[0] for t in track_ids])
    return {"ok": bool(ok), "count": len(track_ids)}


@mcp.tool(annotations=DELETE)
@guard
def unlike_tracks(track_ids: list[str]) -> dict[str, Any]:
    """Убирает треки из «Мне нравится»."""
    ok = client().users_likes_tracks_remove([_split_id(t)[0] for t in track_ids])
    return {"ok": bool(ok), "count": len(track_ids)}


def main() -> None:
    mcp.run()  # stdio


if __name__ == "__main__":
    main()
