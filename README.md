# Twitch Data Visualization Dashboard

Projekt jest aplikacja Flask do wizualizacji danych o streamerach Twitcha dla wybranych gier. Dane sa pobierane do plikow CSV, a nastepnie prezentowane jako interaktywny graf: gra -> kraje -> streamerzy.

## Funkcje

- wybor gry i dnia danych,
- interaktywny graf SVG,
- rozwijanie i zwijanie wezlow krajow,
- reset grafu do widoku domyslnego,
- loader podczas pobierania danych z API aplikacji,
- filtrowanie widocznych streamerow:
  - `Top N overall`,
  - minimalna liczba widzow,
  - wyszukiwarka streamera,
- przycisk `Clear filters`, aktywny tylko wtedy, gdy filtry sa zmienione,
- tooltipy dla gry, krajow i streamerow,
- tooltip streamera z aktualnymi widzami, czasem streama, srednia 30d i wzrostem followersow 30d,
- tooltip kraju oraz gry z suma widzow i liczba tworcow w aktualnym widoku,
- drag-to-pan, zoom i `Fit` dla wygodniejszej nawigacji po grafie,
- fallback `No data` dla brakujacych wartosci w danych tooltipa,
- mapowanie kodow jezykow na flagi krajow oraz neutralny fallback dla `OTHER`.

## Struktura projektu

```text
.
|-- app.py
|-- scrapping.py
|-- templates/
|   `-- index.html
|-- data/
|   `-- YYYY-MM-DD.csv
`-- .env
```

## Pliki

### `app.py`

Glowna aplikacja Flask.

Najwazniejsze endpointy:

- `/` - renderuje dashboard,
- `/api/graph?game=...&date=...` - zwraca dane grafu w JSON.

Endpoint `/api/graph` czyta odpowiedni plik CSV z katalogu `data`, filtruje rekordy po grze, grupuje streamerow po jezyku i zwraca dane potrzebne frontendowi.

### `templates/index.html`

Frontend aplikacji:

- kontrolki wyboru gry i dnia,
- kontrolki filtrowania,
- legenda,
- obszar SVG grafu,
- logika renderowania wezlow, tooltipow, agregatow widzow, zoomu, drag-to-pan i resetu.

### `scrapping.py`

Skrypt do pobierania danych:

1. Autoryzuje sie w Twitch API.
2. Pobiera informacje o skonfigurowanych grach.
3. Pobiera aktywne streamy.
4. Pobiera avatary streamerow.
5. Pobiera 30-dniowe statystyki z TwitchTracker API.
6. Zapisuje wynikowy CSV do katalogu `data`.

## Wymagane biblioteki

Projekt korzysta z Pythona oraz kilku bibliotek instalowanych przez `pip`:

- `flask` - serwer aplikacji i endpointy API,
- `pandas` - odczyt, filtrowanie i zapis danych CSV,
- `requests` - zapytania HTTP do Twitch API i TwitchTracker API,
- `python-dotenv` - wczytywanie zmiennych z pliku `.env`.

Instalacja:

```bash
pip install flask pandas requests python-dotenv
```

## Konfiguracja

Projekt wymaga pliku `.env` z danymi Twitch API:

```env
CLIENT_ID_KEY=twoj_client_id
CLIENT_SECRET_KEY=twoj_client_secret
```

## Uruchamianie aplikacji

```bash
python app.py
```

Domyslnie aplikacja Flask uruchomi sie lokalnie pod adresem:

```text
http://127.0.0.1:5000
```

## Pobieranie nowych danych

```bash
python scrapping.py
```

Skrypt zapisuje plik CSV w katalogu `data` z nazwa aktualnej daty, np.:

```text
data/YYYY-MM-DD.csv
```

## Gry

Lista gier jest zdefiniowana w dwoch miejscach:

- w `scrapping.py` jako `GAME_NAMES`, czyli lista gier pobieranych z Twitch API,
- w `app.py` jako lista `games`, czyli lista gier widocznych w selekcie dashboardu.

Aktualnie uzywany zestaw:

```python
["World of Warcraft", "Path of Exile 2", "Gothic 1 Remake"]
```

W `app.py` istnieje tez mapa niestandardowych ikon gier:

```python
CUSTOM_GAME_ICONS = {
    "World of Warcraft": "...",
    "Path of Exile 2": "...",
    "Gothic 1 Remake": "..."
}
```

## Dane CSV

Pliki CSV w `data` wspolny schemat kolumn. Skladajacy się m.in. z:

- `user_id`,
- `user_login`,
- `user_name`,
- `game_name`,
- `title`,
- `viewer_count`,
- `started_at`,
- `language`,
- `profile_image_url`,
- `uptime_minutes`,
- `avg_viewers_30d`,
- `followers_gained_30d`.

Dla brakujacych danych w kolumnach tooltipa stosowana jest wartosc:

```text
No data
```

## Filtrowanie grafu

Filtry dzialaja po stronie frontendu:

- `Top N overall` wybiera top streamerow globalnie po `viewer_count`, a nie osobno dla kazdego kraju,
- `Min viewers` ukrywa streamerow ponizej podanej liczby widzow,
- `Search` filtruje po nazwie streamera,
- `Clear filters` przywraca:
  - `Top N overall = All`,
  - `Min viewers = 0`,
  - pusta wyszukiwarke.

Agregaty w tooltipach gry i krajach licza aktualny widok po zastosowaniu filtrow. Jesli ustawiony jest `Top N overall` albo `Min viewers`, suma widzow i liczba tworcow dotycza tylko streamerow, ktorzy pozostali widoczni w grafie.

## Tooltipy

- najechanie na gre pokazuje laczna liczbe widzow, liczbe tworcow i liczbe krajow w aktualnym widoku,
- najechanie na kraj pokazuje laczna liczbe widzow i liczbe tworcow dla tej grupy,
- najechanie na streamera pokazuje dane konkretnego tworcy: aktualnych widzow, czas streama, `avg_viewers_30d` i `followers_gained_30d`.

## Nawigacja po grafie

Graf dziala podobnie do mapy:

- przeciaganie mysza lub palcem przesuwa widok,
- `+` przybliza,
- `-` oddala,
- `Fit` dopasowuje caly graf do widoku,
- klikniecie flagi rozwija lub zwija streamerow dla danego jezyka,
- po kliknieciu flagi widok centruje sie na tym wezle.

## Flagi i jezyki

Frontend mapuje kody jezykow Twitcha na kody krajow uzywane przez `flagcdn.com`, np.:

- `en -> gb`,
- `cs -> cz`,
- `uk -> ua`,
- `el -> gr`,
- `ar -> sa`,
- `th -> th`,
- `no -> no`.

Wartosc `OTHER` nie ma jednej poprawnej flagi, dlatego jest renderowana jako neutralny wezel z symbolem zamiast flagi kraju.

## Uwagi o TwitchTracker

Projekt uzywa endpointu:

```text
https://twitchtracker.com/api/channels/summary/{username}
```

## Typowy workflow

1. Uruchom `scrapping.py`, aby pobrac nowy dzien danych.
2. Uruchom `app.py`.
3. Otworz dashboard w przegladarce.
4. Wybierz gre i dzien.
5. Uzyj filtrow, zoomu i rozwijania flag do analizy danych.
