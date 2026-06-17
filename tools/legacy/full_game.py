"""
Macro race model (2 players): does the team kill the Boss before the Village/players die?
Player damage curve is grounded in the economy sim (T1-2 economy, then ~1 weapon/round + an
artifact engine). Boss clock uses tunable damage/anger/minion knobs (provisional until the boss
deck is reworked). Goal: a tense, winnable race -> win rate ~60-70%, ends ~round 7-9, Village/HP
dips low. Tune BOSS_HP, WEP (avg weapon dmg), and boss damage to hit that.
"""
import random
N = 30000
PHP0 = 10
VILLAGE0 = 30                       # reworked: Village 30 (was 40) -> real 2nd clock

def run(P, WEP, ART, boss_v, boss_p, heal, minion_p, lu_round, vscale, rounds=16):
    BOSS_HP = 50 + 15*P             # reworked: 50 + 15 x players
    wins=0; endrounds=[]; minV=[]; lossreason={'village':0,'players':0,'timeout':0}
    for _ in range(N):
        boss=BOSS_HP; village=VILLAGE0; php=[PHP0]*P
        anger=0; minions=0; won=False
        for r in range(1, rounds+1):
            lu = 1.5 if r>lu_round else 1.0
            # --- players' turns: team damage to boss (+ clear a minion if present) ---
            per = 1.2 + max(0, r-2)*WEP*0.5 + (ART if r>=5 else 0)
            tdmg = P*per
            if minions>0:                      # divert ~5 dmg to kill one minion
                tdmg -= 5; minions -= 1
            boss -= max(0, tdmg)
            # team heal (to village if low, else lowest player)
            if village < 25: village = min(VILLAGE0, village+heal)
            else:
                i=php.index(min(php)); php[i]=min(PHP0, php[i]+heal)
            if boss<=0: won=True; endrounds.append(r); break
            # --- boss turn: threat scales with player count (bi=P/2) so the race
            #     stays tense at 2-4p despite team damage scaling with P ---
            # Village is one shared 30-HP target -> its damage scales only gently with
            # player count (vscale); player-focused hits + minions scale with P.
            vfac = 1 + vscale*(P-2)
            village -= boss_v*lu*vfac
            for _ in range(max(1, round(P/2.0))):
                php[random.randrange(P)] -= boss_p*lu
            anger += 1
            if anger>=5:
                anger-=3; village -= 6*lu*vfac    # disaster spike
            if random.random()<minion_p*(1+0.3*(P-2)): minions+=1
            # --- end of round: minions attack ---
            village -= minions*2*lu
            for _ in range(minions):
                php[random.randrange(P)] -= 2*lu
            if village<=0: lossreason['village']+=1; endrounds.append(r); break
            if all(h<=0 for h in php): lossreason['players']+=1; endrounds.append(r); break
        else:
            lossreason['timeout']+=1; endrounds.append(rounds)
        if won: wins+=1
        minV.append(village)
    return dict(win=wins/N, end=sum(endrounds)/N,
                minV=sum(minV)/N, loss=lossreason)

# Reworked-deck knobs: balanced artifacts (smoother ART), scarce healing (2),
# boss village damage up per group G (boss_v ~3), boss player damage ~3.
REWORK = dict(WEP=4, ART=3, boss_v=2.0, boss_p=3, heal=2, minion_p=0.45, lu_round=6, vscale=0.4)
print("=== Reworked deck: 50+15P boss HP, Village 30, scarce heal, group-G village dmg ===")
for P in (2,3,4):
    random.seed(1)
    r=run(P=P, **REWORK)
    print(f'{P}p  bossHP={50+15*P:<3}  win={r["win"]*100:4.0f}%  end~round {r["end"]:.1f}  '
          f'avgVillageHP_end={r["minV"]:4.1f}  loss={r["loss"]}')
