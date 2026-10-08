# Skylands Foraging — Bulgarian Localization

Работно пространство за български превод на играта, използващо `UELocKit`.

Играта е Unreal Engine 5.6.x и използва IO Store. Извлечените оригинални
файлове и външните инструменти остават локални и не се включват в репото.

## Текущ workflow

1. `source/Game.en.locres` е английският източник.
2. `working/Game.bg.json` е работният файл за превод (1155 реда).
3. `working/Game.bg.draft.json` е изходът на локалния модел; върху него
   `tools/repair-draft-qa.py` прилага прегледаните корекции, след което
   съдържанието се копира в `working/Game.bg.json`.
4. `output/Game.bg.locres` е генерираният преводен ресурс.
5. `tools/build-standalone-skylands.ps1` създава `.pak`, `.utoc` и `.ucas`.

За display шрифта има отделен patch. Той оставя английските glyph-ове на
Chelsea Market непроменени и добавя дебела кирилица от Playpen Sans ExtraBold:

```powershell
.\tools\build-font-patch.ps1 -DeployToGame
```

Това създава `pak-output/SkylandsForaging-BG_Font_P.pak` и по желание го
копира в папката `Content/Paks` на играта. Пакетът не съдържа преводни ресурси.

Модът използва вътрешната папка `bg` и регистрира културата `bg-BG` в
собствения `Game.locmeta`. Всички работни файлове също са с наставка `bg`.

Наставката `bs` вече означава само босненската референтна локализация
(`source/reference-localizations/bs/Game.csv`), която служи като подсказка на
локалния модел. Българският слот никога не е бил `bs` — това беше остатък от
тестовия период и е премахнат.

## Инструменти

Проектът използва локалните копия на `UELocKit`, `UnrealLocres`, `UnrealPak`,
`repak` и `retoc`, зададени в игнорирания локален config файл.

Извличане на локализацията:

```powershell
.\tools\extract-skylands-localization.ps1
```

Изграждане на `.locres`:

```powershell
.\build-locres.ps1 -TranslationFormat json
```

Изграждане на IO Store мод пакет без автоматично копиране в играта:

```powershell
.\tools\build-standalone-skylands.ps1 -TranslationFormat json -DeployToGame $false -IncludeFont $true
```

Без `-IncludeFont $true` пакетът се преизгражда само с преводните ресурси:
слетият display шрифт отпада както от `tools/filelist-SkylandsForaging-BG_P.txt`,
така и от самия `.pak`. Затова при пълна сборка винаги подавай `-IncludeFont $true`.

Преди първо използване копирай `config/UELocKit.sample.config.psd1` като
`config/UELocKit.config.psd1` и попълни локалните пътища.
