"""Media placeholders: all three shapes, across locales.

Covers Android "<Media omitted>" full-line stubs, Android "(file
attached)" suffixes, iOS "<attached: ...>" wrappers, iOS typed "omitted"
stubs, and the filename -> media-type classifier.
"""

from chatcarve.media import match_media, media_type_from_filename

LRM = "\u200e"

ANDROID_OMITTED = [
    "<Media omitted>",
    "<Multimedia omitido>",
    "<Medien ausgeschlossen>",
    "<Médias omis>",
    "<Mídia omitida>",
    "<Media omessi>",
    "<Media weggelaten>",
    "<Без медиафайлов>",
    "<Medya atlanmış>",
    "<メディアは含まれていません>",
    "<미디어 파일을 생략한 대화내용>",
]


def test_android_omitted_all_locales():
    for line in ANDROID_OMITTED:
        media = match_media(line)
        assert media is not None, f"not recognized: {line!r}"
        assert media.omitted and media.filename is None


ANDROID_ATTACHED = [
    ("IMG-20231231-WA0012.jpg (file attached)", "IMG-20231231-WA0012.jpg", "image"),
    ("VID-20231224-WA0009.mp4 (arquivo anexado)", "VID-20231224-WA0009.mp4", "video"),
    ("DOC-20231003-WA0003.pdf (Datei angehängt)", "DOC-20231003-WA0003.pdf", "document"),
    ("PTT-20240101-WA0001.opus (archivo adjunto)", "PTT-20240101-WA0001.opus", "audio"),
    ("STK-20240101-WA0002.webp (fichier joint)", "STK-20240101-WA0002.webp", "sticker"),
]


def test_android_attached_locales_and_types():
    for line, filename, media_type in ANDROID_ATTACHED:
        media = match_media(line)
        assert media is not None, f"not recognized: {line!r}"
        assert not media.omitted
        assert media.filename == filename
        assert media.media_type == media_type, f"{line!r}: got {media.media_type}"


def test_ios_attached_english():
    media = match_media("<attached: 00000007-PHOTO-2024-02-14-09-18-22.jpg>")
    assert media.filename == "00000007-PHOTO-2024-02-14-09-18-22.jpg"
    assert media.media_type == "image"


def test_ios_attached_french_spaced_colon():
    # French puts a space *before* the colon: "<pièce jointe : ...>".
    media = match_media("<pièce jointe : 00000012-PHOTO-2024-01-06-14-05-37.jpg>")
    assert media is not None
    assert media.filename == "00000012-PHOTO-2024-01-06-14-05-37.jpg"


def test_ios_attached_with_lrm_prefix():
    media = match_media(f"{LRM}<attached: 00000031-VIDEO-2024-01-01-00-03-10.mp4>")
    assert media is not None
    assert media.media_type == "video"


IOS_OMITTED = [
    ("image omitted", "image"),
    ("imagen omitida", "image"),
    ("画像は省略されました", "image"),
    ("圖片已省略", "image"),
    ("이미지 생략됨", "image"),
    ("video omitted", "video"),
    ("vidéo absente", "video"),
    ("audio omitted", "audio"),
    ("sticker omitted", "sticker"),
    ("GIF omitted", "gif"),
    ("document omitted", "document"),
    ("Contact card omitted", "contact"),
]


def test_ios_typed_omitted_stubs():
    for line, media_type in IOS_OMITTED:
        media = match_media(line)
        assert media is not None, f"not recognized: {line!r}"
        assert media.omitted
        assert media.media_type == media_type, f"{line!r}: got {media.media_type}"


def test_non_placeholders_are_not_media():
    assert match_media("see the attached file tomorrow") is None
    assert match_media("<not a real placeholder>") is None
    # Text following a placeholder on the same line means it is not one;
    # real captions arrive on their own continuation lines.
    assert match_media("image omitted lol") is None


FILENAME_TYPES = [
    ("holiday.HEIC", "image"),
    ("clip.MOV", "video"),
    ("voice.m4a", "audio"),
    ("notes.docx", "document"),
    ("granddad.vcf", "contact"),
    ("00000031-GIF-2024-01-01-00-00-00.mp4", "video"),  # extension beats hint
    ("mystery.bin", None),
]


def test_media_type_from_filename():
    for filename, expected in FILENAME_TYPES:
        assert media_type_from_filename(filename) == expected, filename
