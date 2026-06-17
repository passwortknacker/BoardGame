class_name AI
extends RefCounted
## Heuristic player policy (port of sim/ai.py). Drives headless balance games and serves as the
## "auto-play / suggested move" baseline for the real UI. Profiles differ mainly in what they BUY.

const PROFILES := {
	"mana_greedy":   {"dmg_cat": ["Weapon"], "econ_target": 7, "mana_turns": 6, "aff_target": 2, "want_engine": false, "heal_focus": false},
	"affinity_rush": {"dmg_cat": ["Weapon"], "econ_target": 4, "mana_turns": 2, "aff_target": 3, "want_engine": false, "heal_focus": false},
	"weapons":       {"dmg_cat": ["Weapon"], "econ_target": 5, "mana_turns": 2, "aff_target": 2, "want_engine": false, "heal_focus": false},
	"caster":        {"dmg_cat": ["Artifact", "Weapon"], "econ_target": 5, "mana_turns": 2, "aff_target": 2, "want_engine": true, "heal_focus": false},
	"balanced":      {"dmg_cat": ["Weapon", "Artifact"], "econ_target": 5, "mana_turns": 2, "aff_target": 2, "want_engine": true, "heal_focus": false},
	"healer":        {"dmg_cat": ["Weapon"], "econ_target": 5, "mana_turns": 2, "aff_target": 3, "want_engine": false, "heal_focus": true},
	"support":       {"dmg_cat": ["Support", "Weapon"], "econ_target": 5, "mana_turns": 2, "aff_target": 3, "want_engine": false, "heal_focus": true},
}

static func _prof(p) -> Dictionary:
	return PROFILES.get(p.strategy, PROFILES["balanced"])

static func mana_left(p, ctx) -> int:
	return ctx.mana - ctx.mana_spent

# ============================ play hand ============================
static func play_hand(g: Game, p, ctx) -> void:
	var played_ability := false
	var guard := 0
	while true:
		guard += 1
		if guard > 300 or g.check_end(): return
		var manas := _by_cat(p.hand, "Mana")
		if not manas.is_empty():
			manas.sort_custom(func(a, b): return int(AI._is_scaling_mana(a)) < int(AI._is_scaling_mana(b)))
			_play(g, p, ctx, manas[0], "mana"); continue
		if not played_ability:
			played_ability = true
			_maybe_ability(g, p, ctx); continue
		var sup := _by_cat(p.hand, "Support")
		if not sup.is_empty():
			_play(g, p, ctx, sup[0], "support"); continue
		var weps: Array = []
		for name in p.hand:
			if CardDB.cat(name) == "Weapon" or name == "Wandering Wisp": weps.append(name)
		if not weps.is_empty():
			weps.sort_custom(func(a, b): return int(a == "Multiplier Maul") < int(b == "Multiplier Maul"))
			_play(g, p, ctx, weps[0], "weapon" if weps[0] != "Wandering Wisp" else "wisp"); continue
		return

static func _play(g: Game, p, ctx, name: String, kind: String) -> void:
	p.hand.erase(name)
	match kind:
		"mana": ctx.mana_cards_used += 1
		"support": ctx.support_used += 1
		"weapon": ctx.weapons_played += 1
	ctx.consumed = false
	g.dmg_accum = 0; g.heal_accum = 0
	Effects.apply_player(g, p, ctx, CardDB.fx(name))
	if name != "Wandering Wisp" and not ctx.consumed:
		p.discard.append(name)

static func _maybe_ability(g: Game, p, ctx) -> void:
	if mana_left(p, ctx) < Abilities.ABILITY_COST: return
	var prof := _prof(p)
	var low := 10
	for q in g.players: low = min(low, q.hp)
	var healer := ["Ranger", "Paladin", "Druid", "Cleric", "Bard"].has(p.cls)
	var heal_focus: bool = prof.get("heal_focus", false)
	var hp_thresh := 8 if heal_focus else 5
	var vil_thresh := 26 if heal_focus else 14
	var useful := false
	if healer and (low <= hp_thresh or g.village <= vil_thresh):
		useful = true
	elif p.cls == "Wizard":
		for eq in p.equipped:
			if eq.fires_from_turn <= p.turn_no: useful = true; break
	elif p.cls == "Weaponmaster":
		useful = _has_in_discard(p, "Weapon")
	elif p.cls == "Enchanter":
		useful = p.ultimate() or p.equipped.size() < p.slots
	elif p.cls == "Blacksmith":
		useful = _has_in_discard(p, "Weapon") or p.ultimate()
	if useful:
		ctx.mana_spent += Abilities.ABILITY_COST
		Abilities.use_ability(g, p, ctx)
		ctx.used_ability = true

# ============================ draw phase ============================
static func draw_phase(g: Game, p) -> void:
	if p.hand.is_empty():
		p.draw_to_full(g.HAND_SIZE); return
	var keep: Array = []
	for name in p.hand:
		if CardDB.cat(name) in ["Mana", "Artifact"]: keep.append(name)
	if keep.size() > 5: keep = keep.slice(0, 5)
	for name in p.hand:
		if not keep.has(name): p.discard.append(name)
	p.hand = keep
	p.draw_to_full(g.HAND_SIZE)

# ============================ equip ============================
static func do_equip(g: Game, p, ctx) -> void:
	while true:
		var arts: Array = []
		for name in p.hand:
			if CardDB.cat(name) == "Artifact" and name != "Wandering Wisp": arts.append(name)
		if arts.is_empty(): return
		var art: String = arts[0]
		for name in arts:
			if est_damage(g, p, name) > est_damage(g, p, art): art = name
		if p.free_slots() == 0:
			var nxt: int = (int(g.slot_cost[p.slots]) if p.slots < 5 else 99)
			if p.slots < 5 and mana_left(p, ctx) >= nxt and not g.no_buy:
				ctx.mana_spent += nxt; p.slots += 1
			elif not p.equipped.is_empty():
				var worst = p.equipped[0]
				for e in p.equipped:
					if est_damage(g, p, e.card_name) < est_damage(g, p, worst.card_name): worst = e
				if est_damage(g, p, art) > est_damage(g, p, worst.card_name):
					p.equipped.erase(worst); p.discard.append(worst.card_name)
				else: return
			else: return
		p.hand.erase(art)
		p.equipped.append(Game.Equip.new(art, p.turn_no + g.charge_turns))

# ============================ buys ============================
static func do_buys(g: Game, p, ctx) -> void:
	if g.no_buy: return
	var prof := _prof(p)
	if prof["want_engine"] and p.turn_no >= prof["mana_turns"]:
		while p.slots < 5:
			var cost := int(g.slot_cost[p.slots])
			var waiting: int = _arts_owned(p) - p.slots
			var want: bool = p.slots == 0 or waiting >= 1
			if want and mana_left(p, ctx) >= cost:
				ctx.mana_spent += cost; p.slots += 1
			else: break
	var guard := 0
	while guard < 6:
		guard += 1
		var m := mana_left(p, ctx)
		if m <= 0: break
		var slot = null
		if p.affinity < prof["aff_target"]:
			var affs: Array = []
			for s in g.market_choices(p, m, "Mana"):
				if CardDB.text(s["name"]).contains("Affinity"): affs.append(s)
			if not affs.is_empty():
				slot = affs[0]
				for s in affs:
					if CardDB.cost(s["name"]) < CardDB.cost(slot["name"]): slot = s
			elif m >= 3:
				ctx.mana_spent += 3; p.affinity += 1; continue
		if slot == null:
			var opts := g.market_choices(p, m)
			if opts.is_empty(): break
			var best = opts[0]
			for s in opts:
				if buy_value(g, p, s["name"], prof, ctx) > buy_value(g, p, best["name"], prof, ctx): best = s
			if buy_value(g, p, best["name"], prof, ctx) <= 0.0: break
			slot = best
		var name: String = slot["name"]
		var cost := CardDB.cost(name)
		ctx.mana_spent += cost
		p.gain_card(name)
		g.replace_market_slot(slot)
		if cost == 0: break

# ============================ valuation ============================
static func est_mana(name: String) -> int:
	var t := CardDB.text(name)
	var rx := RegEx.new()
	rx.compile("\\+\\s*(\\d+)\\s*Mana")
	var m := rx.search(t)
	return int(m.get_string(1)) if m else 1

static func est_damage(g: Game, p, name: String) -> float:
	var eq: int = p.equipped.size()
	var aff: int = p.affinity
	match name:
		"Artificer's Fury": return float(1 + 2 * eq)
		"Rupture Relic": return float(2 * max(1, eq))
		"Power Cube": return float(max(5, eq))
		"Affinity Beacon": return float(min(8, max(4, 2 + 2 * aff)))
		"Mana Cannon": return float(5 + 2 * aff)
		"Multiplier Maul": return float(2 * 2 + aff)
		"Ethereal Fragment": return 3.0
		"Pacifier": return float(max(0, 10 - p.hp))
		"Crimson Scythe": return 8.0
		"Thunderstrike", "Volley": return 2.0
		"Alliance Amulet": return 1.0
		"Bloodfire Charm": return 6.0
	var t := CardDB.text(name)
	var rx := RegEx.new()
	rx.compile("(\\d+)\\s*DMG")
	var mm := rx.search(t)
	var base := float(int(mm.get_string(1))) if mm else 0.0
	if t.to_lower().contains("every enemy") or t.to_lower().contains("all enemies"): base += 1.0
	return base

static func buy_value(g: Game, p, name: String, prof: Dictionary, ctx) -> float:
	var category := CardDB.cat(name)
	var t := CardDB.text(name)
	var early: bool = p.turn_no <= int(prof["mana_turns"])
	if category == "Mana":
		if name == "Mana Crystal": return 0.0
		var need: bool = early or ctx.mana < int(prof["econ_target"])
		var v: float = float(est_mana(name))
		if t.contains("Affinity") and p.affinity < int(prof["aff_target"]): v += 1.0
		return v * (2.2 if need else 0.25)
	if category == "Weapon":
		return est_damage(g, p, name) * 1.2
	if category == "Artifact":
		var can_engine: bool = prof["want_engine"] or p.slots > 0
		var cap: int = min(5, p.slots + 1) + (1 if prof["want_engine"] else 0)
		if _arts_owned(p) >= cap: return 0.0
		return est_damage(g, p, name) * (3.0 if can_engine else 0.6)
	if category == "Support":
		var v: float = 1.5
		if t.to_lower().contains("draw"): v += 2.5
		if t.contains("Prevent") or t.to_lower().contains("heal") or t.contains("Village"):
			v += 1.5 if prof.get("heal_focus", false) else 0.5
		return v
	return 0.0

# ---- helpers ----
static func _by_cat(zone: Array, cat: String) -> Array:
	var out: Array = []
	for name in zone:
		if CardDB.cat(name) == cat: out.append(name)
	return out

static func _has_in_discard(p, cat: String) -> bool:
	for name in p.discard:
		if CardDB.cat(name) == cat: return true
	return false

static func _is_scaling_mana(name: String) -> bool:
	var t := CardDB.text(name)
	return t.contains("for every") or t.contains("Increase by")

static func _arts_owned(p) -> int:
	var loose := 0
	for zone in [p.deck, p.hand, p.discard]:
		for name in zone:
			if CardDB.cat(name) == "Artifact" and name != "Wandering Wisp": loose += 1
	return loose + p.equipped.size()
