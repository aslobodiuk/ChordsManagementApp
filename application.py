import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCharFormat, QColor, QFont, QTextFormat, QKeyEvent
from PySide6.QtWidgets import (
    QWidget, QMainWindow, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QListWidget, QTextEdit, QListWidgetItem,
    QStackedWidget, QComboBox, QDialog, QLabel, QMessageBox, QCheckBox, QFileDialog
)

from api_calls import fetch_artists, fetch_songs, fetch_song, create_artist, delete_artist, export_songs_to_pdf, \
    create_song, update_song, delete_songs, search_songs

CHORDS_PATTERN = r"\(([A-G][#b]?(?:m|maj|min|dim|aug|sus|add)?\d*(?:/[A-G][#b]?)?)\)"


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
        self.highlight_chords()

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

    def highlight_chords(self, selected_pos: int = None):
        text = self.lyrics_edit.toPlainText()

        # Save cursor position if not explicitly set
        current_pos = self.lyrics_edit.textCursor().position() if selected_pos is None else selected_pos

        self.lyrics_edit.clear()
        cursor = self.lyrics_edit.textCursor()
        pattern = re.compile(CHORDS_PATTERN)

        pos = 0
        for match in pattern.finditer(text):
            start, end = match.span()

            # Insert normal text with default format
            normal_format = QTextCharFormat()
            cursor.insertText(text[pos:start], normal_format)

            # Insert chord with special format
            chord_format = QTextCharFormat()
            if selected_pos is not None and start <= selected_pos <= end:
                chord_format.setForeground(QColor("#FFA500"))  # orange
            else:
                chord_format.setForeground(QColor("#aa4444"))  # dull red
            chord_format.setFontWeight(QFont.Bold)
            chord_format.setProperty(QTextFormat.UserProperty, "chord")

            cursor.insertText(match.group(), chord_format)
            pos = end

        # Insert any remaining normal text at the end
        normal_format = QTextCharFormat()
        cursor.insertText(text[pos:], normal_format)

        new_cursor = self.lyrics_edit.textCursor()
        new_cursor.setPosition(current_pos)
        self.lyrics_edit.setTextCursor(new_cursor)

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

    def handle_delete_songs(self):
        song_ids = self.get_checked_song_ids()
        if not song_ids:
            QMessageBox.information(self, "No Selection", "Please select songs to delete.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete {len(song_ids)} song(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        try:
            delete_songs(song_ids)
            QMessageBox.information(self, "Success", "Songs deleted successfully.")
            self.load_songs()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete songs: {e}")

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

    def handle_search(self):
        query = self.search_input.text().strip()
        if not query:
            self.search_results_dropdown.hide()
            return

        try:
            songs = search_songs(query)
            self.populate_search_results(songs)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to perform search: {e}")
            self.search_results_dropdown.hide()

    def populate_search_results(self, songs: list[dict]):
        self.search_results_dropdown.clear()
        if not songs:
            self.search_results_dropdown.hide()
            return

        for song in songs:
            title = song.get("title", "Unknown Title")
            artist_name = song.get("artist", {}).get("name", "Unknown Artist")

            highlights = song.get("highlights", {})
            highlight_text = ""
            if highlights.get("title"):
                highlight_text = highlights.get("title")[0]
            elif highlights.get('artist'):
                highlight_text = highlights.get("artist")[0]
            elif highlights.get('lines'):
                highlight_text = highlights.get("lines")[0]

            item = QListWidgetItem()
            item.setData(Qt.UserRole, song["id"])
            self.search_results_dropdown.addItem(item)
            widget = SearchResultItem(f"{title} - {artist_name}", highlight_text)
            self.search_results_dropdown.setItemWidget(item, widget)

            item.setSizeHint(widget.sizeHint())

        self.search_results_dropdown.show()

        # Adjust height based on number of items
        max_visible_items = 5  # max items to show before scrolling
        item_count = len(songs)
        visible_count = min(item_count, max_visible_items)

        # Calculate height needed (itemHeight * visibleCount + frame + scrollbar)
        item_height = self.search_results_dropdown.sizeHintForRow(0) if self.search_results_dropdown.count() > 0 else 20
        frame = self.search_results_dropdown.frameWidth() * 2
        scrollbar_height = self.search_results_dropdown.horizontalScrollBar().sizeHint().height()

        new_height = item_height * visible_count + frame + scrollbar_height
        self.search_results_dropdown.setFixedHeight(new_height)

    def on_search_result_double_clicked(self, item: QListWidgetItem):
        self.load_song_into_editor(item)
        self.search_results_dropdown.hide()

    def create_artist_song_screen(self):
        widget = QWidget()
        main_layout = QVBoxLayout(widget)

        # Top search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search songs...")
        main_layout.addWidget(self.search_input)
        self.search_input.returnPressed.connect(self.handle_search)

        self.search_results_dropdown = QListWidget()
        self.search_results_dropdown.hide()  # hidden by default
        main_layout.addWidget(self.search_results_dropdown)
        self.search_results_dropdown.itemDoubleClicked.connect(self.on_search_result_double_clicked)

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
        self.del_song_btn.clicked.connect(self.handle_delete_songs)
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

        self.lyrics_edit = ChordTextEdit(self)
        self.lyrics_edit.setPlaceholderText("Lyrics with chords in brackets...")
        layout.addWidget(self.lyrics_edit)
        self.lyrics_edit.installEventFilter(self)

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

class SearchResultItem(QWidget):
    def __init__(self, title_artist: str, highlight_text: str):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 8)
        layout.setSpacing(1)

        highlight_text = highlight_text.replace(
            "<em>", '<em style="color: rgba(179, 87, 87, 0.7); font-style: italic;">'
        )
        self.label_main = QLabel(title_artist)
        self.label_highlight = QLabel(highlight_text)
        self.label_highlight.setStyleSheet("font-style: italic; color: gray;")

        layout.addWidget(self.label_main)
        layout.addWidget(self.label_highlight)

class ChordTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.chord_selected = False
        self.main_window = parent

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

        cursor = self.cursorForPosition(event.pos())
        pos = cursor.position()
        text = self.toPlainText()

        for match in re.finditer(CHORDS_PATTERN, text):
            start, end = match.span()
            if start <= pos <= end:
                self.chord_selected = True
                scrollbar = self.verticalScrollBar()
                scroll_pos = scrollbar.value()
                self.main_window.highlight_chords(selected_pos=pos)
                scrollbar.setValue(scroll_pos)
                return

        self.chord_selected = False
        scrollbar = self.verticalScrollBar()
        scroll_pos = scrollbar.value()
        self.main_window.highlight_chords()
        scrollbar.setValue(scroll_pos)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Up, Qt.Key_Down):
            self.chord_selected = False
            scrollbar = self.verticalScrollBar()
            scroll_pos = scrollbar.value()
            self.main_window.highlight_chords()
            scrollbar.setValue(scroll_pos)
            super().keyPressEvent(event)
            return

        if not self.chord_selected:
            super().keyPressEvent(event)
            return

        cursor = self.textCursor()
        position = cursor.position()
        text = self.toPlainText()

        # Find all chord spans
        for match in re.finditer(CHORDS_PATTERN, text):
            start, end = match.span()
            if start <= position <= end:
                chord = match.group(0)
                if event.key() == Qt.Key_Left and start > 0:
                    new_text = text[:start - 1] + chord + text[start - 1:start] + text[end:]
                    new_cursor_pos = start - 1 + len(chord)
                    scrollbar = self.verticalScrollBar()
                    scroll_pos = scrollbar.value()
                    self.setPlainText(new_text)
                    self.main_window.highlight_chords(selected_pos=new_cursor_pos)
                    scrollbar.setValue(scroll_pos)
                    cursor.setPosition(start - 1 + len(chord))
                    self.setTextCursor(cursor)
                    return
                elif event.key() == Qt.Key_Right and end < len(text):
                    new_text = text[:start] + text[end] + chord + text[end + 1:]
                    new_cursor_pos = start + 1 + len(chord)
                    scrollbar = self.verticalScrollBar()
                    scroll_pos = scrollbar.value()
                    self.setPlainText(new_text)
                    self.main_window.highlight_chords(selected_pos=new_cursor_pos)
                    scrollbar.setValue(scroll_pos)
                    cursor.setPosition(start + 1 + len(chord))
                    self.setTextCursor(cursor)
                    return

        # Default behavior
        super().keyPressEvent(event)