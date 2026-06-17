extends Control
## Feel-demo / interactive spec for the Hearthstone-tier target. The board state is the REAL
## authoritative engine (engine/Game.gd): clicking a card resolves its actual effect, and the boss
## bar / mana / floating numbers / screenshake / SFX all react. Placeholder visuals + procedural
## SFX stand in for the art/audio pass. This is the reference the full board UI will grow from.
##
## NOTE: a relaxed sandbox turn (no mana-cost enforcement, manual "Boss Turn") so you can feel card
## plays. The full turn loop + drag-to-play + targeting come in the vertical slice.

var game: Game
var player
var ctx

var boss_bar: ProgressBar
var boss_label: Label
var telegraph: Label
var hud: Label
var hand_root: Control
var boss_panel: Panel
var boss_max := 1

const HAND_Y := 760.0
const SPACING := 116.0

func _ready() -> void:
	if not CardDB.ensure_loaded():
		var err := Label.new()
		err.text = "data/cards.json missing — run: python tools/export_godot_data.py"
		err.position = Vector2(40, 40)
		add_child(err)
		return
	_build_ui()
	_new_game()

# ---------------- UI construction ----------------
func _build_ui() -> void:
	var bg := ColorRect.new()
	bg.color = Color(0.07, 0.08, 0.11)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	var title := Label.new()
	title.text = "🐉  RED DRAGON  —  feel demo"
	title.add_theme_font_size_override("font_size", 26)
	title.position = Vector2(40, 24)
	add_child(title)

	boss_panel = Panel.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.18, 0.08, 0.08)
	sb.set_corner_radius_all(16)
	sb.set_border_width_all(3)
	sb.border_color = Color(0.8, 0.3, 0.2)
	boss_panel.add_theme_stylebox_override("panel", sb)
	boss_panel.position = Vector2(660, 90)
	boss_panel.size = Vector2(600, 230)
	add_child(boss_panel)

	var crest := Label.new()
	crest.text = "RED DRAGON"
	crest.add_theme_font_size_override("font_size", 30)
	crest.position = Vector2(40, 24)
	crest.size = Vector2(520, 40)
	crest.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	boss_panel.add_child(crest)

	boss_bar = ProgressBar.new()
	boss_bar.position = Vector2(40, 110)
	boss_bar.size = Vector2(520, 40)
	boss_bar.show_percentage = false
	boss_panel.add_child(boss_bar)

	boss_label = Label.new()
	boss_label.add_theme_font_size_override("font_size", 22)
	boss_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	boss_label.position = Vector2(40, 112)
	boss_label.size = Vector2(520, 36)
	boss_panel.add_child(boss_label)

	telegraph = Label.new()
	telegraph.add_theme_font_size_override("font_size", 16)
	telegraph.position = Vector2(40, 165)
	telegraph.size = Vector2(520, 30)
	boss_panel.add_child(telegraph)

	hud = Label.new()
	hud.add_theme_font_size_override("font_size", 20)
	hud.position = Vector2(60, 120)
	hud.size = Vector2(540, 200)
	add_child(hud)

	hand_root = Control.new()
	hand_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	hand_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(hand_root)

	_make_button("New Game", Vector2(40, 980), _new_game)
	_make_button("Refill Hand", Vector2(200, 980), _refill)
	_make_button("Boss Turn", Vector2(380, 980), _boss_turn)

func _make_button(text: String, pos: Vector2, cb: Callable) -> void:
	var b := Button.new()
	b.text = text
	b.position = pos
	b.size = Vector2(150, 44)
	b.pressed.connect(func():
		AudioManager.play_sfx("ui_click")
		cb.call())
	add_child(b)

# ---------------- game wiring ----------------
func _new_game() -> void:
	game = Game.new(randi())
	game.setup(2, [["Cleric", "healer"], ["Paladin", "weapons"]])
	player = game.players[0]
	ctx = Game.Ctx.new()
	boss_max = game.boss
	_relayout_hand()
	_refresh()

func _refill() -> void:
	player.draw_to_full(game.HAND_SIZE)
	ctx = Game.Ctx.new()   # fresh sandbox turn
	_relayout_hand()
	_refresh()

func _boss_turn() -> void:
	var v_before := game.village
	game.boss_turn()
	Juice.shake(boss_panel, 8.0)
	var dv := v_before - game.village
	if dv > 0:
		AudioManager.play_sfx("hit")
		Juice.float_text(self, Vector2(330, 220), "Village -%d" % dv, Color(1, 0.6, 0.3))
	_refresh()
	_check_over()

func _relayout_hand() -> void:
	for c in hand_root.get_children():
		c.queue_free()
	var n: int = player.hand.size()
	for i in range(n):
		var card := CardView.new()
		card.card_name = player.hand[i]
		var x: float = 640.0 + (i - (n - 1) / 2.0) * SPACING
		card.position = Vector2(x, HAND_Y)
		card.base_y = HAND_Y
		card.rotation_degrees = (i - (n - 1) / 2.0) * 2.5
		card.pressed.connect(_play_card.bind(card))
		hand_root.add_child(card)

func _play_card(card_name: String, card: CardView) -> void:
	if not player.hand.has(card_name):
		return
	player.hand.erase(card_name)
	var cat := CardDB.cat(card_name)
	match cat:
		"Mana": ctx.mana_cards_used += 1
		"Support": ctx.support_used += 1
		"Weapon": ctx.weapons_played += 1
	var mana_before: int = ctx.mana
	game.dmg_accum = 0
	game.heal_accum = 0
	var v_before := game.village
	Effects.apply_player(game, player, ctx, CardDB.fx(card_name))
	Events.card_played.emit(card_name, player.pid)

	# fly the card up and fade, then relayout the remaining hand (the hand-has guard above
	# prevents a double-play if clicked again mid-animation)
	Juice.fly_to(card, Vector2(card.position.x, card.position.y - 220), 0.28,
		func():
			card.queue_free()
			_relayout_hand())

	var enemy_dmg := game.dmg_accum
	if enemy_dmg > 0:
		AudioManager.play_sfx("boss_hit")
		Juice.shake(boss_panel, 14.0)
		Juice.float_text(self, Vector2(940, 150), "-%d" % enemy_dmg, Color(1, 0.85, 0.3), 44)
		Events.damage_dealt.emit(enemy_dmg, true)
	var gained: int = ctx.mana - mana_before
	if gained > 0:
		AudioManager.play_sfx("card_play")
		Juice.float_text(self, Vector2(card.position.x, card.position.y - 40), "+%d mana" % gained, Color(0.5, 0.8, 1.0))
	if game.heal_accum > 0:
		AudioManager.play_sfx("heal")
		Juice.float_text(self, Vector2(120, 180), "+%d" % game.heal_accum, Color(0.4, 1.0, 0.5))
	if enemy_dmg == 0 and gained == 0 and game.heal_accum == 0:
		AudioManager.play_sfx("card_play")
	if game.village < v_before:
		Juice.float_text(self, Vector2(330, 220), "Village -%d" % (v_before - game.village), Color(1, 0.6, 0.3))
	_refresh()
	_check_over()

func _refresh() -> void:
	boss_bar.max_value = boss_max
	var shown := max(0, game.boss)
	var t := boss_bar.create_tween()
	t.tween_property(boss_bar, "value", float(shown), 0.3).set_trans(Tween.TRANS_CUBIC)
	boss_label.text = "%d / %d HP" % [shown, boss_max]
	telegraph.text = "Next: %s" % (game.boss_deck[0] if not game.boss_deck.is_empty() else "—")
	var eq := []
	for e in player.equipped:
		eq.append(e.card_name)
	hud.text = "P0 %s   HP %d   Affinity %d   Slots %d/%d\nMana (this sandbox turn): %d\nVillage: %d/%d   Anger: %d   Minions: %d\nEquipped: %s" % [
		player.cls, player.hp, player.affinity, player.equipped.size(), player.slots,
		ctx.mana, game.village, game.village_max, game.anger, game.minions.size(),
		", ".join(eq) if eq else "—"]

func _check_over() -> void:
	if game.boss <= 0:
		AudioManager.play_sfx("victory")
		Juice.float_text(self, Vector2(900, 200), "VICTORY!", Color(1, 0.9, 0.4), 56)
		Events.game_over.emit("win")
	elif game.village <= 0:
		AudioManager.play_sfx("defeat")
		Juice.float_text(self, Vector2(300, 220), "VILLAGE FALLEN", Color(1, 0.4, 0.4), 48)
		Events.game_over.emit("village")
