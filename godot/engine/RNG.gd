class_name RNG
extends RefCounted
## Deterministic, seeded RNG. The engine NEVER touches Godot's global RNG (Array.shuffle(),
## randi(), etc.) so that a (seed, intent-log) pair fully reproduces a game — the determinism
## contract the game plan requires for replays and bug reports.

var _rng := RandomNumberGenerator.new()

func _init(seed_value: int = 0) -> void:
	_rng.seed = seed_value

## Exact generator position — captured/restored for save+resume determinism.
func get_state() -> int:
	return _rng.state

func set_state(s: int) -> void:
	_rng.state = s

## Inclusive integer in [a, b].
func randi_range(a: int, b: int) -> int:
	return _rng.randi_range(a, b)

func randf() -> float:
	return _rng.randf()

## A random element of arr (null if empty).
func choice(arr: Array):
	if arr.is_empty():
		return null
	return arr[_rng.randi_range(0, arr.size() - 1)]

## In-place Fisher–Yates shuffle (deterministic for this RNG).
func shuffle(arr: Array) -> void:
	for i in range(arr.size() - 1, 0, -1):
		var j := _rng.randi_range(0, i)
		var tmp = arr[i]
		arr[i] = arr[j]
		arr[j] = tmp

## k distinct elements of arr (order randomized), like Python's random.sample.
func sample(arr: Array, k: int) -> Array:
	var pool := arr.duplicate()
	shuffle(pool)
	return pool.slice(0, min(k, pool.size()))
