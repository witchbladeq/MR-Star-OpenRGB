#!/usr/bin/env python3
"""Findn MR Star LED strip BLE client and CLI.

Protocol reverse-engineered from the Android app (MyApplication.d -> FFF3).
Framing: BC | CMD | LEN | PAYLOAD | 55
"""

from __future__ import annotations

import argparse
import asyncio
import colorsys
import logging
import sys
from datetime import datetime
from typing import Callable, Optional

from bleak import BleakClient, BleakError, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic

# ---------------------------------------------------------------------------
# Constants (from MyApplication / GATT discovery in app)
# ---------------------------------------------------------------------------

# No device-specific default — pass --mac AA:BB:CC:DD:EE:FF (use `led.py scan`)
DEFAULT_MAC = ""

SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
WRITE_UUID = "0000fff3-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000fff4-0000-1000-8000-00805f9b34fb"

PKT_START = 0xBC
PKT_END = 0x55
MAX_CHUNK = 20
CHUNK_DELAY_S = 0.200
RECONNECT_DELAY_S = 1.0
CONNECT_TIMEOUT_S = 20.0

# CMD IDs
CMD_POWER = 1
CMD_RGB_ORDER = 2
CMD_PIXELS = 3
CMD_HSV = 4
CMD_BRIGHTNESS = 5
CMD_SCENE = 6
CMD_DIRECTION = 7
CMD_SPEED = 8
CMD_PHONE_MIC_HSV = 9
CMD_CLOCK = 11
CMD_TIMER_QUERY = 12
CMD_TIMER = 13
CMD_MIC_SOURCE = 15
CMD_MIC_MODE = 17
CMD_SENSITIVITY = 18
CMD_ANGLE = 19

RGB_ORDERS = {
    1: "RGB",
    2: "RBG",
    3: "GRB",
    4: "GBR",
    5: "BRG",
    6: "BGR",
}

MIC_MODES = {
    1: "Energy",
    2: "Rhythm",
    3: "Spectrum",
    4: "Scroll",
}

SCENES: dict[int, str] = {
    1: "Automatic loop",
    2: "Symphony",
    3: "Colorful energy",
    4: "Colorful jumps",
    5: "Red-green-blue jumps",
    6: "Yellow-blue-purple jumps",
    7: "7 colors strobe",
    8: "Red-green-blue strobe",
    9: "Yellow-purple-blue strobe",
    10: "7 colors gradient",
    11: "Alternate red-yellow gradient",
    12: "Alternate red-purple gradient",
    13: "Green-green alternate gradient",
    14: "Alternate green-yellow gradient",
    15: "Blue-purple alternating gradient",
    16: "Red horse racing",
    17: "Green horse racing",
    18: "Blue horse racing",
    19: "Yellow horse racing",
    20: "Cyan horse racing",
    21: "Purple horse racing",
    22: "White horse racing",
    23: "Colorful chasing light",
    24: "Red-green-blue follow-up",
    25: "Yellow-cyan-purple follow-up light",
    26: "Colorful fluttering",
    27: "Red-green-blue fluttering",
    28: "Yellow-cyan-purple fluttering",
    29: "Colorful brushing",
    30: "Red-green-blue color brushing",
    31: "Yellow-cyan-purple color brushing",
    32: "Colorful brush color brush closed-pull",
    33: "Red-green-blue color brush closed-pull",
    34: "Yellow-cyan-purple color brush closed-pull",
    35: "7 colors opening-closing",
    36: "Red-green-blue opening-closing",
    37: "Yellow-cyan-purple opening-closes",
    38: "Red opening-closing",
    39: "Green opening-closing",
    40: "Blue opening-closing",
    41: "Yellow opening-closing",
    42: "Cyan opening-closing",
    43: "purple opening-closing",
    44: "White opening-closing",
    45: "7 colors light-dark transition",
    46: "Blue-red-green light-dark transition",
    47: "Violet-green-yellow light-dark transition",
    48: "6 colors light-dark transition red",
    49: "6 colors light-dark transition green",
    50: "6 colors light-dark transition blue",
    51: "6 colors light-dark transition cyan",
    52: "6 colors light-dark transition yellow",
    53: "6 colors light-dark transition purple",
    54: "6 colors light-dark transition white",
    55: "7 colors flowing water",
    56: "Blue-green-red running water",
    57: "Purple-green-yellow running water",
    58: "Red-green running water",
    59: "Green-blue running water",
    60: "Yellow-blue running water",
    61: "Yellow-cyan running water",
    62: "Blue-purple running water",
    63: "Black-white running water",
    64: "White-red-white flow",
    65: "White-green-white flow",
    66: "White-blue-white flow",
    67: "White-yellow-white flow",
    68: "White-green-white flow",
    69: "White purple-white flow",
    70: "Red-white-red flow",
    71: "Green-white-green flow",
    72: "Blue-white-blue flow",
    73: "yellow-white-yellow flow",
    74: "Blue-white-blue flow",
    75: "Purple-white-purple flow",
    76: "7 colors trailing",
    77: "Red trailing",
    78: "Green trailing",
    79: "Blue trailing",
    80: "Yellow trailing",
    81: "Cyan tailing",
    82: "Purple tailing",
    83: "White trailing",
    84: "Red running",
    85: "Green running",
    86: "Blue running",
    87: "Yellow running",
    88: "Cyan running",
    89: "Purple running",
    90: "White running",
    91: "7 colors running",
    92: "Blue-green-red running",
    93: "Purple-cyan-yellow running",
    94: "Blue-purple-cyan-yellow running",
    95: "Blue-green-cyan-yellow running",
    96: "Red dot on white background running",
    97: "Red background and green dot running",
    98: "Green background and blue dot running",
    99: "Yellow dot on the blue background running",
    100: "Yellow background and blue dots running",
    101: "Blue background and purple dots are running",
    102: "White dots running on purple background",
    103: "Red background and white dots running",
    104: "7 colors running with red background",
    105: "7 colors running with green background",
    106: "7 colors running with blue background",
    107: "7 colors yellow background running",
    108: "Green background 7 colors running",
    109: "7 colors running with purple background",
    110: "7 colors running on white background",
    111: "Blue background and green dot running",
    112: "Red background and green dot running",
    113: "Red dot on the blue background running",
    114: "Yellow background and blue dots running",
    115: "The yellow dots on the purple bottom running",
    116: "Yellow background and white dots running",
    117: "Yellow dots on white background running",
}

DAY_BITS = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

log = logging.getLogger("led")


def hex_bytes(data: bytes | bytearray) -> str:
    return " ".join(f"{b:02X}" for b in data)


def u16_be_div256(value: int) -> tuple[int, int]:
    """App encoding for most uint16 fields: value/256, value%256."""
    if value < 0 or value > 0xFFFF:
        raise ValueError(f"uint16 out of range: {value}")
    return (value // 256) & 0xFF, (value % 256) & 0xFF


def u16_be_div255(value: int) -> tuple[int, int]:
    """Scene ID encoding (ModeFragment.f0): value/255, value%255."""
    if value < 0:
        raise ValueError(f"scene id out of range: {value}")
    return (value // 255) & 0xFF, (value % 255) & 0xFF


def build_packet(cmd: int, payload: bytes | bytearray | list[int] = b"") -> bytes:
    pl = bytes(payload)
    if len(pl) > 255:
        raise ValueError("payload too long")
    return bytes([PKT_START, cmd & 0xFF, len(pl), *pl, PKT_END])


def rgb_to_hsv_app(r: int, g: int, b: int) -> tuple[int, int]:
    """Match e2.e.B / Color.RGBToHSV -> H degrees, S*1000."""
    rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
    h, s, _v = colorsys.rgb_to_hsv(rf, gf, bf)
    hue = h * 360.0
    # App forces sat=1.0 when sat>1 or (hue==0 and sat==0)
    if s > 1.0 or (hue == 0.0 and s == 0.0):
        s = 1.0
    return int(hue), int(s * 1000.0)


def parse_hex_packet(text: str) -> bytes:
    cleaned = text.replace(" ", "").replace(":", "").replace("-", "").strip()
    if len(cleaned) % 2:
        raise ValueError("hex length must be even")
    data = bytes.fromhex(cleaned)
    if not data:
        raise ValueError("empty packet")
    return data


def week_mask(days: list[str] | None, include_bit7: bool = True) -> int:
    mask = 0
    if days:
        for d in days:
            key = d.strip().lower()[:3]
            if key not in DAY_BITS:
                raise ValueError(f"unknown day: {d} (use mon..sun)")
            mask |= 1 << DAY_BITS[key]
    if include_bit7:
        mask |= 1 << 7
    return mask & 0xFF


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class LEDClient:
    """Async BLE client for the findn.mrstar protocol."""

    def __init__(
        self,
        address: str = DEFAULT_MAC,
        *,
        auto_reconnect: bool = True,
        on_notify: Optional[Callable[[bytes], None]] = None,
    ) -> None:
        self.address = address.upper()
        self.auto_reconnect = auto_reconnect
        self.on_notify = on_notify
        self._client: Optional[BleakClient] = None
        self._lock = asyncio.Lock()
        self._notify_enabled = False
        self._closing = False

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    def _handle_notify(
        self, _characteristic: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        raw = bytes(data)
        print(f"RX {hex_bytes(raw)}")
        if self.on_notify:
            try:
                self.on_notify(raw)
            except Exception:  # noqa: BLE001 - user callback must not kill notify path
                log.exception("notify callback failed")

    async def connect(self, timeout: float = CONNECT_TIMEOUT_S) -> None:
        self._closing = False
        if self.is_connected:
            return
        log.info("Connecting to %s …", self.address)
        client = BleakClient(
            self.address,
            disconnected_callback=self._on_disconnect,
            timeout=timeout,
        )
        await client.connect()
        self._client = client
        print(f"Connected to {self.address}")
        if self._notify_enabled:
            await self._start_notify()

    def _on_disconnect(self, _client: BleakClient) -> None:
        print("Disconnected")
        if self._closing or not self.auto_reconnect:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        while not self._closing and not self.is_connected:
            try:
                print(f"Reconnecting in {RECONNECT_DELAY_S:.0f}s …")
                await asyncio.sleep(RECONNECT_DELAY_S)
                if self._closing:
                    return
                await self.connect()
            except Exception as exc:  # noqa: BLE001
                print(f"Reconnect failed: {exc}")

    async def disconnect(self) -> None:
        self._closing = True
        self.auto_reconnect = False
        client = self._client
        self._client = None
        if client is not None and client.is_connected:
            try:
                if self._notify_enabled:
                    await client.stop_notify(NOTIFY_UUID)
            except Exception:  # noqa: BLE001
                pass
            await client.disconnect()

    async def ensure_connected(self) -> BleakClient:
        if not self.is_connected:
            await self.connect()
        assert self._client is not None
        return self._client

    async def _start_notify(self) -> None:
        client = await self.ensure_connected()
        await client.start_notify(NOTIFY_UUID, self._handle_notify)
        self._notify_enabled = True

    async def enable_notify(self) -> None:
        self._notify_enabled = True
        await self._start_notify()
        print(f"Notifications enabled on {NOTIFY_UUID}")

    async def write(self, packet: bytes, *, response: bool = False) -> None:
        if not packet:
            raise ValueError("empty write")
        async with self._lock:
            client = await self.ensure_connected()
            print(f"TX {hex_bytes(packet)}")
            # Match app: split payloads > 20 bytes
            if len(packet) <= MAX_CHUNK:
                await client.write_gatt_char(WRITE_UUID, packet, response=response)
                return
            offset = 0
            while offset < len(packet):
                chunk = packet[offset : offset + MAX_CHUNK]
                print(f"TX chunk {hex_bytes(chunk)}")
                await client.write_gatt_char(WRITE_UUID, chunk, response=response)
                offset += MAX_CHUNK
                if offset < len(packet):
                    await asyncio.sleep(CHUNK_DELAY_S)

    async def send_cmd(self, cmd: int, payload: bytes | bytearray | list[int] = b"") -> None:
        await self.write(build_packet(cmd, payload))

    # ----- high-level commands -----

    async def power(self, on: bool) -> None:
        # AdjustFragment cb_power: checked shows ic_off and sends 0; unchecked
        # shows ic_on and sends 1. So ON=0x01, OFF=0x00.
        await self.send_cmd(CMD_POWER, [0x01 if on else 0x00])

    async def set_rgb_order(self, order: int) -> None:
        if order not in RGB_ORDERS:
            raise ValueError(f"order must be 1-6 {RGB_ORDERS}")
        await self.send_cmd(CMD_RGB_ORDER, [order])

    async def set_pixels(self, count: int) -> None:
        if not 8 <= count <= 300:
            raise ValueError("pixels must be 8-300 (app UI range)")
        hi, lo = u16_be_div256(count)
        await self.send_cmd(CMD_PIXELS, [hi, lo])

    async def set_hsv(self, hue: int, sat: int, *, phone_mic: bool = False) -> None:
        """hue 0-360 degrees, sat 0-1000 (app scale)."""
        if not 0 <= hue <= 360:
            raise ValueError("hue must be 0-360")
        if not 0 <= sat <= 1000:
            raise ValueError("sat must be 0-1000")
        hh, hl = u16_be_div256(hue)
        sh, sl = u16_be_div256(sat)
        cmd = CMD_PHONE_MIC_HSV if phone_mic else CMD_HSV
        await self.send_cmd(cmd, [hh, hl, sh, sl, 0x00, 0x00])

    async def set_rgb(self, r: int, g: int, b: int) -> None:
        for name, v in (("r", r), ("g", g), ("b", b)):
            if not 0 <= v <= 255:
                raise ValueError(f"{name} must be 0-255")
        hue, sat = rgb_to_hsv_app(r, g, b)
        await self.set_hsv(hue, sat)

    async def set_color_hex(self, hex_color: str) -> None:
        text = hex_color.strip().lstrip("#")
        if len(text) != 6:
            raise ValueError("color must be 6 hex digits, e.g. ff0000")
        r = int(text[0:2], 16)
        g = int(text[2:4], 16)
        b = int(text[4:6], 16)
        await self.set_rgb(r, g, b)

    async def set_brightness(self, value: int) -> None:
        if not 0 <= value <= 1000:
            raise ValueError("brightness must be 0-1000")
        # App clamps <3 to 3 on seekbar stop
        if value < 3:
            value = 3
        hi, lo = u16_be_div256(value)
        await self.send_cmd(CMD_BRIGHTNESS, [hi, lo, 0, 0, 0, 0])

    async def set_scene(self, scene_id: int) -> None:
        if scene_id < 1 or scene_id > 117:
            raise ValueError("scene id must be 1-117")
        hi, lo = u16_be_div255(scene_id)
        await self.send_cmd(CMD_SCENE, [hi, lo])
        name = SCENES.get(scene_id, "?")
        print(f"Scene {scene_id}: {name}")

    async def set_direction(self, reverse: bool) -> None:
        # reverse True -> 0, forward -> 1
        await self.send_cmd(CMD_DIRECTION, [0x00 if reverse else 0x01])

    async def set_speed(self, speed: int) -> None:
        if not 1 <= speed <= 100:
            raise ValueError("speed must be 1-100")
        await self.send_cmd(CMD_SPEED, [speed & 0xFF])

    async def set_mic_source(self, device_mic: bool) -> None:
        await self.send_cmd(CMD_MIC_SOURCE, [0x01 if device_mic else 0x00])

    async def set_mic_mode(self, mode: int) -> None:
        if mode not in MIC_MODES:
            raise ValueError(f"mic mode must be 1-4 {MIC_MODES}")
        await self.send_cmd(CMD_MIC_MODE, [mode])
        print(f"Mic mode {mode}: {MIC_MODES[mode]}")

    async def set_sensitivity(self, level: int) -> None:
        if not 1 <= level <= 100:
            raise ValueError("sensitivity must be 1-100")
        await self.send_cmd(CMD_SENSITIVITY, [level & 0xFF])

    async def set_angle(self, degrees: int) -> None:
        if not 0 <= degrees <= 360:
            raise ValueError("angle must be 0-360")
        hi, lo = u16_be_div256(degrees)
        await self.send_cmd(CMD_ANGLE, [hi, lo])

    async def sync_clock(self, when: Optional[datetime] = None) -> None:
        dt = when or datetime.now()
        year = dt.year
        y_hi = (year >> 8) & 0xFF
        y_lo = year & 0xFF
        await self.send_cmd(
            CMD_CLOCK,
            [
                y_hi,
                y_lo,
                dt.month,
                dt.day,
                dt.hour,
                dt.minute,
                dt.second,
            ],
        )

    async def timer_query(self) -> None:
        await self.send_cmd(CMD_TIMER_QUERY, [0x01])

    async def set_timer(
        self,
        *,
        slot_on: bool,
        enabled: bool,
        hour: int,
        minute: int,
        days: list[str] | None = None,
        week: Optional[int] = None,
    ) -> None:
        if not 0 <= hour <= 23:
            raise ValueError("hour must be 0-23")
        if not 0 <= minute <= 59:
            raise ValueError("minute must be 0-59")
        mask = week if week is not None else week_mask(days)
        await self.send_cmd(
            CMD_TIMER,
            [
                0x01,
                0x01 if slot_on else 0x00,
                0x01 if enabled else 0x00,
                mask & 0xFF,
                hour & 0xFF,
                minute & 0xFF,
            ],
        )

    async def auto(self, on: bool) -> None:
        """App has no auto BLE toggle; scene 1 is 'Automatic loop'."""
        if on:
            await self.set_scene(1)
        else:
            print(
                "Note: no dedicated auto-off command in the app. "
                "Sending a static color or another scene exits automatic loop."
            )


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------


async def scan_devices(timeout: float = 8.0) -> None:
    print(f"Scanning for {timeout:.0f}s …")
    devices = await BleakScanner.discover(timeout=timeout)
    if not devices:
        print("No devices found")
        return
    for d in sorted(devices, key=lambda x: (x.name or "", x.address)):
        name = d.name or "(no name)"
        print(f"{d.address}  RSSI={getattr(d, 'rssi', '?')}  {name}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="led.py",
        description="findn.mrstar / BLEdina LED BLE control",
    )
    p.add_argument(
        "--mac",
        default=DEFAULT_MAC,
        help="device MAC, e.g. AA:BB:CC:DD:EE:FF (required except for scan/scenes)",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    p.add_argument(
        "--no-reconnect",
        action="store_true",
        help="disable automatic reconnect",
    )

    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("on", help="Power ON (BC 01 01 01 55)")
    sub.add_parser("off", help="Power OFF (BC 01 01 00 55)")

    c = sub.add_parser("color", help="Set color from hex RGB (via HSV CMD 4)")
    c.add_argument("hex", help="e.g. ff0000")

    c = sub.add_parser("rgb", help="Set color from R G B 0-255")
    c.add_argument("r", type=int)
    c.add_argument("g", type=int)
    c.add_argument("b", type=int)

    c = sub.add_parser("hsv", help="Set HSV: hue 0-360, sat 0-1000")
    c.add_argument("hue", type=int)
    c.add_argument("sat", type=int)

    c = sub.add_parser("brightness", help="Brightness 3-1000 (CMD 5)")
    c.add_argument("value", type=int)

    c = sub.add_parser("scene", help="Scene / effect 1-117 (CMD 6)")
    c.add_argument("id", type=int)

    c = sub.add_parser("speed", help="Effect speed 1-100 (CMD 8)")
    c.add_argument("value", type=int)

    c = sub.add_parser(
        "auto",
        help="Automatic loop: on -> scene 1 (no dedicated auto CMD in app)",
    )
    c.add_argument("state", choices=("on", "off"))

    c = sub.add_parser(
        "music",
        help="No BLE music toggle in app; 'on' selects phone-mic source (CMD 15=0)",
    )
    c.add_argument("state", choices=("on", "off"))

    c = sub.add_parser(
        "musicmode",
        help="Alias for micmode (app has no separate music modes)",
    )
    c.add_argument("mode", type=int, choices=(1, 2, 3, 4))

    c = sub.add_parser("mic", help="Mic source: on=device (1), off=phone (0)")
    c.add_argument("state", choices=("on", "off"))

    c = sub.add_parser("micmode", help="Device mic effect 1-4 (CMD 17)")
    c.add_argument("mode", type=int, choices=(1, 2, 3, 4))

    c = sub.add_parser("sensitivity", help="Mic sensitivity 1-100 (CMD 18)")
    c.add_argument("value", type=int)

    c = sub.add_parser("pixels", help="LED count 8-300 (CMD 3)")
    c.add_argument("count", type=int)

    c = sub.add_parser("order", help="RGB wire order 1-6 (CMD 2)")
    c.add_argument("value", type=int, choices=tuple(RGB_ORDERS))

    c = sub.add_parser("direction", help="Effect direction")
    c.add_argument("state", choices=("reverse", "forward", "r", "p"))

    c = sub.add_parser("angle", help="Color wheel angle 0-360 (CMD 19)")
    c.add_argument("degrees", type=int)

    c = sub.add_parser("timer", help="Timer / clock commands")
    tsub = c.add_subparsers(dest="timer_cmd", required=True)
    tsub.add_parser("sync", help="Sync device clock (CMD 11)")
    tsub.add_parser("query", help="Query timers (CMD 12)")
    for slot_name in ("on", "off"):
        tp = tsub.add_parser(slot_name, help=f"Set {slot_name.upper()} timer (CMD 13)")
        tp.add_argument("hour", type=int)
        tp.add_argument("minute", type=int)
        tp.add_argument(
            "--days",
            default="mon,tue,wed,thu,fri,sat,sun",
            help="comma-separated days (default all)",
        )
        tp.add_argument(
            "--disable",
            action="store_true",
            help="disable this timer slot",
        )
        tp.add_argument(
            "--week",
            type=lambda x: int(x, 0),
            default=None,
            help="raw week bitmask (overrides --days)",
        )

    c = sub.add_parser("raw", help="Send raw hex packet")
    c.add_argument("hex", help="e.g. BC01010055")

    c = sub.add_parser("notify", help="Enable notifications and listen")
    c.add_argument(
        "--seconds",
        type=float,
        default=30.0,
        help="listen duration (default 30)",
    )

    sub.add_parser("scan", help="Scan for BLE devices")
    sub.add_parser("scenes", help="List scene IDs and names")

    return p


async def run_command(args: argparse.Namespace) -> int:
    if args.cmd == "scan":
        await scan_devices()
        return 0

    if args.cmd == "scenes":
        for i, name in SCENES.items():
            print(f"{i:3d}  {name}")
        return 0

    if not args.mac:
        print(
            "Pass --mac AA:BB:CC:DD:EE:FF (find it with: python led.py scan)",
            file=sys.stderr,
        )
        return 2

    client = LEDClient(
        args.mac,
        auto_reconnect=not args.no_reconnect,
    )

    try:
        await client.connect()

        if args.cmd == "on":
            await client.power(True)
        elif args.cmd == "off":
            await client.power(False)
        elif args.cmd == "color":
            await client.set_color_hex(args.hex)
        elif args.cmd == "rgb":
            await client.set_rgb(args.r, args.g, args.b)
        elif args.cmd == "hsv":
            await client.set_hsv(args.hue, args.sat)
        elif args.cmd == "brightness":
            await client.set_brightness(args.value)
        elif args.cmd == "scene":
            await client.set_scene(args.id)
        elif args.cmd == "speed":
            await client.set_speed(args.value)
        elif args.cmd == "auto":
            await client.auto(args.state == "on")
        elif args.cmd == "music":
            # App Music tab streams CMD 4 locally; closest BLE switch is phone mic source
            if args.state == "on":
                print(
                    "Note: app music mode has no enable packet; "
                    "selecting phone-mic source (CMD 15=0). "
                    "Music colors are sent as CMD 4 from the phone."
                )
                await client.set_mic_source(False)
            else:
                print(
                    "Note: no music-off BLE command. "
                    "Switching to device mic source (CMD 15=1)."
                )
                await client.set_mic_source(True)
        elif args.cmd in ("musicmode", "micmode"):
            if args.cmd == "musicmode":
                print("Note: app has no music modes; using device mic modes (CMD 17).")
            await client.set_mic_mode(args.mode)
        elif args.cmd == "mic":
            await client.set_mic_source(args.state == "on")
        elif args.cmd == "sensitivity":
            await client.set_sensitivity(args.value)
        elif args.cmd == "pixels":
            await client.set_pixels(args.count)
        elif args.cmd == "order":
            await client.set_rgb_order(args.value)
            print(f"Order {args.value}: {RGB_ORDERS[args.value]}")
        elif args.cmd == "direction":
            rev = args.state in ("reverse", "r")
            await client.set_direction(rev)
        elif args.cmd == "angle":
            await client.set_angle(args.degrees)
        elif args.cmd == "timer":
            if args.timer_cmd == "sync":
                await client.sync_clock()
            elif args.timer_cmd == "query":
                await client.enable_notify()
                await client.timer_query()
                await asyncio.sleep(2.0)
            elif args.timer_cmd in ("on", "off"):
                days = [x for x in args.days.split(",") if x.strip()]
                await client.set_timer(
                    slot_on=(args.timer_cmd == "on"),
                    enabled=not args.disable,
                    hour=args.hour,
                    minute=args.minute,
                    days=days,
                    week=args.week,
                )
        elif args.cmd == "raw":
            await client.write(parse_hex_packet(args.hex))
        elif args.cmd == "notify":
            await client.enable_notify()
            # Also query timer state like the app does when opening Timer tab
            await client.sync_clock()
            await client.timer_query()
            print(f"Listening for {args.seconds:.0f}s (Ctrl+C to stop) …")
            await asyncio.sleep(args.seconds)
        else:
            print(f"Unknown command: {args.cmd}", file=sys.stderr)
            return 2

        # Brief settle for notify / write completion
        await asyncio.sleep(0.15)
        return 0
    except (BleakError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        await client.disconnect()


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)
    try:
        return asyncio.run(run_command(args))
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
