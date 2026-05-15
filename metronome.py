import tkinter as tk
from tkinter import ttk
import threading
import time
import math
import struct
import wave
import io
import random

# 引入 pygame，Win11下 winsound 非常不稳定且会被系统抑制
try:
    import pygame
except ImportError:
    import tkinter.messagebox as messagebox
    tk.Tk().withdraw()
    messagebox.showerror("缺少依赖", "请先在终端运行安装 pygame：\npip install pygame\n\nWin11 系统强制拦截普通提示音，必须使用 pygame 执行底层发声通道。")
    exit()

def generate_click_pygame(
    freq=1800,
    duration=0.045,
    sample_rate=44100,
    volume=0.85,
    noise_amount=0.18,
):
    """
    生成清脆短促的节拍声，直接转为 pygame 的 Sound 对象。
    """
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        num_samples = int(sample_rate * duration)

        for i in range(num_samples):
            t = i / sample_rate

            # 极短的起音 + 更快的指数衰减，形成工程塑料特有的干脆且偏闷的声音
            attack = min(1.0, t / 0.0015)
            envelope = attack * math.exp(-140 * t)

            # 在敲击的瞬间加入音高下坠 (Pitch Drop)，这是合成“木质/塑料”打击乐的核心技巧
            pitch_drop = math.exp(-300 * t)
            current_freq = freq * (1.0 + 0.35 * pitch_drop)

            # 主频 + 非整数倍泛音 (Inharmonic Overtone)，消除金属钟声般的清脆感，增加塑料厚实感
            tone = (
                0.78 * math.sin(2 * math.pi * current_freq * t)
                + 0.22 * math.sin(2 * math.pi * current_freq * 1.55 * t)
            )

            # 极短噪声，模拟塑料部件撞击刹那的物理摩擦
            noise_env = math.exp(-350 * t)
            noise = random.uniform(-1, 1) * noise_amount * noise_env

            audio = (tone * envelope + noise) * volume

            # 防止削波爆音
            audio = max(-1.0, min(1.0, audio))
            sample = int(audio * 32767)

            wav.writeframes(struct.pack("<h", sample))

    buffer.seek(0)
    return pygame.mixer.Sound(buffer)


class MetronomeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("尤克里里节拍器")
        self.root.geometry("400x550")
        self.root.configure(bg="#F5F5F7")
        self.root.resizable(False, False)
        
        # 初始化 Pygame 混音器，设置小 buffer 获取极低无缝延迟
        pygame.mixer.pre_init(44100, -16, 1, 256)
        pygame.mixer.init()

        # 生成 Pygame 专用的内存音频对象 (调整至市面常见的塑料电子节拍器质感)
        self.sound_high = generate_click_pygame(
            freq=1200,          # 降低原有的高音刺耳感
            duration=0.035,     # 缩短发声时间，更加干脆不拖泥带水
            volume=0.90,
            noise_amount=0.25,  # 稍微强调一下打击的“喀”声
        )
        self.sound_low = generate_click_pygame(
            freq=800,           # 浑厚的低音笃声
            duration=0.035,
            volume=0.85,
            noise_amount=0.15,
        )

        # Tkinter 变量只在主线程使用
        self.bpm_var = tk.IntVar(value=80)
        self.beats_per_measure_var = tk.IntVar(value=4)

        # 后台线程只读这些普通变量
        self.bpm_value = 80
        self.beats_per_measure_value = 4

        self.current_beat = 0
        self.is_playing = False
        self.thread = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()

        self.lights = []

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TScale", background="#F5F5F7")
        style.configure("TButton", font=("Microsoft YaHei", 12), padding=5)

        display_frame = tk.Frame(self.root, bg="#F5F5F7")
        display_frame.pack(pady=30)

        self.bpm_label = tk.Label(
            display_frame,
            textvariable=self.bpm_var,
            font=("Helvetica", 64, "bold"),
            bg="#F5F5F7",
            fg="#1D1D1F",
        )
        self.bpm_label.pack()

        tk.Label(
            display_frame,
            text="BPM",
            font=("Helvetica", 14),
            bg="#F5F5F7",
            fg="#86868B",
        ).pack()

        self.light_frame = tk.Frame(self.root, bg="#F5F5F7")
        self.light_frame.pack(pady=10)
        self.create_lights()

        control_frame = tk.Frame(self.root, bg="#F5F5F7")
        control_frame.pack(pady=20, fill="x", padx=40)

        self.slider = ttk.Scale(
            control_frame,
            from_=40,
            to=180,
            orient="horizontal",
            variable=self.bpm_var,
            command=self.on_slider_change,
        )
        self.slider.pack(fill="x")

        quick_frame = tk.Frame(self.root, bg="#F5F5F7")
        quick_frame.pack(pady=10)

        speeds = [50, 60, 70, 80, 90, 100, 110, 120]
        for i, speed in enumerate(speeds):
            btn = tk.Button(
                quick_frame,
                text=str(speed),
                font=("Microsoft YaHei", 10),
                width=4,
                bg="#FFFFFF",
                fg="#1D1D1F",
                relief="flat",
                borderwidth=1,
                command=lambda s=speed: self.set_bpm(s),
            )
            btn.grid(row=i // 4, column=i % 4, padx=5, pady=5)

        beat_frame = tk.Frame(self.root, bg="#F5F5F7")
        beat_frame.pack(pady=15)

        tk.Label(
            beat_frame,
            text="节拍:",
            font=("Microsoft YaHei", 12),
            bg="#F5F5F7",
        ).pack(side="left", padx=5)

        beats_options = [("2/4", 2), ("3/4", 3), ("4/4", 4), ("6/8", 6)]

        for text, val in beats_options:
            tk.Radiobutton(
                beat_frame,
                text=text,
                variable=self.beats_per_measure_var,
                value=val,
                font=("Microsoft YaHei", 11),
                bg="#F5F5F7",
                command=self.on_beats_change,
            ).pack(side="left", padx=5)

        self.play_btn = tk.Button(
            self.root,
            text="▶ 启 动 (空格)",
            font=("Microsoft YaHei", 16, "bold"),
            bg="#007AFF",
            fg="white",
            activebackground="#0056b3",
            activeforeground="white",
            relief="flat",
            width=15,
            command=self.toggle_play,
        )
        self.play_btn.pack(pady=20)

        hint = tk.Label(
            self.root,
            text="Win11 稳定版：Pygame 底层混音 | 按空格键快捷启停",
            font=("Microsoft YaHei", 9),
            bg="#F5F5F7",
            fg="#86868B",
        )
        hint.pack(pady=5)
        
        # 绑定空格键到启动/停止切换
        self.root.bind("<space>", self.toggle_play)

    def create_lights(self):
        for widget in self.light_frame.winfo_children():
            widget.destroy()

        self.lights = []

        beats = self.beats_per_measure_var.get()

        for _ in range(beats):
            light = tk.Canvas(
                self.light_frame,
                width=20,
                height=20,
                bg="#F5F5F7",
                highlightthickness=0,
            )
            light.create_oval(
                2,
                2,
                18,
                18,
                fill="#E5E5EA",
                outline="",
                tags="bulb",
            )
            light.pack(side="left", padx=6)
            self.lights.append(light)

    def on_slider_change(self, event=None):
        bpm = int(float(self.bpm_var.get()))
        bpm = max(40, min(180, bpm))

        self.bpm_var.set(bpm)

        with self.lock:
            self.bpm_value = bpm

    def set_bpm(self, val):
        self.bpm_var.set(val)

        with self.lock:
            self.bpm_value = val

    def on_beats_change(self):
        beats = self.beats_per_measure_var.get()

        with self.lock:
            self.beats_per_measure_value = beats
            self.current_beat = 0

        self.create_lights()
        self.reset_lights()

    def toggle_play(self, event=None):
        if self.is_playing:
            self.stop()
        else:
            self.play()

    def play(self):
        if self.is_playing:
            return

        with self.lock:
            self.bpm_value = int(self.bpm_var.get())
            self.beats_per_measure_value = int(self.beats_per_measure_var.get())
            self.current_beat = 0

        self.is_playing = True
        self.stop_event.clear()

        self.play_btn.config(
            text="■ 停 止 (空格)",
            bg="#FF3B30",
            activebackground="#cc2e26",
        )

        self.thread = threading.Thread(target=self.tick_loop, daemon=True)
        self.thread.start()

    def stop(self):
        if not self.is_playing:
            return

        self.is_playing = False
        self.stop_event.set()

        self.play_btn.config(
            text="▶ 启 动 (空格)",
            bg="#007AFF",
            activebackground="#0056b3",
        )

        self.reset_lights()

    def reset_lights(self):
        for light in self.lights:
            light.itemconfig("bulb", fill="#E5E5EA")

    def update_light(self, beat_idx):
        if not self.lights:
            return

        if beat_idx >= len(self.lights):
            return

        self.reset_lights()

        # 重拍红色，弱拍蓝色
        color = "#FF3B30" if beat_idx == 0 else "#007AFF"
        self.lights[beat_idx].itemconfig("bulb", fill=color)

    def play_click(self, beat_idx):
        sound = self.sound_high if beat_idx == 0 else self.sound_low

        try:
            # 关键改动：使用 Pygame 无限制混音播放音频
            sound.play()
        except Exception:
            pass

    def tick_loop(self):
        next_tick = time.perf_counter()

        while not self.stop_event.is_set():
            with self.lock:
                bpm = max(1, int(self.bpm_value))
                beats_per_measure = max(1, int(self.beats_per_measure_value))
                beat_idx = self.current_beat
                self.current_beat = (self.current_beat + 1) % beats_per_measure

            interval = 60.0 / bpm

            # UI 更新必须回到主线程
            self.root.after(0, self.update_light, beat_idx)

            # 播放极短 click。同步播放 40ms 左右，不会影响正常 BPM。
            self.play_click(beat_idx)

            next_tick += interval

            sleep_time = next_tick - time.perf_counter()

            # 如果系统卡顿导致落后太多，直接重新校准，避免越跑越乱
            if sleep_time < -interval:
                next_tick = time.perf_counter()
                sleep_time = 0

            if sleep_time > 0:
                self.stop_event.wait(sleep_time)

    def on_close(self):
        self.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = MetronomeApp(root)
    root.mainloop()