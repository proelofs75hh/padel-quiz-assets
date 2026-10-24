# Fair or Fault – post engine and image store

Public image store for the Instagram channel **@fairorfault** ("Your Daily Padel Quiz").
Metricool fetches the slide images from `raw.githubusercontent.com`.

- `engine/render.py` – renders `weeks/<week>/posts.json` into 1080×1350 slides in the Fair or Fault design system
- `engine/dupcheck.py` – 90-day duplicate rule against `register.json`; `--register` appends a finished week
- `engine/fonts/` – Bricolage Grotesque, Instrument Sans, JetBrains Mono (SIL Open Font License)
- `weeks/<week>/` – spec, slides and `_sheet.png` contact sheet per week
- `register.json` – every post ever planned (topic key, date, claim, verdict)
