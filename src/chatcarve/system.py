"""Multi-locale catalog of WhatsApp system messages.

System messages ("Messages and calls are end-to-end encrypted", "Alice
added Bob", "You created group X") are written in the *phone's UI
language*, so a parser that only knows the English wording silently turns
every non-English system line into a fake chat message. chatcarve detects
system lines **structurally** first (Android: no ``Author: `` part; iOS: a
leading U+200E mark) and then uses this catalog to assign a canonical
event name. A structural system line that matches nothing is still emitted
as a system message with event ``"unknown"`` — classification refines, it
never gates.

Languages covered by the catalog and the test corpus: en, es, de, fr, pt,
it, nl, ru, tr, ja, zh, ko, ar. Adding a language is a pull request that
touches only this file plus a corpus fixture (see docs/locale-support.md).
"""

from __future__ import annotations

import re
from typing import List, Optional, Pattern, Tuple

from .model import SystemEvent
from .textnorm import clean_for_matching

#: Canonical event names, in the order patterns are tried. More specific
#: events come first so e.g. "missed video call" never falls through to a
#: broader pattern.
EVENTS = (
    "e2e_encrypted",
    "group_created",
    "subject_changed",
    "icon_changed",
    "description_changed",
    "member_added",
    "member_removed",
    "member_left",
    "member_joined",
    "number_changed",
    "missed_video_call",
    "missed_voice_call",
    "disappearing_changed",
    "security_code_changed",
    "unknown",
)


def _compile(patterns: List[str]) -> List[Pattern[str]]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


# Each entry: (canonical event, [regex, ...]). Patterns are matched with
# re.search against a normalized line (direction marks stripped, exotic
# spaces collapsed). Comments name the locale each pattern serves.
_CATALOG: List[Tuple[str, List[Pattern[str]]]] = [
    (
        "e2e_encrypted",
        _compile(
            [
                r"end-to-end encrypted",  # en
                r"cifrad[oa]s? de extremo a extremo",  # es
                r"ende-zu-ende-verschlüsselt",  # de
                r"chiffr[ée]e?s? de bout en bout",  # fr
                r"criptografad[oa]s? de ponta a ponta",  # pt
                r"crittografat[ei] end-to-end",  # it
                r"end-to-end versleuteld",  # nl
                r"сквозным шифрованием",  # ru
                r"uçtan uca şifreli",  # tr
                r"エンドツーエンド暗号化",  # ja
                r"端對端加密|端到端加密",  # zh-TW / zh-CN
                r"종단간 암호화",  # ko
                r"مشفرة تماما",  # ar (normalized without diacritics)
            ]
        ),
    ),
    (
        "group_created",
        _compile(
            [
                r"created (?:the )?group|created this group",  # en
                r"creó el grupo|creaste el grupo",  # es
                r"hat die gruppe .*erstellt|gruppe .*erstellt",  # de
                r"a créé le groupe|avez créé le groupe",  # fr
                r"criou o grupo|você criou o grupo",  # pt
                r"ha creato il gruppo|hai creato il gruppo",  # it
                r"heeft de groep .*gemaakt|groep .*gemaakt",  # nl
                r"создал[аи]? группу",  # ru
                r"grubunu oluşturdu",  # tr
                r"グループ.*を作成しました",  # ja
                r"建立了群組|创建了群组",  # zh
                r"그룹을 만들었습니다",  # ko
                r"أنشأ المجموعة",  # ar
            ]
        ),
    ),
    (
        "subject_changed",
        _compile(
            [
                r"changed the subject|changed the group name",  # en
                r"cambió el asunto|cambió el nombre del grupo",  # es
                r"hat den betreff .*geändert|den gruppennamen .*geändert",  # de
                r"a changé le sujet|a modifié le nom du groupe",  # fr
                r"mudou o assunto|mudou o nome do grupo",  # pt
                r"ha cambiato l'oggetto|ha cambiato il nome del gruppo",  # it
                r"изменил[аи]? тему|изменил[аи]? название группы",  # ru
                r"グループ名を.*に変更しました",  # ja
                r"更改了群組名稱|更改了群名",  # zh
                r"그룹 이름을 .*변경했습니다",  # ko
            ]
        ),
    ),
    (
        "icon_changed",
        _compile(
            [
                r"changed this group's icon|changed the group icon",  # en
                r"cambió el ícono de este grupo|cambió el icono",  # es
                r"hat das gruppenbild geändert",  # de
                r"a changé l'icône de ce groupe",  # fr
                r"mudou a imagem do grupo",  # pt
                r"ha cambiato l'icona del gruppo",  # it
                r"グループのアイコンを変更しました",  # ja
                r"更換了群組圖示",  # zh
            ]
        ),
    ),
    (
        "description_changed",
        _compile(
            [
                r"changed the group description",  # en
                r"cambió la descripción del grupo",  # es
                r"hat die gruppenbeschreibung geändert",  # de
                r"a changé la description du groupe",  # fr
                r"mudou a descrição do grupo",  # pt
                r"グループの説明を変更しました",  # ja
            ]
        ),
    ),
    # Membership events. Order matters: "removed" before "added" would not,
    # but "joined using the invite link" must be tried before the generic
    # verbs below it in this list — hence member_joined precedes nothing
    # here and each verb set is kept mutually exclusive per language.
    (
        "member_joined",
        _compile(
            [
                r"joined using (?:this group's|the) invite link",  # en
                r"se unió (?:al grupo )?usando el enlace",  # es
                r"ist über den einladungslink .*beigetreten",  # de
                r"a rejoint le groupe via le lien",  # fr
                r"entrou usando o link de convite",  # pt
                r"招待リンクから参加しました",  # ja
                r"透過群組邀請連結加入|通过群邀请链接加入",  # zh
            ]
        ),
    ),
    (
        "member_added",
        _compile(
            [
                r"\badded\b",  # en ("Alice added Bob", "You were added")
                r"añadió a|te añadió",  # es
                r"hinzugefügt",  # de ("... hat dich hinzugefügt")
                r"a ajouté|vous a ajouté",  # fr
                r"adicionou",  # pt
                r"ha aggiunto",  # it
                r"heeft .*toegevoegd",  # nl
                r"добавил[аи]?",  # ru
                r"gruba ekledi|grubuna ekledi",  # tr
                r"を追加しました",  # ja
                r"新增了|把.*加入",  # zh
                r"님을 추가했습니다",  # ko
                r"بإضافة",  # ar ("قام ... بإضافة ...")
            ]
        ),
    ),
    (
        "member_removed",
        _compile(
            [
                r"\bremoved\b",  # en
                r"eliminó a|te eliminó",  # es (group context)
                r"wurde entfernt|hat .*entfernt",  # de
                r"a retiré|a exclu",  # fr
                r"removeu",  # pt
                r"ha rimosso",  # it
                r"удалил[аи]?",  # ru
                r"を削除しました",  # ja (member removal)
                r"移除了",  # zh
                r"님을 내보냈습니다",  # ko
            ]
        ),
    ),
    (
        "member_left",
        _compile(
            [
                r"\bleft\b",  # en ("Bob left")
                r"salió del grupo",  # es
                r"hat die gruppe verlassen",  # de
                r"a quitté",  # fr
                r"saiu",  # pt
                r"è uscit[oa]",  # it
                r"heeft de groep verlaten",  # nl
                r"покинул[аи]?",  # ru
                r"gruptan ayrıldı",  # tr
                r"が退出しました|グループを退出しました",  # ja
                r"退出了",  # zh
                r"님이 나갔습니다",  # ko
                r"غادر",  # ar
            ]
        ),
    ),
    (
        "number_changed",
        _compile(
            [
                r"changed their phone number|changed to ",  # en
                r"cambió su número de teléfono",  # es
                r"telefonnummer .*ge(?:wechselt|ändert)",  # de
                r"a changé de numéro",  # fr
                r"mudou de número",  # pt
                r"電話番号を変更しました",  # ja
                r"번호를 변경했습니다",  # ko
            ]
        ),
    ),
    (
        "missed_video_call",
        _compile(
            [
                r"missed video call",  # en
                r"videollamada perdida",  # es
                r"verpasster videoanruf",  # de
                r"appel vidéo manqué",  # fr
                r"chamada de vídeo perdida",  # pt
                r"videochiamata persa",  # it
                r"пропущенный видеозвонок",  # ru
                r"cevapsız görüntülü arama",  # tr
                r"ビデオ通話の不在着信",  # ja
                r"未接視訊通話|未接视频通话",  # zh
                r"부재중 영상통화",  # ko
                r"مكالمة فيديو فائتة",  # ar
            ]
        ),
    ),
    (
        "missed_voice_call",
        _compile(
            [
                r"missed voice call",  # en
                r"llamada perdida",  # es
                r"verpasster sprachanruf",  # de
                r"appel vocal manqué",  # fr
                r"chamada de voz perdida",  # pt
                r"chiamata vocale persa",  # it
                r"пропущенный аудиозвонок",  # ru
                r"cevapsız sesli arama",  # tr
                r"不在着信",  # ja
                r"未接語音通話|未接语音通话",  # zh
                r"부재중 음성통화",  # ko
                r"مكالمة صوتية فائتة",  # ar
            ]
        ),
    ),
    (
        "disappearing_changed",
        _compile(
            [
                r"disappearing messages|message timer",  # en
                r"mensajes temporales",  # es
                r"selbstlöschende nachrichten",  # de
                r"messages éphémères",  # fr
                r"mensagens temporárias",  # pt
                r"messaggi effimeri",  # it
                r"исчезающие сообщения",  # ru
                r"消えるメッセージ",  # ja
                r"限時訊息|阅后即焚",  # zh
                r"사라지는 메시지",  # ko
            ]
        ),
    ),
    (
        "security_code_changed",
        _compile(
            [
                r"security code .*changed",  # en
                r"código de seguridad .*cambió|cambió el código de seguridad",  # es
                r"sicherheitsnummer .*geändert",  # de
                r"code de sécurité .*a changé",  # fr
                r"código de segurança .*mudou",  # pt
                r"セキュリティコードが変更されました",  # ja
            ]
        ),
    ),
]

# "This message was deleted" tombstones are *authored* lines, not system
# lines, so they get their own catalog checked against message bodies.
_DELETED_PATTERNS: List[Pattern[str]] = _compile(
    [
        r"^this message was deleted\.?$|^you deleted this message\.?$",  # en
        r"^se eliminó este mensaje\.?$|^eliminaste este mensaje\.?$",  # es
        r"^diese nachricht wurde gelöscht\.?$|^du hast diese nachricht gelöscht\.?$",  # de
        r"^ce message a été supprimé\.?$|^vous avez supprimé ce message\.?$",  # fr
        r"^essa mensagem foi apagada\.?$|^você apagou esta mensagem\.?$|^apagou esta mensagem\.?$",  # pt
        r"^questo messaggio è stato eliminato\.?$|^hai eliminato questo messaggio\.?$",  # it
        r"^dit bericht is verwijderd\.?$|^u hebt dit bericht verwijderd\.?$",  # nl
        r"^это сообщение было удалено\.?$|^вы удалили это сообщение\.?$",  # ru
        r"^bu mesaj silindi\.?$|^bu mesajı sildiniz\.?$",  # tr
        r"^このメッセージは削除されました。?$|^メッセージを削除しました。?$",  # ja
        r"^此訊息已刪除。?$|^你已刪除這則訊息。?$|^此消息已删除。?$",  # zh
        r"^삭제된 메시지입니다\.?$|^메시지를 삭제했습니다\.?$",  # ko
        r"^تم حذف هذه الرسالة\.?$",  # ar
    ]
)


def classify(text: str) -> Optional[SystemEvent]:
    """Classify a structural system line into a canonical event.

    Returns None when no catalog pattern matches; the caller decides what
    that means (the parser emits ``SystemEvent("unknown")`` for structural
    system lines and treats non-matches on authored lines as plain text).
    """
    normalized = clean_for_matching(text).strip()
    for event, patterns in _CATALOG:
        for pattern in patterns:
            if pattern.search(normalized):
                return SystemEvent(event=event)
    return None


def is_deleted_tombstone(text: str) -> bool:
    """True when an *authored* body is a "this message was deleted" stub."""
    normalized = clean_for_matching(text).strip()
    return any(p.match(normalized) for p in _DELETED_PATTERNS)
