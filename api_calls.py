import requests
from PySide6.QtWidgets import QMessageBox

API_URL = "http://127.0.0.1:8000/"

def fetch_artists():
    try:
        response = requests.get(API_URL + "artists/")
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []

def fetch_songs(artist_id = None):
    try:
        query_params = f"?artists={artist_id}"
        response = requests.get(API_URL + "songs/" + query_params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []

def fetch_song(song_id):
    try:
        query_params = f"?display=for_edit"
        response = requests.get(API_URL + f"songs/{song_id}/" + query_params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        QMessageBox.critical(None, "Error", f"Failed to fetch song: {e}")

def create_artist(name):
    response = requests.post(API_URL + "artists", json={"name": name})
    if response.status_code == 200:
        QMessageBox.information(None, "Success", f"Artist '{name}' added.")
    elif response.status_code == 400:
        detail = response.json().get("detail", "Unknown error")
        QMessageBox.warning(None, "Already exists", detail)
    else:
        QMessageBox.critical(None, "Error", f"Failed to add artist: {response.text}")

def delete_artist(artist_id, artist_name):
    try:
        response = requests.delete(API_URL + f"artists/{artist_id}")
        if response.status_code == 204:
            QMessageBox.information(None, "Success", f"Artist '{artist_name}' was deleted.")
        else:
            QMessageBox.critical(
                None,
                "Error",
                f"Failed to delete artist. Server responded with status {response.status_code}"
            )
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Failed to delete artist: {e}")

def export_songs_to_pdf(song_ids):
    response = requests.post(
        f"{API_URL}/songs/to_pdf",
        json={"song_ids": song_ids},
        stream=True
    )
    if response.status_code != 200:
        raise Exception(f"Failed to export PDF: {response.text}")
    return response

def create_song(title: str, artist_id: int, lyrics: str):
    response = requests.post(
        f"{API_URL}/songs",
        json={"title": title, "artist_id": artist_id, "lyrics": lyrics}
    )
    if response.status_code != 200:
        raise Exception(f"Failed to create song: {response.text}")

def update_song(song_id: int, title: str, artist_id: int, lyrics: str):
    response = requests.put(
        f"{API_URL}/songs/{song_id}",
        json={"title": title, "artist_id": artist_id, "lyrics": lyrics}
    )
    if response.status_code != 200:
        raise Exception(f"Failed to update song: {response.text}")

def delete_songs(song_ids: list[int]):
    response = requests.delete(
        f"{API_URL}/songs",
        json={"song_ids": song_ids}
    )
    if response.status_code != 204:
        raise Exception(response.text)