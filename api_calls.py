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