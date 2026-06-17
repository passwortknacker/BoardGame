class_name Abilities
extends RefCounted
## Class abilities + ultimates (HANDOVER ability table). Normal from start; Ultimate at Affinity 3.
## Cost (3 Mana) is charged by the caller (AI / intent handler); this just applies the effect.

const ABILITY_COST := 3

static func use_ability(g: Game, p, ctx) -> void:
	var ult: bool = p.ultimate()
	match p.cls:
		"Ranger":
			g.heal_village(3 if ult else 2)
			g.attack_target(p, 3 if ult else 2, false)
		"Paladin":
			g.heal_player(g.lowest_heal_target(), 3 if ult else 2)
			g.attack_target(p, 3 if ult else 2, false)
		"Druid":
			g.heal_player(g.lowest_heal_target(), 3 if ult else 2)
			g.heal_village(3 if ult else 2)
		"Cleric":
			if ult:
				for q in _n_lowest(g, 2): g.heal_player(q, 4)
			else:
				g.heal_player(g.lowest_heal_target(), 4)
		"Wizard":
			Effects.refire(g, p, ctx, 2 if ult else 1)
		"Weaponmaster":
			var n := 2 if ult else 1
			for _i in range(n):
				if not Effects.replay_weapon_from_discard(g, p, ctx): break
		"Enchanter":
			if ult: Effects.tutor(g, p, "Artifact", 6, false)
			else: Effects.tutor(g, p, "Artifact", 4, true)
		"Blacksmith":
			if ult: Effects.tutor(g, p, "Weapon", 6, false)
			else: Effects.from_discard(g, p, ctx, "Weapon")
		"Bard":
			if ult: g.heal_player(g.lowest_heal_target(), 3)
			var c = p.draw_one()
			if c != null: p.hand.append(c)

static func _n_lowest(g: Game, n: int) -> Array:
	var injured: Array = []
	for q in g.players:
		if q.hp < g.PLAYER_HP: injured.append(q)
	var pool := injured if not injured.is_empty() else g.players.duplicate()
	pool.sort_custom(func(a, b): return a.hp < b.hp)
	return pool.slice(0, n)
