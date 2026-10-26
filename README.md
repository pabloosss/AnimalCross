# AnimalCross 0.4

Lokalna aplikacja Windows: Ollama/Qwen + ComfyUI/Wan, zespół ról AI, pamięć tekstowa i animowany towarzysz.

## Uruchomienie i aktualizacja

Python 3.10+ z Tcl/Tk, istniejące Ollama oraz Comfy Desktop. Pobierz repozytorium (Code → Download ZIP), rozpakuj i uruchom Uruchom.bat. Przy aktualizacji skopiuj wszystkie pliki .py i BAT do dotychczasowego folderu. Zachowaj data/. Brak dodatkowych zależności Python.

Panel sterowania pokazuje status obu usług i załadowania modelu; uruchamianie osobno lub razem. Sprawdzanie statusu co 15 sekund. Domyślne foldery instalacji zapisano dla C:\Users\Pablo. Zmień je w ustawieniach, jeśli używasz innego konta.

## Zespół i komunikacja

Koordynator tworzy plan → Scenarzysta przekazuje opis → Operator używa narzędzi → Kontroler porównuje wynik ze zleceniem i rzeczywistymi rezultatami narzędzi. Moduł pamięci zapisuje trwałe ustalenia. Są to osobne role i wywołania tego samego lokalnego modelu, wykonywane kolejno; monitoring usług działa w osobnym wątku. Nie ma wielu ciężkich modeli działających równocześnie. Obsługa powitań także przechodzi przez role, więc odpowiedź może potrwać dłużej niż zwykły czat.

Przekazania są zapisywane w data/agent_messages.jsonl z identyfikatorem zadania, nadawcą i odbiorcą. Panel rozmowy pokazuje etap oraz stan każdej roli. Dziennik szczegółów znajduje się w Panel sterowania → Działania AI. Kontroler nie ogląda klatek i nie ocenia jakości wizualnej filmu. Kontrola nie uruchamia jeszcze automatycznej pętli poprawek. Limity operatora: 12 etapów, jedna generacja na wiadomość.

Pamięć: data/pamiec_ai.txt. AI dopisuje notatki i wyciąga trwałe ustalenia po rozmowie. Dotychczasowa pamięć migrowana bez kasowania plików. Pamięć ma ograniczone okno odczytu; zapis nie oznacza treningu. Nie edytuj pliku w Notatniku równocześnie z pracą AI.

## Duszek SarahJK

Grafiki nie są częścią repozytorium. W aplikacji: Panel sterowania → Ustawienia → Importuj duszka z ZIP, wybierz własny plik Ghost PNGTuber Model.zip. Importowany jest dokładny zestaw 16 PNG z katalogu PNGs, bez innych plików archiwum. Grafiki pozostają lokalnie w data/ghost/.

Autorka: SarahJK — https://SarahJK.Carrd.Co . Dostarczona paczka zabrania redystrybucji. Zachowaj oryginalny ReadMe i przestrzegaj jego warunków; repozytorium nie nadaje dodatkowych praw do ilustracji.

Duszek kołysze się, mruga i zmienia wariant obrazu zgodnie ze stanem: oczekiwanie, praca, skupienie podczas generowania, koniec zadania, błąd. Ruch ust to sygnalizacja aktywności, nie synchronizacja z dźwiękiem. Bez importu pokazuje się prosty zastępczy symbol narysowany w aplikacji.

## Test

1. Uruchom usługi z panelu.
2. Zaimportuj ZIP duszka.
3. Kliknij Sprawdź moje środowisko. Zespół powinien przekazać zadania, sprawdzić ComfyUI i modele oraz zapisać ustalenia. Nie zleca to generacji.
4. Sprawdź statusy ról, komunikaty w dzienniku i pamięć.

Testy: `python -m unittest discover -v`. Testy HTTP i atrap modeli nie zastępują testu Windows/AMD/Wan. Brak lokalnego ekranu graficznego w środowisku przygotowania; animacje i układ wymagają potwierdzenia na docelowym Windowsie.

## Ograniczenia

Brak limitu GPU 80%, galerii filmów, wizualnego kontrolera, treningu i przycisku anulowania zapytań AI. Zamknięcie panelu nie zatrzymuje usług ani filmów; generację można przerwać w ComfyUI. Zamknij Cline i inne klienty Ollama, by nie ładowały Qwena podczas pracy Wan. Kontekst i pamięć mają ograniczenia; po sześciu wymianach rozpoczyna się nową rozmowę. Pełna walidacja workflow następuje na serwerze. Samodzielne tworzenie grafów wymaga testowania jakości lokalnego modelu.
