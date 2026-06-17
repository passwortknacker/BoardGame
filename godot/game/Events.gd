extends Node
## Global signal bus. The headless engine (engine/) stays PURE — it never emits these. The
## presentation layer (controllers that drive a Game) emits these so visual/audio feedback is fully
## decoupled from rules: animation, particles, screenshake, SFX, and floating numbers all just
## listen here. This is what keeps "Hearthstone-tier juice" out of the rules code.

signal card_played(card_name: String, by_pid: int)
signal damage_dealt(amount: int, to_boss: bool)
signal village_damaged(amount: int)
signal player_healed(pid: int, amount: int)
signal mana_changed(value: int)
signal boss_card_flipped(card_name: String)
signal minion_spawned(card_name: String, hp: int)
signal disaster_triggered(card_name: String)
signal turn_started(pid: int)
signal game_over(result: String)
