# TDA00 Translation Risk Notes

Auxiliary only. JP wording remains primary.

## Control Marks

- Model input strips or masks `\w`.
- Final Chinese does not keep `\w`.
- Preserve ordinary punctuation, ellipses, quotes, and line intent.

## Do Not Use

- Do not use English slots.
- Do not use old Chinese fallback.
- Do not use fuzzy matching to fill unrelated IDs.
- Do not clear CN only because some external CSV JP is empty. TDA00 baseline has 3713 called JP rows and no called empty JP.

## Known Model Risks

- `deepseek-v4-pro` may output speaker names for silent lines; do not use as main full-translation model.
- `deepseek-v4-flash` may add `jp:` before simple narration; clean automatically.
- Flash may mishandle `ビッグ・マム`; keep `Big Mom`.
- Silence lines must stay silence, not become a character name.
- Short military replies must remain replies, not speaker names.

## Term And Style Risks

- `ハイヴ` stays `HIVE`; `オリジナルハイヴ` -> `原始HIVE`.
- `キング` -> `国王号`.
- `リンク` -> `链路`; `データリンク` -> `数据链`.
- `マリア様` -> `圣母玛利亚`.
- `クソッ` -> `可恶` unless local context needs a stronger profanity and user approves.
- `股間が熱くなるだろう？` in `game_t03208` is confirmed as `那儿热起来了吧？`.
- `Need to know` remains English because JP uses English.

## Context Types

- Narration: usually Will's inner voice; use natural but restrained first-person/reflective Chinese.
- Battle communications: concise radio/command wording.
- Political/memorial speeches: formal and dignified.
- Technical/system explanations: clear, literal, and consistent with terms.
- Jokes/profanity: preserve roughness when JP is rough; flag uncertain sexual/profane phrasing.

