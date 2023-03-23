# autofill data to db stock table in users.db
# item_id = last item in the db + 1
# fields in the db, item_id, moviename, description, poster, trailer_link,cast_names , price, tmdb
# price and tmdb are the movie ids
# movie ids = 500 to 510

import json
import sqlite3

import requests

conn = sqlite3.connect('users.db')
c = conn.cursor()

# Enter your TMDb API key here
API_KEY = "d96c51d9aa944073eb95ae3cdccb11af"


# Function to fetch movie details
def get_movie_details(movie_id):
    # Build the API URL
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US&append_to_response=credits,videos,keywords"

    # Send a GET request to the API
    response = requests.get(url)

    # Check if the response was successful
    if response.status_code == 200:
        # Convert the response JSON data to a Python dictionary
        movie_data = json.loads(response.content)

        # Extract the movie details
        name = movie_data["title"]
        description = movie_data["overview"]
        poster = f"https://image.tmdb.org/t/p/original{movie_data['poster_path']}"
        cast = []
        for cast_member in movie_data["credits"]["cast"][:5]:
            # Get the cast member's details
            person_url = f"https://api.themoviedb.org/3/person/{cast_member['id']}?api_key={API_KEY}&language=en-US"
            person_response = requests.get(person_url)
            person_data = json.loads(person_response.content)

            # Get the cast member's image
            profile_path = person_data["profile_path"]
            if profile_path is not None:
                profile_image = f"https://image.tmdb.org/t/p/original{profile_path}"
            else:
                profile_image = None

            # Add the cast member's name and image to the list
            cast.append({"name": cast_member["name"], "image": profile_image})
        trailer = f"https://www.youtube.com/watch?v={movie_data['videos']['results'][0]['key']}"
        tags = []
        for keyword in movie_data["keywords"]["keywords"]:
            tags.append(keyword["name"])
        categories = []
        for genre in movie_data["genres"]:
            categories.append(genre["name"])

        # Return the movie details as a dictionary
        print(f"Success: {movie_id}.")
        return {
            "name": name,
            "description": description,
            "poster": poster,
            "cast": cast,
            "trailer": trailer,
            "tags": tags,
            "categories": categories
        }

    else:
        # If the API request was unsuccessful, return None
        print(f"Error: {movie_id}.")
        return None


# Get the last item_id from the stock table
c.execute("SELECT item_id FROM stock ORDER BY item_id DESC LIMIT 1")
result = c.fetchone()
last_item_id = result[0] if result is not None else 0

# Define the movie ID range to use
MOVIE_ID_RANGE = range(573, 632)

# Loop through the movie IDs and add them to the database
for movie_id in MOVIE_ID_RANGE:
    # Get the movie details using the TMDB API
    movie_details = get_movie_details(movie_id)

    # Check if the movie details were successfully fetched
    if movie_details is not None:
        # check if all the fields are filled
        # Generate a new item ID by getting the last item in the database and adding 1
        c.execute("SELECT MAX(item_id) FROM stock")
        last_item_id = c.fetchone()[0]
        if last_item_id is not None:
            item_id = last_item_id + 1
        else:
            item_id = 1

        # Get the cast names as a comma-separated string
        cast_names = ", ".join([cast_member["name"] for cast_member in movie_details["cast"]])

        # Insert the movie details into the database
        c.execute("INSERT INTO stock VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
        item_id, movie_details["name"], movie_details["description"], movie_details["poster"], movie_details["trailer"],
        cast_names, movie_id, movie_id))

# Commit the changes to the database
conn.commit()
conn.close()
