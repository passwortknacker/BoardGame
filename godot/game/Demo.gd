extends Control
## Vertical-slice feel demo — a real co-op TURN driven by the authoritative engine. You control
## hero 0; an AI ally takes hero 1; then the Red Dragon responds. Mana is a real resource: play
## Mana cards to fill the pool, spend it on the market / affinity / ability / artifact slots, then
## End Turn. Placeholder visuals + procedural SFX; the full board UX (drag-to-play, targeting,
## multi-hotseat, juiced art) is the next step. Rules = engine/ (verified headless).

var game: Game
var me                       # the human-controlled hero (player 0)
var allies: Array = []       # AI-controlled heroes (players 1..)
var boss_max := 1

# HUD nodes
var boss_bar: ProgressBar
var boss_label: Label
var anger_bar: ProgressBar
var anger_label: Label
var minion_row: Control
var telegraph: Label
var hud: Label
var mana_label: Label
var hand_root: Control
var boss_panel: Panel
var market_panel: Panel
var log_label: Label

const HAND_Y := 770.0
const SPACING := 116.0

func _ready() -> void:
	if not CardDB.ensure_loaded():
		var err := Label.new()
		err.text = "data/cards.json missing — run: python tools/export_godot_data.py"
		err.position = Vector2(40, 40); add_child(err); return
	_build_ui()
	_new_game()

# ---------------- UI ----------------
func _build_ui() -> void:
	var bg := ColorRect.new()
	bg.color = Color(0.07, 0.08, 0.11)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	var title := Label.new()
	title.text = "🐉  RED DRAGON  —  vertical-slice demo"
	title.add_theme_font_size_override("font_size", 24)
	title.position = Vector2(36, 18)
	add_child(title)

	boss_panel = _panel(Vector2(660, 80), Vector2(600, 300), Color(0.18, 0.08, 0.08), Color(0.8, 0.3, 0.2))
	add_child(boss_panel)
	var crest := _label("RED DRAGON", 28, Vector2(40, 18), Vector2(520, 36))
	crest.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	boss_panel.add_child(crest)
	boss_bar = ProgressBar.new()
	boss_bar.position = Vector2(40, 96); boss_bar.size = Vector2(520, 38); boss_bar.show_percentage = false
	boss_panel.add_child(boss_bar)
	boss_label = _label("", 20, Vector2(40, 98), Vector2(520, 34))
	boss_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	boss_panel.add_child(boss_label)
	anger_label = _label("ANGER", 13, Vector2(40, 150), Vector2(120, 18))
	boss_panel.add_child(anger_label)
	anger_bar = ProgressBar.new()
	anger_bar.position = Vector2(150, 150); anger_bar.size = Vector2(410, 18); anger_bar.show_percentage = false
	var afill := StyleBoxFlat.new(); afill.bg_color = Color(0.9, 0.5, 0.1); afill.set_corner_radius_all(4)
	anger_bar.add_theme_stylebox_override("fill", afill)
	boss_panel.add_child(anger_bar)
	telegraph = _label("", 15, Vector2(40, 174), Vector2(520, 40))
	telegraph.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	boss_panel.add_child(telegraph)

	var minion_caption := _label("MINIONS", 12, Vector2(40, 210), Vector2(200, 16))
	boss_panel.add_child(minion_caption)
	# minions occupy a strip in the lower boss panel
	minion_row = Control.new()
	minion_row.position = Vector2(20, 228)
	minion_row.size = Vector2(560, 62)
	boss_panel.add_child(minion_row)

	hud = _label("", 18, Vector2(40, 110), Vector2(560, 220))
	add_child(hud)

	log_label = _label("", 14, Vector2(40, 340), Vector2(580, 380))
	log_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	log_label.vertical_alignment = VERTICAL_ALIGNMENT_TOP
	add_child(log_label)

	mana_label = _label("", 30, Vector2(40, 700), Vector2(560, 40))
	mana_label.add_theme_color_override("font_color", Color(0.5, 0.8, 1.0))
	add_child(mana_label)

	hand_root = Control.new()
	hand_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	hand_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(hand_root)

	_button("Market", Vector2(660, 400), _toggle_market)
	_button("Affinity (3)", Vector2(790, 400), _raise_affinity)
	_button("Ability (3)", Vector2(950, 400), _use_ability)
	_button("Buy Slot", Vector2(1100, 400), _buy_slot)
	_button("END TURN ▶", Vector2(1080, 980), _end_turn, Vector2(180, 50))
	_button("New Game", Vector2(40, 980), _new_game)
	_button("Menu", Vector2(200, 980), func(): get_tree().change_scene_to_file("res://game/Setup.tscn"))

	market_panel = _panel(Vector2(660, 460), Vector2(600, 400), Color(0.10, 0.12, 0.16), Color(0.4, 0.5, 0.7))
	market_panel.visible = false
	add_child(market_panel)
	var mtitle := _label("MARKET — click to buy (under your deck)", 16, Vector2(16, 10), Vector2(560, 24))
	market_panel.add_child(mtitle)

func _panel(pos: Vector2, sz: Vector2, bg: Color, border: Color) -> Panel:
	var pn := Panel.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg; sb.set_corner_radius_all(14); sb.set_border_width_all(3); sb.border_color = border
	pn.add_theme_stylebox_override("panel", sb)
	pn.position = pos; pn.size = sz
	return pn

func _label(text: String, fsize: int, pos: Vector2, sz: Vector2) -> Label:
	var l := Label.new()
	l.text = text; l.add_theme_font_size_override("font_size", fsize)
	l.position = pos; l.size = sz
	return l

func _button(text: String, pos: Vector2, cb: Callable, sz := Vector2(150, 44)) -> void:
	var b := Button.new()
	b.text = text; b.position = pos; b.size = sz
	b.pressed.connect(func(): AudioManager.play_sfx("ui_click"); cb.call())
	add_child(b)

# ---------------- game flow ----------------
func _new_game() -> void:
	var P: int = Session.player_count if Session else 2
	game = Game.new(randi())
	game.setup(P, Session.team if Session else null)
	me = game.players[0]
	allies = game.players.slice(1)
	boss_max = game.boss
	market_panel.visible = false
	var ally_names: Array = []
	for a in allies: ally_names.append(a.cls)
	_log("New game — you are the %s. AI allies: %s." % [me.cls, ", ".join(ally_names) if ally_names else "(none)"])
	_start_my_turn()

func _start_my_turn() -> void:
	if game.result != "": return
	me.turn_no += 1
	game.ctx = Game.Ctx.new()
	# fire charged artifacts
	for eq in me.equipped.duplicate():
		if eq.fires_from_turn <= me.turn_no:
			game.dmg_accum = 0
			Effects.apply_player(game, me, game.ctx, CardDB.fx(eq.card_name))
			if game.dmg_accum > 0:
				_log("%s fires (%d dmg)" % [eq.card_name, game.dmg_accum])
	me.draw_to_full(game.HAND_SIZE)
	_relayout_hand()
	_refresh()

func _end_turn() -> void:
	if game.result != "": return
	# AI allies take their full turns (fire artifacts, play hand, buy, equip, draw)
	for a in allies:
		game.player_turn(a)
		if _ended(): return
	# boss phase for the round
	for _i in range(game.boss_turns_for(game.players.size())):
		var v_before := game.village
		game.boss_turn()
		Juice.shake(boss_panel, 10.0)
		if game.village < v_before:
			Juice.float_text(self, Vector2(330, 200), "Village -%d" % (v_before - game.village), Color(1, 0.6, 0.3))
			AudioManager.play_sfx("hit")
		if _ended(): return
	game.minions_attack()
	if _ended(): return
	game.round_no += 1
	game.village_prevent = 0
	for pl in game.players: pl.prevent = 0
	_log("— Round %d —" % game.round_no)
	_start_my_turn()

func _ended() -> bool:
	if game.check_end():
		if game.result == "win":
			AudioManager.play_sfx("victory")
			Juice.float_text(self, Vector2(900, 180), "VICTORY!", Color(1, 0.9, 0.4), 56)
		else:
			AudioManager.play_sfx("defeat")
			Juice.float_text(self, Vector2(300, 200), game.result.to_upper(), Color(1, 0.4, 0.4), 48)
		Events.game_over.emit(game.result)
		_refresh()
		return true
	return false

# ---------------- hand / play ----------------
func _relayout_hand() -> void:
	for c in hand_root.get_children(): c.queue_free()
	var n: int = me.hand.size()
	for i in range(n):
		var card := CardView.new()
		card.card_name = me.hand[i]
		var x: float = 560.0 + (i - (n - 1) / 2.0) * SPACING
		card.position = Vector2(x, HAND_Y)
		card.base_y = HAND_Y
		card.rotation_degrees = (i - (n - 1) / 2.0) * 2.0
		card.pressed.connect(_play_card.bind(card))
		hand_root.add_child(card)

func _play_card(card_name: String, card: CardView) -> void:
	if game.result != "" or not me.hand.has(card_name): return
	var cat := CardDB.cat(card_name)
	# artifacts equip into a slot instead of resolving immediately
	if cat == "Artifact" and card_name != "Wandering Wisp":
		if me.free_slots() <= 0:
			Juice.float_text(self, card.position, "no free slot", Color(1, 0.6, 0.3))
			return
		me.hand.erase(card_name)
		me.equipped.append(Game.Equip.new(card_name, me.turn_no + game.charge_turns))
		AudioManager.play_sfx("card_play")
		_log("Equip %s (fires next turn)" % card_name)
		_fly_and_relayout(card)
		_refresh()
		return
	me.hand.erase(card_name)
	match cat:
		"Mana": game.ctx.mana_cards_used += 1
		"Support": game.ctx.support_used += 1
		"Weapon": game.ctx.weapons_played += 1
	var mana_before: int = game.ctx.mana
	game.dmg_accum = 0; game.heal_accum = 0
	var v_before := game.village
	Effects.apply_player(game, me, game.ctx, CardDB.fx(card_name))
	Events.card_played.emit(card_name, me.pid)
	if card_name != "Wandering Wisp":
		me.discard.append(card_name)
	_fly_and_relayout(card)
	# feedback
	if game.dmg_accum > 0:
		AudioManager.play_sfx("boss_hit"); Juice.shake(boss_panel, 14.0)
		Juice.float_text(self, Vector2(940, 140), "-%d" % game.dmg_accum, Color(1, 0.85, 0.3), 42)
	if game.ctx.mana - mana_before > 0:
		AudioManager.play_sfx("card_play")
		Juice.float_text(self, Vector2(card.position.x, card.position.y - 30), "+%d mana" % (game.ctx.mana - mana_before), Color(0.5, 0.8, 1.0))
	if game.heal_accum > 0:
		AudioManager.play_sfx("heal")
		Juice.float_text(self, Vector2(120, 160), "+%d" % game.heal_accum, Color(0.4, 1.0, 0.5))
	if game.village > v_before:
		Juice.float_text(self, Vector2(330, 200), "Village +%d" % (game.village - v_before), Color(0.4, 1.0, 0.5))
	_refresh()
	_ended()

func _fly_and_relayout(card: CardView) -> void:
	Juice.fly_to(card, Vector2(card.position.x, card.position.y - 230), 0.26,
		func(): card.queue_free(); _relayout_hand())

# ---------------- spending actions ----------------
func _mana_left() -> int:
	return game.ctx.mana - game.ctx.mana_spent

func _toggle_market() -> void:
	market_panel.visible = not market_panel.visible
	if market_panel.visible: _refresh_market()

func _refresh_market() -> void:
	for c in market_panel.get_children():
		if c is Button: c.queue_free()
	var y := 44
	for slot in game.market:
		var name: String = slot["name"]
		var cost := CardDB.cost(name)
		var gated: bool = CardDB.is_tier2(slot["tier"]) and me.affinity < 2
		var b := Button.new()
		b.text = "%s  [%s %s]  — %d mana%s" % [name, slot["cat"], str(slot["tier"]), cost, ("  (Affinity 2)" if gated else "")]
		b.position = Vector2(16, y); b.size = Vector2(568, 26)
		b.disabled = gated or _mana_left() < cost
		b.pressed.connect(_buy.bind(slot))
		market_panel.add_child(b)
		y += 28

func _buy(slot: Dictionary) -> void:
	var name: String = slot["name"]
	var cost := CardDB.cost(name)
	if game.no_buy or _mana_left() < cost: return
	if CardDB.is_tier2(slot["tier"]) and me.affinity < 2: return
	game.ctx.mana_spent += cost
	me.gain_card(name)
	game.replace_market_slot(slot)
	AudioManager.play_sfx("ui_click")
	_log("Buy %s (-%d mana) → under deck" % [name, cost])
	_refresh(); _refresh_market()

func _raise_affinity() -> void:
	if me.affinity >= 3 or _mana_left() < 3: return
	game.ctx.mana_spent += 3; me.affinity += 1
	_log("Raise Affinity → %d" % me.affinity); _refresh()

func _use_ability() -> void:
	if _mana_left() < 3: return
	game.ctx.mana_spent += 3
	game.heal_accum = 0; game.dmg_accum = 0
	Abilities.use_ability(game, me, game.ctx)
	AudioManager.play_sfx("heal" if game.heal_accum > 0 else "boss_hit")
	_log("%s ability%s" % [me.cls, " (Ultimate)" if me.ultimate() else ""])
	_refresh(); _ended()

func _buy_slot() -> void:
	if me.slots >= 5: return
	var cost := int(game.slot_cost[me.slots])
	if _mana_left() < cost: return
	game.ctx.mana_spent += cost; me.slots += 1
	_log("Buy artifact slot #%d (-%d mana)" % [me.slots, cost]); _refresh()

# ---------------- render ----------------
func _refresh() -> void:
	boss_bar.max_value = boss_max
	var shown: int = max(0, game.boss)
	boss_bar.create_tween().tween_property(boss_bar, "value", float(shown), 0.3)
	boss_label.text = "%d / %d HP" % [shown, boss_max]
	var threshold: int = game.players.size() + 2
	anger_bar.max_value = threshold
	anger_bar.value = game.anger
	anger_label.text = "ANGER %d/%d" % [game.anger, threshold]
	telegraph.text = "Next boss card: %s" % (game.boss_deck[0] if not game.boss_deck.is_empty() else "—")
	_rebuild_minions()
	mana_label.text = "✦ Mana available: %d" % _mana_left()
	var eq: Array = []
	for e in me.equipped: eq.append(e.card_name)
	var ally_txt: Array = []
	for a in allies: ally_txt.append("%s %d" % [a.cls, a.hp])
	hud.text = "YOU — %s   HP %d/%d   Affinity %d   Slots %d/%d\nAllies — %s\nVillage %d/%d   Anger %d   Minions %d   Round %d\nEquipped: %s" % [
		me.cls, me.hp, game.PLAYER_HP, me.affinity, me.equipped.size(), me.slots,
		", ".join(ally_txt) if ally_txt else "(solo)", game.village, game.village_max, game.anger,
		game.minions.size(), game.round_no, ", ".join(eq) if eq else "—"]

func _rebuild_minions() -> void:
	for c in minion_row.get_children(): c.queue_free()
	var x := 0
	for m in game.minions:
		var pn := _panel(Vector2(x, 0), Vector2(132, 58), Color(0.16, 0.10, 0.10), Color(0.7, 0.4, 0.3))
		minion_row.add_child(pn)
		var l := _label("%s\n%d HP" % [m.card_name, m.hp], 13, Vector2(6, 6), Vector2(120, 48))
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		pn.add_child(l)
		x += 140
		if x > 560: break   # overflow guard for very crowded boards

var _log_lines: Array = []
func _log(s: String) -> void:
	_log_lines.append(s)
	if _log_lines.size() > 16: _log_lines.pop_front()
	if log_label: log_label.text = "\n".join(_log_lines)
