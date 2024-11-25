from tmdbv3api import TMDb, Movie

# TMDb-API einrichten
tmdb = TMDb()
tmdb.api_key = '15b140e27f878a1746c3b2513da55cbb'
tmdb.language = 'de'  # Setze die Sprache auf Deutsch (optional)

# Film suchen
movie = Movie()
search = movie.search("Borat")

for result in search:
    print(f"Titel: {result.title}")
    print(f"Erscheinungsjahr: {result.release_date}")
    print(f"ID: {result.id}")
    print(f"Beschreibung: {result.overview}")
    print("---")