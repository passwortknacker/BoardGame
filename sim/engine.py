"""Core game state + turn loop. Mechanics per HANDOVER.md "Design spine - LOCKED"."""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from collections import Counter

from .cards import Card

PLAYER_HP = 10          # design value (the 13 'easy mode' was reverted)
VILLAGE_HP = 40          # fallback; play_game sets village + village_max (20 + 10*players)
START_DECK_SIZE = 8
HAND_SIZE = 5
SLOT_CAP = 5
ROUND_CAP = 16

# Shared market = 15 fixed tier slots (Astro Knights style), mirrors the online test game's
# game/game.js MARKET_SPEC. Each slot is seeded with a RANDOM card of its (category, tier);
# buying a card replaces only that slot with a fresh random pick. Players can only buy what is
# currently on offer — there is NO free pick from the whole supply (that was the old AI model).
MARKET_SPEC = [
    ("Mana", "Moderate"), ("Mana", "Moderate"), ("Mana", "Greater"), ("Mana", "Greater"),
    ("Weapon", "Light"), ("Weapon", "Light"), ("Weapon", "Heavy"), ("Weapon", "Heavy"),
    ("Artifact", "Ancient"), ("Artifact", "Ancient"), ("Artifact", "Common"), ("Artifact", "Common"),
    ("Support", None), ("Support", None), ("Support", None),
]


@dataclass
class MarketSlot:
    cat: str
    tier: str | None
    card: Card


def boss_hp(players: int) -> int:
    return 50 + 15 * players


@dataclass
class Equipped:
    card: Card
    fires_from_turn: int     # this artifact fires on the player's turn >= this number


@dataclass
class Minion:
    card: Card
    hp: int


class Player:
    def __init__(self, pid: int, cls: str, starter: list[Card]):
        self.pid = pid
        self.cls = cls
        self.hp = PLAYER_HP
        self.affinity = 1
        self.slots = 0                       # purchased artifact slots (0..5)
        self.deck: list[Card] = list(starter)
        self.discard: list[Card] = []
        self.hand: list[Card] = []
        self.equipped: list[Equipped] = []   # artifacts in slots
        self.turn_no = 0
        self.prevent = 0                      # damage-prevention tokens on this player (this round)

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def ultimate(self) -> bool:
        return self.affinity >= 3

    # ---- no-shuffle deck: recycle discard in order when deck empties ----
    def draw_one(self) -> Card | None:
        if not self.deck:
            if not self.discard:
                return None
            self.deck = self.discard           # in order, no shuffle
            self.discard = []
        return self.deck.pop(0)

    def draw_to_full(self):
        while len(self.hand) < HAND_SIZE:
            c = self.draw_one()
            if c is None:
                break
            self.hand.append(c)

    def gain_card(self, card: Card, to_deck_top: bool = False):
        """Bought/gained cards go UNDER the deck by default (no-shuffle rule)."""
        if to_deck_top:
            self.deck.insert(0, card)
        else:
            self.deck.append(card)

    def free_slots(self) -> int:
        return self.slots - len(self.equipped)


@dataclass
class EffectContext:
    """Per-play scratch space for 'this turn' scaling and play resolution."""
    mana: int = 0
    mana_spent: int = 0
    weapons_played: int = 0
    artifacts_fired: int = 0
    support_used: int = 0
    mana_cards_used: int = 0
    used_ability: bool = False
    consumed: bool = False        # destroys played card or equipped artifact (removed from game)
    fired_artifact_eqs: set = field(default_factory=set)   # scheduled turn-start fires
    refired_artifact_eqs: set = field(default_factory=set) # extra triggers (Wizard, Arcane Retrieval, …)
    replayed_from_discard: set = field(default_factory=set)  # cards pulled back from discard (1×/turn cap)


class Game:
    def __init__(self, players: list[Player], boss_deck: list[Card], cards: dict[str, Card],
                 rng: random.Random, trace: bool = False):
        self.players = players
        self.cards = cards
        self.rng = rng
        self.trace = trace
        self.village = VILLAGE_HP
        self.village_max = VILLAGE_HP       # scaled by play_game (20 + 10*players)
        self.village_prevent = 0
        self.boss = boss_hp(len(players))
        self.anger = 1
        self.boss_deck = boss_deck          # Boss + Minion cards only (next card telegraphed)
        self.boss_discard: list[Card] = []
        self.disaster_pile: list[Card] = []  # separate hidden pile, drawn on the Anger trigger
        self.disaster_discard: list[Card] = []
        self.boss_level = 0                 # +1 each time the boss deck cycles (Level Up)
        self.anger_step = 1                 # Anger gained per boss turn (rises with Level Up)
        self.minions: list[Minion] = []
        self.round = 0
        self.no_buy = False                 # Trade Block disaster
        self.result: str | None = None      # 'win' | 'village' | 'players' | 'timeout'
        self.stats = Counter()              # per-card play/buy counts + damage tallies
        self.ctx = EffectContext()
        self.verbose = False                # detailed play-by-play logging (to vlines)
        self.focal = 0                      # player id to log in full detail
        self.vlines: list[str] = []
        self._dmg_accum = 0                 # damage to enemies during the current card play (logging)
        self._heal_accum = 0                # healing during the current card play (logging)
        self.chooser = None                 # optional callable(prompt, options, labeler)->option (CLI only)
        # tempo knobs (defaults = locked rules): cumulative slot cost 1/2/3/4/5, 1-turn charge
        self.slot_cost = [1, 2, 3, 4, 5]
        self.charge_turns = 1
        # randomized 15-slot shared market (mirrors the online test game / game.js)
        self.market: list[MarketSlot] = []
        self.build_market()

    def choose(self, prompt, options, default=None, labeler=None):
        """Pick an option. With no chooser set (sims) -> the auto default. CLI sets a chooser
        so the human picks (e.g. which artifact to re-fire, which Supply card to fetch)."""
        if not options:
            return default
        if self.chooser is None or len(options) == 1:
            return default if default is not None else options[0]
        return self.chooser(prompt, options, labeler or (lambda o: str(o)))

    # ---------- logging ----------
    def log(self, msg: str):
        if self.trace:
            print(f"  R{self.round} {msg}")
        if self.verbose:
            self.vlines.append(f"      · {msg}")

    def vlog(self, msg: str):
        if self.verbose:
            self.vlines.append(msg)

    def focused(self, p) -> bool:
        return self.verbose and p is not None and p.pid == self.focal

    # ---------- damage application ----------
    def damage_player(self, p: Player, amount: int):
        amount = self._absorb(p, amount, village=False)
        if amount <= 0:
            return
        p.hp -= amount
        self.log(f"P{p.pid} takes {amount} (hp={p.hp})")

    def damage_village(self, amount: int):
        amount = self._absorb(None, amount, village=True)
        if amount <= 0:
            return
        self.village -= amount
        self.log(f"Village takes {amount} (hp={self.village})")

    def _absorb(self, p: Player | None, amount: int, village: bool) -> int:
        if village:
            used = min(self.village_prevent, amount)
            self.village_prevent -= used
            return amount - used
        used = min(p.prevent, amount)
        p.prevent -= used
        return amount - used

    def attack_target(self, attacker: Player, amount: int, prefer_minion=True) -> None:
        """Player-sourced damage: kill a worthwhile minion, else hit the boss."""
        if amount <= 0:
            return
        if prefer_minion and self.minions:
            m = min(self.minions, key=lambda x: x.hp)   # target the lowest-HP minion
            # clear minions when they pile up (>=2) or when this hit finishes one; their
            # accumulating attacks kill the team otherwise. Else pressure the boss (win condition).
            if len(self.minions) >= 2 or m.hp <= amount:
                m.hp -= amount
                self._dmg_accum += amount
                self.log(f"P{attacker.pid} hits minion {m.card.name} ({m.hp})")
                if m.hp <= 0:
                    self.minions.remove(m)
                    self.log(f"  minion {m.card.name} defeated")
                    self._on_minion_killed(attacker, m)
                return
        self.boss -= amount
        self._dmg_accum += amount
        self.stats["boss_dmg"] += amount
        self.log(f"P{attacker.pid} hits boss ({self.boss})")

    def aoe(self, attacker: Player, amount: int):
        self.boss -= amount
        self._dmg_accum += amount
        for m in list(self.minions):
            m.hp -= amount
            self._dmg_accum += amount
            if m.hp <= 0:
                self.minions.remove(m)
                self._on_minion_killed(attacker, m)

    def _on_minion_killed(self, attacker: Player, m: Minion):
        # defeated minions go to the boss discard (revivable by Reawakening / Tactical Retreat)
        self.boss_discard.append(m.card)

    # ---------- heal ----------
    def heal_player(self, p: Player, amount: int):
        before = p.hp
        p.hp = min(PLAYER_HP, p.hp + amount)
        self._heal_accum += p.hp - before

    def heal_village(self, amount: int):
        before = self.village
        self.village = min(self.village_max, self.village + amount)
        self._heal_accum += self.village - before

    def lowest_heal_target(self, exclude: Player | None = None) -> Player:
        """Lowest-HP hero including downed (0 HP) players — healing revives them first."""
        targets = [q for q in self.players if q.hp < PLAYER_HP and q is not exclude]
        if targets:
            return min(targets, key=lambda q: q.hp)
        pool = [q for q in self.players if q is not exclude] or self.players
        return min(pool, key=lambda q: q.hp)

    # ---------- supply ----------
    def supply_choices(self, p: Player, max_cost: int, category: str | None = None) -> list[Card]:
        """The shared market = only 'All'-class player cards. Class-specific cards (Volley, Bow,
        Grimoire, ...) are STARTERS, not buyable — they exist only in starting decks."""
        out = []
        for c in self.cards.values():
            if not c.is_player_card:
                continue
            if c.cls != "All":                      # class cards are starters, never in the market
                continue
            if category and c.category != category:
                continue
            if c.cost is None or c.cost <= 0 or c.cost > max_cost:   # 0-cost cards are starters, not buyable
                continue
            if c.tier2 and p.affinity < 2:
                continue
            out.append(c)
        return out

    # ---------- randomized tier-slot market (mirrors the online test game) ----------
    def _pool_for(self, cat: str, tier: str | None) -> list[Card]:
        """All 'All'-class buyable cards of a (category, tier) — the candidates for a slot."""
        out = []
        for c in self.cards.values():
            if c.cls != "All" or c.category != cat or not c.cost or c.cost <= 0:
                continue
            if c.tier != tier:
                continue
            out.append(c)
        return out

    def build_market(self):
        """Seed the 15 shared slots with random cards (no dup within a (cat, tier) group)."""
        used: dict[tuple, list[str]] = {}
        self.market = []
        for cat, tier in MARKET_SPEC:
            taken = used.setdefault((cat, tier), [])
            pool = self._pool_for(cat, tier)
            choices = [c for c in pool if c.name not in taken] or pool
            pick = self.rng.choice(choices)
            taken.append(pick.name)
            self.market.append(MarketSlot(cat, tier, pick))

    def replace_market_slot(self, slot: MarketSlot):
        """After a buy, refill that slot with a fresh random card not already on offer."""
        on_offer = {s.card.name for s in self.market if s is not slot}
        pool = self._pool_for(slot.cat, slot.tier)
        choices = [c for c in pool if c.name not in on_offer] or pool
        if choices:
            slot.card = self.rng.choice(choices)

    def market_choices(self, p: Player, max_cost: int, category: str | None = None) -> list[MarketSlot]:
        """Slots a player can actually buy right now: affordable, category-matched, and not
        tier-2-gated below Affinity 2. The constrained replacement for supply_choices on BUYS."""
        out = []
        for s in self.market:
            c = s.card
            if c.cost is None or c.cost <= 0 or c.cost > max_cost:
                continue
            if category and c.category != category:
                continue
            if c.tier2 and p.affinity < 2:
                continue
            out.append(s)
        return out

    # ---------- end conditions ----------
    def check_end(self) -> bool:
        if self.boss <= 0:
            self.result = "win"
            return True
        if self.village <= 0:
            self.result = "village"
            return True
        if all(not pl.alive for pl in self.players):
            self.result = "players"
            return True
        return False
