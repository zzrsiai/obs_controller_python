# OBS Controller — Python 封装库说明文档

> 通过 WebSocket 协议远程控制 OBS Studio 的 Python 封装库，基于 `obsws-python`，支持 OBS Studio WebSocket v5.0（OBS 28+）。

---

## 目录

- [快速开始](#快速开始)
- [系统要求](#系统要求)
- [安装依赖](#安装依赖)
- [OBSController 控制器](#obscontroller-控制器)
  - [初始化与连接](#初始化与连接)
  - [通用操作](#通用操作)
  - [场景管理](#场景管理)
  - [输入源管理](#输入源管理)
  - [场景项管理](#场景项管理)
  - [场景项变换](#场景项变换)
  - [滤镜管理](#滤镜管理)
  - [滤镜预设](#滤镜预设)
  - [录制控制](#录制控制)
  - [推流控制](#推流控制)
  - [虚拟摄像头](#虚拟摄像头)
  - [转场控制](#转场控制)
  - [媒体源控制](#媒体源控制)
  - [输入源设置](#输入源设置)
  - [热键控制](#热键控制)
  - [输入源增删改](#输入源增删改)
  - [音频控制](#音频控制)
  - [音频监听与平衡](#音频监听与平衡)
  - [转场精细控制](#转场精细控制)
  - [场景转场覆盖](#场景转场覆盖)
  - [分组与演播室模式](#分组与演播室模式)
  - [回放缓冲](#回放缓冲)
  - [批量请求](#批量请求)
  - [自动重连与心跳](#自动重连与心跳)
  - [状态快照与恢复](#状态快照与恢复)
  - [动画切换与淡入淡出](#动画切换与淡入淡出)
  - [截图与画面捕获](#截图与画面捕获)
  - [事件监听](#事件监听)
- [枚举与数据类](#枚举与数据类)
- [滤镜预设库](#滤镜预设库)
- [异常处理](#异常处理)
- [日志配置](#日志配置)
- [使用示例](#使用示例)
- [demo_obs_video_window 预览窗口](#demo_obs_video_window-预览窗口)
- [注意事项](#注意事项)
- [推荐扩展功能](#推荐扩展功能)

---

## 快速开始

```python
from obs_controller import OBSController

# 创建控制器（支持上下文管理器）
with OBSController(
    host="localhost",
    port=4455,
    password="your_password"
) as obs:
    # 获取当前场景
    scene = obs.get_current_scene()
    print(f"当前场景: {scene}")

    # 切换场景
    obs.set_current_scene("主场景")

    # 获取所有场景
    scenes = obs.get_scene_names()
    print(f"可用场景: {scenes}")

    # 控制音量
    obs.set_input_volume("麦克风", volume_db=-10.0)
    obs.toggle_input_mute("麦克风")
```

---

## 系统要求

| 组件 | 版本要求 |
|------|---------|
| OBS Studio | **28.0.0** 及以上 |
| obs-websocket 插件 | **5.0.0** 及以上（OBS 28 内置；旧版 OBS 需单独安装插件） |
| Python | **3.9** 及以上 |
| obsws-python | 最新版（`pip install obsws-python`）|

### 启用 obs-websocket 插件

1. 启动 OBS Studio
2. 菜单 → 工具 → obs-websocket 设置
3. 勾选「启用 WebSocket 服务器」
4. 复制生成的密码（建议开启）
5. 确认端口（默认 `4455`）

---

## 安装依赖

```bash
pip install obsws-python Pillow opencv-python
```

| 依赖 | 用途 | 是否必需 |
|------|------|---------|
| `obsws-python` | OBS WebSocket 通信 | **必须** |
| `Pillow` | 图片处理、tkinter 显示 | 推荐（截图功能必需） |
| `opencv-python` | OpenCV 图像处理 | 可选（`screenshot_to_opencv` 必需）|

---

## OBSController 控制器

### 初始化与连接

```python
from obs_controller import OBSController

# 基础连接
obs = OBSController(host="localhost", port=4455, password="your_password")

# 自定义超时（秒）
obs = OBSController(host="localhost", port=4455, password="pwd", timeout=10)

# 上下文管理器（推荐，自动关闭连接）
with OBSController(password="pwd") as obs:
    scenes = obs.get_scene_names()
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `host` | str | `"localhost"` | OBS 主机地址 |
| `port` | int | `4455` | WebSocket 端口 |
| `password` | str | `""` | WebSocket 密码 |
| `timeout` | float | `None` | 请求超时秒数 |
| `log` | bool | `False` | 是否启用详细日志 |

---

### 通用操作

#### `get_version() → Dict`
获取 OBS 和插件版本信息，包括支持的图片格式列表。

```python
info = obs.get_version()
print(f"OBS {info['obsWebSocketVersion']} on OBS {info['obsStudioVersion']}")
print(f"支持的图片格式: {info['supportedImageFormats']}")
```

#### `get_stats() → Dict`
获取 OBS 运行时统计信息（CPU、内存、FPS、录制时长等）。

```python
stats = obs.get_stats()
print(f"CPU: {stats['cpuUsage']:.1f}%  内存: {stats['memoryUsage']:.1f}MB  FPS: {stats['activeFps']}")
```

#### `broadcast_event(data: Dict) → bool`
向所有 WebSocket 客户端广播自定义事件。

```python
obs.broadcast_event({"type": "scene_change", "scene": "BRB"})
```

---

### 场景管理

```python
# 获取场景列表
scenes = obs.get_scene_list()        # 返回完整结构
names  = obs.get_scene_names()       # 仅返回名称列表

# 获取当前场景
current = obs.get_current_scene()

# 切换场景
obs.set_current_scene("主场景")

# 创建 / 删除场景
obs.create_scene("临时场景")
obs.remove_scene("临时场景")
```

| 方法 | 返回 | 说明 |
|------|------|------|
| `get_scene_list()` | `Dict` | 完整场景列表含详细信息 |
| `get_scene_names()` | `List[str]` | 仅场景名称 |
| `get_current_scene()` | `str` | 当前场景名 |
| `set_current_scene(name)` | `bool` | 切换到指定场景 |
| `create_scene(name)` | `str` | 新建场景，返回其名称 |
| `remove_scene(name)` | `bool` | 删除场景 |

---

### 输入源管理

```python
# 获取所有输入源
inputs = obs.get_input_list()        # 全部输入
audio  = obs.get_audio_inputs()      # 仅音频输入（麦克风等）

# 获取当前节目输出混音的音频输入（不含监听）
special = obs.get_special_inputs()   # {'mic1': '麦克风', 'desktop1': '桌面音频', ...}
```

#### 音量控制

```python
# 获取音量（返回线性值和 dB 值）
vol = obs.get_input_volume("麦克风")
print(f"音量: {vol['inputVolumeMul']:.2f} ({vol['inputVolumeDb']:.1f} dB)")

# 设置音量（指定 dB 值，更直观）
obs.set_input_volume("麦克风", volume_db=-10.0)

# 设置音量（指定线性值 0.0-1.0）
obs.set_input_volume("麦克风", volume=0.5)

# 静音
obs.set_input_mute("麦克风", muted=True)
obs.toggle_input_mute("麦克风")     # 切换静音状态
```

#### 音视频同步偏移

```python
offset = obs.get_input_audio_sync_offset("麦克风")   # 获取偏移量（毫秒）
obs.set_input_audio_sync_offset("麦克风", offset_ms=50)  # 调整偏移
```

---

### 场景项管理

场景项（Scene Item）= 场景中的一个个元素（源实例），每个有唯一 ID。

```python
# 获取场景中的所有项
items = obs.get_scene_items("主场景")
for item in items:
    print(f"  [{item['sceneItemId']}] {item['sourceName']} 启用={item['sceneItemEnabled']}")

# 按名称查找 scene_item_id
item_id = obs.get_scene_item_id("主场景", "显示器捕获")

# 启用 / 禁用场景项
obs.set_scene_item_enabled("主场景", item_id, False)
obs.set_scene_item_enabled_by_name("主场景", "显示器捕获", False)

# 移动层级
obs.set_scene_item_index("主场景", item_id, new_index=0)

# 复制场景项
new_id = obs.duplicate_scene_item("主场景", "显示器捕获", target_scene="备选场景")

# 删除场景项
obs.remove_scene_item("主场景", item_id)
obs.remove_scene_item_by_name("主场景", "显示器捕获")
```

---

### 场景项变换

```python
# 获取变换信息
transform = obs.get_scene_item_transform("主场景", item_id)
print(transform)
# {'positionX': 0, 'positionY': 0, 'scaleX': 1.0, 'scaleY': 1.0,
#  'rotation': 0, 'cropTop': 0, 'cropBottom': 0, 'cropLeft': 0, 'cropRight': 0,
#  'boundsType': 'OBS_BOUNDS_STRETCH', 'boundsTypeX': 1.0, 'boundsTypeY': 1.0,
#  'alignment': 5, 'height': 1080, 'width': 1920}

# 设置变换（完整参数）
obs.set_scene_item_transform("主场景", item_id,
    position_x=100, position_y=50,
    scale_x=1.5, scale_y=1.5,
    rotation=15.0,
    crop_top=10, crop_bottom=10, crop_left=5, crop_right=5
)

# 单独设置各项
obs.set_scene_item_position("主场景", item_id, x=100, y=50)
obs.set_scene_item_scale("主场景", item_id, scale_x=1.0, scale_y=1.0)
obs.set_scene_item_rotation("主场景", item_id, rotation=45.0)
obs.set_scene_item_crop("主场景", item_id, left=10, right=10, top=5, bottom=5)

# 混合模式
from obs_controller import BlendMode
obs.set_scene_item_blend_mode("主场景", item_id, BlendMode.SCREEN)

# 锁定 / 解锁
obs.set_scene_item_locked("主场景", item_id, locked=True)
```

---

### 滤镜管理

```python
# 获取源上的滤镜列表
filters = obs.get_filter_list("摄像头")
for f in filters:
    print(f"  {f['filterName']} ({f['filterType']}) 启用={f['filterEnabled']}")

# 获取可用滤镜类型
kinds = obs.get_filter_kinds("camera_capture")
print(f"摄像头支持的滤镜: {kinds}")

# 添加滤镜
obs.add_filter("显示器捕获", "灰度滤镜", "color_filter",
               {"saturation": 0.0})

# 设置滤镜参数
obs.set_filter_settings("显示器捕获", "灰度滤镜", {"saturation": 0.0})
obs.set_filter_enabled("显示器捕获", "灰度滤镜", enabled=False)

# 获取单个滤镜详情
f = obs.get_filter("显示器捕获", "灰度滤镜")

# 重命名滤镜
obs.rename_filter("显示器捕获", "灰度滤镜", "黑白滤镜")

# 调整滤镜顺序（索引 0 = 最先应用）
obs.reorder_filters("摄像头", "美颜滤镜", new_index=0)

# 删除滤镜
obs.remove_filter("显示器捕获", "旧滤镜")
```

---

### 滤镜预设

内置 10 个常用预设，支持一键应用：

```python
# 列出所有预设
presets = obs.list_filter_presets()
print(presets)
# ['美颜-轻度', '美颜-中度', '灰度', '反色', '怀旧', '冷色调', '暖色调', '锐化', '增益', '限幅']

# 应用预设
obs.apply_filter_preset("摄像头", "灰度")
obs.apply_filter_preset("显示器捕获", "美颜-中度")

# 添加自定义预设
obs.add_custom_filter_preset(
    name="我的预设",
    filter_kind="color_filter",
    filter_type="Color Filter",
    settings={"brightness": 0.15, "contrast": 0.1, "saturation": 0.8}
)
```

| 预设名 | 滤镜类型 | 参数 |
|--------|---------|------|
| 美颜-轻度 | Color Filter | brightness=0.05, contrast=0.05, saturation=0.05 |
| 美颜-中度 | Color Filter | brightness=0.1, contrast=0.1, saturation=0.1 |
| 灰度 | Color Filter | saturation=0.0 |
| 反色 | Color Filter | saturation=-1.0, brightness=0.1 |
| 怀旧 | Color Filter | brightness=0, contrast=0.15, saturation=0.5, gamma=1.2 |
| 冷色调 | Color Filter | saturation=0.9, gamma=1.0 |
| 暖色调 | Color Filter | brightness=0.05, saturation=0.9, gamma=1.0 |
| 锐化 | Sharpen | sharpness=0.5 |
| 增益 | Color Filter | brightness=0.2, contrast=0.1 |
| 限幅 | Color Filter | (基本调色) |

---

### 录制控制

```python
# 录制状态
status = obs.get_record_status()
print(f"录制中: {status['outputActive']}  路径: {status['outputPath']}")

# 录制控制
obs.start_record()                   # 开始录制
obs.stop_record()                    # 停止录制（返回输出路径）
obs.toggle_record()                  # 切换录制状态
obs.pause_record()                   # 暂停录制
obs.resume_record()                  # 恢复录制

# 录制章节（录途中插入标记点）
obs.split_record()                  # 在当前位置插入章节分割点
obs.create_record_chapter("开场段落")  # 创建命名章节

# 录制输出路径
path = obs.get_record_directory()
obs.set_record_directory("D:/OBS_Recordings")
```

---

### 推流控制

```python
# 推流状态
status = obs.get_stream_status()
print(f"推流中: {status['outputActive']}")

# 推流控制
obs.start_stream()
obs.stop_stream()
obs.toggle_stream()

# 发送字幕（CEA-608/708）
obs.send_stream_caption("测试字幕内容")

# 推流服务配置
settings = obs.get_stream_service_settings()
obs.set_stream_service_settings("rtmp_custom",
    stream_service_url="rtmp://live.example.com/app",
    stream_key="your_stream_key"
)
# 也支持 "rtmp_stream" / "rtmp_custom" 类型
```

---

### 虚拟摄像头

```python
status = obs.get_virtualcam_status()
print(f"虚拟摄像头: {'运行中' if status['isVirtualCam'] else '已停止'}")

obs.start_virtualcam()
obs.stop_virtualcam()
obs.toggle_virtualcam()
```

---

### 转场控制

```python
# 获取转场列表
transitions = obs.get_transition_list()
for t in transitions:
    print(f"  {t['transitionName']} (固定时间: {t['transitionFixed']}ms)")

# 获取 / 设置当前转场
current = obs.get_current_transition()
obs.set_current_transition("Fade")

# 设置转场时长
obs.set_transition_duration(duration_ms=500)

# 高级：获取转场游标位置（0.0-1.0）
cursor = obs.get_transition_cursor()

# 高级：设置转场设置
obs.set_transition_settings({"name": "自定义", "transitionPoint": 200})

# 高级：T-Bar 位置控制（演播室模式）
obs.set_tbar_position(position=0.5, release=False)  # 移动到 50%，不释放
obs.set_tbar_position(position=0.5, release=True)   # 移动并释放，触发转场
```

---

### 媒体源控制

```python
# 获取媒体状态
status = obs.get_media_input_status("背景视频")
print(f"状态: {status['mediaState']}  时间: {status['timestamp']}")

# 媒体动作
obs.trigger_media_action("背景视频", "OBS_WEBSOCKET_MEDIA_INPUT_ACTION_PLAY")
obs.play_media("背景视频")
obs.pause_media("背景视频")
obs.stop_media("背景视频")
obs.restart_media("背景视频")
```

---

### 输入源设置

```python
# 获取输入源设置
settings = obs.get_input_settings("文本源")
print(settings)

# 设置输入源参数
obs.set_input_settings("文本源", {"text": "Hello OBS!", "font": {"size": 48}}, True)
obs.set_input_settings("浏览器",
    {"url": "https://example.com"},
    overlay=False
)
```

---

### 热键控制

```python
# 获取热键列表
hotkeys = obs.get_hotkey_list()

# 按名称触发热键
obs.trigger_hotkey_by_name("scene_1_switch")

# 按按键序列触发（模拟键盘快捷键）
obs.trigger_hotkey_by_sequence(
    key_id="OBS_KEY_1",
    modifiers=["OBS_KEY_MODIFIER_SHIFT", "OBS_KEY_MODIFIER_CONTROL"],
    release=True
)
```

---

### 输入源增删改

```python
# 查询可用输入类型
kinds = obs.get_input_kinds()
print(kinds)
# ['window_capture', 'monitor_capture', 'video_capture_device', 'browser_source',
#  'image_source', 'color_source', 'text_ft2_source', ...]

# 获取某类型的默认设置
defaults = obs.get_input_default_settings("browser_source")

# 创建输入源
obs.create_input(
    input_name="我的浏览器",
    input_kind="browser_source",
    input_settings={"url": "https://example.com"},
    scene_name="主场景"          # 可选：同时添加到场景
)

# 删除输入源
obs.remove_input("旧浏览器")

# 重命名输入源
obs.rename_input("我的浏览器", "新浏览器")
```

---

### 音频控制

```python
# 获取音频输入列表（麦克风等）
audio_inputs = obs.get_audio_inputs()

# 获取特殊输入（桌面音频、麦克风混音）
special = obs.get_special_inputs()
# {'mic1': '麦克风 (USB Audio Device)', 'desktop1': '桌面音频', ...}

# 音频轨道
tracks = obs.get_input_audio_tracks("麦克风")
# {'1': True, '2': False, '3': False, '4': False, '5': False, '6': False}

obs.set_input_audio_tracks("麦克风", {"1": True, "2": True, "3": False})
obs.enable_audio_track("麦克风", 3)
obs.disable_audio_track("麦克风", 2)

# 音量电平监听（实时音量监控）
def on_volume(data):
    for inp in data.get("inputs", []):
        print(f"{inp['inputName']}: {inp['inputVolumeDb']:.1f} dB")

obs.setup_volume_meter_listener(callback=on_volume, subs=None)
vol = obs.get_input_volume_level("麦克风")
# 返回 {'inputName': '麦克风', 'clipping': False,
#        'magnitude': [0.12], 'peakLevel': [0.08]}
```

---

### 音频监听与平衡

```python
# 监听类型
monitor = obs.get_input_monitor_type("麦克风")
# 'OBS_MONITORING_TYPE_NONE' | 'OBS_MONITORING_TYPE_MONITOR_ONLY' | 'OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT'

from obs_controller import MonitorType
obs.set_input_monitor_type("麦克风", MonitorType.MONITOR_ONLY)
# MonitorType.NONE              = 仅输出，不监听
# MonitorType.MONITOR_ONLY      = 仅监听，不输出
# MonitorType.MONITOR_AND_OUTPUT = 同时监听和输出

# 音频平衡（左右声道）
balance = obs.get_input_audio_balance("麦克风")    # 0.0-1.0，0.5=居中
obs.set_input_audio_balance("麦克风", balance=0.3)
```

---

### 转场精细控制

```python
# 获取转场类型列表
transition_kinds = obs.get_transition_kind_list()
# ['cut', 'fade', 'swipe', 'slide', ...]

# 获取 / 设置转场详细设置
settings = obs.get_transition_settings()
obs.set_transition_settings({"transitionPoint": 200, "swipeDirection": "OBS_TRANSITION_SWIPE_LEFT"})
```

---

### 场景转场覆盖

每个场景可以单独设置退出转场，优先级高于全局转场。

```python
# 获取场景的转场覆盖
override = obs.get_scene_transition_override("BRB场景")
# {'transitionName': 'Fade', 'transitionDuration': 300} 或 None

# 设置场景专属转场
obs.set_scene_transition_override(
    scene_name="BRB场景",
    transition_name="Fade",
    transition_duration_ms=300     # None = 使用全局时长
)

# 清除覆盖（恢复使用全局转场）
obs.set_scene_transition_override(scene_name="BRB场景",
    transition_name=None, transition_duration_ms=None
)
```

---

### 分组与演播室模式

```python
# 分组管理
groups = obs.get_group_list()
items_in_group = obs.get_group_items("道具组")

# 演播室模式
preview = obs.get_current_preview_scene()       # 获取预览场景
obs.set_current_preview_scene("预览场景")       # 设置预览场景
obs.trigger_studio_mode_transition()            # 执行预览→节目转场

# 演播室模式切换事件
obs.on_studio_mode_changed(callback=lambda data: print(f"演播室模式: {data['studioModeEnabled']}"))
```

---

### 回放缓冲

```python
# 回放缓冲（游戏录制常用）
status = obs.get_replay_buffer_status()
# {'outputActive': False, 'seconds': 30, 'MB': 250}

obs.start_replay_buffer()        # 启动缓冲
obs.stop_replay_buffer()         # 停止缓冲
obs.toggle_replay_buffer()       # 切换状态

# 保存当前缓冲（触发"保存重放"效果）
saved = obs.save_replay_buffer()
last_replay = obs.get_last_replay()  # 获取最近一次保存的路径

# 监听保存事件
obs.on_replay_buffer_saved(callback=lambda data: print(f"已保存: {data['savedReplayPath']}"))

# 截图保存事件
obs.on_screenshot_saved(callback=lambda data: print(f"截图: {data['savedScreenshotPath']}"))
```

---

### 批量请求

将多个请求打包成一次往返，减少网络开销。

```python
results = obs.batch_request([
    {"requestType": "GetVersion"},
    {"requestType": "GetStats"},
    {"requestType": "GetRecordStatus"},
    {"requestType": "GetStreamStatus"},
])
for r in results:
    print(r)
```

---

### 自动重连与心跳

```python
# 自动重连（OBS 断开后自动重连）
obs.enable_auto_reconnect(interval=5.0, max_retries=10)
obs.disable_auto_reconnect()

# 心跳监控（定期获取状态）
def on_heartbeat(stats):
    print(f"FPS: {stats['activeFps']}  CPU: {stats['cpuUsage']:.1f}%")

obs.start_heartbeat(interval=10.0, callback=on_heartbeat)
obs.stop_heartbeat()

# 连接状态查询
if obs.is_connected():
    print("已连接")
```

---

### 状态快照与恢复

保存和恢复 OBS 的完整状态，便于场景备份和快速切换。

```python
# 快照（内存）
snapshot = obs.snapshot_state()
print(snapshot.keys())
# dict_keys(['current_scene', 'transition', 'scenes', 'inputs', 'filters'])

# 恢复到快照
obs.restore_state(snapshot, restore_scene=True, restore_transition=True,
                  restore_inputs=True, restore_filters=True)

# 保存到文件
obs.save_state_to_file("obs_state_backup.json")

# 从文件加载
obs.load_state_from_file("obs_state_backup.json")
```

---

### 动画切换与淡入淡出

```python
# 平滑场景切换（带淡入淡出动画）
obs.animate_scene_switch(
    target_scene="主场景",
    duration=1.5,                    # 秒
    easing="ease_in_out",            # ease_linear | ease_in | ease_out | ease_in_out
    fade_audio=True,                 # 同时淡入淡出音频
    source_name="背景音乐",
    target_volume_db=-20.0
)

# 音量淡入淡出（可用于静默切换 BGM）
obs.fade_volume(
    source_name="背景音乐",
    to_volume_db=-60.0,             # 目标音量 dB
    duration=1.0                     # 秒
)
```

---

### 截图与画面捕获

基于 OBS WebSocket 的 `GetSourceScreenshot` 接口，支持获取任意源或场景的单帧画面。

> ⚠️ 注意：OBS WebSocket 协议不支持实时视频流，此处通过定时截图模拟"伪实时"，适合预览/监控场景，延迟约 1-2 帧。如需高帧率低延迟，推荐使用 OBS NDI 插件 + `python-ndi`。

```python
# 查询支持的图片格式
formats = obs.get_supported_image_formats()
print(formats)   # ['png', 'jpg', 'bmp', 'webp']

# 获取截图（原始 bytes，可自行解码）
img_bytes = obs.get_source_screenshot(
    source_name="显示器捕获",         # 源名称（与 source_uuid 二选一）
    # source_uuid="xxx",             # 源 UUID（优先）
    image_format="jpg",              # png / jpg / webp / bmp
    image_width=1920,                # 缩放宽度 8-4096，None=原始分辨率
    image_height=1080,               # 缩放高度 8-4096，None=原始分辨率
    compression_quality=80           # -1=默认，0=高压缩，100=无损
)
print(f"截图大小: {len(img_bytes)} bytes")

# 保存到文件
path = obs.save_source_screenshot(
    source_name="显示器捕获",
    file_path="screenshot.jpg",
    image_format="jpg"
)

# 转换为 PIL.Image（Pillow）
pil_img = obs.screenshot_to_pil(
    source_name="显示器捕获",
    image_format="jpg",
    compression_quality=80
)
pil_img.show()   # 直接显示图片

# 转换为 OpenCV 图像（numpy.ndarray，BGR 格式）
cv_img = obs.screenshot_to_opencv(
    source_name="显示器捕获",
    image_format="jpg"
)
import cv2
cv2.imshow("OBS Preview", cv_img)
cv2.waitKey(0)
```

#### 与 tkinter 配合使用

配合 `demo_obs_video_window.py` 可在 tkinter 窗口中实时预览 OBS 画面：

```bash
# 基本预览（当前场景，20fps）
python demo_obs_video_window.py --password "your_password"

# 指定源预览
python demo_obs_video_window.py --source "显示器捕获" --fps 15

# 多源分屏
python demo_obs_video_window.py --mode multi --multi-sources "显示器捕获" "摄像头"

# OpenCV 模式（适合后续图像处理）
python demo_obs_video_window.py --mode cv2 --source "显示器捕获"
```

---

### 事件监听

通过事件客户端（EventClient）监听 OBS 中的各种状态变化。所有事件方法均支持传入回调函数，回调函数接收一个 `data` 参数（字典）。

```python
# 场景事件
obs.on_scene_created(callback=lambda data: print(f"创建场景: {data['sceneName']}"))
obs.on_scene_removed(callback=lambda data: print(f"删除场景: {data['sceneName']}"))
obs.on_scene_changed(callback=lambda data: print(f"切换到: {data['sceneName']}"))

# 音频事件
obs.on_input_mute_changed(callback=lambda data: print(f"{data['inputName']} 静音: {data['inputMuted']}"))
obs.on_input_volume_changed(callback=lambda data: print(f"{data['inputName']} 音量: {data['inputVolumeDb']}"))

# 录制 / 推流事件
obs.on_record_state_changed(callback=lambda data: print(f"录制状态: {data['outputState']}"))
obs.on_stream_state_changed(callback=lambda data: print(f"推流状态: {data['outputState']}"))

# 输入源增删事件
obs.on_input_created(callback=lambda data: print(f"创建输入: {data['inputName']}"))
obs.on_input_removed(callback=lambda data: print(f"删除输入: {data['inputName']}"))

# 转场事件
obs.on_transition_started(callback=lambda data: print(f"转场开始: {data['transitionName']}"))
obs.on_transition_ended(callback=lambda data: print(f"转场结束: {data['transitionName']}"))

# 媒体播放事件
obs.on_media_started(callback=lambda data: print(f"媒体开始: {data['inputName']}"))
obs.on_media_ended(callback=lambda data: print(f"媒体结束: {data['inputName']}"))

# 演播室模式
obs.on_studio_mode_changed(callback=lambda data: print(f"演播室模式: {data['studioModeEnabled']}"))

# 自定义事件（由 broadcast_event 触发）
obs.on_custom_event(callback=lambda data: print(f"收到事件: {data}"))

# 通用事件注册（注册任意事件）
obs.register_callback("CustomEvent", my_callback)
```

#### 获取 OBS 全局状态摘要

```python
summary = obs.get_summary()
# {'current_scene': '主场景', 'record': {...}, 'stream': {...},
#  'transitions': [...], 'scene_count': 5, 'source_count': 12}
```

#### 等待场景切换完成

```python
# 等待场景切换（最多等 10 秒）
result = obs.wait_for_scene("目标场景", timeout=10.0)
if result:
    print("场景已切换")
else:
    print("等待超时")
```

---

## 枚举与数据类

### MediaAction — 媒体动作枚举

```python
from obs_controller import MediaAction
# MediaAction.PLAY | PAUSE | STOP | RESTART | NEXT | PREVIOUS
obs.trigger_media_action("视频", MediaAction.PAUSE.value)
```

### BlendMode — 场景项混合模式

```python
from obs_controller import BlendMode
# BlendMode.NORMAL | ADD | SUBTRACT | SCREEN | MULTIPLY | OVERLAY
```

### MonitorType — 音频监听类型

```python
from obs_controller import MonitorType
# MonitorType.NONE                 = 仅输出，不监听
# MonitorType.MONITOR_ONLY         = 仅监听（戴耳机时防止声音循环）
# MonitorType.MONITOR_AND_OUTPUT   = 同时监听和输出
```

### OutputState — 输出状态枚举

```python
from obs_controller import OutputState
# OutputState.UNKNOWN | STARTING | STARTED | STOPPING | STOPPED | RECONNECTING | RECONNECTED | PAUSED | RESUMED
```

### SceneItem — 场景项数据类

```python
from obs_controller import SceneItem
item = SceneItem(
    scene_item_id=1,
    source_name="显示器捕获",
    source_type="monitor_capture",
    enabled=True,
    locked=False
)
```

### FilterPreset — 滤镜预设数据类

```python
from obs_controller import FilterPreset
preset = FilterPreset(
    name="自定义灰度",
    filter_kind="color_filter",
    filter_type="Color Filter",
    settings={"saturation": 0.0},
    enabled=True
)
```

---

## 异常处理

```python
from obs_controller import OBSController
from obsws_python.error import OBSSDKError, OBSSDKTimeoutError, OBSSDKRequestError

try:
    obs = OBSController(host="localhost", port=4455, password="wrong")
    scene = obs.get_current_scene()
except OBSSDKTimeoutError:
    print("连接超时，OBS 未响应")
except OBSSDKRequestError as e:
    print(f"请求失败: {e}")
except OBSSDKError as e:
    print(f"OBS SDK 错误: {e}")
```

| 异常 | 触发场景 |
|------|---------|
| `OBSSDKTimeoutError` | WebSocket 请求超时 |
| `OBSSDKRequestError` | OBS 返回错误（如场景不存在）|
| `OBSSDKError` | 其他 SDK 错误（连接失败等）|

---

## 日志配置

```python
import logging

# 启用详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

obs = OBSController(password="pwd", log=True)
```

---

## 使用示例

详见 `obs_controller.py` 文件底部的 `if __name__ == "__main__"` 代码块，包含了所有模块的完整调用示例。运行方式：

```bash
python obs_controller.py
```

---

## demo_obs_video_window 预览窗口

`demo_obs_video_window.py` 提供三个预览窗口类：

### OBSVideoWindowPIL（推荐）

基于 Pillow，依赖最少，适合一般预览场景。

```python
from demo_obs_video_window import OBSVideoWindowPIL

window = OBSVideoWindowPIL(
    host="localhost",
    port=4455,
    password="your_password",
    source_name="显示器捕获",     # None = 预览当前场景
    fps=20,                        # 建议 15-30fps
    width=800,
    height=450,
    image_format="jpg",            # jpg 体积小，png 质量高
    compression_quality=80
)
window.run()   # 阻塞主循环
```

功能：实时预览、暂停/继续、截图保存、控制栏 FPS 显示。

### OBSVideoWindowCV2

基于 OpenCV，适合需要叠加绘制（人脸框、目标跟踪等）的场景。

```bash
python demo_obs_video_window.py --mode cv2 --source "显示器捕获" --fps 20
```

### OBSMultiPreviewWindow

多源分屏，同时预览多个源。

```bash
python demo_obs_video_window.py --mode multi \
  --multi-sources "显示器捕获" "摄像头" "浏览器"
```

---

## 注意事项

1. **OBS 版本要求**：必须使用 OBS 28+，obs-websocket v5 协议仅支持新版 OBS。
2. **密码验证**：生产环境建议开启 obs-websocket 密码保护。
3. **截图性能**：WebSocket 截图有一定开销，FPS 建议不超过 30，避免 OBS 负载过高。
4. **重连机制**：`enable_auto_reconnect()` 开启后，后台线程会在断连时自动重连，无需手动管理。
5. **事件监听**：所有 `on_xxx` 事件回调在线程中执行，不要在回调中做耗时操作。
6. **base64 填充**：`get_source_screenshot()` 已自动修复 OBS 返回的 base64 字符串缺少 `=` 填充符的问题，无需手动处理。
7. **线程安全**：`ReqClient` 是同步客户端，建议在主线程或专用线程中使用；事件客户端在独立线程中运行。
