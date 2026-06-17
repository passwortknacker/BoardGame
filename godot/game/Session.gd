extends Node
## Autoload "Session": carries the chosen setup from the menu into the battle scene (and will hold
## run/meta state later). Kept tiny and serializable-friendly.

var player_count := 2
var team = null   # Array of [cls, strategy], or null to let the engine roll a role comp

func reset() -> void:
	player_count = 2
	team = null
