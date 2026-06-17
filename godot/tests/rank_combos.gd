extends SceneTree
## Rank class combinations by win rate IN THE GODOT ENGINE — the plan's "regenerate balance numbers
## in the shipping engine, not the Python oracle". Prints the top 10 comps per player count.
## Run:  godot --headless --path godot --script res://tests/rank_combos.gd
##
## (Godot's RNG differs from Python's, so absolute numbers won't match sim/ exactly — that's
## expected; what matters is the engine's own balance picture.)

const GAMES := 30   # per combo (quick pass; raise for tighter numbers)

func _initialize() -> void:
	CardDB.ensure_loaded()
	print("== Godot engine combo ranking (%d games/combo) ==" % GAMES)
	for P in [2, 3, 4]:
		var combos := _combinations(Game.CLASSES, P)
		var scored: Array = []
		for combo in combos:
			scored.append([_winrate(P, combo), combo])
		scored.sort_custom(func(a, b): return a[0] > b[0])
		print("\n--- %d players (Boss %d, Village %d) — %d combos ---"
			% [P, 40 + 10 * P, 20 + 10 * P, combos.size()])
		for i in range(min(10, scored.size())):
			print("  %5.0f%%  %s" % [scored[i][0], ", ".join(scored[i][1])])
		var avg := 0.0
		for s in scored: avg += s[0]
		print("  all-combo avg: %.0f%%" % (avg / scored.size()))
	quit(0)

func _winrate(P: int, combo: Array) -> float:
	var team: Array = []
	for c in combo:
		team.append([c, Game.CLASS_STRAT[c]])
	var wins := 0
	for s in range(GAMES):
		var g := Game.new(s)
		g.setup(P, team)
		if g.run()["result"] == "win": wins += 1
	return 100.0 * wins / GAMES

## All k-combinations of `arr` (order-independent), like Python itertools.combinations.
func _combinations(arr: Array, k: int) -> Array:
	var out: Array = []
	var idx: Array = []
	for i in range(k): idx.append(i)
	var n := arr.size()
	while true:
		var combo: Array = []
		for i in idx: combo.append(arr[i])
		out.append(combo)
		var pos := k - 1
		while pos >= 0 and idx[pos] == n - k + pos:
			pos -= 1
		if pos < 0: break
		idx[pos] += 1
		for j in range(pos + 1, k):
			idx[j] = idx[j - 1] + 1
	return out
