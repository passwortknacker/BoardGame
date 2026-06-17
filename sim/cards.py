"""Card model + loader. Cards_Data.xlsx is the single source of truth."""
import os
from dataclasses import dataclass, field
import openpyxl

XLSX = os.path.join(os.path.dirname(__file__), "..", "data", "Cards_Data.xlsx")

# Player-buyable supply categories (Boss/Minion/Disaster/Village are not bought).
PLAYER_CATEGORIES = {"Mana", "Weapon", "Artifact", "Support"}
BOSS_CATEGORIES = {"Boss", "Minion", "Disaster"}

# Tier-2 (unlocked at Affinity 2). Mana is never gated.
TIER2 = {"Greater", "Heavy", "Ancient"}


@dataclass
class Card:
    name: str
    category: str
    tier: str | None
    cls: str           # "All" or a class name
    cost: int | None   # mana cost (None for boss-deck cards / Village)
    text: str

    @property
    def is_player_card(self) -> bool:
        return self.category in PLAYER_CATEGORIES

    @property
    def tier2(self) -> bool:
        """Requires Affinity >= 2 to buy (Greater Mana / Heavy Weapon / Ancient Artifact)."""
        return self.tier in TIER2

    @property
    def minion_hp(self) -> int | None:
        if self.category == "Minion" and self.tier and "HP" in str(self.tier):
            return int(str(self.tier).split()[0])
        return None

    def __repr__(self):
        c = "-" if self.cost is None else self.cost
        return f"<{self.category}:{self.name} ({c})>"


def load_cards(path: str = XLSX) -> dict[str, Card]:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["Cards"]
    cards: dict[str, Card] = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        name = row[0]
        if not name:
            continue
        name = str(name).strip()
        cost = row[4]
        cost = int(cost) if isinstance(cost, (int, float)) else None
        cards[name] = Card(
            name=name,
            category=str(row[1]).strip() if row[1] else "",
            tier=(str(row[2]).strip() if row[2] not in (None, "None") else None),
            cls=str(row[3]).strip() if row[3] else "All",
            cost=cost,
            text=(str(row[5]).replace("\n", " ").strip() if row[5] else ""),
        )
    return cards


def by_category(cards: dict[str, Card]) -> dict[str, list[Card]]:
    out: dict[str, list[Card]] = {}
    for c in cards.values():
        out.setdefault(c.category, []).append(c)
    return out


if __name__ == "__main__":
    cards = load_cards()
    cat = by_category(cards)
    print(f"loaded {len(cards)} cards")
    for k in sorted(cat):
        print(f"  {k:10} {len(cat[k])}")
