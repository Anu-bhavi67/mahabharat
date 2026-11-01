# MAHABHARAT: DIVINE WARFARE

A 2D fighting game built with Python + Pygame. All graphics and text are
generated procedurally — no external assets required.

## Run

```bash
pip install -r requirements.txt
python main.py
```

## Screens & Flow (state machine)

`MENU -> CHARACTER_SELECT -> FIGHT -> RESULT` (loops back to MENU)

- **MENU**: gold title, subtitle "The Kurukshetra Showdown", blinking "Press ENTER to Start"
- **CHARACTER_SELECT**: 6 warriors (Arjuna, Bhima, Krishna, Karna, Duryodhana, Bhishma)
- **FIGHT**: health bars, punch/kick/block/jump, hit sparks, sunset battlefield
- **RESULT**: victory screen with rematch option

## Controls

| Screen            | Player 1                          | Player 2                        |
|-------------------|-----------------------------------|---------------------------------|
| Menu              | ENTER = start, ESC = quit         | —                               |
| Character Select  | A/D browse, W confirm             | LEFT/RIGHT browse, UP confirm   |
| Fight             | A/D move, W jump, S block, F punch, G kick | Arrows move/jump/block, K punch, L kick |
| Result            | ENTER = main menu, C = rematch    | —                               |
