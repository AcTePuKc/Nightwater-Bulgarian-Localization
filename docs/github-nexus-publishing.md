# GitHub и Nexus release workflow

## GitHub архиви

Локално се изграждат два install-ready архива:

```powershell
.\release\package-release.ps1 -Version 0.1.0
```

Всеки архив има коренова папка `SkylandsForaging`, затова се разархивира
директно в папката на играта:

```text
SkylandsForaging/
└── Content/
    └── Paks/
```

`SkylandsForaging-Bulgarian-Localization-*.zip` съдържа превода и включения
шрифт. `SkylandsForaging-Universal-Font-*.zip` съдържа само универсалния
шрифт.

## Nexus

Публичното име на играта е Nightwater. `SkylandsForaging` е вътрешното Unreal
project име и остава само в техническите asset и package пътища. Nexus game ID
`10529` е страницата на Nightwater.

Трябва да се създадат отделни mod страници за:

1. Bulgarian Localization
2. Universal Display Font

След ръчното качване на първия файл към всяка страница се добавят тези
repository secrets:

- `NEXUS_API_KEY`
- `NEXUS_FILE_ID_BULGARIAN_LANGUAGE`
- `NEXUS_FILE_ID_UNIVERSAL_FONT`

Тези три стойности са достатъчни за обновяване на вече създадените Nexus
файлове. Workflow-ът не изпраща Nexus changelog, защото тази опция изисква
отделен `mod_id`; описанието и версията на файла се обновяват директно чрез
`file_id`.
