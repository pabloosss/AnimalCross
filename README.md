# AnimalCross

Lokalne studio AI na Windows: Ollama/Qwen + ComfyUI/Wan, zespół agentów, pamięć i animowany duszek. Wioska pozostaje planowanym interfejsem; obecna aplikacja jest panelem testowym.

## Uruchomienie

1. Zainstaluj Python 3.10+ z Tcl/Tk. Ollama i Comfy Desktop powinny już być skonfigurowane.
2. Pobierz repozytorium przez Code → Download ZIP i rozpakuj.
3. Uruchom **Uruchom.bat** z głównego folderu.
4. W Panel sterowania sprawdź ustawienia i uruchom usługi.

Przy aktualizacji zachowaj dotychczasowy folder **data** na głównym poziomie. Zawiera konfigurację, pamięć, rozmowy i importowane grafiki. Kopiuj aktualną strukturę src, assets oraz pliki startowe. Dawne pliki Python na głównym poziomie nie są już używane przez Uruchom.bat.

## Układ repozytorium

| Folder / plik | Zawartość |
| --- | --- |
| src/ | Kod panelu, agentów, duszka i sterowania usługami |
| tests/ | Testy automatyczne |
| assets/ghost/ | Duszek PNGTuber dodany przez użytkownika |
| assets/characters/ | Bandyci, gobliny i postacie retro |
| assets/world/ | Miasto i otoczenie |
| assets/interiors/ | Meble i wnętrza |
| assets/ui/ | Dymki i elementy interfejsu |
| docs/ | Instrukcje, opis paczek i historia wersji |
| data/ | Lokalne dane użytkownika, poza repozytorium |
| Uruchom.bat | Start programu |
| Testuj.bat | Uruchomienie testów na Windows |

## Funkcje i ograniczenia

Agenci przekazują sobie zadania i wyniki. Kolejne role korzystają z jednego Qwena, monitoring usług działa w tle. AI zapisuje ustalenia w data/pamiec_ai.txt. Film generuje ComfyUI/Wan; przed generacją panel zwalnia model językowy. Kontroler sprawdza wyniki narzędzi, nie ogląda jeszcze klatek filmu.

Panel pozwala uruchamiać i zatrzymywać usługi. Nie wdrożono limitowania GPU, kompletnej wioski ani automatycznego wizualnego poprawiania filmów. Szczegóły dotychczasowych wersji: [historia](docs/HISTORIA_WERSJI.md).

## Grafiki i prawa do materiałów

Spis paczek i znane ograniczenia: [ASSETY.md](docs/ASSETY.md). Repozytorium zawiera materiały różnych autorów; dostępność pliku tutaj nie przyznaje nowych praw do jego użycia. Zachowano oryginalne informacje o autorstwie. Nie nadano wspólnej licencji obejmującej wszystkie grafiki.

## Testy

Na Windows: **Testuj.bat**.

Z terminala w głównym folderze: `PYTHONPATH=src python -m unittest discover -s tests -v` (Linux/macOS).

Testy jednostkowe używają atrap usług i procesów. Rzeczywista obsługa Windows, AMD i generowanie przez Wan wymagają testów na komputerze użytkownika.
