import random
from collections import deque

random.seed(7)
N = 40000
TURNS = 8

def card(m=0, d=0):
    return (m, d)

STARTER = [card(1)]*5 + [card(0)] + [card(0,1)]*2   # 5 mana, 1 support, 2 weapon(1 dmg)

# representative shop
MANA_ORB = card(3)        # +3 mana, cost 3 (Moderate, ungated)
GREATER  = card(3)        # +3 mana, cost 4 (Affinity 2)
# weapons: (dmg, cost, heavy?)
WEAPONS = [(9,8,True),(7,8,True),(6,5,False),(2,4,False),(2,3,False),(2,2,False)]

def best_weapon(mana, aff):
    best=None
    for dmg,cost,heavy in WEAPONS:
        if cost<=mana and (not heavy or aff>=2):
            if best is None or dmg>best[0]:
                best=(dmg,cost)
    return best

def run(strategy):
    agg=[ {'m':0,'d':0,'l':0,'a':0,'s':0} for _ in range(TURNS)]
    for _ in range(N):
        deck=deque(random.sample(STARTER,len(STARTER))); disc=deque()
        aff=1; slots=0; art_dmg=0; art_ready_turn=99
        for t in range(TURNS):
            hand=[]
            for _ in range(5):
                if not deck: deck=disc; disc=deque()
                hand.append(deck.popleft())
            mana=sum(c[0] for c in hand)
            dmg=sum(c[1] for c in hand) + (art_dmg if t>=art_ready_turn else 0)
            spent, adds, daff, dslot, newart = strategy(mana, aff, slots, t)
            aff+=daff; slots+=dslot
            for c in adds: deck.append(c)
            if newart:
                art_dmg+=newart; art_ready_turn=min(art_ready_turn, t+1)
            agg[t]['m']+=mana; agg[t]['d']+=dmg; agg[t]['l']+=mana-spent
            agg[t]['a']+=aff; agg[t]['s']+=slots
            for c in hand: disc.append(c)
    for t in range(TURNS):
        for k in agg[t]: agg[t][k]/=N
    return agg

# ---- strategies: return (spent, [cards to add], d_aff, d_slot, new_artifact_dmg)
def buy_mana(mana):
    if mana>=3: return 3,[MANA_ORB],0,0,0
    if mana>=2: return 2,[card(2)],0,0,0
    return 0,[],0,0,0

def sA(mana,aff,slots,t):                      # keep buying 1 mana/turn forever
    return buy_mana(mana)

def sB(mana,aff,slots,t):                       # rush Affinity, then Greater mana
    if aff<3 and mana>=3: return 3,[],1,0,0
    if aff>=2 and mana>=4: return 4,[GREATER],0,0,0
    return 0,[],0,0,0

def sC(mana,aff,slots,t):                       # mana T1-2, then weapons
    if t<2: return buy_mana(mana)
    w=best_weapon(mana,aff)
    return (w[1],[card(0,w[0])],0,0,0) if w else (0,[],0,0,0)

def sD(mana,aff,slots,t):                       # mana T1-3, then weapons
    if t<3: return buy_mana(mana)
    w=best_weapon(mana,aff)
    return (w[1],[card(0,w[0])],0,0,0) if w else (0,[],0,0,0)

def sE(mana,aff,slots,t):                       # balanced: mana, then aff2 + cheap slot+artifact, then weapons
    if t<2: return buy_mana(mana)
    spent=0; adds=[]; daff=0; dslot=0; art=0; m=mana
    if aff<2 and m>=3: daff=1; m-=3; spent+=3            # reach Affinity 2 once
    if slots<1 and m>=1: dslot=1; m-=1; spent+=1; art=3  # cheap first slot -> 3-dmg artifact engine
    w=best_weapon(m,aff+daff)
    if w: spent+=w[1]; adds.append(card(0,w[0])); m-=w[1]
    return spent,adds,daff,dslot,art

for name,fn in [('A keep buying mana',sA),('B rush Affinity+Greater',sB),
                ('C mana T1-2 then weapons',sC),('D mana T1-3 then weapons',sD),
                ('E balanced (mana->aff2+slot/artifact->weapons)',sE)]:
    r=run(fn)
    print(f'\n=== {name} ===')
    print(f'{"turn":>4}{"mana":>7}{"left":>7}{"DMG":>7}{"aff":>6}{"slots":>7}')
    for t in range(TURNS):
        x=r[t]; print(f'{t+1:>4}{x["m"]:>7.1f}{x["l"]:>7.1f}{x["d"]:>7.1f}{x["a"]:>6.1f}{x["s"]:>7.1f}')
