import tkinter as tk


class RegionPickerApp:
    HANDLE_MARGIN = 8
    MIN_SIZE = 20

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("pyauto-region")
        self.root.geometry("560x260")
        self.root.resizable(False, False)

        self.region = None
        self.overlay = None
        self.canvas = None
        self.rect_id = None
        self.help_text_id = None
        self.value_text_id = None

        self.selection = None
        self.drag_mode = None
        self.drag_start = None
        self.drag_origin = None
        self.screen_w = 0
        self.screen_h = 0
        self.dash_offset = 0

        self.region_var = tk.StringVar(value="(x, y, width, height)")
        self.status_var = tk.StringVar(value="Press Enter to start selecting region.")

        self._build_ui()
        self.root.bind("<Return>", self._start_selection_from_key)
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

        status = tk.Label(
            container,
            textvariable=self.status_var,
            fg="#1f6f43",
            font=("Segoe UI", 10),
            anchor="w",
            pady=12,
        )
        status.pack(fill="x")

    def _start_selection_from_key(self, _event) -> None:
        if self.overlay is None:
            self.start_selection()

    def start_selection(self) -> None:
        if self.overlay is not None:
            return

        self.overlay = tk.Toplevel(self.root)
        self.overlay.withdraw()
        self.overlay.overrideredirect(True)

        self.screen_w = self.overlay.winfo_screenwidth()
        self.screen_h = self.overlay.winfo_screenheight()
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
        self.overlay.bind("<Return>", self._confirm_selection)
        self.overlay.bind("<Escape>", self._cancel_selection)

        self.overlay.deiconify()
        self.overlay.lift()
        self.overlay.focus_force()

        try:
            self.overlay.grab_set()
        except tk.TclError:
            pass

        self.status_var.set("Overlay active. Drag to adjust region, then press Enter.")
        self._render_selection()
        self._animate_dashed_border()
        self._keep_overlay_topmost()

    def _create_default_selection(self) -> None:
        width = max(260, self.screen_w // 4)
        height = max(160, self.screen_h // 4)
        x1 = (self.screen_w - width) // 2
        y1 = (self.screen_h - height) // 2
        x2 = x1 + width
        y2 = y1 + height
        self.selection = (x1, y1, x2, y2)

        self.rect_id = self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            outline="white",
            width=2,
            dash=(4, 4),
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
        x = self._clamp_x(event.x)
        y = self._clamp_y(event.y)
        mode = self._hit_test(x, y)

        self.drag_mode = mode
        self.drag_start = (x, y)

        if self.selection is None:
            self.selection = (x, y, x + self.MIN_SIZE, y + self.MIN_SIZE)
        self.drag_origin = self._normalize_selection(self.selection)

        if mode == "draw":
            self.selection = (x, y, x + self.MIN_SIZE, y + self.MIN_SIZE)
            self.drag_origin = self._normalize_selection(self.selection)

        self._render_selection()

    def _on_canvas_drag(self, event) -> None:
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
        self.drag_mode = None
        self.drag_start = None
        self.drag_origin = None
        if self.canvas is not None:
            self.canvas.configure(cursor="crosshair")

    def _render_selection(self) -> None:
        if self.canvas is None or self.rect_id is None or self.selection is None:
            return

        x1, y1, x2, y2 = self._normalize_selection(self.selection)
        self.selection = (x1, y1, x2, y2)
        self.canvas.coords(self.rect_id, x1, y1, x2, y2)

        width = x2 - x1
        height = y2 - y1
        self.canvas.itemconfig(self.value_text_id, text=f"({x1}, {y1}, {width}, {height})")

    def _confirm_selection(self, _event) -> None:
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

    def _cancel_selection(self, _event) -> None:
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
        self.selection = None
        self.drag_mode = None
        self.drag_start = None
        self.drag_origin = None
        self.dash_offset = 0
        self.root.focus_force()

    def copy_region(self) -> None:
        if self.region is None:
            self.status_var.set("No region recorded. Press Enter and select first.")
            return

        value = f"({self.region[0]}, {self.region[1]}, {self.region[2]}, {self.region[3]})"
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.root.update()
        self.status_var.set(f"Copied to clipboard: {value}")


def main() -> None:
    root = tk.Tk()
    RegionPickerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
