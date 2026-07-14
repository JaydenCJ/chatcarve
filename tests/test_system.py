"""System-message catalog: canonical events across locales.

Each row is a real-shaped system line in one of the catalog languages.
Rows are looped inside one test per event family so that adding a language
means adding rows, not tests; the assert message names the failing row.
"""

from chatcarve.system import classify, is_deleted_tombstone

E2E_LINES = [
    ("en", "Messages and calls are end-to-end encrypted."),
    ("es", "Los mensajes y las llamadas están cifrados de extremo a extremo."),
    ("de", "Nachrichten und Anrufe sind Ende-zu-Ende-verschlüsselt."),
    ("fr", "Les messages et les appels sont chiffrés de bout en bout."),
    ("pt", "As mensagens e as chamadas são criptografadas de ponta a ponta."),
    ("it", "I messaggi e le chiamate sono crittografati end-to-end."),
    ("nl", "Berichten en oproepen zijn end-to-end versleuteld."),
    ("ru", "Сообщения и звонки защищены сквозным шифрованием."),
    ("tr", "Mesajlar ve aramalar uçtan uca şifrelidir."),
    ("ja", "メッセージと通話はエンドツーエンド暗号化されています。"),
    ("zh", "訊息和通話都受到端對端加密。"),
    ("ko", "메시지와 통화는 종단간 암호화됩니다."),
    ("ar", "الرسائل والمكالمات مشفرة تماما بين الطرفين."),
]


def test_e2e_notice_all_locales():
    for locale, line in E2E_LINES:
        event = classify(line)
        assert event is not None, f"{locale}: e2e notice not recognized"
        assert event.event == "e2e_encrypted", f"{locale}: got {event.event}"


MEMBERSHIP_LINES = [
    ("member_added", "Grandma Rosa added Aunt May"),
    ("member_added", "Oma Helga hat Jonas hinzugefügt"),
    ("member_added", "Бабушка Вера добавила Диму"),
    ("member_left", "Jonas hat die Gruppe verlassen"),
    ("member_left", "Tio Beto saiu"),
    ("member_left", "Emre gruptan ayrıldı"),
    ("member_left", "지민님이 나갔습니다"),
    ("member_removed", "Rosa removed May"),
    ("member_joined", "May joined using this group's invite link"),
    ("group_created", 'Abuela Carmen creó el grupo "Posada 2023"'),
    ("group_created", 'Vovó Neide criou o grupo "Ceia de Natal"'),
    ("subject_changed", "おばあちゃんがグループ名を「家族」に変更しました"),
    ("number_changed", "Alice changed their phone number to a new number."),
]


def test_membership_and_group_events():
    for expected, line in MEMBERSHIP_LINES:
        event = classify(line)
        assert event is not None, f"not recognized: {line!r}"
        assert event.event == expected, f"{line!r}: got {event.event}"


def test_missed_video_beats_missed_voice_in_japanese():
    # ja "ビデオ通話の不在着信" contains the voice-call pattern "不在着信";
    # ordering in the catalog must keep video first.
    assert classify("ビデオ通話の不在着信").event == "missed_video_call"
    assert classify("不在着信").event == "missed_voice_call"


def test_unmatched_line_returns_none():
    assert classify("just a normal sentence about nothing") is None


DELETED_LINES = [
    "This message was deleted",
    "You deleted this message",
    "Se eliminó este mensaje.",
    "Diese Nachricht wurde gelöscht.",
    "Ce message a été supprimé",
    "Essa mensagem foi apagada",
    "Questo messaggio è stato eliminato",
    "Dit bericht is verwijderd",
    "Это сообщение было удалено",
    "Bu mesaj silindi.",
    "このメッセージは削除されました",
    "此訊息已刪除",
    "삭제된 메시지입니다.",
    "تم حذف هذه الرسالة",
]


def test_deleted_tombstones_all_locales():
    for line in DELETED_LINES:
        assert is_deleted_tombstone(line), f"not a tombstone: {line!r}"


def test_tombstone_must_match_whole_body():
    # A sentence *mentioning* deletion is a normal message.
    assert not is_deleted_tombstone("I think this message was deleted by mistake?")
    assert not is_deleted_tombstone("This message was deleted and then some")
