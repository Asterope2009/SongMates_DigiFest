"""
MusicMatch – local prototype (Tkinter)
--------------------------------------
A beginner‑friendly desktop app that matches users by their top artists
and shows compatibility percentages. Single-file so you can run it
immediately and customize.

How to run:
1) Install Python 3.10+ from https://python.org
2) (Optional) Create a virtual env
3) Save this file as musicmatch.py and run:  python musicmatch.py

What it does:
- Enter your name and up to 5 artists (comma-separated)
- Click "Find Matches" to compare against a small sample dataset
- Shows top 5 matches with % and shared artists
- Add yourself to the local dataset in-memory (optionally save to JSON)

Collaborating note:
- Tic Tac can work on GUI sections (Tkinter layout/styles)
- Niks can tweak matching logic and data loading/saving

"""
from __future__ import annotations
import random
from tkinter import ttk
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

# ----------------------------
# Data & matching logic (backend)
# ----------------------------


@dataclass
class User:
    name: str
    top_artists: List[str] = field(default_factory=list)

    def normalized_artists(self) -> List[str]:
        return [normalize_artist(a) for a in self.top_artists if a.strip()]


def normalize_artist(a: str) -> str:
    # Lowercase, strip spaces, collapse inner spaces
    return " ".join(a.strip().casefold().split())


def jaccard_similarity(a: List[str], b: List[str]) -> float:
    """Return Jaccard similarity (0..1) of two artist lists, using set logic."""
    set_a = set(a)
    set_b = set(b)
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def overlap_count(a: List[str], b: List[str]) -> int:
    return len(set(a) & set(b))


class Matcher:
    def __init__(self, users: List[User] | None = None):
        self.users: List[User] = users or []

    def add_user(self, user: User) -> None:
        # If name exists, replace; otherwise append
        for i, u in enumerate(self.users):
            if u.name.strip().casefold() == user.name.strip().casefold():
                self.users[i] = user
                return
        self.users.append(user)

    def match(self, query: User, top_k: int = 5) -> List[Tuple[User, float, List[str]]]:
        q_art = query.normalized_artists()
        scored = []
        for u in self.users:
            if u.name.strip().casefold() == query.name.strip().casefold():
                continue  # don't match with self
            u_art = u.normalized_artists()
            score = jaccard_similarity(q_art, u_art)
            shared = sorted(set(q_art) & set(u_art))
            scored.append((u, score, shared))
        # Sort by score desc, then by overlap count desc, then name asc
        scored.sort(key=lambda x: (x[1], len(x[2]),
                    x[0].name.casefold()), reverse=True)
        return scored[:top_k]

    # --- persistence ---
    def to_dict(self) -> Dict:
        return {"users": [{"name": u.name, "top_artists": u.top_artists} for u in self.users]}

    @classmethod
    def from_file(cls, path: str) -> "Matcher":
        if not os.path.exists(path):
            return cls(sample_users())
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        users = [User(u.get("name", ""), u.get("top_artists", []))
                 for u in data.get("users", [])]
        return cls(users)

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


def sample_users() -> List[User]:
    # Lightweight seed data you can edit
    seed = [
        ("Aarav", ["Taylor Swift", "Weeknd",
         "Imagine Dragons", "AURORA", "Coldplay"]),
        ("Zoya", ["BTS", "Blackpink", "IU", "NewJeans", "Weeknd"]),
        ("Kabir", ["Arijit Singh", "Pritam",
         "Shreya Ghoshal", "A R Rahman", "Jubin Nautiyal"]),
        ("Mia", ["Billie Eilish", "Lana Del Rey",
         "AURORA", "Grimes", "FKA twigs"]),
        ("Rishabh", ["Linkin Park", "Imagine Dragons",
         "Fall Out Boy", "Green Day", "My Chemical Romance"]), +
        ("Anaya", ["AP Dhillon", "Shubh",
         "Karan Aujla", "Badshah", "Diljit Dosanjh"]),
        ("Noah", ["Drake", "Kendrick Lamar",
         "J. Cole", "Travis Scott", "SZA"]),
        ("Ishi", ["A R Rahman", "Shreya Ghoshal",
         "KK", "Arijit Singh", "Sonu Nigam"]),
        ("Yuto", ["YOASOBI", "Kenshi Yonezu", "Aimer", "King Gnu", "Eve"]),
        ("Sana", ["Twice", "Blackpink", "NewJeans", "LE SSERAFIM", "IVE"]),
    ]
    return [User(n, a) for n, a in seed]


# ----------------------------
# GUI (frontend) – Tkinter
# ----------------------------


root = tk.Tk()
root.title("Music Match")
root.geometry("500x500")
root.configure(bg="#1e1e2f")

# --- Styling ---
style = ttk.Style(root)
style.theme_use("clam")

style.configure("TLabel",
                background="#1e1e2f",
                foreground="white",
                font=("Segoe UI", 12))

style.configure("TButton",
                background="#6c63ff",
                foreground="white",
                font=("Segoe UI", 11, "bold"),
                padding=10,
                relief="flat")

style.map("TButton",
          background=[("active", "#857dff")])

# --- Data ---
artists = [
    "Taylor Swift", "The Weeknd", "Billie Eilish",
    "Drake", "Kendrick Lamar", "Ariana Grande",
    "Ed Sheeran", "Dua Lipa", "Coldplay", "BTS"
]

selected_artists = []

# --- Functions ---


def add_artist(event):
    widget = event.widget
    index = widget.nearest(event.y)
    artist = widget.get(index)

    if artist not in selected_artists and len(selected_artists) < 5:
        selected_artists.append(artist)
        selected_label.config(text="Selected: " + ", ".join(selected_artists))


def on_hover(event):
    event.widget.itemconfig("active", foreground="lime")


def on_leave(event):
    index = event.widget.nearest(event.y)
    event.widget.itemconfig(index, foreground="white")


def find_match():
    if len(selected_artists) < 5:
        result_label.config(
            text="⚠️ Please select 5 artists!", foreground="orange")
        return

    # fake % matching (random for now)
    percentage = random.randint(50, 100)
    result_label.config(
        text=f"✨ You matched {percentage}% ✨", foreground="#6c63ff")


# --- Widgets ---
title_label = ttk.Label(root, text="🎶 Music Match 🎶",
                        font=("Segoe UI", 20, "bold"))
title_label.pack(pady=20)

listbox = tk.Listbox(root, bg="#2c2c3e", fg="white", selectbackground="#6c63ff",
                     font=("Segoe UI", 12), width=30, height=8, activestyle="none")
for artist in artists:
    listbox.insert(tk.END, artist)
listbox.pack(pady=10)

# Bind hover + click
listbox.bind("<Motion>", on_hover)
listbox.bind("<Leave>", on_leave)
listbox.bind("<Button-1>", add_artist)

selected_label = ttk.Label(root, text="Selected: None")
selected_label.pack(pady=10)

match_button = ttk.Button(root, text="Find My Match", command=find_match)
match_button.pack(pady=20)

result_label = ttk.Label(root, text="", font=("Segoe UI", 14, "bold"))
result_label.pack(pady=20)

root.mainloop()
