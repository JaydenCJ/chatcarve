"""Multi-locale detection of media placeholders and attachment references.

WhatsApp represents attachments three different ways depending on platform
and export mode, and localizes every one of them:

- **Android, "without media"**: ``<Media omitted>`` (``<Medien
  ausgeschlossen>``, ``<Multimedia omitido>``, ...).
- **Android, "with media"**: ``IMG-20240101-WA0001.jpg (file attached)``
  (``(archivo adjunto)``, ``(Datei angehängt)``, ...).
- **iOS, "with media"**: ``<attached: 00000010-PHOTO-....jpg>`` — iOS also
  emits typed "omitted" stubs (``image omitted``, ``video omitted``,
  ``imagen omitida``, ``画像は省略されました``) when exporting without media.

This module recognizes all three shapes across the catalog languages and
classifies the media type from the placeholder wording or, when a filename
survives, from WhatsApp's own filename conventions.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Pattern, Tuple

from .model import MediaRef
from .textnorm import clean_for_matching

# --- Android: <Media omitted> -----------------------------------------------

#: Localized full-line placeholders for "exported without media".
_ANDROID_OMITTED = frozenset(
    token.casefold()
    for token in [
        "<Media omitted>",  # en
        "<Multimedia omitido>",  # es
        "<Medien ausgeschlossen>",  # de
        "<Médias omis>",  # fr
        "<Mídia omitida>",  # pt-BR
        "<Arquivo de mídia oculto>",  # pt-BR (older exports)
        "<Media omessi>",  # it
        "<Media weggelaten>",  # nl
        "<Без медиафайлов>",  # ru
        "<Medya atlanmış>",  # tr
        "<メディアは含まれていません>",  # ja
        "<省略多媒體檔案>",  # zh-TW
        "<媒体省略>",  # zh-CN
        "<미디어 파일을 생략한 대화내용>",  # ko
        "<تم استبعاد الوسائط>",  # ar
    ]
)

# --- Android: filename (file attached) ---------------------------------------

#: Localized "(file attached)" suffixes; the filename precedes them.
_ANDROID_ATTACHED_RE = re.compile(
    r"^(?P<file>\S[^\n]*?)\s\((?:"
    r"file attached"  # en
    r"|archivo adjunto"  # es
    r"|Datei angehängt"  # de
    r"|fichier joint"  # fr
    r"|arquivo anexado"  # pt
    r"|file allegato"  # it
    r"|bestand bijgevoegd"  # nl
    r"|файл добавлен"  # ru
    r"|dosya ekli"  # tr
    r"|添付ファイル"  # ja
    r"|附件檔案|文件附件"  # zh
    r"|파일 첨부됨"  # ko
    r")\)$",
    re.IGNORECASE,
)

# --- iOS: <attached: filename> ------------------------------------------------

_IOS_ATTACHED_RE = re.compile(
    r"^<(?:"
    r"attached"  # en
    r"|adjunto"  # es
    r"|Anhang"  # de
    r"|pièce jointe"  # fr
    r"|anexado"  # pt
    r"|allegato"  # it
    r"|bijlage"  # nl
    r"|вложение"  # ru
    r"|ekli dosya"  # tr
    r"|添付"  # ja
    r"|附件"  # zh
    r"|첨부"  # ko
    r"|مرفق"  # ar
    r")\s?:\s?(?P<file>[^>]+)>$",
    re.IGNORECASE,
)

# --- iOS: typed "omitted" stubs -----------------------------------------------

#: Localized full-line stubs mapped to a media type.
_IOS_OMITTED: Dict[str, str] = {}


def _register_omitted(media_type: str, phrases: List[str]) -> None:
    for phrase in phrases:
        _IOS_OMITTED[phrase.casefold()] = media_type


_register_omitted(
    "image",
    [
        "image omitted",  # en
        "imagen omitida",  # es
        "Bild weggelassen",  # de
        "image absente",  # fr
        "imagem ocultada",  # pt
        "immagine omessa",  # it
        "afbeelding weggelaten",  # nl
        "изображение отсутствует",  # ru
        "görüntü dahil edilmedi",  # tr
        "画像は省略されました",  # ja
        "圖片已省略",  # zh-TW
        "图片已省略",  # zh-CN
        "이미지 생략됨",  # ko
        "الصورة غير مشمولة",  # ar
    ],
)
_register_omitted(
    "video",
    [
        "video omitted",  # en
        "video omitido",  # es
        "Video weggelassen",  # de
        "vidéo absente",  # fr
        "vídeo omitido",  # pt
        "video omesso",  # it
        "video weggelaten",  # nl
        "видео отсутствует",  # ru
        "video dahil edilmedi",  # tr
        "動画は省略されました",  # ja
        "影片已省略",  # zh-TW
        "视频已省略",  # zh-CN
        "동영상 생략됨",  # ko
        "الفيديو غير مشمول",  # ar
    ],
)
_register_omitted(
    "audio",
    [
        "audio omitted",  # en
        "audio omitido",  # es
        "Audio weggelassen",  # de
        "audio absent",  # fr
        "áudio ocultado",  # pt
        "audio omesso",  # it
        "audio weggelaten",  # nl
        "аудио отсутствует",  # ru
        "ses dahil edilmedi",  # tr
        "音声メッセージは省略されました",  # ja
        "語音訊息已省略",  # zh-TW
        "音频已省略",  # zh-CN
        "오디오 생략됨",  # ko
    ],
)
_register_omitted(
    "sticker",
    [
        "sticker omitted",  # en
        "sticker omitido",  # es
        "Sticker weggelassen",  # de
        "sticker absent",  # fr
        "figurinha omitida",  # pt
        "sticker omesso",  # it
        "стикер отсутствует",  # ru
        "çıkartma dahil edilmedi",  # tr
        "スタンプは省略されました",  # ja
        "貼圖已省略",  # zh-TW
        "스티커 생략됨",  # ko
    ],
)
_register_omitted(
    "gif",
    [
        "GIF omitted",  # en
        "GIF omitido",  # es
        "GIF weggelassen",  # de
        "GIF absent",  # fr
        "GIF omitida",  # pt
        "GIF omesso",  # it
        "GIF отсутствует",  # ru
        "GIFは省略されました",  # ja
        "GIF已省略",  # zh
        "GIF 생략됨",  # ko
    ],
)
_register_omitted(
    "document",
    [
        "document omitted",  # en
        "documento omitido",  # es
        "Dokument weggelassen",  # de
        "document absent",  # fr
        "documento ocultado",  # pt
        "documento omesso",  # it
        "документ отсутствует",  # ru
        "belge dahil edilmedi",  # tr
        "文書は省略されました",  # ja
        "文件已省略",  # zh
        "문서 생략됨",  # ko
    ],
)
_register_omitted(
    "contact",
    [
        "Contact card omitted",  # en
        "Tarjeta de contacto omitida",  # es
        "Kontaktkarte weggelassen",  # de
        "fiche contact absente",  # fr
        "cartão do contato omitido",  # pt
        "scheda contatto omessa",  # it
        "контакт отсутствует",  # ru
        "連絡先カードは省略されました",  # ja
        "聯絡人名片已省略",  # zh-TW
        "연락처 카드 생략됨",  # ko
    ],
)

# --- filename -> media type -----------------------------------------------------

_EXTENSION_TYPES: List[Tuple[Pattern[str], str]] = [
    (re.compile(r"\.(?:jpe?g|png|heic|heif)$", re.IGNORECASE), "image"),
    (re.compile(r"\.webp$", re.IGNORECASE), "sticker"),
    (re.compile(r"\.gif$", re.IGNORECASE), "gif"),
    (re.compile(r"\.(?:mp4|mov|3gp|mkv|avi)$", re.IGNORECASE), "video"),
    (re.compile(r"\.(?:opus|ogg|m4a|mp3|aac|amr|wav)$", re.IGNORECASE), "audio"),
    (re.compile(r"\.(?:vcf)$", re.IGNORECASE), "contact"),
]

#: WhatsApp's own filename conventions, e.g. ``IMG-20240101-WA0001.jpg``
#: (Android) or ``00000010-PHOTO-2024-01-01-12-00-00.jpg`` (iOS). Checked
#: after extensions so an unambiguous extension always wins.
_NAME_HINTS: List[Tuple[Pattern[str], str]] = [
    (re.compile(r"^IMG-\d{8}-WA\d+", re.IGNORECASE), "image"),
    (re.compile(r"^VID-\d{8}-WA\d+", re.IGNORECASE), "video"),
    (re.compile(r"^(?:AUD|PTT)-\d{8}-WA\d+", re.IGNORECASE), "audio"),
    (re.compile(r"^STK-\d{8}-WA\d+", re.IGNORECASE), "sticker"),
    (re.compile(r"^DOC-\d{8}-WA\d+", re.IGNORECASE), "document"),
    (re.compile(r"-PHOTO-", re.IGNORECASE), "image"),
    (re.compile(r"-VIDEO-", re.IGNORECASE), "video"),
    (re.compile(r"-AUDIO-", re.IGNORECASE), "audio"),
    (re.compile(r"-GIF-", re.IGNORECASE), "gif"),
    (re.compile(r"-STICKER-", re.IGNORECASE), "sticker"),
]


def media_type_from_filename(filename: str) -> Optional[str]:
    """Best-effort media type from a filename, or None when unknown."""
    for pattern, media_type in _EXTENSION_TYPES:
        if pattern.search(filename):
            return media_type
    for pattern, media_type in _NAME_HINTS:
        if pattern.search(filename):
            return media_type
    if re.search(r"\.pdf$|\.docx?$|\.xlsx?$|\.pptx?$|\.txt$", filename, re.IGNORECASE):
        return "document"
    return None


def match_media(body: str) -> Optional[MediaRef]:
    """Return a :class:`MediaRef` when *body* is a media placeholder.

    *body* must be the full message body (single line); anything with
    trailing caption text is not matched here — WhatsApp puts captions on
    their own continuation lines, which the parser attaches as text.
    """
    normalized = clean_for_matching(body).strip()
    if not normalized:
        return None

    if normalized.casefold() in _ANDROID_OMITTED:
        return MediaRef(filename=None, media_type=None, omitted=True)

    omitted_type = _IOS_OMITTED.get(normalized.casefold())
    if omitted_type is not None:
        return MediaRef(filename=None, media_type=omitted_type, omitted=True)

    ios = _IOS_ATTACHED_RE.match(normalized)
    if ios is not None:
        filename = ios.group("file").strip()
        return MediaRef(
            filename=filename,
            media_type=media_type_from_filename(filename),
            omitted=False,
        )

    android = _ANDROID_ATTACHED_RE.match(normalized)
    if android is not None:
        filename = android.group("file").strip()
        return MediaRef(
            filename=filename,
            media_type=media_type_from_filename(filename),
            omitted=False,
        )

    return None
