class_name CardDB
extends RefCounted
## Single content source: loads data/cards.json (generated from Cards_Data.xlsx via
## tools/export_godot_data.py) into static tables. Cards are referenced everywhere by NAME
## (String); this resolves name -> data. Static (not an autoload) so it works identically in the
## game scene and in a bare `--headless --script` test loop.

const DATA_PATH := "res://data/cards.json"

static var loaded := false
static var version := ""
static var config: Dictionary = {}
static var classes: Array = []
static var players: Dictionary = {}     # name -> {cat,cost,tier,cls,text,fx}
static var boss: Dictionary = {}        # name -> {cat,text,bfx,(hp)}
static var starters: Dictionary = {}    # class -> Array[String]

static func ensure_loaded() -> bool:
	if loaded: return true
	return load_data()

static func load_data() -> bool:
	if not FileAccess.file_exists(DATA_PATH):
		push_error("CardDB: %s not found — run `python tools/export_godot_data.py`." % DATA_PATH)
		return false
	var data = JSON.parse_string(FileAccess.get_file_as_string(DATA_PATH))
	if typeof(data) != TYPE_DICTIONARY:
		push_error("CardDB: cards.json did not parse to a Dictionary.")
		return false
	version = data.get("version", "")
	config = data.get("config", {})
	classes = data.get("classes", [])
	players = data.get("players", {})
	boss = data.get("boss", {})
	starters = data.get("starters", {})
	loaded = true
	return true

# ---- player-card lookups ----
static func is_player(name: String) -> bool: return players.has(name)
static func cat(name: String) -> String:     return _entry(name).get("cat", "")
static func cost(name: String) -> int:        return int(players.get(name, {}).get("cost", 0))
static func tier(name: String):               return players.get(name, {}).get("tier", null)
static func cls(name: String) -> String:      return players.get(name, {}).get("cls", "All")
static func fx(name: String) -> Array:        return players.get(name, {}).get("fx", [])
static func text(name: String) -> String:     return _entry(name).get("text", "")

# ---- boss-deck lookups ----
static func is_boss_card(name: String) -> bool: return boss.has(name)
static func bfx(name: String) -> Array:         return boss.get(name, {}).get("bfx", [])
static func minion_base_hp(name: String) -> int: return int(boss.get(name, {}).get("hp", 0))

static func is_tier2(t) -> bool:
	return t != null and (config.get("tier2", []) as Array).has(t)

static func _entry(name: String) -> Dictionary:
	if players.has(name): return players[name]
	if boss.has(name): return boss[name]
	return {}

## All buyable All-class player-card names of a (category, tier) — the pool for one market slot.
static func pool_for(category: String, t) -> Array:
	var out: Array = []
	for name in players:
		var c: Dictionary = players[name]
		if c.get("cls", "All") != "All": continue
		if c.get("cat", "") != category: continue
		if int(c.get("cost", 0)) <= 0: continue
		if c.get("tier", null) != t: continue
		out.append(name)
	return out

static func names_in_category(category: String) -> Array:
	var out: Array = []
	for name in boss:
		if boss[name].get("cat", "") == category: out.append(name)
	return out
