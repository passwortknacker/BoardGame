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

## Drag a card above this Y (viewport coords) to play it; release lower snaps it back.
const PLAY_THRESHOLD := 640.0
const DRAG_DEADZONE := 8.0

var card_name := ""
var base_y := 0.0
var _dragging := false
var _moved := false
var _home := Vector2.ZERO
var _grab := Vector2.ZERO

func _ready() -> void:
	custom_minimum_size = Vector2(W, H)
	size = Vector2(W, H)
	mouse_filter = Control.MOUSE_FILTER_STOP
	_build()
	mouse_entered.connect(func(): if not _dragging: Juice.hover_in(self))
	mouse_exited.connect(func(): if not _dragging: Juice.hover_out(self, base_y))
	gui_input.connect(_on_gui_input)

func _on_gui_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT and e.pressed:
		_dragging = true
		_moved = false
		_home = Vector2(position.x, base_y)
		_grab = get_global_mouse_position() - position
		z_index = 50

## While dragging we listen globally so motion/release outside the card still register.
func _input(e: InputEvent) -> void:
	if not _dragging:
		return
	if e is InputEventMouseMotion:
		var target := get_global_mouse_position() - _grab
		if target.distance_to(_home) > DRAG_DEADZONE:
			_moved = true
		position = target
	elif e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT and not e.pressed:
		_dragging = false
		z_index = 0
		# a quick click (no real drag) OR a drag up into the play zone = play
		if not _moved or position.y < PLAY_THRESHOLD:
			AudioManager.play_sfx("ui_click")
			pressed.emit(card_name)
		else:
			create_tween().set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT) \
				.tween_property(self, "position", _home, 0.18)

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
