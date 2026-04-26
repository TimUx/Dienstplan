# Entscheidungsvorlage Queue/Worker-Entkopplung

## Ziel

Bewerten, ob die aktuelle In-Process-Planung durch eine entkoppelte Queue/Worker-Architektur ersetzt werden soll.

## Option A: Status Quo (In-Process Pool)

- **Vorteile**
  - geringe Komplexitaet
  - keine zusaetzliche Infrastruktur
- **Nachteile**
  - Skalierung an API-Prozess gekoppelt
  - Recovery bei Prozess-Neustarts eingeschraenkt

## Option B: Queue + Worker

- **Vorteile**
  - horizontale Skalierung von API und Solver getrennt
  - robusteres Retry-/Backoff-Verhalten
  - bessere Isolation bei Lastspitzen
- **Nachteile**
  - hoehere Betriebs- und Architekturkomplexitaet
  - zusaetzliches Monitoring/Alerting noetig

## Entscheidungskriterien

- Planungsjobs pro Stunde (Peak)
- mittlere/95p Planungsdauer
- Fehlerrate unter Last
- Recovery-Anforderungen (RTO/RPO)
- Betriebskosten (Infra + Wartung)

## Empfehlung (Phase 5)

Kurzfristig beim aktuellen Modell bleiben und Metrikdaten sammeln.  
Ab mittelfristig wiederkehrender Lastspitzen oder steigender Fehlerraten: Pilot fuer Queue/Worker starten.
