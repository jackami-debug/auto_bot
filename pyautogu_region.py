import tkinter as tk
import time
import sys
import ctypes
import re

try:
    from pynput import keyboard as pynput_keyboard
except Exception:
    pynput_keyboard = None


def _enable_windows_dpi_awareness() -> None:
    if not sys.platform.startswith("win"):
        return

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class RegionPickerApp:
    HANDLE_MARGIN = 8
    MIN_SIZE = 20

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("pyauto-region")
        self.root.geometry("560x600")
        self.root.resizable(False, False)

        self.region = None
        self.point = None
        self.overlay = None
        self.canvas = None
        self.rect_id = None
        self.help_text_id = None
        self.value_text_id = None
        self.point_marker_id = None
        self.point_cross_h_id = None
        self.point_cross_v_id = None

        self.selection = None
        self.preview_kind = None
        self.drag_mode = None
        self.drag_start = None
        self.drag_origin = None
        self.screen_w = 0
        self.screen_h = 0
        self.dash_offset = 0
        self.last_enter_trigger = 0.0
        self.global_listener = None
        self.global_enabled = tk.BooleanVar(value=False)
        detected_resolution = f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}"
        self.resolution_options = [
            f"Auto ({detected_resolution})",
            "1920x1080",
            "1600x900",
            "1366x768",
            "1280x720",
            "2560x1440",
        ]
        self.resolution_var = tk.StringVar(value=self.resolution_options[0])

        self.region_var = tk.StringVar(value="(x, y, width, height)")
        self.point_var = tk.StringVar(value="(x, y)")
        self.reverse_input_var = tk.StringVar(value="74,849,360,71")
        self.status_var = tk.StringVar(value="Press Enter to start selecting region.")

        self._build_ui()
        self.root.bind("<Return>", self._on_enter_pressed)
        self.root.bind("0", self._on_point_hotkey)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(120, self.root.focus_force)

    def _build_ui(self) -> None:
        container = tk.Frame(self.root, padx=18, pady=16)
        container.pack(fill="both", expand=True)

        title = tk.Label(
            container,
            text="Press Enter to start selecting region",
            font=("Segoe UI", 14, "bold"),
            anchor="w",
        )
        title.pack(fill="x")

        desc = tk.Label(
            container,
            text=(
                "After overlay appears, drag edges/corners to resize, drag inside to move. "
                "Press Enter to confirm, Esc to cancel."
            ),
            font=("Segoe UI", 10),
            anchor="w",
            justify="left",
            wraplength=520,
            pady=10,
        )
        desc.pack(fill="x")

        resolution_row = tk.Frame(container)
        resolution_row.pack(fill="x", pady=(0, 8))

        resolution_label = tk.Label(
            resolution_row,
            text="Resolution:",
            font=("Segoe UI", 10),
            anchor="w",
        )
        resolution_label.pack(side="left")

        resolution_menu = tk.OptionMenu(
            resolution_row,
            self.resolution_var,
            *self.resolution_options,
        )
        resolution_menu.configure(font=("Segoe UI", 10), width=18)
        resolution_menu.pack(side="left", padx=(8, 0))

        global_row = tk.Frame(container)
        global_row.pack(fill="x", pady=(2, 8))

        global_check = tk.Checkbutton(
            global_row,
            text="Global listen",
            variable=self.global_enabled,
            command=self._toggle_global_listener,
            font=("Segoe UI", 10),
            anchor="w",
        )
        global_check.pack(side="left")

        if pynput_keyboard is None:
            global_check.configure(state="disabled")
            note = tk.Label(
                global_row,
                text="(install: pip install pynput)",
                font=("Segoe UI", 9),
                fg="#a35300",
            )
            note.pack(side="left", padx=(8, 0))

        row = tk.Frame(container)
        row.pack(fill="x", pady=(12, 6))

        copy_btn = tk.Button(
            row,
            text="region",
            width=10,
            font=("Consolas", 11, "bold"),
            command=self.copy_region,
        )
        copy_btn.pack(side="left")

        equal = tk.Label(
            row,
            text=" = ",
            font=("Consolas", 12, "bold"),
            padx=8,
        )
        equal.pack(side="left")

        value = tk.Label(
            row,
            textvariable=self.region_var,
            font=("Consolas", 12),
            anchor="w",
        )
        value.pack(side="left", fill="x", expand=True)

        point_row = tk.Frame(container)
        point_row.pack(fill="x", pady=(0, 6))

        point_btn = tk.Button(
            point_row,
            text="point",
            width=10,
            font=("Consolas", 11, "bold"),
            command=self.copy_point,
        )
        point_btn.pack(side="left")

        point_equal = tk.Label(
            point_row,
            text=" = ",
            font=("Consolas", 12, "bold"),
            padx=8,
        )
        point_equal.pack(side="left")

        point_value = tk.Label(
            point_row,
            textvariable=self.point_var,
            font=("Consolas", 12),
            anchor="w",
        )
        point_value.pack(side="left", fill="x", expand=True)

        reverse_row = tk.Frame(container)
        reverse_row.pack(fill="x", pady=(14, 6))

        reverse_label = tk.Label(
            reverse_row,
            text="座標:",
            font=("Segoe UI", 10),
            anchor="w",
        )
        reverse_label.pack(side="left")

        reverse_entry = tk.Entry(
            reverse_row,
            textvariable=self.reverse_input_var,
            font=("Consolas", 12),
            width=24,
        )
        reverse_entry.pack(side="left", padx=(8, 8), fill="x", expand=True)

        reverse_btn = tk.Button(
            reverse_row,
            text="反推畫面位置",
            width=14,
            font=("Segoe UI", 10, "bold"),
            command=self.preview_input_position,
        )
        reverse_btn.pack(side="left")

        reverse_hint = tk.Label(
            container,
            text="格式：x,y 代表點位；x,y,w,h 代表螢幕區域。",
            font=("Segoe UI", 9),
            fg="#666666",
            anchor="w",
            pady=4,
        )
        reverse_hint.pack(fill="x")

        status = tk.Label(
            container,
            textvariable=self.status_var,
            fg="#1f6f43",
            font=("Segoe UI", 10),
            anchor="w",
            pady=12,
        )
        status.pack(fill="x")

    def _on_enter_pressed(self, _event=None) -> None:
        self._trigger_enter_action()

    def _trigger_enter_action(self) -> None:
        now = time.monotonic()
        if now - self.last_enter_trigger < 0.22:
            return
        self.last_enter_trigger = now

        if self.overlay is None:
            self.start_selection()
        else:
            self._confirm_selection()

    def _on_point_hotkey(self, _event=None) -> None:
        self._record_point()

    def _get_cursor_position(self) -> tuple[int, int]:
        if sys.platform.startswith("win"):
            class _POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            pt = _POINT()
            if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
                return int(pt.x), int(pt.y)
        return self.root.winfo_pointerx(), self.root.winfo_pointery()

    def _record_point(self) -> None:
        x, y = self._get_cursor_position()
        self.point = (x, y)
        self.point_var.set(f"({x}, {y})")
        self.status_var.set(f"Point recorded: {x}, {y}. Click point button to copy.")
        if self.overlay is not None:
            self._close_overlay()

    def _parse_reverse_input(self, raw_value: str) -> tuple[str, tuple[int, ...]]:
        normalized = raw_value.strip()
        normalized = normalized.replace("(", "").replace(")", "")
        normalized = normalized.replace("，", ",")
        parts = [part for part in re.split(r"[\s,]+", normalized) if part]

        if len(parts) not in (2, 4):
            raise ValueError("Expected 2 or 4 numbers.")

        values = tuple(int(part) for part in parts)
        return ("point" if len(values) == 2 else "region"), values

    def preview_input_position(self) -> None:
        raw_value = self.reverse_input_var.get()

        try:
            kind, values = self._parse_reverse_input(raw_value)
        except Exception:
            self.status_var.set("Invalid input. Use x,y or x,y,w,h.")
            return

        if kind == "point":
            x, y = values
            self._show_point_preview(x, y)
            self.status_var.set(f"Previewing point: ({x}, {y})")
            return

        x, y, width, height = values
        if width <= 0 or height <= 0:
            self.status_var.set("Region width and height must be greater than 0.")
            return

        self._show_region_preview(x, y, width, height)
        self.status_var.set(f"Previewing region: ({x}, {y}, {width}, {height})")

    def _show_region_preview(self, x: int, y: int, width: int, height: int) -> None:
        self._close_overlay()
        self.start_selection()
        if self.canvas is None:
            return

        left = self._clamp_x(x)
        top = self._clamp_y(y)
        right = max(left, min(x + width, self.screen_w))
        bottom = max(top, min(y + height, self.screen_h))

        if right < left:
            left, right = right, left
        if bottom < top:
            top, bottom = bottom, top

        self.preview_kind = "region"
        self.selection = (left, top, right, bottom)
        self._render_selection()
        if self.help_text_id is not None:
            self.canvas.itemconfig(self.help_text_id, text="Preview mode: press Esc or Enter to close")
        if self.value_text_id is not None:
            self.canvas.itemconfig(
                self.value_text_id,
                text=f"Preview: ({left}, {top}, {right - left}, {bottom - top})",
            )

    def _show_point_preview(self, x: int, y: int) -> None:
        self._close_overlay()
        self.start_selection()
        if self.canvas is None:
            return

        cx = self._clamp_x(x)
        cy = self._clamp_y(y)
        self.preview_kind = "point"
        self.selection = None
        self._render_point_preview(cx, cy)
        if self.help_text_id is not None:
            self.canvas.itemconfig(self.help_text_id, text="Preview mode: press Esc or Enter to close")
        if self.value_text_id is not None:
            self.canvas.itemconfig(self.value_text_id, text=f"Preview: ({cx}, {cy})")

    def _render_point_preview(self, x: int, y: int) -> None:
        if self.canvas is None:
            return

        self._clear_point_preview()

        radius = 10
        color = "#ff4d4f"
        self.point_marker_id = self.canvas.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            outline=color,
            width=3,
        )
        self.point_cross_h_id = self.canvas.create_line(
            x - radius - 6,
            y,
            x + radius + 6,
            y,
            fill=color,
            width=2,
        )
        self.point_cross_v_id = self.canvas.create_line(
            x,
            y - radius - 6,
            x,
            y + radius + 6,
            fill=color,
            width=2,
        )
        self.canvas.create_text(
            x + 18,
            y - 18,
            anchor="nw",
            fill="white",
            font=("Consolas", 11, "bold"),
            text=f"({x}, {y})",
        )

    def _clear_point_preview(self) -> None:
        if self.canvas is None:
            return

        for attr_name in ("point_marker_id", "point_cross_h_id", "point_cross_v_id"):
            item_id = getattr(self, attr_name)
            if item_id is not None:
                try:
                    self.canvas.delete(item_id)
                except tk.TclError:
                    pass
                setattr(self, attr_name, None)

    def start_selection(self) -> None:
        if self.overlay is not None:
            return

        self.overlay = tk.Toplevel(self.root)
        self.overlay.withdraw()
        self.overlay.overrideredirect(True)

        self.screen_w, self.screen_h = self._get_selected_resolution()
        self.overlay.geometry(f"{self.screen_w}x{self.screen_h}+0+0")

        try:
            self.overlay.attributes("-topmost", True)
        except tk.TclError:
            pass

        try:
            self.overlay.attributes("-alpha", 0.28)
        except tk.TclError:
            pass

        self.overlay.configure(bg="black")

        self.canvas = tk.Canvas(
            self.overlay,
            cursor="cross",
            bg="black",
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self._create_default_selection()
        self._draw_overlay_guides()

        self.canvas.bind("<ButtonPress-1>", self._on_canvas_press)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        self.canvas.bind("<Motion>", self._on_canvas_motion)
        self.overlay.bind("<Return>", self._on_enter_pressed)
        self.overlay.bind("0", self._on_point_hotkey)
        self.overlay.bind("<Escape>", self._cancel_selection)

        self.overlay.deiconify()
        self.overlay.lift()
        self.overlay.focus_force()

        try:
            self.overlay.grab_set()
        except tk.TclError:
            pass

        self.status_var.set(
            f"Overlay active ({self.screen_w}x{self.screen_h}). Drag to adjust, then press Enter."
        )
        self._render_selection()
        self._animate_dashed_border()
        self._keep_overlay_topmost()

    def _get_selected_resolution(self) -> tuple[int, int]:
        actual_w = self.overlay.winfo_screenwidth()
        actual_h = self.overlay.winfo_screenheight()
        selected = self.resolution_var.get().strip()

        if selected.startswith("Auto"):
            return actual_w, actual_h

        try:
            width_text, height_text = selected.lower().split("x", 1)
            width = int(width_text)
            height = int(height_text)
        except (ValueError, TypeError):
            return actual_w, actual_h

        width = max(640, min(width, actual_w))
        height = max(360, min(height, actual_h))
        return width, height

    def _create_default_selection(self) -> None:
        self.selection = None
        self.rect_id = self.canvas.create_rectangle(
            0,
            0,
            0,
            0,
            outline="white",
            width=2,
            dash=(4, 4),
            state="hidden",
        )

    def _draw_overlay_guides(self) -> None:
        self.help_text_id = self.canvas.create_text(
            16,
            16,
            anchor="nw",
            fill="white",
            font=("Segoe UI", 11, "bold"),
            text="Drag border/corners to resize, drag inside to move, Enter confirm, Esc cancel",
        )

        self.value_text_id = self.canvas.create_text(
            16,
            44,
            anchor="nw",
            fill="white",
            font=("Consolas", 11),
            text="",
        )

    def _keep_overlay_topmost(self) -> None:
        if self.overlay is None:
            return

        try:
            self.overlay.lift()
            self.overlay.attributes("-topmost", True)
        except tk.TclError:
            return

        self.overlay.after(250, self._keep_overlay_topmost)

    def _animate_dashed_border(self) -> None:
        if self.overlay is None or self.canvas is None or self.rect_id is None:
            return

        self.dash_offset = (self.dash_offset + 1) % 8
        self.canvas.itemconfig(self.rect_id, dashoffset=self.dash_offset)
        self.overlay.after(90, self._animate_dashed_border)

    def _clamp_x(self, value: int) -> int:
        return max(0, min(value, self.screen_w - 1))

    def _clamp_y(self, value: int) -> int:
        return max(0, min(value, self.screen_h - 1))

    def _normalize_selection(self, selection) -> tuple[int, int, int, int]:
        x1, y1, x2, y2 = selection
        left = min(x1, x2)
        right = max(x1, x2)
        top = min(y1, y2)
        bottom = max(y1, y2)
        return left, top, right, bottom

    def _hit_test(self, x: int, y: int) -> str:
        if self.selection is None:
            return "draw"

        x1, y1, x2, y2 = self._normalize_selection(self.selection)
        m = self.HANDLE_MARGIN

        on_left = abs(x - x1) <= m and y1 - m <= y <= y2 + m
        on_right = abs(x - x2) <= m and y1 - m <= y <= y2 + m
        on_top = abs(y - y1) <= m and x1 - m <= x <= x2 + m
        on_bottom = abs(y - y2) <= m and x1 - m <= x <= x2 + m
        inside = x1 + m < x < x2 - m and y1 + m < y < y2 - m

        if on_left and on_top:
            return "nw"
        if on_right and on_top:
            return "ne"
        if on_left and on_bottom:
            return "sw"
        if on_right and on_bottom:
            return "se"
        if on_left:
            return "w"
        if on_right:
            return "e"
        if on_top:
            return "n"
        if on_bottom:
            return "s"
        if inside:
            return "move"
        return "draw"

    def _cursor_for_mode(self, mode: str) -> str:
        cursor_map = {
            "move": "fleur",
            "n": "sb_v_double_arrow",
            "s": "sb_v_double_arrow",
            "e": "sb_h_double_arrow",
            "w": "sb_h_double_arrow",
            "ne": "size_ne_sw",
            "sw": "size_ne_sw",
            "nw": "size_nw_se",
            "se": "size_nw_se",
            "draw": "crosshair",
        }
        return cursor_map.get(mode, "crosshair")

    def _on_canvas_motion(self, event) -> None:
        if self.overlay is None or self.canvas is None:
            return

        x = self._clamp_x(event.x)
        y = self._clamp_y(event.y)
        mode = self.drag_mode if self.drag_mode else self._hit_test(x, y)
        self.canvas.configure(cursor=self._cursor_for_mode(mode))

    def _on_canvas_press(self, event) -> None:
        if self.preview_kind is not None:
            return

        x = self._clamp_x(event.x)
        y = self._clamp_y(event.y)
        mode = self._hit_test(x, y)

        self.drag_mode = mode
        self.drag_start = (x, y)

        if self.selection is None:
            self.selection = (x, y, x + self.MIN_SIZE, y + self.MIN_SIZE)
            self.canvas.itemconfig(self.rect_id, state="normal")
        self.drag_origin = self._normalize_selection(self.selection)

        if mode == "draw":
            self.selection = (x, y, x + self.MIN_SIZE, y + self.MIN_SIZE)
            self.drag_origin = self._normalize_selection(self.selection)

        self._render_selection()

    def _on_canvas_drag(self, event) -> None:
        if self.preview_kind is not None:
            return

        if self.drag_mode is None or self.drag_start is None or self.drag_origin is None:
            return

        x = self._clamp_x(event.x)
        y = self._clamp_y(event.y)

        start_x, start_y = self.drag_start
        x1, y1, x2, y2 = self.drag_origin
        width = x2 - x1
        height = y2 - y1

        if self.drag_mode == "draw":
            left = min(start_x, x)
            right = max(start_x, x)
            top = min(start_y, y)
            bottom = max(start_y, y)
            self.selection = (left, top, right, bottom)
            self._render_selection()
            return

        if self.drag_mode == "move":
            dx = x - start_x
            dy = y - start_y

            left = max(0, min(x1 + dx, self.screen_w - width))
            top = max(0, min(y1 + dy, self.screen_h - height))
            right = left + width
            bottom = top + height
            self.selection = (left, top, right, bottom)
            self._render_selection()
            return

        left, top, right, bottom = x1, y1, x2, y2

        if "w" in self.drag_mode:
            left = min(x, right - self.MIN_SIZE)
        if "e" in self.drag_mode:
            right = max(x, left + self.MIN_SIZE)
        if "n" in self.drag_mode:
            top = min(y, bottom - self.MIN_SIZE)
        if "s" in self.drag_mode:
            bottom = max(y, top + self.MIN_SIZE)

        left = max(0, left)
        top = max(0, top)
        right = min(self.screen_w - 1, right)
        bottom = min(self.screen_h - 1, bottom)

        if right - left < self.MIN_SIZE:
            if "w" in self.drag_mode:
                left = max(0, right - self.MIN_SIZE)
            else:
                right = min(self.screen_w - 1, left + self.MIN_SIZE)

        if bottom - top < self.MIN_SIZE:
            if "n" in self.drag_mode:
                top = max(0, bottom - self.MIN_SIZE)
            else:
                bottom = min(self.screen_h - 1, top + self.MIN_SIZE)

        self.selection = (left, top, right, bottom)
        self._render_selection()

    def _on_canvas_release(self, _event) -> None:
        if self.preview_kind is not None:
            return

        self.drag_mode = None
        self.drag_start = None
        self.drag_origin = None
        if self.canvas is not None:
            self.canvas.configure(cursor="crosshair")

    def _render_selection(self) -> None:
        if self.canvas is None or self.rect_id is None:
            return

        if self.selection is None:
            self.canvas.itemconfig(self.rect_id, state="hidden")
            self.canvas.itemconfig(self.value_text_id, text="")
            return

        x1, y1, x2, y2 = self._normalize_selection(self.selection)
        self.selection = (x1, y1, x2, y2)
        self.canvas.itemconfig(self.rect_id, state="normal")
        self.canvas.coords(self.rect_id, x1, y1, x2, y2)

        width = x2 - x1
        height = y2 - y1
        self.canvas.itemconfig(self.value_text_id, text=f"({x1}, {y1}, {width}, {height})")

    def _confirm_selection(self, _event=None) -> None:
        if self.preview_kind == "point":
            self.status_var.set("Point preview shown. Press Esc or Enter to close.")
            self._close_overlay()
            return

        if self.selection is None or self.overlay is None:
            self.status_var.set("No region selected yet.")
            return

        x1, y1, x2, y2 = self._normalize_selection(self.selection)
        width = x2 - x1
        height = y2 - y1

        if width < self.MIN_SIZE or height < self.MIN_SIZE:
            self.status_var.set("Region is too small. Adjust and press Enter again.")
            return

        screen_x = x1 + self.overlay.winfo_rootx()
        screen_y = y1 + self.overlay.winfo_rooty()

        self.region = (screen_x, screen_y, width, height)
        self.region_var.set(f"({screen_x}, {screen_y}, {width}, {height})")
        self.status_var.set("Region recorded. Click region button to copy.")
        self._close_overlay()

    def _cancel_selection(self, _event=None) -> None:
        self.status_var.set("Selection canceled. Press Enter to start again.")
        self._close_overlay()

    def _close_overlay(self) -> None:
        if self.overlay is not None:
            try:
                self.overlay.grab_release()
            except tk.TclError:
                pass
            self.overlay.destroy()

        self.overlay = None
        self.canvas = None
        self.rect_id = None
        self.help_text_id = None
        self.value_text_id = None
        self.point_marker_id = None
        self.point_cross_h_id = None
        self.point_cross_v_id = None
        self.selection = None
        self.preview_kind = None
        self.drag_mode = None
        self.drag_start = None
        self.drag_origin = None
        self.dash_offset = 0
        if not self.global_enabled.get():
            self.root.focus_force()

    def _toggle_global_listener(self) -> None:
        if self.global_enabled.get():
            self._start_global_listener()
        else:
            self._stop_global_listener()

    def _start_global_listener(self) -> None:
        if pynput_keyboard is None:
            self.global_enabled.set(False)
            self.status_var.set("Global listen unavailable. Install with: pip install pynput")
            return

        if self.global_listener is not None:
            return

        def on_press(key) -> None:
            self.root.after(0, self._handle_global_key, key)

        self.global_listener = pynput_keyboard.Listener(on_press=on_press)
        self.global_listener.daemon = True
        self.global_listener.start()
        self.status_var.set("Global listen is ON.")

    def _stop_global_listener(self) -> None:
        if self.global_listener is not None:
            self.global_listener.stop()
            self.global_listener = None
        self.status_var.set("Global listen is OFF.")

    def _handle_global_key(self, key) -> None:
        if key == pynput_keyboard.Key.enter:
            self._trigger_enter_action()
            return
        if key == pynput_keyboard.Key.esc:
            if self.overlay is not None:
                self._cancel_selection()
            return
        if isinstance(key, pynput_keyboard.KeyCode) and key.char:
            if key.char == "0":
                self._record_point()
                return
            try:
                self.root.event_generate(f"<KeyPress-{key.char}>")
            except tk.TclError:
                pass

    def _on_close(self) -> None:
        self._stop_global_listener()
        if self.overlay is not None:
            self._close_overlay()
        self.root.destroy()

    def copy_region(self) -> None:
        if self.region is None:
            self.status_var.set("No region recorded. Press Enter and select first.")
            return

        value = f"{self.region[0]},{self.region[1]},{self.region[2]},{self.region[3]}"
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.root.update()
        self.status_var.set(f"Copied to clipboard: {value}")

    def copy_point(self) -> None:
        if self.point is None:
            self.status_var.set("No point recorded. Press 0 to capture first.")
            return

        value = f"{self.point[0]},{self.point[1]}"
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.root.update()
        self.status_var.set(f"Copied to clipboard: {value}")


def main() -> None:
    _enable_windows_dpi_awareness()
    root = tk.Tk()
    RegionPickerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
