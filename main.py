"""Stellar Spectrum — a realtime star-orbit visualizer for PC audio.

Usage:
    python main.py                # capture the default speaker (WASAPI loopback)
    python main.py --demo         # built-in synth loop, no audio hardware needed
    python main.py --list-devices
"""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from stellar.analysis import AnalysisFrame, SpectrumAnalyzer
from stellar.audio import AudioSource, AudioStream, DemoSource, default_source, list_sources
from stellar.galaxy import GalaxyRenderer as Renderer
from stellar.hud import Hud
from stellar.orbit import OrbitRenderer
from stellar.spectrum import SpectrumRenderer
from stellar.themes import THEMES, THEME_BY_KEY, Theme
from stellar.wave import WaveRenderer

APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
SHOT_DIR = APP_DIR / "screenshots"
TITLE = "星轨频谱 · Stellar Spectrum"

PRESET_CLASSES = {
    "galaxy": Renderer,
    "orbit": OrbitRenderer,
    "wave": WaveRenderer,
    "spectrum": SpectrumRenderer,
}
PRESET_LABELS = {
    "galaxy": "3D GALAXY",
    "orbit": "STAR ORBIT",
    "wave": "AURORA WAVE",
    "spectrum": "CLASSIC SPECTRUM",
}
PRESET_NAMES = {
    "galaxy": "3D 星系",
    "orbit": "星际轨道",
    "wave": "极光波形",
    "spectrum": "经典频谱",
}
PRESET_ORDER = ["galaxy", "orbit", "wave", "spectrum"]


def install_error_log() -> None:
    def hook(exc_type, exc, tb):
        try:
            text = "".join(traceback.format_exception(exc_type, exc, tb))
            (APP_DIR / "error.log").write_text(text, encoding="utf-8")
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = hook


def enable_dpi_awareness() -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def load_config() -> dict:
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def save_config(data: dict) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def parse_size(text: str) -> Tuple[int, int]:
    try:
        w, h = text.lower().replace("×", "x").split("x")
        return max(640, int(w)), max(480, int(h))
    except Exception:
        return 1600, 900


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="星轨频谱 — 实时系统声音可视化")
    p.add_argument("--demo", action="store_true", help="使用内置合成音乐演示，不采集系统声音")
    p.add_argument("--list-devices", action="store_true", help="列出可用的声音来源后退出")
    p.add_argument("--device", type=int, default=None, help="声音来源编号（1 开始，见 --list-devices）")
    p.add_argument("--device-name", type=str, default=None, help="按名称片段选择声音来源")
    p.add_argument("--mic", action="store_true", help="直接使用第一个麦克风，而不是系统声音")
    p.add_argument("--fullscreen", action="store_true", help="全屏启动")
    p.add_argument("--size", type=str, default="1600x900", help="窗口尺寸，例如 1600x900")
    p.add_argument("--fps", type=int, default=60, help="目标帧率")
    p.add_argument("--theme", type=str, choices=[t.key for t in THEMES], default=None)
    p.add_argument("--preset", type=str, choices=PRESET_ORDER, default=None, help="视觉预设：galaxy / wave / spectrum")
    p.add_argument("--sensitivity", type=float, default=None, help="频谱灵敏度 0.5 - 2.0")
    p.add_argument("--screenshot", type=str, default=None, help="离屏渲染并保存一张截图后退出")
    p.add_argument("--frames", type=int, default=360, help="截图模式渲染帧数")
    p.add_argument("--no-hud", action="store_true", help="隐藏界面文字")
    p.add_argument("--probe-audio", action="store_true", help=argparse.SUPPRESS)
    return p.parse_args(argv)


def select_source(args, config: dict) -> Tuple[List[AudioSource], Optional[int]]:
    sources = list_sources()
    if not sources:
        return sources, None
    if args.device is not None:
        idx = args.device - 1
        if 0 <= idx < len(sources):
            return sources, idx
    if args.device_name:
        needle = args.device_name.lower()
        for i, src in enumerate(sources):
            if needle in src.name.lower():
                return sources, i
    if args.mic:
        for i, src in enumerate(sources):
            if src.kind == "mic":
                return sources, i
    saved = config.get("device_id")
    if saved:
        for i, src in enumerate(sources):
            if src.source_id == saved:
                return sources, i
    preferred = default_source(sources)
    if preferred is not None:
        for i, src in enumerate(sources):
            if src.source_id == preferred.source_id:
                return sources, i
    return sources, 0


class App:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.config = load_config()
        enable_dpi_awareness()
        pygame.init()
        pygame.display.set_caption(TITLE)

        self.windowed_size = parse_size(args.size)
        self.fullscreen = bool(args.fullscreen or self.config.get("fullscreen", False))
        self.screen = self._set_display(self.fullscreen)
        self.size = self.screen.get_size()

        theme_key = args.theme or self.config.get("theme", "nebula")
        self.theme = THEME_BY_KEY.get(theme_key, THEMES[0])
        preset_key = args.preset or self.config.get("preset", "galaxy")
        self.preset = preset_key if preset_key in PRESET_CLASSES else "galaxy"
        self.renderer = PRESET_CLASSES[self.preset](self.size, self.theme)
        self.renderer.set_target(self.screen)
        self.hud = Hud(self.size, self.theme)
        self.hud.preset_label = PRESET_LABELS[self.preset]
        self.show_hud = not args.no_hud

        self.sensitivity = float(
            args.sensitivity
            if args.sensitivity is not None
            else self.config.get("sensitivity", 1.0)
        )
        self.sensitivity = max(0.5, min(2.0, self.sensitivity))
        self.analyzer = SpectrumAnalyzer(48000)
        self.analyzer.sensitivity = self.sensitivity

        self.clock = pygame.time.Clock()
        self.fps_target = max(30, min(144, args.fps))
        self.now = 0.0
        self.elapsed = 0.0
        self.paused = False
        self.pause_surface: Optional[pygame.Surface] = None
        self.quit = False

        self.sources: List[AudioSource] = []
        self.current_source = -1
        self.stream: Optional[AudioStream] = None
        self.error: Optional[str] = None
        self.demo: Optional[DemoSource] = None
        self.demo_hist = np.zeros(4096, dtype=np.float32)

        if args.demo:
            self.demo = DemoSource()
            self.analyzer = SpectrumAnalyzer(self.demo.samplerate)
            self.analyzer.sensitivity = self.sensitivity
            self.hud.toast("演示模式 · 内置合成音乐", self.now)
        else:
            self.sources, index = select_source(args, self.config)
            if index is not None:
                self.open_source(index, announce=False)
            else:
                self.error = "未找到可用音频设备 · 按 D 重新扫描"
            if self.error:
                self.hud.open_menu(self.sources, max(0, self.current_source))

        self.hud.toast(
            "系统声音已连接 · 按 ? 查看快捷键" if not self.error else "未连接声音来源 · 按 D 选择",
            self.now,
        )

    # -- display -----------------------------------------------------------
    def _set_display(self, fullscreen: bool) -> pygame.Surface:
        if fullscreen:
            try:
                info = pygame.display.Info()
                size = (info.current_w, info.current_h)
            except Exception:
                size = self.windowed_size
            return pygame.display.set_mode(size, pygame.FULLSCREEN)
        w, h = self.windowed_size
        try:
            dw, dh = pygame.display.get_desktop_sizes()[0]
            if dw > 0:
                w = min(w, max(800, dw - 80))
            if dh > 0:
                h = min(h, max(600, dh - 100))
        except Exception:
            pass
        return pygame.display.set_mode((w, h), pygame.RESIZABLE)

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        if not self.fullscreen:
            self.screen = self._set_display(False)
        else:
            self.screen = self._set_display(True)
        self.size = self.screen.get_size()
        self.renderer.set_target(self.screen)
        self.renderer.resize(self.size)
        self.hud.resize(self.size)
        self.hud.toast("全屏模式" if self.fullscreen else "窗口模式", self.now)

    # -- audio -------------------------------------------------------------
    def open_source(self, index: int, announce: bool = True) -> bool:
        if not (0 <= index < len(self.sources)):
            return False
        if (
            index == self.current_source
            and self.stream is not None
            and self.stream.running
            and self.error is None
        ):
            return True
        source = self.sources[index]
        new_stream = AudioStream(source)
        ok = new_stream.start()
        if not ok:
            self.error = new_stream.error or "无法打开音频源"
            self.hud.toast(self.error, self.now)
            return False
        old_stream = self.stream
        self.stream = new_stream
        if old_stream is not None:
            old_stream.close()
        self.current_source = index
        self.error = None
        self.analyzer = SpectrumAnalyzer(new_stream.samplerate)
        self.analyzer.sensitivity = self.sensitivity
        self.demo_hist = np.zeros(4096, dtype=np.float32)
        if announce:
            self.hud.toast(f"声音来源：{source.display()}", self.now)
        self.config["device_id"] = source.source_id
        save_config(self.config)
        return True

    def _source_label(self) -> str:
        if self.demo is not None:
            return "内置合成音乐 · DEMO LOOP"
        if 0 <= self.current_source < len(self.sources):
            return self.sources[self.current_source].display()
        return "未选择声音来源"

    def _read_samples(self, dt: float) -> np.ndarray:
        dt = max(1.0 / 240.0, min(0.05, dt))
        if self.demo is not None:
            n = max(1, int(self.demo.samplerate * dt))
            chunk = self.demo.read(n)
            mono = chunk.mean(axis=1)
            self.demo_hist = np.concatenate((self.demo_hist, mono))[-4096:]
            return self.demo_hist
        if self.stream is not None and self.stream.running:
            return self.stream.read(4096)
        return np.zeros(4096, dtype=np.float32)

    # -- actions -----------------------------------------------------------
    def set_theme(self, theme: Theme) -> None:
        if theme.key == self.theme.key:
            return
        self.theme = theme
        self.renderer.set_theme(theme)
        self.renderer.set_target(self.screen)
        self.hud.set_theme(theme)
        self.hud.toast(f"主题：{theme.name} · {theme.english}", self.now)
        self.config["theme"] = theme.key
        save_config(self.config)

    def set_preset(self, key: str, announce: bool = True) -> None:
        if key not in PRESET_CLASSES or key == self.preset:
            return
        self.preset = key
        self.renderer = PRESET_CLASSES[key](self.size, self.theme)
        self.renderer.set_target(self.screen)
        self.renderer.resize(self.size)
        self.hud.preset_label = PRESET_LABELS[key]
        if announce:
            self.hud.toast(f"预设：{PRESET_NAMES[key]}  ·  按 P 切换", self.now)
        self.config["preset"] = key
        save_config(self.config)

    def cycle_preset(self, direction: int = 1) -> None:
        idx = PRESET_ORDER.index(self.preset)
        self.set_preset(PRESET_ORDER[(idx + direction) % len(PRESET_ORDER)])

    def take_screenshot(self) -> None:
        SHOT_DIR.mkdir(parents=True, exist_ok=True)
        name = time.strftime("stellar_%Y%m%d_%H%M%S.png")
        path = SHOT_DIR / name
        try:
            pygame.image.save(self.screen, str(path))
            self.hud.toast(f"截图已保存：screenshots/{name}", self.now)
        except Exception as exc:
            self.hud.toast(f"截图失败：{exc}", self.now)

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        if self.paused:
            self.pause_surface = self.screen.copy()
        else:
            self.pause_surface = None

    def toggle_menu(self) -> None:
        if self.hud.menu_open:
            self.hud.close_menu()
            return
        if self.demo is not None:
            self.hud.toast("当前是演示模式 · 关闭后用 启动.bat 捕获系统声音", self.now)
            return
        self.renderer.end_drag()
        self.sources = list_sources()
        current = max(0, self.current_source)
        self.hud.open_menu(self.sources, current)
        self.hud.help_open = False

    def refresh_sources(self) -> None:
        self.sources = list_sources()
        current = max(0, self.current_source)
        self.hud.open_menu(self.sources, current)
        self.hud.toast("声音来源已刷新", self.now)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.quit = True
            return
        if event.type == pygame.VIDEORESIZE and not self.fullscreen:
            w, h = max(640, event.w), max(480, event.h)
            self.windowed_size = (w, h)
            self.screen = pygame.display.set_mode((w, h), pygame.RESIZABLE)
            self.size = (w, h)
            self.renderer.set_target(self.screen)
            self.renderer.resize(self.size)
            self.hud.resize(self.size)
            self.paused = False
            self.pause_surface = None
            return
        if event.type == pygame.KEYDOWN:
            key = event.key
            if key == pygame.K_ESCAPE:
                if self.hud.menu_open:
                    self.hud.close_menu()
                elif self.hud.help_open:
                    self.hud.help_open = False
                else:
                    self.quit = True
                return
            if key == pygame.K_F11:
                self.toggle_fullscreen()
                return
            if self.hud.menu_open:
                if key in (pygame.K_UP, pygame.K_w):
                    self.hud.move_menu(-1)
                elif key in (pygame.K_DOWN, pygame.K_s):
                    self.hud.move_menu(1)
                elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    idx = self.hud.selected
                    if self.sources:
                        if self.open_source(idx):
                            self.hud.close_menu()
                elif key == pygame.K_r:
                    self.refresh_sources()
                elif key == pygame.K_d:
                    self.hud.close_menu()
                return
            if key == pygame.K_d:
                self.toggle_menu()
            elif key == pygame.K_h:
                self.show_hud = not self.show_hud
                if self.show_hud:
                    self.hud.toast("界面已显示", self.now)
            elif key in (pygame.K_QUESTION, pygame.K_SLASH):
                self.hud.help_open = not self.hud.help_open
            elif key == pygame.K_F1:
                self.hud.help_open = not self.hud.help_open
            elif key == pygame.K_v:
                self.renderer.reset_view()
                self.hud.toast("视角已重置", self.now)
            elif key == pygame.K_s:
                self.take_screenshot()
            elif key == pygame.K_SPACE:
                self.toggle_pause()
            elif pygame.K_1 <= key <= pygame.K_4:
                self.set_theme(THEMES[key - pygame.K_1])
            elif key == pygame.K_t:
                idx = THEMES.index(self.theme)
                self.set_theme(THEMES[(idx + 1) % len(THEMES)])
            elif key == pygame.K_p:
                self.cycle_preset(-1 if event.mod & pygame.KMOD_SHIFT else 1)
            elif key == pygame.K_LEFTBRACKET:
                self.sensitivity = max(0.5, self.sensitivity - 0.1)
                self.analyzer.sensitivity = self.sensitivity
                self.hud.toast(f"频谱灵敏度 {self.sensitivity:.1f}", self.now)
                self.config["sensitivity"] = self.sensitivity
                save_config(self.config)
            elif key == pygame.K_RIGHTBRACKET:
                self.sensitivity = min(2.0, self.sensitivity + 0.1)
                self.analyzer.sensitivity = self.sensitivity
                self.hud.toast(f"频谱灵敏度 {self.sensitivity:.1f}", self.now)
                self.config["sensitivity"] = self.sensitivity
                save_config(self.config)
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.hud.menu_open:
                if event.button == 1:
                    idx = self.hud.menu_hit(event.pos)
                    if idx is not None:
                        self.hud.selected = idx
                        if self.open_source(idx):
                            self.hud.close_menu()
                elif event.button == 4:
                    self.hud.move_menu(-1)
                elif event.button == 5:
                    self.hud.move_menu(1)
                return
            if event.button == 1:
                if getattr(event, "clicks", 1) >= 2:
                    self.renderer.reset_view()
                    self.hud.toast("视角已重置", self.now)
                else:
                    self.renderer.start_drag(event.pos)
            elif event.button == 4:
                self.renderer.zoom(1.0)
            elif event.button == 5:
                self.renderer.zoom(-1.0)
            return
        if event.type == pygame.MOUSEWHEEL and not self.hud.menu_open:
            self.renderer.zoom(float(event.y))
            return
        if event.type == pygame.MOUSEMOTION:
            if self.renderer.dragging and not self.hud.menu_open:
                self.renderer.drag(event.rel)
            return
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.renderer.end_drag()
            return

    # -- main loop ---------------------------------------------------------
    def run(self) -> None:
        while not self.quit:
            dt = self.clock.tick(self.fps_target) / 1000.0
            dt = max(0.001, min(0.06, dt))
            self.now += dt
            self.elapsed += dt
            for event in pygame.event.get():
                self.handle_event(event)
            if self.quit:
                break

            if self.stream is not None and self.stream.error and self.error != self.stream.error:
                self.error = self.stream.error
                self.hud.toast(self.error, self.now)
                self.hud.open_menu(self.sources, max(0, self.current_source))

            samples = self._read_samples(dt)
            frame = self.analyzer.update(samples, dt)
            if not self.paused:
                self.renderer.draw(frame, dt)

            if self.show_hud or self.hud.menu_open or self.hud.help_open:
                self.hud.draw(
                    self.screen,
                    frame,
                    self._source_label(),
                    self.clock.get_fps() or self.fps_target,
                    self.sensitivity,
                    self.now,
                    demo=self.demo is not None,
                    error=self.error,
                    connected=self.demo is not None or (self.stream is not None and self.stream.running),
                    elapsed=self.elapsed,
                )
            if self.paused:
                if self.pause_surface is None:
                    self.pause_surface = self.screen.copy()
                self.screen.blit(self.pause_surface, (0, 0))
                self._draw_pause_badge()
            pygame.display.flip()

        if self.stream is not None:
            self.stream.close()
        self.config["fullscreen"] = self.fullscreen
        self.config["theme"] = self.theme.key
        self.config["preset"] = self.preset
        self.config["sensitivity"] = self.sensitivity
        save_config(self.config)
        pygame.quit()

    def _draw_pause_badge(self) -> None:
        w, h = self.size
        u = self.hud.u
        font = self.hud.font("cjk", int(12 * u), bold=True)
        img = font.render("已暂停  ·  Space 继续", True, (235, 242, 255))
        padding_x, padding_y = int(18 * u), int(9 * u)
        box = pygame.Surface((img.get_width() + padding_x * 2, img.get_height() + padding_y * 2), pygame.SRCALPHA)
        pygame.draw.rect(box, (6, 8, 18, 190), box.get_rect(), border_radius=int(9 * u))
        pygame.draw.rect(box, (*self.theme.primary, 120), box.get_rect(), width=1, border_radius=int(9 * u))
        box.blit(img, (padding_x, padding_y))
        self.screen.blit(box, box.get_rect(midtop=(w // 2, int(120 * u))))


def run_screenshot(args: argparse.Namespace) -> int:
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    size = parse_size(args.size)
    screen = pygame.display.set_mode(size)
    theme = THEME_BY_KEY.get(args.theme or "nebula", THEMES[0])
    preset = args.preset or load_config().get("preset", "galaxy")
    if preset not in PRESET_CLASSES:
        preset = "galaxy"
    renderer = PRESET_CLASSES[preset](size, theme)
    renderer.set_target(screen)
    hud = Hud(size, theme)
    hud.preset_label = PRESET_LABELS[preset]
    demo = DemoSource()
    analyzer = SpectrumAnalyzer(demo.samplerate)
    analyzer.sensitivity = args.sensitivity if args.sensitivity is not None else 1.0
    hist = np.zeros(4096, dtype=np.float32)
    fps = 60.0
    dt = 1.0 / fps
    now = 0.0
    last_frame = None
    frames = max(30, args.frames)
    for i in range(frames):
        chunk = demo.read(int(demo.samplerate * dt))
        hist = np.concatenate((hist, chunk.mean(axis=1)))[-4096:]
        frame = analyzer.update(hist, dt)
        now += dt
        renderer.draw(frame, dt)
        if not args.no_hud:
            hud.draw(
                screen,
                frame,
                "内置合成音乐 · DEMO LOOP",
                fps,
                analyzer.sensitivity,
                now,
                demo=True,
                error=None,
                connected=True,
                elapsed=now,
            )
        last_frame = frame
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(args.screenshot)
    if not path.is_absolute():
        path = APP_DIR / path
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(screen, str(path))
    print(f"saved {path} (beat_pulse={last_frame.beat_pulse:.2f}, level={last_frame.level:.2f})")
    pygame.quit()
    return 0


def run_audio_probe(args: argparse.Namespace) -> int:
    """Diagnostic used to verify capture inside a packaged build."""
    config = load_config()
    sources, index = select_source(args, config)
    if index is None:
        text = "no audio source found"
    else:
        source = sources[index]
        stream = AudioStream(source)
        if not stream.start():
            text = f"source: {source.display()}\nerror: {stream.error}"
        else:
            time.sleep(1.2)
            data = stream.read(stream.samplerate)
            rms = float(np.sqrt(np.mean(data * data)))
            peak = float(np.max(np.abs(data)))
            stream.close()
            text = (
                f"source: {source.display()}\n"
                f"samplerate: {stream.samplerate}\n"
                f"rms: {rms:.6f}\npeak: {peak:.6f}\n"
            )
    path = APP_DIR / "audio_probe.txt"
    path.write_text(text, encoding="utf-8")
    print(text)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    install_error_log()
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if args.list_devices:
        sources = list_sources()
        if not sources:
            print("未找到音频设备。请确认 soundcard 已安装并且 Windows 音频服务正在运行。")
            return 1
        for i, src in enumerate(sources, 1):
            print(f"{i:2d}. [{src.kind.upper():6s}] {src.name}")
        return 0
    if args.screenshot:
        return run_screenshot(args)
    if args.probe_audio:
        return run_audio_probe(args)
    app = App(args)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
