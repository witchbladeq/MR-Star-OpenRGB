# Scenes (CMD 6)

Extracted from Android string resources `cmode1` … `cmode117` in the OEM app.

Packet: `BC 06 02 <id/255> <id%255> 55`

## UI tabs (`ModeFragment`)

Tabs loaded (skips Flow / `tab_mode5`): **Basic**, **Opening & closing**, **Transition**, **Running water**, **Tailing**, **Running**.

| Tab | List | Scene IDs selectable in UI |
|-----|------|----------------------------|
| Basic | `Z` | 1, 2, 3, 4, 7, 10, 26, 27, 29, 30, 31, 32 |
| Opening & closing | `a0` | 35–44 |
| Transition | `b0` | 45–54 |
| Running water | `c0` | 55–62 |
| Flow (dead — list built, tab not added) | `d0` | 63–75 |
| Tailing | `e0` | 76–83 |
| Running | `f0` | 84–93 |

**Basic ID mapping from wheel position** (`e1.i` / `WheelPicker`):

| Position | Scene ID |
|----------|----------|
| 0–3 | pos + 1 → 1–4 |
| 4 | 7 |
| 5 | 10 |
| 6–7 | pos + 20 → 26–27 |
| 8+ | pos + 21 → 29–32 |

Other tabs: `id = position + offset` (35, 45, 55, 63, 76, 84).

Scenes with string resources but **not** selectable in the shipped UI are still valid device IDs if sent directly.

---

## Complete table

| ID | Name | In UI |
|----|------|-------|
| 1 | Automatic loop | Basic |
| 2 | Symphony | Basic |
| 3 | Colorful energy | Basic |
| 4 | Colorful jumps | Basic |
| 5 | Red-green-blue jumps | — |
| 6 | Yellow-blue-purple jumps | — |
| 7 | 7 colors strobe | Basic |
| 8 | Red-green-blue strobe | — |
| 9 | Yellow-purple-blue strobe | — |
| 10 | 7 colors gradient | Basic |
| 11 | Alternate red-yellow gradient | — |
| 12 | Alternate red-purple gradient | — |
| 13 | Green-green alternate gradient | — |
| 14 | Alternate green-yellow gradient | — |
| 15 | Blue-purple alternating gradient | — |
| 16 | Red horse racing | — |
| 17 | Green horse racing | — |
| 18 | Blue horse racing | — |
| 19 | Yellow horse racing | — |
| 20 | Cyan horse racing | — |
| 21 | Purple horse racing | — |
| 22 | White horse racing | — |
| 23 | Colorful chasing light | — |
| 24 | Red-green-blue follow-up | — |
| 25 | Yellow-cyan-purple follow-up light | — |
| 26 | Colorful fluttering | Basic |
| 27 | Red-green-blue fluttering | Basic |
| 28 | Yellow-cyan-purple fluttering | — |
| 29 | Colorful brushing | Basic |
| 30 | Red-green-blue color brushing | Basic |
| 31 | Yellow-cyan-purple color brushing | Basic |
| 32 | Colorful brush color brush closed-pull | Basic |
| 33 | Red-green-blue color brush closed-pull | — |
| 34 | Yellow-cyan-purple color brush closed-pull | — |
| 35 | 7 colors opening-closing | Opening |
| 36 | Red-green-blue opening-closing | Opening |
| 37 | Yellow-cyan-purple opening-closes | Opening |
| 38 | Red opening-closing | Opening |
| 39 | Green opening-closing | Opening |
| 40 | Blue opening-closing | Opening |
| 41 | Yellow opening-closing | Opening |
| 42 | Cyan opening-closing | Opening |
| 43 | purple opening-closing | Opening |
| 44 | White opening-closing | Opening |
| 45 | 7 colors light-dark transition | Transition |
| 46 | Blue-red-green light-dark transition | Transition |
| 47 | Violet-green-yellow light-dark transition | Transition |
| 48 | 6 colors light-dark transition red | Transition |
| 49 | 6 colors light-dark transition green | Transition |
| 50 | 6 colors light-dark transition blue | Transition |
| 51 | 6 colors light-dark transition cyan | Transition |
| 52 | 6 colors light-dark transition yellow | Transition |
| 53 | 6 colors light-dark transition purple | Transition |
| 54 | 6 colors light-dark transition white | Transition |
| 55 | 7 colors flowing water | Water |
| 56 | Blue-green-red running water | Water |
| 57 | Purple-green-yellow running water | Water |
| 58 | Red-green running water | Water |
| 59 | Green-blue running water | Water |
| 60 | Yellow-blue running water | Water |
| 61 | Yellow-cyan running water | Water |
| 62 | Blue-purple running water | Water |
| 63 | Black-white running water | Flow (dead tab) |
| 64 | White-red-white flow | Flow (dead tab) |
| 65 | White-green-white flow | Flow (dead tab) |
| 66 | White-blue-white flow | Flow (dead tab) |
| 67 | White-yellow-white flow | Flow (dead tab) |
| 68 | White-green-white flow | Flow (dead tab) |
| 69 | White purple-white flow | Flow (dead tab) |
| 70 | Red-white-red flow | Flow (dead tab) |
| 71 | Green-white-green flow | Flow (dead tab) |
| 72 | Blue-white-blue flow | Flow (dead tab) |
| 73 | yellow-white-yellow flow | Flow (dead tab) |
| 74 | Blue-white-blue flow | Flow (dead tab) |
| 75 | Purple-white-purple flow | Flow (dead tab) |
| 76 | 7 colors trailing | Tailing |
| 77 | Red trailing | Tailing |
| 78 | Green trailing | Tailing |
| 79 | Blue trailing | Tailing |
| 80 | Yellow trailing | Tailing |
| 81 | Cyan tailing | Tailing |
| 82 | Purple tailing | Tailing |
| 83 | White trailing | Tailing |
| 84 | Red running | Running |
| 85 | Green running | Running |
| 86 | Blue running | Running |
| 87 | Yellow running | Running |
| 88 | Cyan running | Running |
| 89 | Purple running | Running |
| 90 | White running | Running |
| 91 | 7 colors running | Running |
| 92 | Blue-green-red running | Running |
| 93 | Purple-cyan-yellow running | Running |
| 94 | Blue-purple-cyan-yellow running | — |
| 95 | Blue-green-cyan-yellow running | — |
| 96 | Red dot on white background running | — |
| 97 | Red background and green dot running | — |
| 98 | Green background and blue dot running | — |
| 99 | Yellow dot on the blue background running | — |
| 100 | Yellow background and blue dots running | — |
| 101 | Blue background and purple dots are running | — |
| 102 | White dots running on purple background | — |
| 103 | Red background and white dots running | — |
| 104 | 7 colors running with red background | — |
| 105 | 7 colors running with green background | — |
| 106 | 7 colors running with blue background | — |
| 107 | 7 colors yellow background running | — |
| 108 | Green background 7 colors running | — |
| 109 | 7 colors running with purple background | — |
| 110 | 7 colors running on white background | — |
| 111 | Blue background and green dot running | — |
| 112 | Red background and green dot running | — |
| 113 | Red dot on the blue background running | — |
| 114 | Yellow background and blue dots running | — |
| 115 | The yellow dots on the purple bottom running | — |
| 116 | Yellow background and white dots running | — |
| 117 | Yellow dots on white background running | — |

Names are copied verbatim from the English string resources (including capitalization quirks such as `purple opening-closing` and `Yellow-cyan-purple opening-closes`).
