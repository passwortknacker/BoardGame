extends SceneTree
## Behavioural assertion suite for the engine — asserts specific outcomes (not just "no crash").
## Run from the godot/ project dir:
##   godot --headless --script res://tests/run_headless.gd      (smoke + balance)
##   godot --headless --script res://tests/test_effects.gd      (this: correctness asserts)

var passed := 0
var failed := 0

func _initialize() -> void:
	CardDB.ensure_loaded()
	print("== engine assertion suite ==")
	_test_primitives()
	_test_combat_targeting()
	_test_prevention()
	_test_discard_cap()
	_test_market()
	_test_abilities()
	_test_boss_ops()
	_test_deferred_ops()
	_test_engine_misc()
	_test_save_restore()
	_test_end_conditions()
	print("== %d passed, %d failed ==" % [passed, failed])
	quit(1 if failed > 0 else 0)

# ---- helpers ----
func _mkgame(P := 2) -> Game:
	var g := Game.new(1)
	var clss := ["Cleric", "Paladin", "Ranger", "Wizard"]
	for i in range(P):
		var pl := Game.Player.new(i, clss[i], [])
		pl.hp = g.PLAYER_HP
		g.players.append(pl)
	g.boss = 60
	g.village = 40
	g.village_max = 40
	g.ctx = Game.Ctx.new()
	return g

func _apply(g: Game, p, fx: Array) -> void:
	Effects.apply_player(g, p, g.ctx, fx)

func eq(a, b, msg: String) -> void:
	if a == b: passed += 1
	else: failed += 1; print("  FAIL %s: got %s, expected %s" % [msg, str(a), str(b)])

func ok(cond: bool, msg: String) -> void:
	if cond: passed += 1
	else: failed += 1; print("  FAIL %s" % msg)

# ---- tests ----
func _test_primitives() -> void:
	var g := _mkgame()
	var p = g.players[0]
	_apply(g, p, [{"mana": 3}])
	eq(g.ctx.mana, 3, "mana +3")
	_apply(g, p, [{"dmg": 5}])
	eq(g.boss, 55, "dmg 5 to boss")
	p.hp = 4
	_apply(g, p, [{"heal": 4, "who": "self"}])
	eq(p.hp, 8, "heal self 4 (4->8)")
	p.hp = 9
	_apply(g, p, [{"heal": 5, "who": "self"}])
	eq(p.hp, g.PLAYER_HP, "heal caps at PLAYER_HP")
	g.village = 30
	_apply(g, p, [{"vheal": 6}])
	eq(g.village, 36, "village heal +6")
	_apply(g, p, [{"affinity": 1}])
	eq(p.affinity, 2, "affinity +1")
	_apply(g, p, [{"slot": 1}])
	eq(p.slots, 1, "slot +1")

func _test_combat_targeting() -> void:
	var g := _mkgame()
	var p = g.players[0]
	# single weak minion + boss: a non-finishing hit pressures the boss (sim targeting rule)
	g.minions.append(Game.Minion.new("Kobold", 4))
	_apply(g, p, [{"dmg": 2}])
	eq(g.boss, 58, "1 minion, non-lethal -> hit boss")
	eq(g.minions[0].hp, 4, "minion untouched when boss pressured")
	# lethal hit clears the lone minion
	_apply(g, p, [{"dmg": 5}])
	eq(g.minions.size(), 0, "lethal hit removes lone minion")
	eq(g.boss, 58, "boss unchanged on minion kill")
	# AoE hits boss and all minions
	g.minions.append(Game.Minion.new("Kobold", 4))
	g.minions.append(Game.Minion.new("Wyrm", 8))
	_apply(g, p, [{"aoe": 4}])
	eq(g.boss, 54, "aoe hits boss")
	eq(g.minions.size(), 1, "aoe kills the 4hp minion")

func _test_prevention() -> void:
	var g := _mkgame()
	var p = g.players[0]
	_apply(g, p, [{"prevent": 5, "who": "village"}])
	g.damage_village(8)
	eq(g.village, 37, "village prevent 5 absorbs (8 -> 3)")
	_apply(g, p, [{"prevent": 4, "who": "self"}])
	g.damage_player(p, 6)
	eq(p.hp, 8, "self prevent 4 absorbs (6 -> 2)")

func _test_discard_cap() -> void:
	var g := _mkgame()
	var p = g.players[0]
	p.discard = ["Longsword"]
	var first := Effects.from_discard(g, p, g.ctx, "Weapon")
	ok(first, "from_discard pulls a weapon to hand")
	eq(p.hand.size(), 1, "weapon moved to hand")
	p.discard.append("Longsword")        # it's back in discard somehow
	var second := Effects.from_discard(g, p, g.ctx, "Weapon")
	ok(not second, "same card can't be pulled twice in one turn (1x/turn cap)")

func _test_market() -> void:
	var g := _mkgame()
	g.build_market()
	eq(g.market.size(), 15, "market has 15 slots")
	var p = g.players[0]
	p.affinity = 1
	for s in g.market_choices(p, 99):
		ok(not CardDB.is_tier2(s["tier"]), "no tier-2 card offered at affinity 1")
	# buying replaces the slot with a valid card of the same (cat,tier)
	var slot = g.market[0]
	var before: String = slot["name"]
	g.replace_market_slot(slot)
	ok(CardDB.cat(slot["name"]) == slot["cat"], "replaced slot keeps its category")

func _test_abilities() -> void:
	var g := _mkgame()
	var cleric = g.players[0]
	g.players[1].hp = 3
	Abilities.use_ability(g, cleric, g.ctx)
	eq(g.players[1].hp, 7, "Cleric heals lowest hero 4 (3->7)")
	# Ranger ability: village heal + boss damage
	var g2 := _mkgame(3)
	g2.village = 30
	var ranger = g2.players[2]
	Abilities.use_ability(g2, ranger, g2.ctx)
	eq(g2.village, 32, "Ranger ability heals village 2")
	eq(g2.boss, 58, "Ranger ability deals 2 to boss")

func _test_boss_ops() -> void:
	var g := _mkgame()
	Effects.resolve_boss(g, "Claw Swipe")
	eq(g.village, 35, "Claw Swipe: village -5")
	var g2 := _mkgame()
	Effects.resolve_boss(g2, "Wide Swing")
	ok(g2.players[0].hp == 8 and g2.players[1].hp == 8, "Wide Swing: all heroes -2")

func _test_deferred_ops() -> void:
	var g := _mkgame()
	var p = g.players[0]
	# Blood Ritual with a minion: pay 2 HP, execute the biggest minion
	g.minions.append(Game.Minion.new("Wyrm", 8))
	_apply(g, p, [{"bloodRitual": true}])
	eq(p.hp, 8, "Blood Ritual costs 2 HP")
	eq(g.minions.size(), 0, "Blood Ritual executes the minion")
	# Divine Favor: +1, +1 if weapon-or-artifact, +1 if both
	var g2 := _mkgame()
	var p2 = g2.players[0]
	p2.hand = ["Longsword"]                 # a weapon in hand, no artifact equipped
	_apply(g2, p2, [{"divineFavor": true}])
	eq(g2.ctx.mana, 2, "Divine Favor: +2 with weapon only")
	# Pacifier reduces anger by 2
	var g3 := _mkgame()
	g3.anger = 5
	_apply(g3, g3.players[0], [{"pacifier": true}])
	eq(g3.anger, 3, "Pacifier: anger -2")

func _test_engine_misc() -> void:
	# Level-up: emptying the boss deck recycles the discard and bumps boss_level (+2 HP/minion).
	var g := _mkgame()
	g.boss_deck = []
	g.boss_discard = ["Kobold"]
	var flipped = g._flip()
	eq(g.boss_level, 1, "boss deck cycle -> level up")
	ok(flipped != null, "flip returns a card after recycle")
	eq(g.minion_hp_for("Kobold"), CardDB.minion_base_hp("Kobold") + 2, "minion HP +2 per boss level")
	# With 2+ minions on board, a non-lethal hit still strikes the lowest minion (clears crowds).
	var g2 := _mkgame()
	g2.minions.append(Game.Minion.new("Wyrm", 8))
	g2.minions.append(Game.Minion.new("Kobold", 4))
	_apply(g2, g2.players[0], [{"dmg": 3}])
	eq(g2.minions[1].hp, 1, "2+ minions: lowest minion takes the hit (4->1)")
	eq(g2.boss, 60, "boss untouched while a crowd of minions stands")
	# Healing revives a downed (0 HP) hero before topping up an injured one.
	var g3 := _mkgame()
	g3.players[0].hp = 0
	g3.players[1].hp = 6
	eq(g3.lowest_heal_target().pid, 0, "lowest_heal_target picks the downed hero first")

func _test_save_restore() -> void:
	# Advance a real game a couple of rounds, snapshot mid-game, then resume two ways and require
	# identical outcomes — proves save/restore + RNG-state capture give a deterministic resume.
	var g1 := Game.new(123)
	g1.setup(2)
	for _r in range(2):
		g1.player_turn(g1.players[0]); g1.player_turn(g1.players[1])
		g1.boss_turn(); g1.minions_attack()
	var snap := g1.snapshot()
	eq(snap["schema_version"], Game.SCHEMA_VERSION, "snapshot carries schema_version")
	# resume via in-memory restore
	var g2 := Game.new(999)
	ok(g2.restore(snap), "restore accepts a current-schema snapshot")
	# resume via a JSON round-trip (catches 64-bit RNG precision loss — state is stored as String)
	var g3 := Game.new(7)
	var reparsed = JSON.parse_string(JSON.stringify(snap))
	ok(g3.restore(reparsed), "restore from JSON round-trip")
	var a := g1.run()
	var b := g2.run()
	var c := g3.run()
	ok(a["result"] == b["result"] and a["round"] == b["round"] and a["boss"] == b["boss"],
		"in-memory restore resumes identically")
	ok(a["result"] == c["result"] and a["round"] == c["round"] and a["boss"] == c["boss"],
		"JSON-roundtrip restore resumes identically")
	# schema guard rejects an unknown future version
	var bad := snap.duplicate(); bad["schema_version"] = 999
	ok(not Game.new(1).restore(bad), "restore rejects a mismatched schema_version")

func _test_end_conditions() -> void:
	var g := _mkgame()
	g.boss = 3
	_apply(g, g.players[0], [{"dmg": 5}])
	ok(g.check_end() and g.result == "win", "boss <= 0 -> win")
	var g2 := _mkgame()
	g2.village = 2
	g2.damage_village(5)
	ok(g2.check_end() and g2.result == "village", "village <= 0 -> lose")
