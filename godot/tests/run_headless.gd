extends SceneTree
## Headless self-test + balance sample for the GDScript engine — the analogue of
## `python -m sim.validate` + `python tools/run_sim.py`. Run from the godot/ project dir:
##
##   godot --headless --script res://tests/run_headless.gd
##
## Checks: data loads, every card has an effect encoding, seeded determinism holds, smoke games
## run without errors, and reports win-rate samples + any approximated (unimplemented) ops.

const SMOKE := 200
const SAMPLE := 300

func _initialize() -> void:
	var ok := true
	print("== Red Dragon engine — headless self-test ==")

	if not CardDB.ensure_loaded():
		print("FAIL: could not load data/cards.json"); quit(1); return
	print("data v%s: %d player cards, %d boss-deck cards, %d classes"
		% [CardDB.version, CardDB.players.size(), CardDB.boss.size(), CardDB.classes.size()])

	# 1) coverage — every boss/minion/disaster card has a structured effect
	var no_bfx: Array = []
	for name in CardDB.boss:
		if (CardDB.bfx(name) as Array).is_empty(): no_bfx.append(name)
	if no_bfx.is_empty():
		print("OK   coverage: all %d boss-deck cards have bfx" % CardDB.boss.size())
	else:
		ok = false; print("FAIL coverage: boss cards without bfx: ", no_bfx)

	# 2) determinism — same seed reproduces the same outcome (compare fields, not Dictionary identity)
	var a := _one(3, 12345)
	var b := _one(3, 12345)
	if a["result"] == b["result"] and a["round"] == b["round"] and a["boss"] == b["boss"] and a["village"] == b["village"]:
		print("OK   determinism: seed 12345 reproduces (%s r%d)" % [a["result"], a["round"]])
	else:
		ok = false; print("FAIL determinism: ", a, " != ", b)

	# 3) smoke — run games across player counts without crashing; tally approximated ops
	var warns: Dictionary = {}
	for i in range(SMOKE):
		var P := 2 + (i % 3)
		var r := _one(P, i)
		for op in r["warnings"]:
			warns[op] = int(warns.get(op, 0)) + int(r["warnings"][op])
	print("OK   smoke: %d games ran to completion" % SMOKE)

	# 4) win-rate sample
	print("win-rate sample (%d games each, role comps):" % SAMPLE)
	for P in [2, 3, 4]:
		var wins := 0
		for s in range(SAMPLE):
			if _one(P, s)["result"] == "win": wins += 1
		print("   %dp: %d/%d (%d%%)" % [P, wins, SAMPLE, int(100.0 * wins / SAMPLE)])

	if warns.is_empty():
		print("OK   all effect ops fully implemented in smoke set")
	else:
		print("NOTE approximated/deferred ops (foundation scope): ", warns)

	print("== %s ==" % ("ALL CHECKS PASSED" if ok else "FAILURES ABOVE"))
	quit(0 if ok else 1)

func _one(P: int, seed_value: int) -> Dictionary:
	var g := Game.new(seed_value)
	g.setup(P)
	return g.run()
