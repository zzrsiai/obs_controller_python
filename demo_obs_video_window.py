"""
OBS 画面预览窗口演示
使用定时截图方式在 tkinter 窗口中显示 OBS 预览和输出画面

依赖:
    pip install obsws-python Pillow opencv-python

工作原理:
    OBS WebSocket 的 GetSourceScreenshot 接口可以抓取任意源或场景的单帧画面，
    通过定时器周期性截图（建议 15-30fps），即可在 tkinter 中模拟"实时"预览。

    注意：这是基于定时截图的伪实时，延迟约 1-2 帧，适合监控/预览场景，
    不适合对实时性要求极高的场景（如游戏直播监控）。

如果需要真正的高帧率视频流，推荐方案:
    1. OBS NDI 插件 + python-ndi 接收（延迟 ~1 帧）
    2. OBS 虚拟摄像头 + opencv 读取摄像头（延迟 ~1 帧）
    3. OBS Source 插件 + 自定义渲染插件（零延迟）
"""

import obs_controller
import tkinter as tk
from tkinter import ttk
import threading
import time
import sys
import traceback
from typing import Optional

# 尝试导入可选依赖
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


# ============================================================================
# 方案 A: 使用 PIL（推荐，最简单）
# ============================================================================

class OBSVideoWindowPIL:
    """
    基于 PIL 的 OBS 视频预览窗口
    适合不需要 OpenCV 处理的场景，内存占用较低
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 4455,
        password: str = "",
        source_name: Optional[str] = None,
        scene_name: Optional[str] = None,
        fps: int = 20,
        width: Optional[int] = None,
        height: Optional[int] = None,
        image_format: str = "jpg",
        compression_quality: int = 80
    ):
        """
        Args:
            host:              OBS WebSocket 主机地址
            port:              OBS WebSocket 端口
            password:           OBS WebSocket 密码
            source_name:        要截取的源名称（优先使用）
            scene_name:         要截取的场景名称（source_name 为 None 时使用）
            fps:               每秒帧数（建议 15-30，太高会增加 OBS 负载）
            width:             窗口宽度（None=自动）
            height:            窗口高度（None=自动）
            image_format:      截图格式（jpg 体积小，png 质量高）
            compression_quality: 截图压缩质量 0-100
        """
        if not HAS_PIL:
            raise ImportError("Pillow 未安装: pip install Pillow")

        self.fps = fps
        self.frame_interval = 1.0 / fps
        self.source_name = source_name
        self.scene_name = scene_name
        self.image_format = image_format
        self.compression_quality = compression_quality

        # 目标源：优先 source_name，其次 scene_name
        self.capture_target = source_name if source_name else scene_name
        if not self.capture_target:
            self.capture_target = None  # 会自动选择第一个源

        # 创建 OBS 控制器
        self.obs = obs_controller.OBSController(
            host=host,
            port=port,
            password=password
        )

        # Tkinter 窗口
        self.root = tk.Tk()
        self.root.title(f"OBS 预览 - {self.capture_target or '自动选择'}")
        self.root.configure(bg="#1e1e1e")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 视频显示 Label
        self.video_label = tk.Label(
            self.root,
            bg="#1e1e1e",
            text="正在连接 OBS...",
            fg="#888",
            font=("微软雅黑", 12)
        )
        self.video_label.pack(fill=tk.BOTH, expand=True)

        # 控制栏
        control_frame = tk.Frame(self.root, bg="#2d2d2d", height=50)
        control_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = tk.Label(
            control_frame,
            text="状态: 初始化中",
            bg="#2d2d2d",
            fg="#aaa",
            font=("微软雅黑", 9)
        )
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.fps_label = tk.Label(
            control_frame,
            text=f"FPS: {fps}",
            bg="#2d2d2d",
            fg="#aaa",
            font=("微软雅黑", 9)
        )
        self.fps_label.pack(side=tk.RIGHT, padx=10)

        # 截图按钮
        self.screenshot_btn = ttk.Button(
            control_frame,
            text="📷 截图",
            command=self.take_screenshot
        )
        self.screenshot_btn.pack(side=tk.RIGHT, padx=5)

        # 暂停/继续按钮
        self.paused = False
        self.pause_btn = ttk.Button(
            control_frame,
            text="⏸ 暂停",
            command=self.toggle_pause
        )
        self.pause_btn.pack(side=tk.RIGHT, padx=5)

        # 设置窗口大小
        if width and height:
            self.root.geometry(f"{width}x{height}")

        # 运行时状态
        self.running = True
        self.photo: Optional[ImageTk.PhotoImage] = None
        self.last_frame_time = 0
        self.frame_count = 0
        self.start_time = time.time()

    def toggle_pause(self):
        """暂停/继续预览"""
        self.paused = not self.paused
        self.pause_btn.config(text="▶ 继续" if self.paused else "⏸ 暂停")
        self.status_label.config(text="状态: 已暂停" if self.paused else "状态: 播放中")

    def take_screenshot(self):
        """立即截图并保存"""
        try:
            # 使用全分辨率截图
            img = self.obs.screenshot_to_pil(
                source_name=self.source_name,
                image_format="png",
                compression_quality=100
            )
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            path = f"obs_screenshot_{timestamp}.png"
            img.save(path)
            self.status_label.config(text=f"截图已保存: {path}", fg="#4CAF50")
            # 3秒后恢复状态文字
            self.root.after(3000, lambda: self.status_label.config(
                text="状态: 播放中" if not self.paused else "状态: 已暂停",
                fg="#aaa"
            ))
        except Exception as e:
            self.status_label.config(text=f"截图失败: {e}", fg="#f44336")

    def update_frame(self):
        """定时更新画面（每次从 OBS 截图一帧）"""
        if not self.running:
            return

        try:
            if not self.paused:
                # 获取截图
                img = self.obs.screenshot_to_pil(
                    source_name=self.source_name,
                    image_format=self.image_format,
                    compression_quality=self.compression_quality
                )

                # 缩放到 Label 尺寸（如果有）
                label_w = self.video_label.winfo_width()
                label_h = self.video_label.winfo_height()
                if label_w > 1 and label_h > 1:
                    img.thumbnail((label_w, label_h), Image.Resampling.LANCZOS)

                # 转换为 PhotoImage
                self.photo = ImageTk.PhotoImage(img)
                self.video_label.config(image=self.photo, text="", fg="#888")

            # FPS 计算
            self.frame_count += 1
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                current_fps = self.frame_count / elapsed
                self.fps_label.config(text=f"FPS: {current_fps:.1f}")

        except Exception as e:
            self.video_label.config(text=f"连接失败:\n{e}\n\n请确认 OBS 已启动\n且 obs-websocket 插件已启用", fg="#f44336")

        # 安排下一次更新
        self.root.after(int(self.frame_interval * 1000), self.update_frame)

    def run(self):
        """启动窗口主循环（阻塞）"""
        # 窗口渲染完成后开始更新
        self.root.after(100, self.update_frame)
        self.status_label.config(text="状态: 播放中")
        self.root.mainloop()

    def on_close(self):
        """关闭窗口"""
        self.running = False
        try:
            self.obs.close()
        except Exception:
            pass
        self.root.destroy()


# ============================================================================
# 方案 B: 使用 OpenCV（适合需要图像处理的场景，如人脸识别/目标跟踪）
# ============================================================================

class OBSVideoWindowCV2:
    """
    基于 OpenCV 的 OBS 视频预览窗口
    适合需要对画面进行实时图像处理的场景
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 4455,
        password: str = "",
        source_name: Optional[str] = None,
        scene_name: Optional[str] = None,
        fps: int = 20,
        width: int = 640,
        height: int = 360,
        image_format: str = "jpg",
        compression_quality: int = 80
    ):
        if not HAS_CV2:
            raise ImportError("opencv-python 未安装: pip install opencv-python")

        self.fps = fps
        self.frame_interval = 1.0 / fps
        self.source_name = source_name
        self.scene_name = scene_name
        self.image_format = image_format
        self.compression_quality = compression_quality
        self.width = width
        self.height = height

        self.obs = obs_controller.OBSController(
            host=host,
            port=port,
            password=password
        )

        # tkinter 窗口
        self.root = tk.Tk()
        self.root.title(f"OBS 预览 (OpenCV) - {source_name or scene_name or '自动'}")
        self.root.configure(bg="#1e1e1e")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 视频画布（Canvas 支持叠加绘制）
        self.canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            bg="#000",
            highlightthickness=0
        )
        self.canvas.pack()
        self.canvas.bind("<Configure>", self.on_resize)

        # 控制栏
        control_frame = tk.Frame(self.root, bg="#2d2d2d", height=50)
        control_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_label = tk.Label(
            control_frame,
            text="状态: 初始化中",
            bg="#2d2d2d",
            fg="#aaa",
            font=("微软雅黑", 9)
        )
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.fps_label = tk.Label(
            control_frame,
            text=f"FPS: {fps}",
            bg="#2d2d2d",
            fg="#aaa",
            font=("微软雅黑", 9)
        )
        self.fps_label.pack(side=tk.RIGHT, padx=10)

        ttk.Button(control_frame, text="📷 截图", command=self.take_screenshot).pack(side=tk.RIGHT, padx=5)

        self.running = True
        self.paused = False
        self.tk_photo = None
        self.frame_count = 0
        self.start_time = time.time()

    def on_resize(self, event):
        """窗口大小变化时更新画布"""
        self.width = event.width
        self.height = event.height
        self.canvas.config(width=self.width, height=self.height)

    def toggle_pause(self):
        self.paused = not self.paused
        self.status_label.config(text="状态: 已暂停" if self.paused else "状态: 播放中")

    def take_screenshot(self):
        try:
            img = self.obs.screenshot_to_opencv(
                source_name=self.source_name,
                image_format="png"
            )
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            path = f"obs_screenshot_{timestamp}.png"
            cv2.imwrite(path, img)
            self.status_label.config(text=f"截图已保存: {path}", fg="#4CAF50")
            self.root.after(3000, lambda: self.status_label.config(text="状态: 播放中", fg="#aaa"))
        except Exception as e:
            self.status_label.config(text=f"截图失败: {e}", fg="#f44336")

    def update_frame(self):
        if not self.running:
            return

        try:
            if not self.paused:
                # BGR → RGB（OpenCV 截图为 BGR）
                frame = self.obs.screenshot_to_opencv(
                    source_name=self.source_name,
                    image_format=self.image_format,
                    compression_quality=self.compression_quality
                )
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # 缩放适应窗口
                h, w = rgb.shape[:2]
                scale = min(self.width / w, self.height / h)
                new_w = int(w * scale)
                new_h = int(h * scale)
                rgb = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

                # numpy array → PIL Image → PhotoImage
                pil_img = Image.fromarray(rgb)
                self.tk_photo = ImageTk.PhotoImage(pil_img)

                # 居中显示
                x = (self.width - new_w) // 2
                y = (self.height - new_h) // 2
                self.canvas.delete("all")
                self.canvas.create_image(x, y, anchor=tk.NW, image=self.tk_photo)

            self.frame_count += 1
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                self.fps_label.config(text=f"FPS: {self.frame_count / elapsed:.1f}")

        except Exception as e:
            self.canvas.delete("all")
            self.canvas.create_text(
                self.width // 2, self.height // 2,
                text=f"连接失败:\n{e}\n\n请确认 OBS 已启动\n且 obs-websocket 已启用",
                fill="#f44336",
                font=("微软雅黑", 11),
                justify=tk.CENTER
            )

        self.root.after(int(self.frame_interval * 1000), self.update_frame)

    def run(self):
        self.root.after(100, self.update_frame)
        self.status_label.config(text="状态: 播放中")
        self.root.mainloop()

    def on_close(self):
        self.running = False
        try:
            self.obs.close()
        except Exception:
            pass
        self.root.destroy()


# ============================================================================
# 方案 C: 分屏显示（同时预览多个源）
# ============================================================================

class OBSMultiPreviewWindow:
    """同时预览多个 OBS 源/场景的分屏窗口"""

    def __init__(
        self,
        sources: list[dict],
        host: str = "localhost",
        port: int = 4455,
        password: str = "",
        fps: int = 15
    ):
        """
        Args:
            sources: 源列表，每项为 {"name": "源名", "label": "显示名"}
            host/port/password: OBS 连接参数
            fps: 每源每秒帧数
        """
        if not HAS_PIL:
            raise ImportError("Pillow 未安装: pip install Pillow")

        self.fps = fps
        self.frame_interval = 1.0 / fps
        self.sources = sources  # [{"name": str, "label": str}, ...]
        self.n = len(sources)

        self.obs = obs_controller.OBSController(host=host, port=port, password=password)

        # 布局：2列或1列
        cols = 2 if self.n >= 2 else 1
        rows = (self.n + cols - 1) // cols

        self.root = tk.Tk()
        self.root.title(f"OBS 多源预览 - {self.n} 个源")
        self.root.configure(bg="#1e1e1e")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 创建网格标签
        self.labels: list[tk.Label] = []
        self.photos: list[Optional[ImageTk.PhotoImage]] = [None] * self.n

        for i, src in enumerate(sources):
            row, col = i // cols, i % cols
            cell = tk.Frame(self.root, bg="#1e1e1e", padx=2, pady=2)
            cell.grid(row=row, column=col, sticky="nsew")
            self.root.grid_rowconfigure(row, weight=1)
            self.root.grid_columnconfigure(col, weight=1)

            lbl = tk.Label(cell, text=src.get("label", src["name"]), bg="#2d2d2d", fg="#aaa", font=("微软雅黑", 9))
            lbl.pack(fill=tk.X)

            video = tk.Label(cell, bg="#000")
            video.pack(fill=tk.BOTH, expand=True)
            self.labels.append(video)

        for c in range(cols):
            self.root.columnconfigure(c, weight=1)
        for r in range(rows):
            self.root.rowconfigure(r, weight=1)

        self.running = True
        self.frame_count = 0
        self.start_time = time.time()

    def update_frame(self):
        if not self.running:
            return

        for i, src in enumerate(self.sources):
            try:
                img = self.obs.screenshot_to_pil(
                    source_name=src["name"],
                    image_format="jpg",
                    compression_quality=75
                )
                w = self.labels[i].winfo_width()
                h = self.labels[i].winfo_height()
                if w > 1 and h > 1:
                    img.thumbnail((w, h), Image.Resampling.LANCZOS)
                self.photos[i] = ImageTk.PhotoImage(img)
                self.labels[i].config(image=self.photos[i], text="", bg="#000")
            except Exception:
                self.labels[i].config(image="", text="连接失败", bg="#1e1e1e", fg="#f44336")

        self.frame_count += 1
        elapsed = time.time() - self.start_time
        self.root.title(f"OBS 多源预览 ({self.n}源) - FPS: {self.frame_count / elapsed:.1f if elapsed > 0 else 0}")
        self.root.after(int(self.frame_interval * 1000), self.update_frame)

    def run(self):
        self.root.after(200, self.update_frame)
        self.root.mainloop()

    def on_close(self):
        self.running = False
        try:
            self.obs.close()
        except Exception:
            pass
        self.root.destroy()


# ============================================================================
# 入口
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OBS 画面预览窗口")
    parser.add_argument("--host", default="localhost", help="OBS WebSocket 主机")
    parser.add_argument("--port", type=int, default=4455, help="OBS WebSocket 端口")
    parser.add_argument("--password", default="", help="OBS WebSocket 密码")
    parser.add_argument("--source", default=None, help="要预览的源名称（留空则预览当前场景）")
    parser.add_argument("--fps", type=int, default=20, help="每秒帧数（建议15-30）")
    parser.add_argument("--format", default="jpg", choices=["jpg", "png", "webp"], help="截图格式")
    parser.add_argument("--quality", type=int, default=80, help="截图压缩质量 0-100")
    parser.add_argument("--width", type=int, default=800, help="窗口宽度")
    parser.add_argument("--height", type=int, default=450, help="窗口高度")
    parser.add_argument("--mode", default="pil", choices=["pil", "cv2", "multi"], help="渲染模式")
    parser.add_argument("--multi-sources", nargs="+", help="多源模式: 源名称列表（用空格分隔）")

    args = parser.parse_args()

    print(f"=" * 50)
    print(f"OBS 画面预览")
    print(f"  主机: {args.host}:{args.port}")
    print(f"  源: {args.source or '(当前场景)'}")
    print(f"  FPS: {args.fps}")
    print(f"  格式: {args.format} (质量 {args.quality})")
    print(f"  模式: {args.mode}")
    print(f"=" * 50)
    print("提示: OBS Studio 必须正在运行，且 obs-websocket 插件已启用并配置正确。")
    print()

    try:
        if args.mode == "multi" or args.multi_sources:
            sources = [{"name": s, "label": s} for s in (args.multi_sources or [])]
            if not sources:
                print("错误: 多源模式需要通过 --multi-sources 指定至少一个源名称")
                sys.exit(1)
            window = OBSMultiPreviewWindow(
                sources=sources,
                host=args.host,
                port=args.port,
                password=args.password,
                fps=args.fps
            )
        elif args.mode == "cv2":
            if not HAS_CV2:
                print("错误: opencv-python 未安装，请运行: pip install opencv-python")
                sys.exit(1)
            window = OBSVideoWindowCV2(
                host=args.host,
                port=args.port,
                password=args.password,
                source_name=args.source,
                fps=args.fps,
                width=args.width,
                height=args.height,
                image_format=args.format,
                compression_quality=args.quality
            )
        else:
            window = OBSVideoWindowPIL(
                host=args.host,
                port=args.port,
                password=args.password,
                source_name=args.source,
                fps=args.fps,
                width=args.width,
                height=args.height,
                image_format=args.format,
                compression_quality=args.quality
            )
        window.run()
    except KeyboardInterrupt:
        print("\n已退出。")
    except Exception as e:
        print(f"\n错误: {e}")
        traceback.print_exc()
