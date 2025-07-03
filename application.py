from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QMainWindow, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QListWidget, QTextEdit, QListWidgetItem,
    QStackedWidget, QComboBox, QDialog, QLabel, QMessageBox, QCheckBox, QFileDialog
)

from api_calls import fetch_artists, fetch_songs, fetch_song, create_artist, delete_artist, export_songs_to_pdf, \
    create_song, update_song


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chords Manager")
        self.setMinimumSize(800, 600)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.artist_song_screen = self.create_artist_song_screen()
        self.editor_screen = self.create_editor_screen()

        self.stack.addWidget(self.artist_song_screen)
        self.stack.addWidget(self.editor_screen)

        self.stack.setCurrentWidget(self.artist_song_screen)

    def load_artists(self):
        self.artist_list.clear()

        # add special All item
        all_item = QListWidgetItem("All")
        font = all_item.font()
        font.setBold(True)
        all_item.setFont(font)
        self.artist_list.addItem(all_item)

        for artist in fetch_artists():
            item = QListWidgetItem(f"    {artist["name"]}")
            item.setData(Qt.UserRole, artist["id"])
            self.artist_list.addItem(item)

    def load_songs(self, artist_id = None):
        self.song_list.clear()
        for song in fetch_songs(artist_id):
            item = QListWidgetItem(song["title"])
            item.setData(Qt.UserRole, song["id"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.song_list.addItem(item)

    def toggle_all_song_checkboxes(self, state):
        for i in range(self.song_list.count()):
            item = self.song_list.item(i)
            item.setCheckState(Qt.Checked if state == Qt.Checked.value else Qt.Unchecked)

    def get_checked_song_ids(self):
        ids = []
        for i in range(self.song_list.count()):
            item = self.song_list.item(i)
            if item.checkState() == Qt.Checked:
                song_id = item.data(Qt.UserRole)
                ids.append(song_id)
        return ids

    def on_artist_selected(self, item):
        artist_id = item.data(Qt.UserRole)
        self.load_songs(artist_id)

    def open_add_artist_dialog(self):
        dialog = AddArtistDialog(self)
        if dialog.exec():  # User pressed Save
            name = dialog.get_name()
            if not name:
                QMessageBox.warning(self, "Input Error", "Artist name cannot be empty.")
                return
            create_artist(name)
            self.load_artists()

    def delete_selected_artist(self):
        item = self.artist_list.currentItem()
        if not item or item.text() == "All":
            QMessageBox.warning(self, "No Selection", "Please select an artist to delete (not 'All').")
            return

        artist_name = item.text().strip()
        artist_id = item.data(Qt.UserRole)

        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete artist '{artist_name}'?\nAll artist's songs will be deleted.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        delete_artist(artist_id, artist_name)
        self.load_artists()
        self.load_songs()

    def open_create_song_editor(self):
        # Clear previous values
        self.title_input.setText("")
        self.lyrics_edit.setPlainText("")
        self.current_editing_song_id = None  # Custom attribute to track mode
        self.editor_save_mode = "create"

        # Optional: reset artist dropdown to default (first index)
        self.artist_dropdown.setCurrentIndex(0)

        # Switch to editor screen
        self.stack.setCurrentWidget(self.editor_screen)

    def load_song_into_editor(self, item: QListWidgetItem):
        song_id = item.data(Qt.UserRole)

        song = fetch_song(song_id)

        # Fill editor fields
        self.title_input.setText(song["title"])
        self.lyrics_edit.setPlainText(song["lyrics"])

        # Set artist dropdown
        artist_name = song["artist"]["name"]
        index = self.artist_dropdown.findText(artist_name)
        if index >= 0:
            self.artist_dropdown.setCurrentIndex(index)

        # Store current song id for save/update
        self.current_editing_song_id = song_id
        self.editor_save_mode = "edit"

        # Switch to editor screen
        self.stack.setCurrentWidget(self.editor_screen)

    def go_back(self):
        self.stack.setCurrentIndex(0)

    def export_selected_songs(self):
        selected_song_ids = self.get_checked_song_ids()

        if not selected_song_ids:
            QMessageBox.warning(self, "No Songs Selected", "Please select at least one song to export.")
            return

        try:
            response = export_songs_to_pdf(selected_song_ids)

            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save PDF", "exported_songs.pdf", "PDF files (*.pdf)"
            )

            if save_path:
                with open(save_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                QMessageBox.information(self, "Success", "PDF saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", str(e))

    def handle_save_song(self):
        title = self.title_input.text().strip()
        artist_name = self.artist_dropdown.currentText()
        lyrics = self.lyrics_edit.toPlainText().strip()

        if not title or not artist_name or not lyrics:
            QMessageBox.warning(self, "Validation Error", "All fields must be filled out.")
            return

        artist_id = self.artist_dropdown.currentData()

        if not artist_id:
            QMessageBox.critical(self, "Error", "Invalid artist selected.")
            return

        try:
            if self.editor_save_mode == "create":
                create_song(title, artist_id, lyrics)
                QMessageBox.information(self, "Success", "Song created successfully.")
            elif self.editor_save_mode == "edit":
                update_song(self.current_editing_song_id, title, artist_id, lyrics)
                QMessageBox.information(self, "Success", "Song updated successfully.")
            else:
                raise Exception("Unknown editor mode.")

            self.load_songs()  # refresh song list
            self.stack.setCurrentIndex(0)  # go back to main screen

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def create_artist_song_screen(self):
        widget = QWidget()
        main_layout = QVBoxLayout(widget)

        # Top search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search songs...")
        main_layout.addWidget(self.search_input)

        # Content layout
        content_layout = QHBoxLayout()

        # Left block - Artist list
        left_layout = QVBoxLayout()
        self.artist_list = QListWidget()
        self.load_artists()
        self.artist_list.itemDoubleClicked.connect(self.on_artist_selected)
        left_layout.addWidget(self.artist_list)

        artist_buttons = QHBoxLayout()
        artist_buttons.setContentsMargins(0, 0, 0, 0)
        artist_buttons.addStretch()  # pushes buttons to right
        self.add_artist_btn = QPushButton("+")
        self.del_artist_btn = QPushButton("-")
        artist_buttons.addWidget(self.add_artist_btn)
        artist_buttons.addWidget(self.del_artist_btn)
        left_layout.addLayout(artist_buttons)
        self.add_artist_btn.clicked.connect(self.open_add_artist_dialog)
        self.del_artist_btn.clicked.connect(self.delete_selected_artist)

        # Right block - Song list
        right_layout = QVBoxLayout()

        # Select All checkbox
        self.select_all_songs_cb = QCheckBox("Select All")
        self.select_all_songs_cb.stateChanged.connect(self.toggle_all_song_checkboxes)
        right_layout.addWidget(self.select_all_songs_cb)

        self.song_list = QListWidget()
        self.load_songs()
        self.song_list.itemDoubleClicked.connect(self.load_song_into_editor)
        right_layout.addWidget(self.song_list)

        song_buttons = QHBoxLayout()
        song_buttons.setContentsMargins(0, 0, 0, 0)
        song_buttons.addStretch()  # pushes buttons to right
        self.add_song_btn = QPushButton("+")
        self.del_song_btn = QPushButton("-")
        self.export_song_btn = QPushButton("Export")
        song_buttons.addWidget(self.add_song_btn)
        song_buttons.addWidget(self.del_song_btn)
        song_buttons.addWidget(self.export_song_btn)
        self.add_song_btn.clicked.connect(self.open_create_song_editor)
        self.export_song_btn.clicked.connect(self.export_selected_songs)
        right_layout.addLayout(song_buttons)

        content_layout.addLayout(left_layout, 1)
        content_layout.addLayout(right_layout, 2)
        main_layout.addLayout(content_layout)

        return widget

    def create_editor_screen(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Song title")
        layout.addWidget(self.title_input)

        self.artist_dropdown = QComboBox()
        layout.addWidget(self.artist_dropdown)
        # Populate dropdown
        artists = fetch_artists()
        for artist in artists:
            self.artist_dropdown.addItem(artist["name"], artist["id"])

        self.lyrics_edit = QTextEdit()
        self.lyrics_edit.setPlaceholderText("Lyrics with chords in brackets...")
        layout.addWidget(self.lyrics_edit)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addStretch()  # pushes buttons to right
        self.back_btn = QPushButton("Back")
        self.save_song_btn = QPushButton("Save")
        button_layout.addWidget(self.back_btn)
        button_layout.addWidget(self.save_song_btn)
        layout.addLayout(button_layout)

        self.back_btn.clicked.connect(self.go_back)
        self.save_song_btn.clicked.connect(self.handle_save_song)

        return widget

class AddArtistDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Artist")

        layout = QVBoxLayout()

        self.name_input = QLineEdit()
        layout.addWidget(QLabel("Artist Name:"))
        layout.addWidget(self.name_input)

        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Discard")
        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def get_name(self) -> str:
        return self.name_input.text().strip()