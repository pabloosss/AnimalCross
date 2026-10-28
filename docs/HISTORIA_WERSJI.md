# Aktualizacja 0.5

Duch jest wczytywany automatycznie z Ghost/PNGs obok plików aplikacji. Przy aktualizacji skopiuj również cały folder Ghost z repozytorium. Import ZIP pozostaje opcją zastępczą. Zachowaj oryginalne informacje o autorce SarahJK i prawach w Ghost/ReadMe.txt. Integracja nie zmienia licencji grafik.

Panel sterowania: Ollama i ComfyUI mają Uruchom i Zatrzymaj, Qwen ma Zwolnij model. Zatrzymaj usługi próbuje zakończyć oba serwery. Przerwij film wysyła /interrupt do ComfyUI, ale nie kasuje oczekującej kolejki. Lista pokazuje też dostępność Wan, enkodera i VAE, obecność folderu Ghost oraz działanie Pythona. Brak odpowiedzi API to stan niedostępny/nieznany, a nie gwarancja braku procesu. Dostępność modelu nie oznacza załadowania do VRAM.

Zatrzymywanie działa na Windows: identyfikuje PID nasłuchujący na lokalnym porcie i sprawdza nazwę/komendę procesu. Nie kończy wszystkich procesów Python. Działa również dla serwera uruchomionego wcześniej poza panelem, jeśli rozpoznanie się powiedzie. Przy braku uprawnień lub nieznanym procesie wyświetla błąd. Okno Comfy Desktop lub ikona Ollama w zasobniku mogą pozostać otwarte albo ponownie uruchomić serwer — o faktycznej dostępności informuje kolejny pomiar statusu.

Zatrzymanie ustawia znacznik anulowania dalszych wywołań agentów. Trwająca odpowiedź HTTP może zakończyć się dopiero po przerwaniu serwera lub zwrocie odpowiedzi. Wtedy nie są wykonywane kolejne narzędzia. Nie jest to natychmiastowe anulowanie obliczeń Qwena przy zatrzymaniu samego ComfyUI.

Przeszło 16 testów logiki; zatrzymywanie procesów Windows sprawdzono na atrapach subprocess, nie na rzeczywistym komputerze użytkownika.

# AnimalCross 0.5

Lokalna aplikacja Windows: Ollama/Qwen + ComfyUI/Wan, zespół ról AI, pamięć tekstowa i animowany towarzysz.

## Uruchomienie i aktualizacja

Python 3.10+ z Tcl/Tk, istniejące Ollama oraz Comfy Desktop. Pobierz repozytorium (Code → Download ZIP), rozpakuj i uruchom Uruchom.bat. Przy aktualizacji skopiuj wszystkie pliki .py i BAT do dotychczasowego folderu. Zachowaj data/. Brak dodatkowych zależności Python.

Panel sterowania pokazuje status obu usług i załadowania modelu; uruchamianie osobno lub razem. Sprawdzanie statusu co 15 sekund. Domyślne foldery instalacji zapisano dla C:\Users\Pablo. Zmień je w ustawieniach, jeśli używasz innego konta.

## Zespół i komunikacja

Koordynator tworzy plan → Scenarzysta przekazuje opis → Operator używa narzędzi → Kontroler porównuje wynik ze zleceniem i rzeczywistymi rezultatami narzędzi. Moduł pamięci zapisuje trwałe ustalenia. Są to osobne role i wywołania tego samego lokalnego modelu, wykonywane kolejno; monitoring usług działa w osobnym wątku. Nie ma wielu ciężkich modeli działających równocześnie. Obsługa powitań także przechodzi przez role, więc odpowiedź może potrwać dłużej niż zwykły czat.

Przekazania są zapisywane w data/agent_messages.jsonl z identyfikatorem zadania, nadawcą i odbiorcą. Panel rozmowy pokazuje etap oraz stan każdej roli. Dziennik szczegółów znajduje się w Panel sterowania → Działania AI. Kontroler nie ogląda klatek i nie ocenia jakości wizualnej filmu. Kontrola nie uruchamia jeszcze automatycznej pętli poprawek. Limity operatora: 12 etapów, jedna generacja na wiadomość.

Pamięć: data/pamiec_ai.txt. AI dopisuje notatki i wyciąga trwałe ustalenia po rozmowie. Dotychczasowa pamięć migrowana bez kasowania plików. Pamięć ma ograniczone okno odczytu; zapis nie oznacza treningu. Nie edytuj pliku w Notatniku równocześnie z pracą AI.

## Duszek SarahJK

Grafiki dodane przez użytkownika do Ghost/PNGs są wczytywane automatycznie. Alternatywnie w aplikacji: Panel sterowania → Ustawienia → Importuj duszka z ZIP, wybierz własny plik Ghost PNGTuber Model.zip. Importowany jest dokładny zestaw 16 PNG z katalogu PNGs, bez innych plików archiwum. Grafiki pozostają lokalnie w data/ghost/.

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

