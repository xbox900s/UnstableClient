# Tier Tagger DB (Fabric 1.21.4 - 1.21.11)

Client-Mod mit MySQL-Anbindung auf Tabelle `TierModDB`.

## Features
- NameTags mit Tier-Badge (Farben + Icons).
- `Owner` über Ventachu (`1b170739-2776-4bd7-b64a-c094d4cb4422`).
- `Tester!` über Namen für Tester.
- Verifizierungs-Haken hinter Namen:
  - Owner: **roter** Haken
  - Tester: **lila** Haken
  - Normal verifiziert: **grüner** Haken
- `/tier <player>` zeigt alle gesetzten Tiers des Spielers (nur vorhandene, kein `unranked`).
- `/verify <code>` prüft den Code in `TierModDB` und verknüpft den Minecraft-Account.

## Erwartete DB-Struktur (`TierModDB`)
Wesentliche Felder:

- `discord_id BIGINT PRIMARY KEY`
- `minecraft_name VARCHAR(32)`
- `minecraft_uuid CHAR(36)`
- `verify_code VARCHAR(64)`
- `verify_code_created_at DATETIME`
- `linked_at DATETIME`
- `link_source VARCHAR(16)`
- `is_blacklisted TINYINT(1)`
- optional `is_tester TINYINT(1)`
- `tier_crystal, tier_sword, tier_axe, tier_nethpot, tier_pot, tier_uhc, tier_smp`

## Build & Run (ohne Binärdateien im Repo)
Voraussetzungen lokal:
- Java 21
- Gradle installiert (oder Gradle Wrapper später selbst erzeugen)

Build:
```bash
gradle build
```

Danach liegt die Mod-JAR unter:
- `build/libs/tier-tagger-db-1.1.0.jar`

## Hinweis
Dieses Repository enthält absichtlich **keine** Binärdateien (kein ZIP, keine JAR, kein Icon-Binary), damit es sauber per PR übernommen werden kann.
