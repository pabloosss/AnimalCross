# AnimalCross

Lokalne studio AI na Windows: Ollama/Qwen + ComfyUI/Wan, zespół agentów, pamięć i animowany duszek. Wersja 0.7 otwiera się w animowanej wiosce powiązanej z rzeczywistymi zdarzeniami zespołu.

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

## Ruch, test i stała praca — 0.7

- NPC stale patrolują ścieżki. Po otrzymaniu pracy idą do swojego stanowiska; podczas przekazania wiadomości odwiedzają budynek odbiorcy i wracają. Chodzenie korzysta z animacji Front/Back/Left/Right Walking. Przy stanowisku pojawia się animowane biurko z dokumentem i piórem.
- **Test wioski · bez AI**: około 38 sekund symulacji, bez uruchamiania usług, zapisu pamięci i generowania. **Pauza testu** zatrzymuje pokaz, **Zakończ test** wraca do patrolu. Podczas prawdziwego zlecenia test jest zablokowany.
- **Stała praca AI: pomysły**: po ręcznym włączeniu kolejne rzeczywiste zadania przygotowują nowe pomysły i scenariusze, sprawdzają środowisko i proszą operatora o zapis propozycji do pamięci. Ollama i ComfyUI muszą działać. Następne zlecenie zaczyna się do 10 sekund po zakończeniu poprzedniego. Każde ma osobny kontekst i zapis historii. Tryb nie uruchamia renderów ani publikacji. Zużywa zasoby do chwili wyłączenia. Nie włącza się sam po restarcie; błąd wyłącza nowe zlecenia.
- **Dziennik zadań**: aktualizowany na żywo, godzina, wykonawca, przekazanie i rezultat. Pokazuje ostatnie 500 wpisów sesji, a trwały zapis rzeczywistych zleceń jest w **Wyniki i historia**. Wpisy TEST nie są rzeczywistym wynikiem AI.
- Odznaczenie stałej pracy pozwala dokończyć bieżące zadanie. **Przerwij pracę** blokuje dalsze działania i wyłącza nowe zlecenia; aktywne zapytanie Ollama może jeszcze kończyć się w tle.

NPC w patrolu nie wykonuje obliczeń AI. Ciągłe zadania korzystają z dotychczasowego zespołu i wspólnego modelu; nie oznacza to sześciu równoczesnych modeli na GPU.

## Wioska AI — 0.6

W zakładce **Wioska AI** wpisz opis, np. „Duszek otwiera leśną kawiarnię”. Wybierz **Przygotuj pomysł** (bez generacji) albo **Stwórz krótki film** (zlecenie generacji jednego klipu). Kliknij mieszkańca, aby zobaczyć jego aktualną czynność. Domy i animacje NPC korzystają z materiałów w assets; przy brakujących obrazach pojawiają się proste symbole.

- Ratusz: koordynator przygotowuje plan.
- Pracownia: scenarzysta opracowuje scenę.
- Warsztat: technik sprawdza API ComfyUI równolegle ze scenarzystą. Technik jest modułem diagnostycznym, nie osobnym modelem AI.
- Studio: operator używa narzędzi i buduje workflow.
- Wieża: kontroler porównuje wynik z dowodami narzędzi.
- Biblioteka: moduł pamięci dopisuje ustalenia do notatnika.

**Wyniki i historia** pokazują zapisane zlecenia, przekazane wiadomości i pliki zwrócone przez narzędzie generowania. Wybrany plik otwiera się w przeglądarce przez ComfyUI, które musi być włączone. Ręczne generacje z zakładki Zaawansowane nie są jeszcze dodawane do tej listy. Zakończenie obsługi zlecenia nie oznacza automatycznie, że powstał film: przeczytaj wynik i dowody.

Zlecenia zapisują się w `data/productions`, wyjścia renderów w `data/renders`. Po zamknięciu podczas pracy zlecenie zostanie oznaczone jako przerwane. Nie jest automatycznie powtarzane: render może nadal działać na serwerze. Przycisk przerwania blokuje dalsze wywołania zespołu i wysyła `/interrupt` do ComfyUI; aktywna odpowiedź Ollama może jeszcze kończyć się w tle. Nie czyści kolejki ComfyUI.

## Funkcje i ograniczenia

Agenci przekazują sobie zadania i wyniki. Kolejne role korzystają z jednego Qwena, monitoring usług działa w tle. AI zapisuje ustalenia w data/pamiec_ai.txt. Film generuje ComfyUI/Wan; przed generacją panel zwalnia model językowy. Kontroler sprawdza wyniki narzędzi, nie ogląda jeszcze klatek filmu.

Panel pozwala uruchamiać i zatrzymywać usługi. Nie wdrożono limitowania GPU, niezależnych długotrwałych pętli AI dla każdego NPC, montażu wielu scen, głosu, muzyki ani automatycznej oceny klatek. Wioska jest interfejsem lokalnego zespołu, a nie symulacją autonomicznego życia. Wywołania modelu językowego i generacja Wan pozostają kolejno; równoległy jest odczyt techniczny i monitoring. Szczegóły dotychczasowych wersji: [historia](docs/HISTORIA_WERSJI.md).

## Grafiki i prawa do materiałów

Spis paczek i znane ograniczenia: [ASSETY.md](docs/ASSETY.md). Repozytorium zawiera materiały różnych autorów; dostępność pliku tutaj nie przyznaje nowych praw do jego użycia. Zachowano oryginalne informacje o autorstwie. Nie nadano wspólnej licencji obejmującej wszystkie grafiki.

## Testy

Na Windows: **Testuj.bat**.

Z terminala w głównym folderze: `PYTHONPATH=src python -m unittest discover -s tests -v` (Linux/macOS).

Testy jednostkowe używają atrap usług i procesów. Rzeczywista obsługa Windows, AMD i generowanie przez Wan wymagają testów na komputerze użytkownika.

Po oczyszczeniu repozytorium zachowano gotowe grafiki i animacje dla aplikacji i przyszłej wioski. Pliki projektowe innych edytorów i eksporty innych silników usunięto z bieżącej wersji; historia Git pozostaje zachowana. Rozmiar pełnego klonu może więc nie zmaleć tak jak rozmiar nowego archiwum ZIP.
