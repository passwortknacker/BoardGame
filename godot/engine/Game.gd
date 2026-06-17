class_name Game
extends RefCounted
## Authoritative, headless rules engine — a GDScript port of the Python sim (sim/). No rendering;
## deterministic given a seed. The UI (game/) only reads this state and sends intents. Balance
## sweeps run many of these headless (see tests/run_headless.gd) — same code, zero drift.
##
## Decks/hands/discards hold card NAMES (String); CardDB resolves name -> data.

# ---------------- config (filled from CardDB.config) ----------------
var PLAYER_HP := 10
var HAND_SIZE := 5
var SLOT_CAP := 5
var ROUND_CAP := 16
var slot_cost: Array = [1, 2, 3, 4, 5]
var charge_turns := 1

const CLASSES := ["Ranger", "Paladin", "Druid", "Cleric", "Wizard",
	"Weaponmaster", "Enchanter", "Blacksmith", "Bard"]
const ROLE_CLASSES := {
	"caster": ["Wizard", "Enchanter"],
	"fighter": ["Weaponmaster", "Blacksmith", "Paladin", "Ranger"],
	"healer": ["Cleric", "Bard", "Druid"],
	"village": ["Druid", "Ranger"],
}
const ROLE_STRAT := {"caster": "caster", "fighter": "weapons", "healer": "healer", "village": "support"}
const CLASS_STRAT := {
	"Wizard": "caster", "Enchanter": "caster", "Cleric": "healer", "Bard": "healer",
	"Druid": "support", "Ranger": "support", "Paladin": "weapons",
	"Weaponmaster": "weapons", "Blacksmith": "weapons",
}
const DEFAULT_ROLES := {2: ["fighter", "village"], 3: ["caster", "fighter", "healer"],
	4: ["caster", "fighter", "healer", "village"]}

# ---------------- inner models ----------------
class Equip:
	var card_name: String
	var fires_from_turn: int
	func _init(n: String, f: int) -> void:
		card_name = n
		fires_from_turn = f

class Minion:
	var card_name: String
	var hp: int
	func _init(n: String, h: int) -> void:
		card_name = n
		hp = h

class Player:
	var pid: int
	var cls: String
	var strategy := "balanced"
	var hp := 10
	var affinity := 1
	var slots := 0
	var turn_no := 0
	var prevent := 0
	var deck: Array = []
	var discard: Array = []
	var hand: Array = []
	var equipped: Array = []   # Array[Equip]
	func _init(p: int, c: String, starter: Array) -> void:
		pid = p
		cls = c
		deck = starter.duplicate()
	func alive() -> bool: return hp > 0
	func ultimate() -> bool: return affinity >= 3
	func free_slots() -> int: return slots - equipped.size()
	func draw_one():
		if deck.is_empty():
			if discard.is_empty(): return null
			deck = discard         # no-shuffle recycle, in order
			discard = []
		return deck.pop_front()
	func draw_to_full(hand_size: int) -> void:
		while hand.size() < hand_size:
			var c = draw_one()
			if c == null: break
			hand.append(c)
	func gain_card(name: String, to_top := false) -> void:
		if to_top: deck.push_front(name)
		else: deck.push_back(name)

class Ctx:
	var mana := 0
	var mana_spent := 0
	var weapons_played := 0
	var artifacts_fired := 0
	var support_used := 0
	var mana_cards_used := 0
	var used_ability := false
	var consumed := false
	var fired_eqs: Array = []        # Array[Equip] fired this turn
	var refired_eqs: Array = []      # Array[Equip] re-fired this turn
	var replayed: Array = []         # Array[String] card names pulled from discard (1x/turn cap)

# ---------------- state ----------------
var rng: RNG
var players: Array = []             # Array[Player]
var village := 40
var village_max := 40
var village_prevent := 0
var boss := 60
var anger := 1
var anger_step := 1
var boss_level := 0
var boss_deck: Array = []           # Array[String]
var boss_discard: Array = []
var disaster_pile: Array = []
var disaster_discard: Array = []
var minions: Array = []             # Array[Minion]
var round_no := 0
var no_buy := false
var result := ""                    # "" | win | village | players | timeout
var ctx: Ctx
var market: Array = []              # Array[{cat,tier,name}]
var _postpone_boss := false
var warnings: Dictionary = {}       # unimplemented-op tally (op -> count)

# logging accumulators used by Effects for AI valuation/telemetry
var dmg_accum := 0
var heal_accum := 0

func _init(seed_value := 0) -> void:
	rng = RNG.new(seed_value)
	CardDB.ensure_loaded()
	_apply_config()

func _apply_config() -> void:
	var c: Dictionary = CardDB.config
	if c.is_empty(): return
	PLAYER_HP = int(c.get("player_hp", PLAYER_HP))
	HAND_SIZE = int(c.get("hand_size", HAND_SIZE))
	ROUND_CAP = int(c.get("round_cap", ROUND_CAP))
	slot_cost = c.get("slot_cost", slot_cost)
	charge_turns = int(c.get("charge_turns", charge_turns))

func warn_op(op: String) -> void:
	warnings[op] = int(warnings.get(op, 0)) + 1

# ================= setup =================
func build_starter(cls: String) -> Array:
	return (CardDB.starters.get(cls, []) as Array).duplicate()

func build_team(P: int, roles = null) -> Array:
	if roles == null: roles = DEFAULT_ROLES[P]
	var used := {}
	var team: Array = []
	for role in roles:
		var cands: Array = []
		for c in ROLE_CLASSES[role]:
			if not used.has(c): cands.append(c)
		if cands.is_empty(): cands = ROLE_CLASSES[role]
		var cls = rng.choice(cands)
		used[cls] = true
		team.append([cls, ROLE_STRAT[role]])
	return team

## team = Array of [cls, strategy]; if null a role-based comp is rolled.
func setup(P: int, team = null, boss_base := 40, boss_slope := 10,
		village_base := 20, village_slope := 10, boss_n := 12, minion_n := 7,
		disaster_n := 6) -> void:
	if team == null: team = build_team(P)
	for i in range(P):
		var pl := Player.new(i, team[i][0], build_starter(team[i][0]))
		pl.strategy = team[i][1]
		pl.hp = PLAYER_HP
		pl.draw_to_full(HAND_SIZE)
		players.append(pl)
	_build_boss_deck(boss_n, minion_n)
	disaster_pile = _build_disaster_pile(disaster_n)
	boss = boss_base + boss_slope * P
	village = village_base + village_slope * P
	village_max = village
	build_market()

func _build_boss_deck(n_boss: int, n_minion: int) -> void:
	var bosses := CardDB.names_in_category("Boss")
	var mins := CardDB.names_in_category("Minion")
	boss_deck = rng.sample(bosses, n_boss) + rng.sample(mins, n_minion)
	rng.shuffle(boss_deck)

func _build_disaster_pile(n: int) -> Array:
	var pile := rng.sample(CardDB.names_in_category("Disaster"), n)
	rng.shuffle(pile)
	return pile

# ================= market (randomized 15 tier slots) =================
func build_market() -> void:
	var spec: Array = CardDB.config.get("market_spec", [])
	var used := {}
	market = []
	for entry in spec:
		var category: String = entry[0]
		var t = entry[1]
		var key := "%s|%s" % [category, str(t)]
		var taken: Array = used.get(key, [])
		var pool := CardDB.pool_for(category, t)
		var choices: Array = []
		for n in pool:
			if not taken.has(n): choices.append(n)
		if choices.is_empty(): choices = pool
		var pick = rng.choice(choices)
		taken.append(pick)
		used[key] = taken
		market.append({"cat": category, "tier": t, "name": pick})

func replace_market_slot(slot: Dictionary) -> void:
	var on_offer := {}
	for s in market:
		if s != slot: on_offer[s["name"]] = true
	var pool := CardDB.pool_for(slot["cat"], slot["tier"])
	var choices: Array = []
	for n in pool:
		if not on_offer.has(n): choices.append(n)
	if choices.is_empty(): choices = pool
	if not choices.is_empty():
		slot["name"] = rng.choice(choices)

## Slots the player can buy now (affordable, category-matched, not tier-2-gated below Affinity 2).
func market_choices(p: Player, max_cost: int, category := "") -> Array:
	var out: Array = []
	for s in market:
		var name: String = s["name"]
		var cost := CardDB.cost(name)
		if cost <= 0 or cost > max_cost: continue
		if category != "" and CardDB.cat(name) != category: continue
		if CardDB.is_tier2(s["tier"]) and p.affinity < 2: continue
		out.append(s)
	return out

# ================= combat / damage / heal =================
func _absorb(p, amount: int, is_village: bool) -> int:
	if is_village:
		var used: int = min(village_prevent, amount)
		village_prevent -= used
		return amount - used
	var u: int = min(p.prevent, amount)
	p.prevent -= u
	return amount - u

func damage_player(p, amount: int) -> void:
	amount = _absorb(p, amount, false)
	if amount <= 0: return
	p.hp -= amount

func damage_village(amount: int) -> void:
	amount = _absorb(null, amount, true)
	if amount <= 0: return
	village -= amount

func attack_target(attacker, amount: int, prefer_minion := true) -> void:
	if amount <= 0: return
	if prefer_minion and not minions.is_empty():
		var m = minions[0]
		for x in minions:
			if x.hp < m.hp: m = x
		if minions.size() >= 2 or m.hp <= amount:
			m.hp -= amount
			dmg_accum += amount
			if m.hp <= 0:
				minions.erase(m)
				boss_discard.append(m.card_name)
			return
	boss -= amount
	dmg_accum += amount

func aoe(amount: int) -> void:
	boss -= amount
	dmg_accum += amount
	for m in minions.duplicate():
		m.hp -= amount
		dmg_accum += amount
		if m.hp <= 0:
			minions.erase(m)
			boss_discard.append(m.card_name)

func heal_player(p, amount: int) -> void:
	var before: int = p.hp
	p.hp = min(PLAYER_HP, p.hp + amount)
	heal_accum += p.hp - before

func heal_village(amount: int) -> void:
	var before := village
	village = min(village_max, village + amount)
	heal_accum += village - before

func living() -> Array:
	var out: Array = []
	for p in players:
		if p.alive(): out.append(p)
	return out

func lowest_heal_target(exclude = null):
	var injured: Array = []
	for q in players:
		if q.hp < PLAYER_HP and q != exclude: injured.append(q)
	var pool := injured
	if pool.is_empty():
		for q in players:
			if q != exclude: pool.append(q)
		if pool.is_empty(): pool = players
	var best = pool[0]
	for q in pool:
		if q.hp < best.hp: best = q
	return best

func minion_hp_for(card_name: String) -> int:
	return CardDB.minion_base_hp(card_name) + 2 * boss_level

# ================= end conditions =================
func check_end() -> bool:
	if boss <= 0: result = "win"; return true
	if village <= 0: result = "village"; return true
	var any_alive := false
	for p in players:
		if p.alive(): any_alive = true
	if not any_alive: result = "players"; return true
	return false

# ================= boss engine =================
func _flip():
	if boss_deck.is_empty():
		boss_level += 1
		anger_step += 1
		boss_deck = boss_discard
		boss_discard = []
		rng.shuffle(boss_deck)
	return boss_deck.pop_front() if not boss_deck.is_empty() else null

func _trigger_disaster() -> void:
	if disaster_pile.is_empty():
		if disaster_discard.is_empty(): return
		disaster_pile = disaster_discard
		disaster_discard = []
		rng.shuffle(disaster_pile)
	var card: String = disaster_pile.pop_front()
	Effects.resolve_boss(self, card)
	disaster_discard.append(card)

func boss_turn() -> void:
	if _postpone_boss and not boss_deck.is_empty():
		_postpone_boss = false
		var nxt: String = boss_deck.pop_front()
		var idx := (rng.randi_range(1, boss_deck.size()) if not boss_deck.is_empty() else 0)
		boss_deck.insert(idx, nxt)
	var card = _flip()
	if card == null: return
	if CardDB.boss[card].get("cat", "") == "Minion":
		minions.append(Minion.new(card, minion_hp_for(card)))
	else:
		Effects.resolve_boss(self, card)
		boss_discard.append(card)
	anger += anger_step
	if anger >= players.size() + 2:
		anger = 1
		_trigger_disaster()

func minions_attack() -> void:
	for m in minions.duplicate():
		if result != "": break
		Effects.resolve_boss(self, m.card_name)
		check_end()

# ================= turn / round loop =================
func player_turn(p) -> void:
	if not p.alive(): return
	p.turn_no += 1
	ctx = Ctx.new()
	for eq in p.equipped.duplicate():
		if not p.equipped.has(eq): continue
		if eq.fires_from_turn <= p.turn_no:
			ctx.consumed = false
			ctx.artifacts_fired += 1
			Effects.apply_player(self, p, ctx, CardDB.fx(eq.card_name))
			ctx.fired_eqs.append(eq)
			if ctx.consumed and p.equipped.has(eq): p.equipped.erase(eq)
			if check_end(): return
	AI.play_hand(self, p, ctx)
	if check_end(): return
	AI.do_buys(self, p, ctx)
	AI.do_equip(self, p, ctx)
	AI.draw_phase(self, p)

func boss_turns_for(P: int) -> int:
	return int(ceil(float(P) / 2.0))

## Joker goes to the best-engine hero: most artifacts, then affinity, then HP (single scalar key).
func _joker_rank(q) -> int:
	return q.equipped.size() * 10000 + q.affinity * 100 + q.hp

func run() -> Dictionary:
	var P := players.size()
	for rnd in range(1, ROUND_CAP + 1):
		round_no = rnd
		village_prevent = 0
		for pl in players: pl.prevent = 0
		no_buy = false
		var order: Array = []
		for pl in players:
			if pl.alive(): order.append(["P", pl])
		if P % 2 == 1:
			var alive := living()
			if not alive.is_empty():
				var joker = alive[0]
				for q in alive:
					if _joker_rank(q) > _joker_rank(joker): joker = q
				order.append(["P", joker])
		for _i in range(boss_turns_for(P)): order.append(["B", null])
		rng.shuffle(order)
		for entry in order:
			if result != "": break
			if entry[0] == "P": player_turn(entry[1])
			else: boss_turn()
			if check_end(): break
		if result != "": break
		minions_attack()
		if check_end(): break
	if result == "": result = "timeout"
	var alive_count := 0
	for p in players:
		if p.alive(): alive_count += 1
	return {"result": result, "round": round_no, "village": village, "boss": boss,
		"P": P, "alive": alive_count, "warnings": warnings}
