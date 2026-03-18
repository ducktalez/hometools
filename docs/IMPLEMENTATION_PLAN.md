# Implementation Plan

## Next tasks

- Scheduler um echte, explizit aktivierte Wartungsaktionen erweitern (z. B. Reports, Prewarm-Hinweise, Sync-Vorschläge)
- Deduplizierung/Heuristiken für wiederkehrende NAS-, Cache- und Metadaten-Probleme weiter verfeinern
- Cooldown/Noise-Schutz um bekannte Noise-Quellen, Quell-spezifische Schwellen und ggf. manuelle Acknowledgements erweitern

## Done

- CLI-Dashboard (`stream-dashboard`) — kombinierte Ansicht aus Issues, TODO-Kandidaten und letztem Scheduler-Lauf als Box-Drawing-Tabelle; `--json` und `--fail-on-match` Flags; Makefile-Targets `dashboard` / `dashboard-json`
- Verwaiste `.tmp_*`-Testverzeichnisse aufgeräumt und in `.gitignore` eingetragen
- Issues/Tasks-Leiste aus der Browser-UI entfernt — Issues/TODOs werden nur noch serverseitig geloggt und über API-Endpunkte bereitgestellt
- Katalog-API-Endpunkte optimiert: Cache-First statt Library-Check-First → Server ist sofort nutzbar während Index-Rebuild

