# Output formats

## JSONL

`chatcarve parse` emits one JSON object per message, keys sorted, UTF-8
without ASCII escaping. The schema is stable within a major version; every
key is always present (absent concepts are `null`, never missing keys).

```json
{
  "author": "Dev",
  "index": 3,
  "kind": "text",
  "line": 4,
  "media": null,
  "raw_timestamp": "30/08/2024, 10:15:11",
  "system": null,
  "text": "Right, who's driving?",
  "timestamp": "2024-08-30T10:15:11"
}
```

| Key | Type | Meaning |
|---|---|---|
| `index` | int | 0-based message position in the export |
| `timestamp` | string \| null | ISO 8601 local time (exports carry no timezone); `null` if the date was invalid under the chosen order |
| `raw_timestamp` | string | the timestamp exactly as written in the file, so nothing is lost to normalization |
| `author` | string \| null | sender display name; `null` for system messages |
| `kind` | string | `text`, `media`, `system`, or `deleted` |
| `text` | string | full message text (multi-line joined with `\n`), or the original placeholder line for media/system |
| `line` | int | 1-based line number of the message header in the source file |
| `media` | object \| null | `{filename, media_type, omitted}` — see below |
| `system` | object \| null | `{event}` — a canonical event name |

### `media`

- `filename` — the attachment filename, or `null` when the chat was
  exported *without media* ("media omitted").
- `media_type` — `image`, `video`, `audio`, `sticker`, `gif`, `document`,
  `contact`, or `null` when unknown. Derived from the placeholder wording
  or from WhatsApp's filename conventions (`IMG-…-WA0001.jpg`,
  `…-PHOTO-…`).
- `omitted` — `true` when the file itself is not in the export.

### `system` events

`e2e_encrypted`, `group_created`, `subject_changed`, `icon_changed`,
`description_changed`, `member_added`, `member_removed`, `member_left`,
`member_joined`, `number_changed`, `missed_voice_call`,
`missed_video_call`, `disappearing_changed`, `security_code_changed`, and
`unknown` for a structurally-system line no catalog pattern matched (the
original wording is always preserved in `text`).

## Markdown

`--markdown` renders a readable archive document: one `###` heading per
calendar day, bold time + author per message, system lines in italics.
Media references become links relative to `--media-dir` — images as
embeds (`![…](…)`), everything else as plain links — so the document
works when placed next to the exported attachment folder. Chat text is
escaped so message content can never inject Markdown structure.
