#!/usr/bin/env python3
"""OpenRGB bridge for Findn MR Star / compatible LED strips.

OpenRGB has no generic BLE manual device. This process pretends to be an
E1.31 (sACN) and/or DDP receiver on localhost; OpenRGB sends colors here,
and we translate them to the BLE protocol via led.LEDClient.

Setup in OpenRGB (Settings -> Manually added devices):
  1. Add device -> E1.31
  2. IP: 127.0.0.1
  3. Start Universe: 1
  4. Start Channel: 1
  5. Number of LEDs: 1   (device is whole-strip, not per-LED)
  6. Universe Size: 512
  7. Save, then Rescan / Update device list
  8. Keep this bridge running

Usage:
  python openrgb_bridge.py --mac AA:BB:CC:DD:EE:FF
  python openrgb_bridge.py --mac AA:BB:CC:DD:EE:FF --universe 1
"""

from __future__ import annotations

import argparse
import asyncio
import struct
import sys
import time
from typing import Optional

from led import LEDClient, rgb_to_hsv_app

E131_PORT = 5568
DDP_PORT = 4048
ACN_PID = b"ASC-E1.17\x00\x00\x00"

# Minimum gap between BLE color writes (device + GATT cannot keep up with sACN rates)
MIN_BLE_INTERVAL_S = 0.05


def parse_e131(data: bytes) -> Optional[tuple[int, bytes]]:
    """Return (universe, dmx_channels_without_start_code) or None."""
    if len(data) < 126:
        return None
    if data[4:16] != ACN_PID:
        return None
    universe = struct.unpack("!H", data[113:115])[0]
    # data[125] = DMX start code (0); channels follow
    dmx = data[126:]
    return universe, dmx


def parse_ddp(data: bytes) -> Optional[bytes]:
    """Return RGB payload bytes or None. DDP header is 10 bytes."""
    if len(data) < 10:
        return None
    # flags in data[0]; data type in data[2] — accept RGB payloads
    length = struct.unpack("!H", data[8:10])[0]
    payload = data[10 : 10 + length]
    if len(payload) < 3:
        return None
    return payload


def rgb_from_dmx(dmx: bytes, start_channel: int = 1) -> Optional[tuple[int, int, int]]:
    """1-based DMX start channel -> first RGB triplet."""
    idx = start_channel - 1
    if idx < 0 or idx + 2 >= len(dmx):
        return None
    return dmx[idx], dmx[idx + 1], dmx[idx + 2]


def rgb_from_leds(payload: bytes, mode: str = "first") -> tuple[int, int, int]:
    """Collapse multi-LED RGB blob to one color for whole-strip device."""
    n = len(payload) // 3
    if n <= 0:
        return 0, 0, 0
    if mode == "first" or n == 1:
        return payload[0], payload[1], payload[2]
    # average
    rs = gs = bs = 0
    for i in range(n):
        rs += payload[i * 3]
        gs += payload[i * 3 + 1]
        bs += payload[i * 3 + 2]
    return rs // n, gs // n, bs // n


class ColorBridge:
    def __init__(
        self,
        client: LEDClient,
        *,
        universe: int,
        start_channel: int,
        collapse: str,
        min_interval: float,
    ) -> None:
        self.client = client
        self.universe = universe
        self.start_channel = start_channel
        self.collapse = collapse
        self.min_interval = min_interval
        self._last_rgb: Optional[tuple[int, int, int]] = None
        self._last_hsb: Optional[tuple[int, int, int]] = None
        self._last_sent = 0.0
        self._pending: Optional[tuple[int, int, int]] = None
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self.packets_e131 = 0
        self.packets_ddp = 0

    def submit_rgb(self, r: int, g: int, b: int) -> None:
        self._pending = (r & 0xFF, g & 0xFF, b & 0xFF)
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush_loop())

    async def _flush_loop(self) -> None:
        while True:
            await asyncio.sleep(self.min_interval)
            pending = self._pending
            if pending is None:
                return
            self._pending = None
            await self._apply(pending)

    async def _apply(self, rgb: tuple[int, int, int]) -> None:
        async with self._lock:
            now = time.monotonic()
            if rgb == self._last_rgb and (now - self._last_sent) < 1.0:
                return
            wait = self.min_interval - (now - self._last_sent)
            if wait > 0:
                await asyncio.sleep(wait)

            r, g, b = rgb
            level = max(r, g, b)
            # Never toggle power from the color wheel. OpenRGB often passes
            # through black while dragging; power OFF stuck the strip.
            # Black / off in OpenRGB => minimum brightness only.
            if level == 0:
                hue, sat, bri = 0, 0, 3
            else:
                # Normalize to full brightness for stable hue/sat, dim via CMD 5
                scale = 255.0 / level
                nr = min(255, int(round(r * scale)))
                ng = min(255, int(round(g * scale)))
                nb = min(255, int(round(b * scale)))
                hue, sat = rgb_to_hsv_app(nr, ng, nb)
                bri = max(3, int(round(level * 1000 / 255)))

            hsb = (hue, sat, bri)
            try:
                if self._last_hsb is None or hsb[0] != self._last_hsb[0] or hsb[1] != self._last_hsb[1]:
                    if level > 0:
                        await self.client.set_hsv(hue, sat)
                if self._last_hsb is None or hsb[2] != self._last_hsb[2]:
                    await self.client.set_brightness(bri)
                self._last_rgb = rgb
                self._last_hsb = hsb
                self._last_sent = time.monotonic()
            except Exception as exc:  # noqa: BLE001
                print(f"BLE write failed: {exc}")

    def handle_e131(self, data: bytes) -> None:
        parsed = parse_e131(data)
        if parsed is None:
            return
        univ, dmx = parsed
        if univ != self.universe:
            return
        self.packets_e131 += 1
        rgb = rgb_from_dmx(dmx, self.start_channel)
        if rgb is None:
            return
        # If OpenRGB sends many LEDs starting at start_channel, collapse
        idx = self.start_channel - 1
        blob = dmx[idx:]
        if len(blob) >= 6 and self.collapse != "first":
            r, g, b = rgb_from_leds(blob, self.collapse)
        else:
            r, g, b = rgb
        self.submit_rgb(r, g, b)

    def handle_ddp(self, data: bytes) -> None:
        payload = parse_ddp(data)
        if payload is None:
            return
        self.packets_ddp += 1
        r, g, b = rgb_from_leds(payload, self.collapse)
        self.submit_rgb(r, g, b)


class DatagramProto(asyncio.DatagramProtocol):
    def __init__(self, handler) -> None:
        self._handler = handler

    def datagram_received(self, data: bytes, _addr) -> None:
        try:
            self._handler(data)
        except Exception as exc:  # noqa: BLE001
            print(f"packet error: {exc}")


async def run_bridge(args: argparse.Namespace) -> int:
    client = LEDClient(args.mac, auto_reconnect=True)
    bridge = ColorBridge(
        client,
        universe=args.universe,
        start_channel=args.start_channel,
        collapse=args.collapse,
        min_interval=args.interval,
    )

    print(f"Connecting BLE {args.mac} …")
    await client.connect()
    await client.power(True)

    loop = asyncio.get_running_loop()
    transports = []

    if not args.no_e131:
        t, _ = await loop.create_datagram_endpoint(
            lambda: DatagramProto(bridge.handle_e131),
            local_addr=(args.bind, E131_PORT),
        )
        transports.append(t)
        print(f"E1.31 listening on {args.bind}:{E131_PORT} universe={args.universe}")

    if not args.no_ddp:
        t, _ = await loop.create_datagram_endpoint(
            lambda: DatagramProto(bridge.handle_ddp),
            local_addr=(args.bind, DDP_PORT),
        )
        transports.append(t)
        print(f"DDP   listening on {args.bind}:{DDP_PORT}")

    print()
    print("OpenRGB setup:")
    print("  Settings -> Manually added devices -> Add device... -> E1.31")
    print(f"  IP (Unicast):   {args.bind if args.bind != '0.0.0.0' else '127.0.0.1'}")
    print(f"  Start Universe: {args.universe}")
    print(f"  Start Channel:  {args.start_channel}")
    print("  Number of LEDs: 1")
    print("  Universe Size:  512")
    print("  then: Update device list / Rescan")
    print()
    print("Bridge running. Ctrl+C to stop.")

    try:
        while True:
            await asyncio.sleep(10)
            if args.stats:
                print(
                    f"stats e131={bridge.packets_e131} ddp={bridge.packets_ddp} "
                    f"last={bridge._last_rgb}"
                )
    except asyncio.CancelledError:
        pass
    finally:
        for t in transports:
            t.close()
        await client.disconnect()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="OpenRGB E1.31/DDP -> BLEdina BLE bridge")
    p.add_argument(
        "--mac",
        required=True,
        help="LED MAC address, e.g. AA:BB:CC:DD:EE:FF (python led.py scan)",
    )
    p.add_argument("--bind", default="127.0.0.1", help="UDP bind address")
    p.add_argument("--universe", type=int, default=1, help="E1.31 universe")
    p.add_argument("--start-channel", type=int, default=1, help="E1.31 start channel (1-based)")
    p.add_argument(
        "--collapse",
        choices=("first", "average"),
        default="first",
        help="How to map multi-LED frames to whole-strip color",
    )
    p.add_argument(
        "--interval",
        type=float,
        default=MIN_BLE_INTERVAL_S,
        help="Min seconds between BLE updates",
    )
    p.add_argument("--no-e131", action="store_true", help="Disable E1.31 listener")
    p.add_argument("--no-ddp", action="store_true", help="Disable DDP listener")
    p.add_argument("--stats", action="store_true", help="Print packet counters")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return asyncio.run(run_bridge(args))
    except KeyboardInterrupt:
        print("\nStopped")
        return 130
    except OSError as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        print(
            "If port 5568 is busy, close other sACN software or change OpenRGB to another machine IP.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
