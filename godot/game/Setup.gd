extends Control
## Title / setup screen: pick player count + party, then enter the battle. Minimal but real — the
## menu→battle flow the full game keeps (later: class portraits, sim-ranked party picker, options).

var count := 2
var count_label: Label

func _ready() -> void:
	CardDB.ensure_loaded()
	var bg := ColorRect.new()
	bg.color = Color(0.06, 0.07, 0.10)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)

	_text("🐉  RED DRAGON", 56, Vector2(0, 120), 1920, Color(0.9, 0.4, 0.3))
	_text("Co-op deckbuilding boss-battler — vertical-slice build", 22, Vector2(0, 200), 1920, Color(0.8, 0.8, 0.85))
	_text("HOW MANY HEROES?", 22, Vector2(0, 320), 1920, Color(0.7, 0.7, 0.75))

	for i in range(3):
		var n := 2 + i
		var b := Button.new()
		b.text = str(n)
		b.size = Vector2(90, 90)
		b.position = Vector2(820 + i * 110, 370)
		b.add_theme_font_size_override("font_size", 32)
		b.pressed.connect(func(): AudioManager.play_sfx("ui_click"); _set_count(n))
		add_child(b)

	count_label = _text("", 22, Vector2(0, 490), 1920, Color(0.6, 0.85, 1.0))

	var start := Button.new()
	start.text = "START BATTLE  ▶"
	start.size = Vector2(320, 70)
	start.position = Vector2(800, 580)
	start.add_theme_font_size_override("font_size", 26)
	start.pressed.connect(_start)
	add_child(start)

	_text("Party is rolled from sim-ranked role comps. You control hero 1; the rest are AI allies.",
		16, Vector2(0, 680), 1920, Color(0.55, 0.55, 0.6))
	_set_count(2)

func _text(s: String, fsize: int, pos: Vector2, width: int, color := Color.WHITE) -> Label:
	var l := Label.new()
	l.text = s
	l.add_theme_font_size_override("font_size", fsize)
	l.add_theme_color_override("font_color", color)
	l.position = pos
	l.size = Vector2(width, fsize + 12)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	add_child(l)
	return l

func _set_count(n: int) -> void:
	count = n
	count_label.text = "%d heroes  —  Boss %d HP, Village %d HP" % [n, 40 + 10 * n, 20 + 10 * n]

func _start() -> void:
	AudioManager.play_sfx("ui_click")
	Session.player_count = count
	Session.team = null   # engine rolls a role comp
	get_tree().change_scene_to_file("res://game/Demo.tscn")
