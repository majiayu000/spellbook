#!/usr/bin/env python3
"""Put a signed-off character into a film: replaces the CHARACTER section of the HTML.
Usage: python3 use_character.py <character.js> <film.html>
"""
import sys
from pathlib import Path

char, film = Path(sys.argv[1]), Path(sys.argv[2])
html = film.read_text()
start, end = html.index("/* ========== CHARACTER"), html.index("/* ========== WORLD HELPERS")
film.write_text(html[:start] + char.read_text() + "\n" + html[end:])
print("character set in", film)
