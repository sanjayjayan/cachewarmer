import tkinter as tk
from tkinter import messagebox
import json
import os
import threading
import sys
import traceback
import webbrowser
import ctypes

try:
    # Fix for Windows Taskbar Icon
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("cachewarmer.app.v1")
except Exception:
    pass


# Wrap everything in try-except to catch initialization errors
try:
    from services.app import start_app, request_stop, APP_VERSION
except Exception as e:
    print(f"Error importing services.app: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

CONFIG_FILE = "config.json"

# Optional tray (pystray + Pillow)
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    pystray = None


# -------------------------
# Helpers
# -------------------------

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self.tip,
            text=self.text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            justify=tk.LEFT
        ).pack()

    def hide(self, event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class TextRedirector:
    def __init__(self, widget):
        self.widget = widget

    def write(self, text):
        # Schedule the update on the main thread to be thread-safe
        self.widget.after(0, self._append, text)

    def _append(self, text):
        try:
            self.widget.insert(tk.END, text)
            self.widget.see(tk.END)
        except Exception:
            pass

    def flush(self):
        pass


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)


config = load_config()



# -------------------------
# Window
# -------------------------

root = tk.Tk()
root.title(f"CacheWarmer v{APP_VERSION}")
if os.path.exists("cloud.ico"):
    try:
        root.iconbitmap("cloud.ico")
    except Exception:
        pass
root.minsize(560, 700)

# Center window on screen (cross-platform)
root.update_idletasks()
width = 600
height = 800
x = (root.winfo_screenwidth() // 2) - (width // 2)
y = (root.winfo_screenheight() // 2) - (height // 2)
root.geometry(f'{width}x{height}+{x}+{y}')

# Main padded frame so content doesn't touch edges
main = tk.Frame(root, padx=20, pady=14)
main.pack(fill=tk.BOTH, expand=True)
main.columnconfigure(1, weight=1)

# -------------------------
# Fields
# -------------------------

row = 0

tk.Label(main, text="Real-Debrid API Key").grid(row=row, column=0, sticky="w")
api_entry = tk.Entry(main, width=62)
api_entry.grid(row=row, column=1)
api_entry.insert(0, config.get("real_debrid_api_key", ""))
row += 1

tk.Label(main, text="Delay Between Movies (sec)").grid(row=row, column=0, sticky="w")
delay_entry = tk.Entry(main)
delay_entry.grid(row=row, column=1)
delay_entry.insert(0, str(config.get("delay_between_movies", 5)))
row += 1

tk.Label(main, text="Minimum Seeders").grid(row=row, column=0, sticky="w")
seed_entry = tk.Entry(main)
seed_entry.grid(row=row, column=1)
seed_entry.insert(0, str(config.get("min_seeders", 5)))
row += 1

tk.Label(main, text="Minimum Resolution").grid(row=row, column=0, sticky="w")
res_var = tk.StringVar(value=str(config.get("min_resolution", 720)))
res_menu = tk.OptionMenu(main, res_var, "720", "1080", "2160")
res_menu.grid(row=row, column=1)
row += 1

tk.Label(main, text="Max Per Quality").grid(row=row, column=0, sticky="w")
maxpq_entry = tk.Entry(main)
maxpq_entry.grid(row=row, column=1)
maxpq_entry.insert(0, str(config.get("max_per_quality", 1)))
row += 1

pack_var = tk.BooleanVar(value=config.get("allow_packs_fallback", True))
pack_check = tk.Checkbutton(main, text="Allow Pack Fallback", variable=pack_var)
pack_check.grid(row=row, columnspan=2)
row += 1

# -------------------------
# Run mode
# -------------------------
RUN_MODE_LABELS = ("One-shot", "Loop forever", "Repeat every X min")
RUN_MODE_VALUES = {"One-shot": "oneshot", "Loop forever": "loop", "Repeat every X min": "interval"}
RUN_MODE_REVERSE = {v: k for k, v in RUN_MODE_VALUES.items()}
tk.Label(main, text="Run mode").grid(row=row, column=0, sticky="w")
run_mode_var = tk.StringVar(value=RUN_MODE_REVERSE.get(config.get("run_mode", "oneshot"), "One-shot"))
run_mode_menu = tk.OptionMenu(main, run_mode_var, *RUN_MODE_LABELS)
run_mode_menu.grid(row=row, column=1)
row += 1

tk.Label(main, text="Repeat interval (min)").grid(row=row, column=0, sticky="w")
repeat_minutes_entry = tk.Entry(main, width=6)
repeat_minutes_entry.grid(row=row, column=1)
repeat_minutes_entry.insert(0, str(config.get("repeat_minutes", 60)))
row += 1

# -------------------------
# TMDB Discover+ Addon
# -------------------------

tk.Label(main, text="TMDB Discover+ Base URLs\n(Click to open / Right-click copy)").grid(row=row, column=0, sticky="nw")
link_frame = tk.Frame(main)
link_frame.grid(row=row, column=1, sticky="w")

def open_url(url):
    webbrowser.open(url)

def copy_url(url):
    root.clipboard_clear()
    root.clipboard_append(url)
    root.update()
    messagebox.showinfo("Copied", "URL copied to clipboard!")

def make_link_label(parent, text, url):
    lbl = tk.Label(parent, text=text, fg="blue", cursor="hand2", font=("TkDefaultFont", 9, "underline"))
    lbl.bind("<Button-1>", lambda e: open_url(url))
    lbl.bind("<Button-3>", lambda e: copy_url(url))
    return lbl

link1 = make_link_label(link_frame, "Link 1: baby-beamup.club", "https://84f50d1c22e7-tmdb-discover-plus.baby-beamup.club/")
link1.pack(anchor="w")

link2 = make_link_label(link_frame, "Link 2: ElfHosted", "https://tmdb-discover-plus.elfhosted.com/")
link2.pack(anchor="w")
row += 1

tk.Label(main, text="TMDB Discover+ Manifest URL").grid(row=row, column=0, sticky="nw")
tmdb_manifest_text = tk.Text(main, height=4, width=50)
tmdb_manifest_text.grid(row=row, column=1, columnspan=2, sticky="ew", pady=2)
tmdb_manifest_text.insert("1.0", config.get("tmdb_manifest_url", ""))
row += 1

tk.Label(main, text="TMDB Catalog Pages to Fetch").grid(row=row, column=0, sticky="w")
tmdb_pages_entry = tk.Entry(main, width=10)
tmdb_pages_entry.grid(row=row, column=1, sticky="w")
tmdb_pages_entry.insert(0, str(config.get("tmdb_catalog_pages", 5)))
row += 1

# -------------------------
# IMDb List URL(s)
# -------------------------

tk.Label(main, text="IMDb List URL(s)").grid(row=row, column=0, sticky="nw")
imdb_urls_text = tk.Text(main, height=3, width=50)
imdb_urls_text.grid(row=row, column=1, columnspan=2, sticky="ew", pady=2)
row += 1

# -------------------------
# Movies (IMDb IDs)
# -------------------------

tk.Label(main, text="Movies (IMDb IDs)").grid(row=row, column=0, sticky="nw")
movies_text = tk.Text(main, height=4, width=50)
movies_text.grid(row=row, column=1, columnspan=2, sticky="ew", pady=2)
row += 1

# -------------------------
# Series (IMDb IDs or URLs) — cache all episodes
# -------------------------

tk.Label(main, text="Series (IMDb IDs/URLs)").grid(row=row, column=0, sticky="nw")
series_text = tk.Text(main, height=2, width=50)
series_text.grid(row=row, column=1, columnspan=2, sticky="ew", pady=2)
row += 1

# -------------------------
# Buttons (centered row)
# -------------------------

def save_clicked():
    try:
        repeat_m = int(repeat_minutes_entry.get())
    except (ValueError, TypeError):
        repeat_m = 60
    try:
        tmdb_pages = int(tmdb_pages_entry.get())
    except (ValueError, TypeError):
        tmdb_pages = 5
    cfg = {
        "real_debrid_api_key": api_entry.get().strip(),
        "delay_between_movies": int(delay_entry.get()),
        "min_seeders": int(seed_entry.get()),
        "min_resolution": int(res_var.get()),
        "max_per_quality": int(maxpq_entry.get()),
        "allow_packs_fallback": pack_var.get(),
        "run_mode": RUN_MODE_VALUES.get(run_mode_var.get(), "oneshot"),
        "repeat_minutes": repeat_m,
        "tmdb_manifest_url": tmdb_manifest_text.get("1.0", tk.END).strip(),
        "tmdb_catalog_pages": tmdb_pages,
    }

    save_config(cfg)
    messagebox.showinfo("Saved", "Settings saved!")


def start_clicked():
    # Validate API Key
    api_key = api_entry.get().strip()
    if not api_key:
        messagebox.showerror("Error", "Real-Debrid API Key is required!")
        return

    # Get Inputs
    imdb_urls = imdb_urls_text.get("1.0", tk.END).strip()
    movies = movies_text.get("1.0", tk.END).strip()
    series = series_text.get("1.0", tk.END).strip()
    tmdb_manifest_url = tmdb_manifest_text.get("1.0", tk.END).strip()

    # Validate Inputs
    if not imdb_urls and not movies and not series and not tmdb_manifest_url:
        messagebox.showerror("Error", "Please provide at least one input:\n- TMDB Discover+ Manifest URL\n- IMDb List URL\n- Movie ID/Title\n- Series ID/URL")
        return

    # Cross-validation: IDs in URL box?
    for line in imdb_urls.splitlines():
        line = line.strip()
        if not line: continue
        # Detect simple ID like tt1234567 inside URL box
        if line.lower().startswith("tt") and "imdb.com" not in line.lower():
            messagebox.showerror("Input Error", f"Found ID in List URL box: '{line}'\nPlease paste IDs in the Movies or Series box, and only List URLs here.")
            return

    # Cross-validation: List URLs in ID box?
    for line in (movies + "\n" + series).splitlines():
        line = line.strip()
        if "imdb.com/list" in line.lower():
            messagebox.showerror("Input Error", f"Found List URL in Movies/Series box: '{line}'\nPlease move it to the 'IMDb List URL(s)' box.")
            return

    log_box.delete("1.0", tk.END)
    try:
        repeat_m = int(repeat_minutes_entry.get())
    except (ValueError, TypeError):
        repeat_m = 60
    try:
        tmdb_pages = int(tmdb_pages_entry.get())
    except (ValueError, TypeError):
        tmdb_pages = 5
    messagebox.showinfo("Started", "Cache Warmer running in background.")
    
    # Helper for catalog selection on main thread
    def select_catalog_ui(catalogs):
        import queue
        q = queue.Queue()
        
        def ask():
            try:
                # Create a top-level window for selection
                top = tk.Toplevel(root)
                top.title("Select Catalog")
                top.geometry("400x300")
                
                # Center it
                x = root.winfo_x() + (root.winfo_width() // 2) - 200
                y = root.winfo_y() + (root.winfo_height() // 2) - 150
                top.geometry(f"+{x}+{y}")
                top.grab_set() # Modal
                
                tk.Label(top, text="Please select a catalog to fetch:", font=("Arial", 10, "bold")).pack(pady=10)
                
                lb = tk.Listbox(top, selectmode=tk.SINGLE, width=50, height=10)
                lb.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
                
                for cat in catalogs:
                    name = cat.get("name", "Unknown")
                    cat_id = cat.get("id", "")
                    cat_type = cat.get("type", "")
                    lb.insert(tk.END, f"{name} ({cat_type}) - {cat_id}")
                
                def on_select():
                    sel = lb.curselection()
                    if not sel:
                        return
                    idx = sel[0]
                    q.put(catalogs[idx])
                    top.destroy()
                
                tk.Button(top, text="Select", command=on_select).pack(pady=10)
                top.protocol("WM_DELETE_WINDOW", lambda: (q.put(None), top.destroy()))
                
                top.wait_window()
            except Exception as e:
                print(f"Error in selection UI: {e}")
                q.put(None)

        root.after(0, ask)
        # Block background thread until user selects
        return q.get()

    kwargs = {
        "imdb_list_urls": imdb_urls or None,
        "movies": movies or None,
        "series_list": series or None,
        "tmdb_manifest_url": tmdb_manifest_url or None,
        "tmdb_catalog_pages": tmdb_pages,
        "run_mode": RUN_MODE_VALUES.get(run_mode_var.get(), "oneshot"),
        "repeat_minutes": repeat_m,
        "api_key": api_key,
        "select_catalog_func": select_catalog_ui,
    }

    start_btn.config(state="disabled")

    def run_wrapper():
        try:
            start_app(**kwargs)
        finally:
            # Re-enable start button on main thread
            root.after(0, lambda: start_btn.config(state="normal"))

    threading.Thread(target=run_wrapper, daemon=True).start()


def stop_clicked():
    request_stop()
    messagebox.showinfo("Stopped", "Stopping Cache Warmer...")

btn_row = tk.Frame(main)
btn_row.grid(row=row, column=0, columnspan=3, pady=(6, 8))
btn_row.columnconfigure(0, weight=1)
btn_row.columnconfigure(1, weight=0)
btn_row.columnconfigure(2, weight=1)
btn_inner = tk.Frame(btn_row)
btn_inner.grid(row=0, column=1)
tk.Button(btn_inner, text="Save Settings", command=save_clicked).pack(side=tk.LEFT, padx=6)
start_btn = tk.Button(btn_inner, text="Start Cache Warmer", command=start_clicked)
start_btn.pack(side=tk.LEFT, padx=6)

tk.Button(btn_inner, text="Stop", command=stop_clicked).pack(side=tk.LEFT, padx=6)
row += 1

# -------------------------
# Logs
# -------------------------

log_box = tk.Text(main, height=15, width=70)
log_box.grid(row=row, column=0, columnspan=3, pady=(10, 20), sticky="nsew")
main.rowconfigure(row, weight=1)

sys.stdout = TextRedirector(log_box)
sys.stderr = TextRedirector(log_box)

# -------------------------
# Tooltips
# -------------------------

ToolTip(api_entry, "Your Real-Debrid API token")
ToolTip(delay_entry, "Seconds to wait between movies")
ToolTip(seed_entry, "Minimum seeders required")
ToolTip(res_menu, "Lowest allowed resolution")
ToolTip(maxpq_entry, "How many torrents per quality")
ToolTip(pack_check, "Allow pack torrents if no singles exist")
ToolTip(run_mode_menu, "One-shot: run once and exit. Loop: repeat forever. Interval: run once, wait X min, repeat.")
ToolTip(repeat_minutes_entry, "Minutes to wait between runs when Run mode is 'interval'")
ToolTip(link1, "https://84f50d1c22e7-tmdb-discover-plus.baby-beamup.club/")
ToolTip(link2, "https://tmdb-discover-plus.elfhosted.com/")
ToolTip(tmdb_manifest_text, "Paste TMDB Discover+ manifest URL (e.g. https://addon.example.com/manifest.json)")
ToolTip(tmdb_pages_entry, "Number of catalog pages to fetch (each page ~20 items, default: 5 pages = ~100 items)")
ToolTip(imdb_urls_text, "Paste one or more IMDb list URLs (e.g. https://www.imdb.com/list/ls091520106/) — one per line")
ToolTip(movies_text, "Paste IMDb IDs (tt...) or titles — one per line; combined with lists above")
ToolTip(series_text, "Paste series IMDb IDs or URLs (e.g. tt0944947 or https://www.imdb.com/title/tt0944947/) — one per line; caches all seasons & episodes")

# -------------------------
# Tray icon (minimize to tray, Show / Start / Stop / Exit)
# -------------------------
tray_icon = None
SHOWN_MINIMIZE_MESSAGE = False


def _tray_show_window():
    root.deiconify()
    root.lift()
    root.focus_force()


def _tray_quit():
    if tray_icon:
        try:
            tray_icon.stop()
        except Exception:
            pass
    root.quit()


def _update_tray_tooltip():
    if not TRAY_AVAILABLE or not tray_icon:
        return
    try:
        from services.app import TRAY_RUNNING, TRAY_CURRENT_ITEM
        status = "Running" if TRAY_RUNNING else "Idle"
        item = (TRAY_CURRENT_ITEM or "").strip()
        if item:
            tip = f"CacheWarmer — {status} — {item}"
        else:
            tip = f"CacheWarmer — {status}"
        if len(tip) > 128:
            tip = tip[:125] + "..."
        tray_icon.title = tip
    except Exception:
        pass
    root.after(2000, _update_tray_tooltip)


def _setup_tray():
    global tray_icon
    if not TRAY_AVAILABLE:
        return
    try:
        def make_icon_image():
            if os.path.exists("cloud.ico"):
                try:
                    return Image.open("cloud.ico")
                except Exception:
                    pass
            w, h = 64, 64
            img = Image.new("RGBA", (w, h), (40, 44, 52, 255))
            draw = ImageDraw.Draw(img)
            draw.rectangle((8, 8, w - 8, h - 8), outline=(97, 175, 239), width=3)
            draw.rectangle((16, 16, w - 16, h - 16), fill=(97, 175, 239, 80))
            return img

        menu = pystray.Menu(
            pystray.MenuItem("Show", lambda *a: root.after(0, _tray_show_window), default=True),
            pystray.MenuItem("Start", lambda *a: root.after(0, start_clicked)),
            pystray.MenuItem("Stop", lambda *a: root.after(0, stop_clicked)),
            pystray.MenuItem("Exit", lambda *a: root.after(0, _tray_quit)),
        )
        icon_image = make_icon_image()
        tray_icon = pystray.Icon("CacheWarmer", icon_image, "CacheWarmer — Idle", menu)
        root.after(2000, _update_tray_tooltip)
        threading.Thread(target=tray_icon.run, daemon=True).start()
    except Exception as e:
        sys.stderr.write(f"Tray setup failed: {e}\n")
        tray_icon = None


def _on_close():
    global SHOWN_MINIMIZE_MESSAGE
    root.withdraw()
    
    if TRAY_AVAILABLE and tray_icon and not SHOWN_MINIMIZE_MESSAGE:
        try:
            tray_icon.notify(
                "I'm operating covertly in the tray... 🕶️\nRight-click icon to Exit.",
                "CacheWarmer Minimized"
            )
            SHOWN_MINIMIZE_MESSAGE = True
        except Exception:
            pass


if TRAY_AVAILABLE:
    root.protocol("WM_DELETE_WINDOW", _on_close)
    # <Iconify> binding removed as it causes crashes on Windows

_setup_tray()


try:
    root.mainloop()
except Exception as e:
    print(f"Error in mainloop: {e}")
    traceback.print_exc()
    sys.exit(1)
