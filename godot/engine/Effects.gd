class_name Effects
extends RefCounted
## Data-driven effect resolver. Player cards carry an `fx` op list; boss/minion/disaster cards
## carry a `bfx` op list (see tools/export_godot_data.py for the vocabulary). This is the GDScript
## analogue of sim/effects.py — but interpreted from data, so adding a card = editing the xlsx,
## never touching code.
##
## NOTE (foundation scope): the common ops are fully implemented. A handful of exotic card ops are
## approximated and tallied in g.warnings via g.warn_op() so the engine runs end-to-end honestly.

# ============================ PLAYER CARDS ============================
static func apply_player(g: Game, p, ctx, fx: Array) -> void:
	for op in fx:
		_player_op(g, p, ctx, op)

static func _player_op(g: Game, p, ctx, op: Dictionary) -> void:
	if op.has("mana"):
		ctx.mana += int(op["mana"])
	elif op.has("dmg"):
		g.attack_target(p, int(op["dmg"]), not op.has("slayer"))
	elif op.has("aoe"):
		g.aoe(int(op["aoe"]))
	elif op.has("dmgWeapons"):
		var d = op["dmgWeapons"]
		g.attack_target(p, int(d.get("per", 0)) * ctx.weapons_played + int(d.get("aff", 0)) * p.affinity)
	elif op.has("dmgAff"):
		var d = op["dmgAff"]
		var v: int = int(d.get("b", 0)) + int(d.get("per", 0)) * p.affinity
		if d.has("min"): v = max(int(d["min"]), v)
		if d.has("max"): v = min(int(d["max"]), v)
		g.attack_target(p, v)
	elif op.has("dmgArt"):
		var d = op["dmgArt"]
		g.attack_target(p, int(d.get("b", 0)) + int(d.get("per", 0)) * p.equipped.size())
	elif op.has("dmgSupport"):
		var d = op["dmgSupport"]
		g.attack_target(p, int(d.get("b", 0)) + int(d.get("per", 0)) * ctx.support_used)
	elif op.has("dmgScaleArts"):
		g.attack_target(p, max(int(op["dmgScaleArts"].get("min", 0)), p.equipped.size()))
	elif op.has("scaleMana"):
		ctx.mana += _scale_value(g, p, ctx, op["scaleMana"])
	elif op.has("bonusIf"):
		var d = op["bonusIf"]
		if _stat(g, p, ctx, d.get("stat", "")) >= int(d.get("min", 1)):
			ctx.mana += int(d.get("add", 1))
	elif op.has("heal"):
		_heal(g, p, int(op["heal"]), op.get("who", "lowest"))
	elif op.has("vheal"):
		g.heal_village(int(op["vheal"]))
	elif op.has("vhealOrHeal"):
		g.heal_village(2)
	elif op.has("prevent"):
		_prevent(g, p, int(op["prevent"]), op.get("who", "village"))
	elif op.has("affinity"):
		p.affinity = min(3, p.affinity + int(op["affinity"]))
	elif op.has("slot"):
		p.slots = min(g.SLOT_CAP, p.slots + int(op["slot"]))
	elif op.has("draw"):
		_draw(g, p, int(op["draw"]))
	elif op.has("drawAll"):
		for q in g.living(): _draw(g, q, int(op["drawAll"]))
	elif op.has("discard"):
		_discard_self(g, p, int(op["discard"]))
	elif op.has("fromDiscard"):
		from_discard(g, p, ctx, op["fromDiscard"].get("cat", "Weapon"))
	elif op.has("tutorHand"):
		tutor(g, p, op["tutorHand"].get("cat", null), int(op["tutorHand"].get("max", 99)), true)
	elif op.has("tutor"):
		tutor(g, p, op["tutor"].get("cat", null), int(op["tutor"].get("max", 99)), false)
	elif op.has("optionalTutor"):
		tutor(g, p, op["optionalTutor"].get("cat", null), int(op["optionalTutor"].get("max", 99)), false)
	elif op.has("refire"):
		refire(g, p, ctx, int(op["refire"]))
	elif op.has("replayWeapon"):
		replay_weapon_from_discard(g, p, ctx)
	elif op.has("selfdmg"):
		p.hp -= int(op["selfdmg"])
	elif op.has("villageStrike"):
		# Armed Militia: _trigger_village(bonus). Encoded value is the non-ult total; +4 if ultimate.
		_trigger_village(g, p, int(op["villageStrike"]) - 2)
	elif op.has("triggerVillage"):
		_trigger_village(g, p, 0)               # Townsaver rider: 2 dmg, or 6 at Ultimate
	elif op.has("villageReduce"):
		g.village -= int(op["villageReduce"])   # Collateral Carnage: unpreventable village chip
	elif op.has("postponeBoss"):
		g._postpone_boss = true
	elif op.has("pacifier"):
		g.attack_target(p, max(0, g.PLAYER_HP - p.hp))
		g.anger = max(0, g.anger - 2)
	elif op.has("bloodfire"):
		var spend := min(2, max(0, p.hp - 1))
		p.hp -= spend
		g.attack_target(p, 2 + 2 * spend)
	elif op.has("bloodRitual"):
		p.hp -= 2
		_execute_or_aoe(g, p, 4)                # kill the biggest minion, else 4 AoE
	elif op.has("fateArbiter"):
		if not g.minions.is_empty(): _execute_or_aoe(g, p, 0)
		else: _draw(g, p, 1)
	elif op.has("genesisEdge"):
		if not g.minions.is_empty():
			for m in g.minions.duplicate(): g.boss_discard.append(m.card_name)
			g.minions.clear()
		else:
			for q in g.living(): _draw(g, q, 1)
	elif op.has("divineFavor"):
		var w: bool = _count_hand(p, "Weapon") > 0
		var a: bool = p.equipped.size() > 0
		ctx.mana += 1 + (1 if (w or a) else 0) + (1 if (w and a) else 0)
	elif op.has("tryAbility") or op.has("secretTechnique"):
		Abilities.use_ability(g, p, ctx)
	elif op.has("dmgOrDraw"):
		g.attack_target(p, int(op["dmgOrDraw"].get("dmg", 3)))
	elif op.has("destroyDraw"):
		if _destroy_one(g, p): _draw(g, p, 1)   # Composter / Worthy Sacrifice
	elif op.has("optionalDestroy"):
		_destroy_one(g, p, op["optionalDestroy"].get("cat", null))
	elif op.has("passWisp"):
		var nb = g.players[(p.pid + 1) % g.players.size()]
		nb.discard.append("Wandering Wisp")
	elif op.has("helpingHand") or op.has("encourage"):
		if not from_discard(g, p, ctx, "Weapon"): tutor(g, p, "Artifact", 4, true)
	elif op.has("reshuffleMarket"):
		g.build_market()
	elif op.has("optionalSelfDestroy") or op.has("slayer"):
		pass   # AI keeps the card / slayer already resolved as damage above
	else:
		g.warn_op("unknown:" + str(op.keys()))

# --- player helpers ---
static func _draw(g: Game, p, n: int) -> void:
	for _i in range(n):
		var c = p.draw_one()
		if c == null: break
		p.hand.append(c)

static func _discard_self(g: Game, p, n: int) -> void:
	for _i in range(min(n, p.hand.size())):
		p.discard.append(p.hand.pop_back())

static func _heal(g: Game, p, amount: int, who: String) -> void:
	match who:
		"self": g.heal_player(p, amount)
		"lowest": g.heal_player(g.lowest_heal_target(), amount)
		"lowest2":
			var first = g.lowest_heal_target()
			g.heal_player(first, amount)
			g.heal_player(g.lowest_heal_target(first), amount)
		_: g.heal_player(g.lowest_heal_target(), amount)   # "choose" -> auto lowest

static func _prevent(g: Game, p, amount: int, who: String) -> void:
	match who:
		"self": p.prevent += amount
		"village": g.village_prevent += amount
		_:  # "choose": shield the Village if it's under half, else the acting hero
			if g.village < g.village_max / 2: g.village_prevent += amount
			else: p.prevent += amount

## A card may be pulled back from discard at most ONCE per turn (mirrors the sim bug-fix that
## stops two mutual retrievers — e.g. 2x Arsenal Enforcer — from ping-ponging forever).
static func from_discard(g: Game, p, ctx, cat: String) -> bool:
	for name in p.discard:
		if CardDB.cat(name) == cat and not ctx.replayed.has(name):
			p.discard.erase(name)
			ctx.replayed.append(name)
			p.hand.append(name)
			return true
	return false

static func replay_weapon_from_discard(g: Game, p, ctx) -> bool:
	for name in p.discard:
		if CardDB.cat(name) == "Weapon" and not ctx.replayed.has(name):
			ctx.replayed.append(name)
			p.discard.erase(name)
			ctx.weapons_played += 1
			apply_player(g, p, ctx, CardDB.fx(name))
			return true
	return false

## Village-attack rider (Townsaver/Armed Militia): 2 dmg to an enemy, 6 at Ultimate, + bonus.
static func _trigger_village(g: Game, p, bonus: int) -> void:
	g.attack_target(p, (6 if p.ultimate() else 2) + bonus, false)

## Defeat the highest-HP minion (counting its HP as damage dealt); else deal `fallback` AoE.
static func _execute_or_aoe(g: Game, p, fallback: int) -> void:
	if not g.minions.is_empty():
		var m = g.minions[0]
		for x in g.minions:
			if x.hp > m.hp: m = x
		g.dmg_accum += m.hp
		g.minions.erase(m)
		g.boss_discard.append(m.card_name)
	elif fallback > 0:
		g.aoe(fallback)

## Deck-thinning: destroy (remove from game) a Mana Crystal from hand/discard if present.
## Mirrors the sim AI auto-pick (thin a basic Mana Crystal, else keep all). Returns true if removed.
static func _destroy_one(g: Game, p, only_cat = null) -> bool:
	for zone in [p.hand, p.discard]:
		for name in zone:
			if name == "Mana Crystal" and (only_cat == null or CardDB.cat(name) == only_cat):
				zone.erase(name)
				return true
	return false

static func refire(g: Game, p, ctx, n: int) -> int:
	var count := 0
	while count < n:
		var ready = null
		for eq in p.equipped:
			if eq.fires_from_turn <= p.turn_no and eq.card_name != "Timeless Talisman" \
					and not ctx.refired_eqs.has(eq):
				ready = eq
				break
		if ready == null: break
		ctx.refired_eqs.append(ready)   # mark before firing (no self-recursion)
		ctx.consumed = false
		apply_player(g, p, ctx, CardDB.fx(ready.card_name))
		if ctx.consumed and p.equipped.has(ready): p.equipped.erase(ready)
		count += 1
	return count

## Fetch the most expensive affordable All-class card of cat from the open supply (not the market).
static func tutor(g: Game, p, cat, max_cost: int, to_hand: bool) -> bool:
	var best := ""
	var best_cost := -1
	for name in CardDB.players:
		var c: Dictionary = CardDB.players[name]
		if c.get("cls", "All") != "All": continue
		if int(c.get("cost", 0)) <= 0 or int(c.get("cost", 0)) > max_cost: continue
		if cat != null and c.get("cat", "") != cat: continue
		if CardDB.is_tier2(c.get("tier", null)) and p.affinity < 2: continue
		if int(c.get("cost", 0)) > best_cost:
			best_cost = int(c.get("cost", 0)); best = name
	if best == "": return false
	if to_hand: p.hand.append(best)
	else: p.discard.append(best)
	return true

# --- scaling stats ---
static func _stat(g: Game, p, ctx, stat: String) -> int:
	match stat:
		"otherMana": return max(0, ctx.mana_cards_used - 1)
		"artifactsEq": return p.equipped.size()
		"minions": return g.minions.size()
		"supportHand": return _count_hand(p, "Support")
		"weaponsHand": return _count_hand(p, "Weapon")
		"weaponsDiscard": return _count_discard(p, "Weapon")
		"missingHp": return max(0, g.PLAYER_HP - p.hp)
		"anger": return g.anger
		"maxArts": return p.slots
		"aff": return p.affinity
		_: return 0

static func _scale_value(g: Game, p, ctx, d: Dictionary) -> int:
	var stat := _stat(g, p, ctx, d.get("stat", ""))
	var v: int = int(d.get("b", 0))
	if d.has("per"): v += int(d["per"]) * stat
	if d.has("step"):
		for threshold in d["step"]:
			if stat >= int(threshold): v += 1   # +1 per threshold met (approx. of sim step curve)
	return v

static func _count_hand(p, cat: String) -> int:
	var n := 0
	for name in p.hand:
		if CardDB.cat(name) == cat: n += 1
	return n

static func _count_discard(p, cat: String) -> int:
	var n := 0
	for name in p.discard:
		if CardDB.cat(name) == cat: n += 1
	return n

# ============================ BOSS / MINION / DISASTER ============================
static func resolve_boss(g: Game, card_name: String) -> void:
	for op in CardDB.bfx(card_name):
		_boss_op(g, op)

static func _boss_op(g: Game, op: Dictionary) -> void:
	if op.has("vdmg"):
		g.damage_village(int(op["vdmg"]))
	elif op.has("vdmgScaleMinions"):
		var d = op["vdmgScaleMinions"]
		g.damage_village(int(d.get("b", 0)) + int(d.get("per", 0)) * g.minions.size())
	elif op.has("pdmg"):
		_pdmg(g, op["pdmg"])
	elif op.has("manaDmg"):
		var t = _best(g.living(), "mana", g)
		if t != null: g.damage_player(t, _mana_in_hand(t))
	elif op.has("discard"):
		var d = op["discard"]
		for pl in g.rng.sample(g.living(), int(d.get("k", 1))):
			_discard_n(pl, int(d.get("n", 1)))
	elif op.has("discardCollective"):
		var n = op["discardCollective"]
		var count: int = g.living().size() if typeof(n) == TYPE_STRING else int(n)
		_discard_collective(g, count)
	elif op.has("discardEach"):
		for pl in g.living(): _discard_n(pl, int(op["discardEach"]))
	elif op.has("drawAll"):
		for pl in g.living(): _draw(g, pl, int(op["drawAll"]))
	elif op.has("loseAff"):
		var d = op["loseAff"]
		var targets = g.living() if d.get("who", "rand") == "all" else g.rng.sample(g.living(), int(d.get("k", 1)))
		for pl in targets: _lose_aff(pl)
	elif op.has("unequip"):
		var d = op["unequip"]
		var targets = g.living() if d.get("who", "rand") == "all" else g.rng.sample(g.living(), int(d.get("k", 1)))
		for pl in targets:
			if not pl.equipped.is_empty():
				var eq = pl.equipped.pop_back()
				pl.discard.append(eq.card_name)
	elif op.has("anger"):
		g.anger += int(op["anger"])
	elif op.has("noBuy"):
		g.no_buy = true
	elif op.has("minionsAttack"):
		for m in g.minions.duplicate(): resolve_boss(g, m.card_name)
	elif op.has("reviveMinion"):
		_revive_minions(g, int(op["reviveMinion"].get("n", 1)))
	elif op.has("tacticalRetreat"):
		var revived := 1
		if not g.minions.is_empty():
			var m = g.minions[0]
			for x in g.minions:
				if x.hp < m.hp: m = x
			g.minions.erase(m); g.boss_discard.append(m.card_name)
			revived = 2
		_revive_minions(g, revived)
	else:
		g.warn_op("boss:" + str(op.keys()))

static func _pdmg(g: Game, d: Dictionary) -> void:
	var who: String = d.get("who", "rand")
	var amt = d.get("amt", 0)
	if who == "all":
		var n := _amt(g, amt)
		for pl in g.living(): g.damage_player(pl, n)
	elif who == "rand":
		for pl in g.rng.sample(g.living(), int(d.get("k", 1))):
			g.damage_player(pl, _amt(g, amt))
	else:
		var t = _best(g.living(), who, g)
		if t != null: g.damage_player(t, _amt(g, amt))

static func _amt(g: Game, amt) -> int:
	if typeof(amt) == TYPE_STRING and amt == "livingHalf":
		return max(1, int(g.living().size() / 2))
	return int(amt)

## who in {highHp,lowHp,highAff,lowAff,mana(highest mana-in-hand)}
static func _best(pool: Array, who: String, g: Game):
	if pool.is_empty(): return null
	var best = pool[0]
	for q in pool:
		var better := false
		match who:
			"highHp": better = q.hp > best.hp
			"lowHp": better = q.hp < best.hp
			"highAff": better = q.affinity > best.affinity
			"lowAff": better = q.affinity < best.affinity
			"mana": better = _mana_in_hand(q) > _mana_in_hand(best)
		if better: best = q
	return best

static func _mana_in_hand(p) -> int:
	var n := 0
	for name in p.hand:
		if CardDB.cat(name) == "Mana": n += 1
	return n

static func _lose_aff(p) -> void:
	p.affinity = max(1, p.affinity - 1)

static func _discard_n(p, n: int) -> void:
	for _i in range(min(n, p.hand.size())):
		p.discard.append(p.hand.pop_back())

static func _discard_collective(g: Game, n: int) -> void:
	var pls := g.living()
	if pls.is_empty(): return
	for i in range(n):
		var p = pls[i % pls.size()]
		if not p.hand.is_empty(): p.discard.append(p.hand.pop_back())

static func _revive_minions(g: Game, n: int) -> void:
	var revived := 0
	for name in g.boss_discard.duplicate():
		if revived >= n: break
		if CardDB.boss.get(name, {}).get("cat", "") == "Minion":
			g.boss_discard.erase(name)
			g.minions.append(Game.Minion.new(name, g.minion_hp_for(name)))
			revived += 1
