extends Node
## Audio manager (autoload). Plays SFX by name on the SFX bus and music on the Music bus, with a
## small voice pool. SFX are loaded from assets/audio/sfx/<name>.wav if present; missing ones are
## logged once and no-op, so the game runs before real audio is sourced.

const SFX_DIR := "res://assets/audio/sfx"
const MUSIC_DIR := "res://assets/audio/music"
const VOICES := 12

var _sfx: Dictionary = {}                 # name -> AudioStream
var _pool: Array[AudioStreamPlayer] = []
var _next := 0
var _missing_logged := {}
var _music: AudioStreamPlayer

func _ready() -> void:
	_load_sfx()
	for i in range(VOICES):
		var p := AudioStreamPlayer.new()
		p.bus = "SFX"
		add_child(p)
		_pool.append(p)
	_music = AudioStreamPlayer.new()
	_music.bus = "Music"
	add_child(_music)

func _load_sfx() -> void:
	var dir := DirAccess.open(SFX_DIR)
	if dir == null: return
	for f in dir.get_files():
		if f.ends_with(".wav") or f.ends_with(".ogg"):
			var stream = load("%s/%s" % [SFX_DIR, f])
			if stream != null:
				_sfx[f.get_basename()] = stream

func play_sfx(name: String, pitch := 1.0, volume_db := 0.0) -> void:
	if not _sfx.has(name):
		if not _missing_logged.has(name):
			_missing_logged[name] = true
			push_warning("AudioManager: no SFX '%s' (drop %s/%s.wav)" % [name, SFX_DIR, name])
		return
	var p := _pool[_next]
	_next = (_next + 1) % _pool.size()
	p.stream = _sfx[name]
	p.pitch_scale = pitch
	p.volume_db = volume_db
	p.play()

func play_music(name: String) -> void:
	var path := "%s/%s.ogg" % [MUSIC_DIR, name]
	if not ResourceLoader.exists(path): return
	_music.stream = load(path)
	_music.play()
