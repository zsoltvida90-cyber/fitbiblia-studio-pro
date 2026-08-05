# Fit Biblia 4.0 — a 3 dok összefésülése és döntések (2026-08-05)

Forrás (ebben a mappában megőrizve):
- `FB4.0_30day_master_FULL.txt` — a teljes 30 napos mesterterv (Nap 1-30). **Ez a valódi deliverable.**
- `FB4.0_30day_master_corrected_partial.txt` — ugyanaz korrektúrázva, de csak ~Nap 7-ig (csonka). Pontosabb számok, lásd lent.
- `FB4.0_fejlesztesi_javaslatok.txt` — meta-javaslatcsomag a rendszerre (ritmus, personák, CTA, mérés).

## A mag (egyesítve)
- 4 saját modell: Deficit Spektrum, Fehérje Pajzs, Súrlódási Mátrix, Adaptációs Hurok.
- 7 persona + 5 rotált CTA + 4 záró szlogen. Arculat = Obszidián (kánonnal egyező).
- Heti műsorrend, napi 2 poszt (12:00 / 19:30), fix napi típusok (Mindset, Boncolás, Protokoll, Pattern Interrupt, Labor).
- Visszatérő sorozatok: Boncolás #01-04 (mítoszrombolás, forrással), Protokollok, vasárnapi LABOR (adatviz hero).

## Számkorrekciók (a corrected variánsból, ez a helyes)
- cheat-day: "napi -500 (össz -2500)" a félreérthető "-2500" helyett.
- ezres tagolás: "20 000" (nem "20.000").
- fehérje: "1,6-2,2 g/kg".

## BEÉPÍTENDŐ
- A teljes 30 napos naptár mint tartalom-nyersanyag (a Fázis 2 template-pipeline-ba).
- 3-szintű CTA-hierarchia.
- Forrásmegjelölés-standard minden evidencia-posztnál (anti-hype pozíció).
- Heti 3 metrika (elérés, mentés/share, link-katt UTM) + 15. napi audit rutin.

## DOBANDÓ (kritikai szűrő)
- 5.3 új arculati variánsok (soft gold / matte black) — ütközik a lezárt Obszidián SSOT-tal (ART_DIRECTION_v2).
- LABOR "csiszolt arany grafikonok" ha szövegre viszik — a sárga-arany olvashatatlanság ismert kifogása. Sötét háttér + világos adat.
- 5.1 Reel-pivot MOST — a P0 a PDF+carousel pipeline, korai.
- Konkrét %-ígéretek ("10-25% elérésnövekedés reális") — kitalált, adat nélkül.
- Generikus social-guru töltelék (1-es dok fele).

## Belső ellentmondások (a dok saját magának feszül; a mi mércénk dönt)
- "6 slide minden Protokoll" szabály vs a saját Nap 4 = 7 slide.
- Nap 26 péntek "Protokoll" vs a rendszer szerint péntek = Pattern Interrupt.
- 20-21h javasolt slot vs a fixált 19:30.
- Döntő marad: `fitbiblia-carousel-nogo` minőségi mérce + a template-rendszer, NEM a merev 6-os szabály.

## Ahol MI erősebbek vagyunk
- A dok csali-logikája gyenge ("töltsd le a bio-linkről"). A miénk marad: **csali PDF + email-capture az első naptól**. Csak a CTA-hierarchiát fűzzük bele.

## Forrás-validálás kötelező gyártás előtt
Boncolás-tények (Holt Satiety Index, JAMA ~7500 lépés, Donahoo BMR) hihetők, de a `fitbiblia-validated-books-workflow` szerint ellenőrzendők, mielőtt slide-ra kerülnek.
