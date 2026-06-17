class_name Juice
extends RefCounted
## Reusable "game feel" helpers (tweens/particles-lite) for Hearthstone-tier juice. Static so any
## scene can call Juice.pop(node), Juice.shake(node), Juice.float_text(...), etc. Real particle
## systems (impact bursts, card-trail) come with the art pass; these are the motion primitives.

const HOVER_SCALE := 1.12

static func ensure_pivot(c: Control) -> void:
	c.pivot_offset = c.size / 2.0

static func hover_in(c: Control) -> void:
	ensure_pivot(c)
	var t := c.create_tween().set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	t.tween_property(c, "scale", Vector2(HOVER_SCALE, HOVER_SCALE), 0.12)
	t.parallel().tween_property(c, "position:y", c.position.y - 24.0, 0.12)

static func hover_out(c: Control, base_y: float) -> void:
	var t := c.create_tween().set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	t.tween_property(c, "scale", Vector2.ONE, 0.12)
	t.parallel().tween_property(c, "position:y", base_y, 0.12)

## Quick scale punch (e.g. on play / on damage taken).
static func pop(c: Control, strength := 1.25) -> void:
	ensure_pivot(c)
	c.scale = Vector2(strength, strength)
	c.create_tween().set_trans(Tween.TRANS_ELASTIC).set_ease(Tween.EASE_OUT) \
		.tween_property(c, "scale", Vector2.ONE, 0.35)

## Screen/element shake by jittering position around its current value.
static func shake(node: Control, strength := 12.0, dur := 0.3) -> void:
	var origin := node.position
	var t := node.create_tween()
	var steps := 6
	for i in range(steps):
		var falloff := strength * (1.0 - float(i) / steps)
		var off := Vector2(randf_range(-falloff, falloff), randf_range(-falloff, falloff))
		t.tween_property(node, "position", origin + off, dur / steps)
	t.tween_property(node, "position", origin, dur / steps)

## Spawn a floating, fading combat-text label on `parent` at local `pos`.
static func float_text(parent: Control, pos: Vector2, text: String, color: Color, size := 34) -> void:
	var l := Label.new()
	l.text = text
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_outline_color", Color.BLACK)
	l.add_theme_constant_override("outline_size", 6)
	l.add_theme_font_size_override("font_size", size)
	l.position = pos
	l.z_index = 100
	parent.add_child(l)
	var t := l.create_tween()
	t.tween_property(l, "position:y", pos.y - 70.0, 0.8).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	t.parallel().tween_property(l, "modulate:a", 0.0, 0.8)
	t.tween_callback(l.queue_free)

## Fly a node to a target position, then call `on_done` (Callable or empty).
static func fly_to(node: Control, target: Vector2, dur := 0.3, on_done := Callable()) -> void:
	var t := node.create_tween().set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
	t.tween_property(node, "position", target, dur)
	if on_done.is_valid():
		t.tween_callback(on_done)
