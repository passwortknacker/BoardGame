class_name CardView
extends Control
## A single card's visual. Procedurally drawn (StyleBox frame, category-tinted art band, cost badge,
## name/type/text) so it looks presentable before real card art exists — drop a texture into the art
## band later. Handles hover-lift and click; the controller wires `pressed` to an engine intent.

signal pressed(card_name: String)

const W := 150.0
const H := 210.0

const CAT_COLOR := {
	"Mana": Color(0.20, 0.45, 0.92),
	"Weapon": Color(0.85, 0.32, 0.22),
	"Artifact": Color(0.62, 0.32, 0.82),
	"Support": Color(0.26, 0.70, 0.42),
}

var card_name := ""
var base_y := 0.0

func _ready() -> void:
	custom_minimum_size = Vector2(W, H)
	size = Vector2(W, H)
	mouse_filter = Control.MOUSE_FILTER_STOP
	_build()
	mouse_entered.connect(func(): Juice.hover_in(self))
	mouse_exited.connect(func(): Juice.hover_out(self, base_y))
	gui_input.connect(_on_gui_input)

func _on_gui_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT and e.pressed:
		AudioManager.play_sfx("ui_click")
		pressed.emit(card_name)

func _build() -> void:
	var cat := CardDB.cat(card_name)
	var accent: Color = CAT_COLOR.get(cat, Color(0.5, 0.5, 0.55))

	var bg := Panel.new()
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.10, 0.11, 0.14)
	sb.set_corner_radius_all(12)
	sb.set_border_width_all(3)
	sb.border_color = accent
	sb.shadow_color = Color(0, 0, 0, 0.5)
	sb.shadow_size = 6
	bg.add_theme_stylebox_override("panel", sb)
	add_child(bg)

	var art := ColorRect.new()
	art.color = accent.darkened(0.15)
	art.position = Vector2(10, 30)
	art.size = Vector2(W - 20, 88)
	add_child(art)

	var nm := Label.new()
	nm.text = card_name
	nm.add_theme_font_size_override("font_size", 13)
	nm.add_theme_color_override("font_outline_color", Color.BLACK)
	nm.add_theme_constant_override("outline_size", 4)
	nm.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	nm.position = Vector2(8, 7)
	nm.size = Vector2(W - 16, 20)
	add_child(nm)

	var cost := CardDB.cost(card_name)
	if cost > 0:
		var badge := Panel.new()
		var bsb := StyleBoxFlat.new()
		bsb.bg_color = Color(0.13, 0.20, 0.42)
		bsb.set_corner_radius_all(16)
		bsb.set_border_width_all(2)
		bsb.border_color = Color(0.6, 0.8, 1.0)
		badge.add_theme_stylebox_override("panel", bsb)
		badge.position = Vector2(6, 6)
		badge.size = Vector2(30, 30)
		add_child(badge)
		var cl := Label.new()
		cl.text = str(cost)
		cl.add_theme_font_size_override("font_size", 16)
		cl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		cl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		cl.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		badge.add_child(cl)

	var tp := Label.new()
	tp.text = cat.to_upper()
	tp.add_theme_font_size_override("font_size", 10)
	tp.add_theme_color_override("font_color", accent.lightened(0.3))
	tp.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	tp.position = Vector2(8, 120)
	tp.size = Vector2(W - 16, 14)
	add_child(tp)

	var tx := Label.new()
	tx.text = CardDB.text(card_name)
	tx.add_theme_font_size_override("font_size", 10)
	tx.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	tx.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	tx.position = Vector2(10, 138)
	tx.size = Vector2(W - 20, H - 148)
	add_child(tx)
