import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import serial
except ImportError:
    serial = None


PITCH_OPTIONS = [
    "NOTE_C4",
    "NOTE_CS4",
    "NOTE_D4",
    "NOTE_DS4",
    "NOTE_E4",
    "NOTE_F4",
    "NOTE_FS4",
    "NOTE_G4",
    "NOTE_GS4",
    "NOTE_A4",
    "NOTE_AS4",
    "NOTE_B4",
    "NOTE_C5",
    "NOTE_D5",
    "NOTE_E5",
    "NOTE_F5",
    "NOTE_G5",
    "NOTE_A5",
    "NOTE_B5",
    "REST",
]

NOTE_FREQUENCIES = {
    "NOTE_C4": 262,
    "NOTE_CS4": 277,
    "NOTE_D4": 294,
    "NOTE_DS4": 311,
    "NOTE_E4": 330,
    "NOTE_F4": 349,
    "NOTE_FS4": 370,
    "NOTE_G4": 392,
    "NOTE_GS4": 415,
    "NOTE_A4": 440,
    "NOTE_AS4": 466,
    "NOTE_B4": 494,
    "NOTE_C5": 523,
    "NOTE_D5": 587,
    "NOTE_E5": 659,
    "NOTE_F5": 698,
    "NOTE_G5": 784,
    "NOTE_A5": 880,
    "NOTE_B5": 988,
    "REST": 0,
}


class MusicStudioApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Arduino Buzzer Music Studio")
        self.root.geometry("1080x620")

        self.notes = []
        self.tempo_gap_ms = 90
        self.loop_pause_ms = 1800
        self.buzzer_pin = 9
        self.timeline_scale = 0.35
        self.selected_index = None
        self.serial_conn = None

        self.pitch_var = tk.StringVar(value="NOTE_C4")
        self.duration_var = tk.StringVar(value="300")
        self.tempo_var = tk.StringVar(value=str(self.tempo_gap_ms))
        self.pin_var = tk.StringVar(value=str(self.buzzer_pin))
        self.port_var = tk.StringVar(value="/dev/ttyACM0")
        self.status_var = tk.StringVar(value="Ready.")

        self._build_ui()
        self._redraw_timeline()

    def _build_ui(self):
        main = tk.Frame(self.root, bg="#1e1e1e")
        main.pack(fill=tk.BOTH, expand=True)

        toolbar = tk.Frame(main, bg="#2b2b2b", padx=8, pady=8)
        toolbar.pack(fill=tk.X)

        ttk.Label(toolbar, text="Pitch").grid(row=0, column=0, sticky="w", padx=4)
        self.pitch_box = ttk.Combobox(toolbar, textvariable=self.pitch_var, values=PITCH_OPTIONS, width=14, state="readonly")
        self.pitch_box.grid(row=0, column=1, padx=4)

        ttk.Label(toolbar, text="Duration (ms)").grid(row=0, column=2, sticky="w", padx=4)
        tk.Entry(toolbar, textvariable=self.duration_var, width=9).grid(row=0, column=3, padx=4)

        ttk.Label(toolbar, text="Tempo Gap (ms)").grid(row=0, column=4, sticky="w", padx=4)
        tk.Entry(toolbar, textvariable=self.tempo_var, width=9).grid(row=0, column=5, padx=4)

        ttk.Label(toolbar, text="Buzzer Pin").grid(row=0, column=6, sticky="w", padx=4)
        tk.Entry(toolbar, textvariable=self.pin_var, width=6).grid(row=0, column=7, padx=4)

        tk.Button(toolbar, text="Add Note", bg="#4CAF50", fg="white", command=self.add_note).grid(row=0, column=8, padx=6)
        tk.Button(toolbar, text="Update Selected", command=self.update_selected).grid(row=0, column=9, padx=6)
        tk.Button(toolbar, text="Delete Selected", command=self.delete_selected).grid(row=0, column=10, padx=6)
        tk.Button(toolbar, text="Clear", command=self.clear_notes).grid(row=0, column=11, padx=6)
        tk.Button(toolbar, text="Save C++", command=self.save_cpp).grid(row=0, column=12, padx=6)

        serial_bar = tk.Frame(main, bg="#252526", padx=8, pady=6)
        serial_bar.pack(fill=tk.X)
        ttk.Label(serial_bar, text="Serial Port").grid(row=0, column=0, padx=4, sticky="w")
        tk.Entry(serial_bar, textvariable=self.port_var, width=20).grid(row=0, column=1, padx=4)
        tk.Button(serial_bar, text="Connect", command=self.connect_arduino).grid(row=0, column=2, padx=4)
        tk.Button(serial_bar, text="Disconnect", command=self.disconnect_arduino).grid(row=0, column=3, padx=4)
        tk.Button(serial_bar, text="Play on Arduino", command=self.play_on_arduino, bg="#1976D2", fg="white").grid(row=0, column=4, padx=8)
        tk.Button(serial_bar, text="Stop", command=self.stop_on_arduino).grid(row=0, column=5, padx=4)

        body = tk.PanedWindow(main, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, bg="#1e1e1e")
        body.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(body, bg="#1e1e1e")
        right = tk.Frame(body, bg="#1e1e1e")
        body.add(left, stretch="always")
        body.add(right, minsize=370)

        self.canvas = tk.Canvas(left, bg="#1f1f1f", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        cols = ("#", "Pitch", "Duration")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=18)
        for col in cols:
            self.tree.heading(col, text=col)
        self.tree.column("#", width=50, anchor=tk.CENTER)
        self.tree.column("Pitch", width=140, anchor=tk.CENTER)
        self.tree.column("Duration", width=120, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_note)

        status = tk.Label(main, textvariable=self.status_var, bg="#111", fg="#ddd", anchor="w", padx=10)
        status.pack(fill=tk.X)

    def _set_status(self, text: str):
        self.status_var.set(text)

    def _validate_positive_int(self, value: str, field_name: str) -> int:
        try:
            val = int(value)
        except ValueError:
            raise ValueError(f"{field_name} must be an integer.")
        if val <= 0:
            raise ValueError(f"{field_name} must be greater than 0.")
        return val

    def _read_inputs(self):
        pitch = self.pitch_var.get().strip()
        if pitch not in PITCH_OPTIONS:
            raise ValueError("Pitch is invalid.")
        duration = self._validate_positive_int(self.duration_var.get().strip(), "Duration")
        self.tempo_gap_ms = self._validate_positive_int(self.tempo_var.get().strip(), "Tempo Gap")
        self.buzzer_pin = self._validate_positive_int(self.pin_var.get().strip(), "Buzzer Pin")
        return pitch, duration

    def _refresh_table(self):
        self.tree.delete(*self.tree.get_children())
        for idx, note in enumerate(self.notes):
            self.tree.insert("", tk.END, iid=str(idx), values=(idx + 1, note["pitch"], note["duration"]))

    def _redraw_timeline(self):
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 900)
        height = max(self.canvas.winfo_height(), 420)

        for ms in range(0, 12000, 500):
            x = 40 + int(ms * self.timeline_scale)
            if x > width:
                break
            self.canvas.create_line(x, 0, x, height, fill="#2f2f2f")
            self.canvas.create_text(x + 2, 12, text=f"{ms}", fill="#9e9e9e", anchor="nw", font=("Arial", 8))

        x = 40
        y0, y1 = 100, 165
        for idx, note in enumerate(self.notes):
            w = max(20, int(note["duration"] * self.timeline_scale))
            color = note["color"]
            if idx == self.selected_index:
                outline = "#fff"
                stroke = 2
            else:
                outline = "#444"
                stroke = 1
            self.canvas.create_rectangle(x, y0, x + w, y1, fill=color, outline=outline, width=stroke)
            self.canvas.create_text(x + w // 2, y0 + 22, text=note["pitch"], fill="white")
            self.canvas.create_text(x + w // 2, y0 + 44, text=f'{note["duration"]} ms', fill="#e0e0e0", font=("Arial", 8))
            x += w + 8

        self._refresh_table()

    def add_note(self):
        try:
            pitch, duration = self._read_inputs()
        except ValueError as exc:
            messagebox.showerror("Input Error", str(exc))
            return

        color = "#{:06x}".format(random.randint(0x3377AA, 0x99DDFF))
        self.notes.append({"pitch": pitch, "duration": duration, "color": color})
        self.selected_index = len(self.notes) - 1
        self._redraw_timeline()
        self._set_status(f"Added {pitch} ({duration} ms).")

    def on_select_note(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        idx = int(selected[0])
        self.selected_index = idx
        note = self.notes[idx]
        self.pitch_var.set(note["pitch"])
        self.duration_var.set(str(note["duration"]))
        self._redraw_timeline()

    def update_selected(self):
        if self.selected_index is None:
            messagebox.showwarning("No selection", "Select a note first.")
            return
        try:
            pitch, duration = self._read_inputs()
        except ValueError as exc:
            messagebox.showerror("Input Error", str(exc))
            return
        self.notes[self.selected_index]["pitch"] = pitch
        self.notes[self.selected_index]["duration"] = duration
        self._redraw_timeline()
        self._set_status(f"Updated note #{self.selected_index + 1}.")

    def delete_selected(self):
        if self.selected_index is None:
            messagebox.showwarning("No selection", "Select a note first.")
            return
        del self.notes[self.selected_index]
        if not self.notes:
            self.selected_index = None
        else:
            self.selected_index = min(self.selected_index, len(self.notes) - 1)
        self._redraw_timeline()
        self._set_status("Deleted selected note.")

    def clear_notes(self):
        self.notes.clear()
        self.selected_index = None
        self._redraw_timeline()
        self._set_status("Composition cleared.")

    def connect_arduino(self):
        if serial is None:
            messagebox.showerror("Missing Dependency", "Install pyserial first:\n\npip install pyserial")
            return
        if self.serial_conn and self.serial_conn.is_open:
            self._set_status("Arduino is already connected.")
            return
        port = self.port_var.get().strip()
        try:
            self.serial_conn = serial.Serial(port=port, baudrate=115200, timeout=2)
            self._set_status(f"Connected to {port}.")
        except Exception as exc:
            messagebox.showerror("Connection Error", f"Could not connect to {port}.\n\n{exc}")

    def disconnect_arduino(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self._set_status("Disconnected.")
        else:
            self._set_status("No active serial connection.")

    def _build_serial_payload(self):
        if not self.notes:
            raise ValueError("Add at least one note before playback.")
        chunks = []
        for note in self.notes:
            freq = NOTE_FREQUENCIES.get(note["pitch"], 0)
            chunks.append(f"{freq}:{note['duration']}")
        sequence = ",".join(chunks)
        return f"PLAY|{self.buzzer_pin}|{self.tempo_gap_ms}|{sequence}"

    def play_on_arduino(self):
        if not (self.serial_conn and self.serial_conn.is_open):
            messagebox.showwarning("Not Connected", "Connect to Arduino first.")
            return
        try:
            payload = self._build_serial_payload()
            self.serial_conn.write((payload + "\n").encode("utf-8"))
            self._set_status("Song sent. Arduino should start playing now.")
        except Exception as exc:
            messagebox.showerror("Serial Error", str(exc))

    def stop_on_arduino(self):
        if not (self.serial_conn and self.serial_conn.is_open):
            self._set_status("No serial connection.")
            return
        try:
            self.serial_conn.write(b"STOP\n")
            self._set_status("Stop command sent.")
        except Exception as exc:
            messagebox.showerror("Serial Error", str(exc))

    def _generate_cpp_code(self):
        notes_cpp = ", ".join(note["pitch"] for note in self.notes)
        durations_cpp = ", ".join(str(note["duration"]) for note in self.notes)
        return f"""#include "pitches.h"

const int buzzerPin = {self.buzzer_pin};
const int tempoGapMs = {self.tempo_gap_ms};
const int loopPauseMs = {self.loop_pause_ms};

const int melody[] = {{{notes_cpp}}};
const int noteDurations[] = {{{durations_cpp}}};
const int melodyLength = sizeof(melody) / sizeof(melody[0]);

void playSong() {{
  for (int i = 0; i < melodyLength; i++) {{
    if (melody[i] == REST) {{
      noTone(buzzerPin);
      delay(noteDurations[i]);
    }} else {{
      tone(buzzerPin, melody[i], noteDurations[i]);
      delay(noteDurations[i]);
      noTone(buzzerPin);
    }}
    delay(tempoGapMs);
  }}
}}

void setup() {{
  pinMode(buzzerPin, OUTPUT);
}}

void loop() {{
  playSong();
  delay(loopPauseMs);
}}
"""

    def save_cpp(self):
        if not self.notes:
            messagebox.showwarning("No notes", "Add at least one note before exporting.")
            return
        try:
            self._read_inputs()
        except ValueError as exc:
            messagebox.showerror("Input Error", str(exc))
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".cpp",
            filetypes=[("C++ File", "*.cpp"), ("Arduino Sketch", "*.ino"), ("All files", "*.*")],
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self._generate_cpp_code())
            self._set_status(f"Saved C++ file: {file_path}")
            messagebox.showinfo("Exported", "Arduino C++ file saved successfully.")
        except Exception as exc:
            messagebox.showerror("Save Error", str(exc))


if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    app = MusicStudioApp(root)
    root.mainloop()
