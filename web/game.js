"use strict";
/* Red Dragon — web prototype. Card data in cards_data.js (run export_web_cards.py to refresh). */

const CARDS = CARDS_DATA;

// market: fixed tier slots (ordered). All-class buyable cards only.
const MARKET_SPEC = [
  ["Mana", "Moderate"], ["Mana", "Moderate"], ["Mana", "Greater"], ["Mana", "Greater"],
  ["Weapon", "Light"], ["Weapon", "Light"], ["Weapon", "Heavy"], ["Weapon", "Heavy"],
  ["Artifact", "Ancient"], ["Artifact", "Ancient"], ["Artifact", "Common"], ["Artifact", "Common"],
  ["Support", null], ["Support", null], ["Support", null],
];
const LOCKED_TIERS = ["Greater", "Heavy", "Ancient"];
function poolFor(cat, tier) {
  return Object.keys(CARDS).filter(n => {
    const c = CARDS[n];
    if (c.cls !== "All" || c.cat !== cat || !c.cost) return false;
    if (tier == null) return !c.tier;
    return c.tier === tier;
  });
}
function marketPool(cat, tier) { return poolFor(cat, tier); }

const BOSS_CARDS = {
  "Claw Swipe":{type:"Boss",desc:"Village takes 5",fn:G=>vdmg(G,5)},
  "Tail Attack":{type:"Boss",desc:"Village takes 6",fn:G=>vdmg(G,6)},
  "Wide Swing":{type:"Boss",desc:"all heroes take 2",fn:G=>aliveHeroes(G).forEach(p=>pdmg(G,p,2))},
  "Scorching Gaze":{type:"Boss",desc:"a hero takes 3",fn:G=>{const p=randHero(G);if(p)pdmg(G,p,3);}},
  "Predatory Strike":{type:"Boss",desc:"highest-HP hero takes 5",fn:G=>{const p=topBy(G,h=>h.hp);if(p)pdmg(G,p,5);}},
  "Rising Hostility":{type:"Boss",desc:"Village takes 3, +2 Anger",fn:G=>{vdmg(G,3);G.anger+=2;}},
  "Mana Dominance":{type:"Boss",desc:"highest-Affinity hero takes 4",fn:G=>{const p=topBy(G,h=>h.aff);if(p)pdmg(G,p,4);}},
  "Kobold":{type:"Minion",hp:4,desc:"Village 3/round",fn:G=>vdmg(G,3)},
  "Kobold Horde":{type:"Minion",hp:8,desc:"Village 5/round",fn:G=>vdmg(G,5)},
  "Dragon Cultist":{type:"Minion",hp:6,desc:"a hero 3/round",fn:G=>{const p=randHero(G);if(p)pdmg(G,p,3);}},
  "Wyrm":{type:"Minion",hp:8,desc:"highest-HP hero 4/round",fn:G=>{const p=topBy(G,h=>h.hp);if(p)pdmg(G,p,4);}},
  "Fire Breather":{type:"Minion",hp:5,desc:"Village 5/round",fn:G=>vdmg(G,5)},
  "Kobold Marauder":{type:"Minion",hp:5,desc:"a hero 4/round",fn:G=>{const p=randHero(G);if(p)pdmg(G,p,4);}},
};
const DISASTERS = {
  "Unnatural Disaster":G=>vdmg(G,8),
  "Fiery Explosion":G=>{aliveHeroes(G).forEach(p=>pdmg(G,p,3));vdmg(G,3);},
  "Critical Hit":G=>{const p=lowestHero(G);if(p)pdmg(G,p,5);},
  "Supply Depletion":G=>aliveHeroes(G).forEach(p=>{for(let i=0;i<2&&p.hand.length;i++)p.discard.push(p.hand.pop());}),
  "Gear Purge":G=>G.players.forEach(p=>{if(p.equipped.length){const eq=p.equipped.pop();p.discard.push(card(eq.name));}}),
};
const ABILITIES = {
  Cleric:(G,p)=>{heal(G,lowestHero(G),4);if(p.aff>=3){const o=lowestHero(G,lowestHero(G));if(o)heal(G,o,4);}},
  Wizard:(G,p)=>refireArtifacts(G,p,p.aff>=3?2:1),
  Paladin:(G,p)=>{const n=p.aff>=3?3:2;heal(G,lowestHero(G),n);atk(G,p,n);},
  Druid:(G,p)=>{const n=p.aff>=3?3:2;heal(G,lowestHero(G),n);vheal(G,n);},
  Ranger:(G,p)=>{const n=p.aff>=3?3:2;vheal(G,n);atk(G,p,n);},
  Bard:(G,p)=>{if(p.aff>=3)heal(G,lowestHero(G),3);draw(G,p,1);},
  Weaponmaster:(G,p)=>{const n=p.aff>=3?2:1;for(let i=0;i<n;i++)replayFromDiscard(G,p,"Weapon");},
  Enchanter:(G,p)=>{if(p.aff>=3)tutorToDiscard(G,p,"Artifact",6);else tutorToHand(G,p,"Artifact",4);},
  Blacksmith:(G,p)=>{if(p.aff>=3)tutorToDiscard(G,p,"Weapon",6);else moveDiscardToHand(G,p,"Weapon");},
};
const ABILITY_DESC={
  Cleric:{n:"Heal the lowest-HP hero for 4 HP",u:"Heal the two lowest-HP heroes for 4 HP each"},
  Wizard:{n:"Trigger 1 equipped Artifact again (pick which)",u:"Trigger 2 equipped Artifacts again"},
  Paladin:{n:"Heal lowest hero 2 HP and deal 2 DMG",u:"Heal lowest hero 3 HP and deal 3 DMG"},
  Druid:{n:"Heal lowest hero 2 HP and Village +2 HP",u:"Heal lowest hero 3 HP and Village +3 HP"},
  Ranger:{n:"Village +2 HP and deal 2 DMG",u:"Village +3 HP and deal 3 DMG"},
  Bard:{n:"Draw 1 card",u:"Heal lowest hero 3 HP, then draw 1 card"},
  Weaponmaster:{n:"Replay 1 Weapon from your discard",u:"Replay up to 2 Weapons from your discard"},
  Enchanter:{n:"Fetch an Artifact (≤4 Mana) from Supply to hand",u:"Fetch an Artifact (≤6 Mana) to discard"},
  Blacksmith:{n:"Move a Weapon from discard to hand",u:"Fetch a Weapon (≤6 Mana) to discard"},
};
function abilityBlurb(cls,aff){
  const d=ABILITY_DESC[cls];if(!d)return cls;
  const tier=aff>=3?`Ultimate @ Affinity ${aff}`:`Normal @ Affinity ${aff}`;
  return `<b>${cls}</b> — ${tier}: ${aff>=3?d.u:d.n}`;
}
/* ----------------------------- setup ----------------------------- */
let setupP=0;

function fillComboPicker(P){
  const sel=$("compick");
  const list=TOP_COMBOS[String(P)]||[];
  sel.innerHTML=list.map((e,i)=>{
    const label=`#${i+1} ${e.classes.join(" + ")} (${e.winrate}% sim win)`;
    return `<option value="${i}">${label}</option>`;
  }).join("");
}

/* ----------------------------- state & helpers ----------------------------- */
let G=null;
const $=id=>document.getElementById(id);
const rint=n=>Math.floor(Math.random()*n);
const shuffle=a=>{for(let i=a.length-1;i>0;i--){const j=rint(i+1);[a[i],a[j]]=[a[j],a[i]];}return a;};
const sample=(a,n)=>shuffle(a.slice()).slice(0,n);
const aliveHeroes=G=>G.players.filter(p=>p.hp>0);
/** Lowest HP hero for heals — downed (0 HP) and injured before healthy; matches sim lowest_heal_target. */
function lowestHealTarget(G,exclude){
  const pool=G.players.filter(q=>q!==exclude);
  if(!pool.length)return null;
  const injured=pool.filter(q=>q.hp<q.maxhp);
  if(injured.length)return injured.slice().sort((a,b)=>a.hp-b.hp)[0];
  return pool.slice().sort((a,b)=>a.hp-b.hp)[0];
}
const lowestHero=(G,not)=>lowestHealTarget(G,not);
const randHero=G=>{const a=aliveHeroes(G);return a.length?a[rint(a.length)]:null;};
const topBy=(G,f)=>aliveHeroes(G).slice().sort((a,b)=>f(b)-f(a))[0]||null;
const botBy=(G,f)=>aliveHeroes(G).slice().sort((a,b)=>f(a)-f(b))[0]||null;
const card=name=>Object.assign({name},CARDS[name]);
function supplyPool(p,cat,maxCost){
  return Object.keys(CARDS).filter(n=>{const c=CARDS[n];return c.cls==="All"&&c.cost>0&&c.cost<=maxCost&&(!cat||c.cat===cat)&&!(c.tier&&LOCKED_TIERS.includes(c.tier)&&p.aff<2);});
}
function tutorToDiscard(G,p,cat,maxCost,cb){
  const pool=supplyPool(p,cat,maxCost);
  if(!pool.length){if(cb)cb();return;}
  askChoice(`Fetch which ${cat||"card"} (≤${maxCost} Mana) to discard?`,pool.map(n=>({label:`${n} (${CARDS[n].cost})`})),(label,i)=>{
    p.discard.push(card(pool[i]));if(cb)cb();render();
  });
}
function tutorToHand(G,p,cat,maxCost,cb){
  const pool=supplyPool(p,cat,maxCost);
  if(!pool.length){if(cb)cb();return;}
  askChoice(`Fetch which ${cat||"card"} (≤${maxCost} Mana) to hand?`,pool.map(n=>({label:`${n} (${CARDS[n].cost})`})),(label,i)=>{
    const nm=pool[i];
    if(cat==="Artifact"&&p.equipped.length<p.slots){
      askChoice(`Add ${nm} to hand or equip now?`,[{label:"Equip into a slot (fires next turn)"},{label:"Add to hand"}],(lab)=>{
        if(lab.startsWith("Equip")){p.equipped.push({name:nm,fireTurn:p.turn+1});log(`&nbsp;&nbsp;equipped ${nm} from Supply`);}
        else p.hand.push(card(nm));
        if(cb)cb();render();
      });
    }else{p.hand.push(card(nm));if(cb)cb();render();}
  });
}
function helpingHand(G,p,done){
  const hasWpn=p.discard.some(c=>(CARDS[c.name]?.cat||c.cat)==="Weapon");
  if(hasWpn)pickFromDiscard(G,p,{cat:"Weapon"},done);
  else tutorToHand(G,p,"Artifact",4,done);
}
function pickFromDiscard(G,p,spec,done){
  const cats=spec.cats||[spec.cat];
  const opts=[];
  p.discard.forEach((c,idx)=>{
    const nm=c.name||c;
    const cat=CARDS[nm]?.cat||c.cat;
    if(cats.includes(cat))opts.push({label:`${nm} (${cat})`,idx,cat,nm});
  });
  if(!opts.length){if(done)done();return;}
  const finish=(pick)=>{
    const c=p.discard.splice(pick.idx,1)[0];
    const nm=pick.nm;
    const canEquip=spec.equip||spec.equipArtifacts&&pick.cat==="Artifact";
    if(canEquip&&p.equipped.length<p.slots){
      askChoice(`Move ${nm} — equip now or add to hand?`,[{label:"Equip into a slot (fires next turn)"},{label:"Add to hand"}],(label)=>{
        if(label.startsWith("Equip")){p.equipped.push({name:nm,fireTurn:p.turn+1});log(`&nbsp;&nbsp;equipped ${nm} from discard`);}
        else p.hand.push(Object.assign({name:nm},CARDS[nm]));
        if(done)done();render();
      });
    }else{
      p.hand.push(Object.assign({name:nm},CARDS[nm]));
      if(done)done();render();
    }
  };
  if(spec.optional){
    askChoice("Move an Artifact from discard?",opts.map(o=>({label:o.label})).concat([{label:"(skip)"}]),(label,i)=>{
      if(i>=opts.length){if(done)done();return;}
      finish(opts[i]);
    });
    return;
  }
  askChoice("Move which card from discard to hand?",opts.map(o=>({label:o.label})),(label,i)=>finish(opts[i]));
}
function moveDiscardToHand(G,p,cat,done){
  pickFromDiscard(G,p,{cat},done||(()=>{}));
}
function destroyOne(G,p,onlyCat,done){
  const opts=[];
  p.hand.forEach((c,i)=>{const cat=CARDS[c.name]?.cat||c.cat;if(!onlyCat||cat===onlyCat)opts.push({label:`${c.name} (hand)`,from:"hand",idx:i});});
  p.discard.forEach((c,i)=>{const cat=CARDS[c.name]?.cat||c.cat;if(!onlyCat||cat===onlyCat)opts.push({label:`${c.name} (discard)`,from:"disc",idx:i});});
  const choices=opts.concat([{label:"(keep all — destroy nothing)",skip:true}]);
  if(!opts.length){if(done)done(null);return;}
  askChoice("Destroy which card? (removed permanently)",choices,(label,i)=>{
    const pick=choices[i];
    if(!pick||pick.skip){if(done)done(null);return;}
    (pick.from==="hand"?p.hand:p.discard).splice(pick.idx,1);
    if(done)done(pick);render();
  });
}
function tryAbilityFree(G,p,done){
  askChoice(`Use ${p.cls} ability for free?`,[{label:"Yes"},{label:"No"}],(label)=>{
    if(label.startsWith("Yes"))ABILITIES[p.cls](G,p);
    if(done)done();render();
  });
}
function collectiveDraw(G,total,maxPer,done){
  let left=total;const n={};G.players.forEach(p=>{n[p.id]=0;});
  const step=()=>{
    if(left<=0){if(done)done();return;}
    const opts=G.players.filter(p=>n[p.id]<maxPer).map(p=>({label:`P${p.id} ${p.cls} (drew ${n[p.id]})`,id:p.id}));
    if(!opts.length){if(done)done();return;}
    askChoice(`Draw ${left} more card(s) — choose player (max ${maxPer} each):`,opts,(label,i)=>{
      draw(G,G.players[opts[i].id],1);n[opts[i].id]++;left--;step();
    });
  };
  step();
}
function encourage(G,p,done){
  const ready=p.equipped.filter(eq=>eq.fireTurn<=p.turn&&eq.name!=="Timeless Talisman"&&!(G.ctx.refiredArts&&G.ctx.refiredArts.has(eq)));
  if(ready.length){
    askChoice("Encourage — trigger which equipped Artifact again?",ready.map(eq=>({label:eq.name})),(label,i)=>{
      const eq=ready[i];G._firingEq=eq;
      applyFx(G,p,CARDS[eq.name].fx,()=>{if(!G.ctx.refiredArts)G.ctx.refiredArts=new Set();G.ctx.refiredArts.add(eq);G._firingEq=null;if(done)done();render();});
    });
  }else{
    replayFromDiscard(G,p,"Weapon");if(done)done();render();
  }
}
function replayFromDiscard(G,p,cat){
  const wi=p.discard.findIndex(c=>(CARDS[c.name]?.cat||c.cat)===cat);
  if(wi<0)return;
  const c=p.discard.splice(wi,1)[0];const nm=c.name||c;
  if(cat==="Weapon")G.ctx.weapons++;
  applyFx(G,p,CARDS[nm].fx);
}
function refireArtifacts(G,p,n,done){
  if(!G.ctx.refiredArts)G.ctx.refiredArts=new Set();
  let k=0;
  const next=()=>{
    if(k>=n){if(done)done();return;}
    const ready=p.equipped.filter(eq=>eq.fireTurn<=p.turn&&eq.name!=="Timeless Talisman"&&!G.ctx.refiredArts.has(eq));
    if(!ready.length){if(done)done();return;}
    askChoice(`Trigger which equipped Artifact again? (${n-k} remaining)`,ready.map(eq=>({label:eq.name})),(label,i)=>{
      const eq=ready[i];G._firingEq=eq;
      applyFx(G,p,CARDS[eq.name].fx,()=>{G.ctx.refiredArts.add(eq);G._firingEq=null;k++;next();});
    });
  };
  next();
}
const manaLeft=()=>G.ctx.mana-G.ctx.spent;
const locked=c=>c.tier&&LOCKED_TIERS.includes(c.tier)&&G.active&&G.active.aff<2;
function log(html){const l=$("log");l.innerHTML+=html+"<br>";l.scrollTop=l.scrollHeight;}

/* ----------------------------- choice modal ----------------------------- */
let choiceCb=null;
function askChoice(title,options,cb){
  choiceCb=cb;
  $("chtitle").textContent=title;
  $("chbody").innerHTML=options.map((o,i)=>`<button style="display:block;width:100%;margin:6px 0;text-align:left" onclick="pickChoice(${i})">${o.label}</button>`).join("");
  $("choice").style.display="flex";
}
function pickChoice(i){
  const opts=[...$("chbody").querySelectorAll("button")];
  const labels=opts.map(b=>b.textContent);
  $("choice").style.display="none";
  const cb=choiceCb;choiceCb=null;
  if(cb)cb(labels[i],i);
}
window.pickChoice=pickChoice;

/* ----------------------------- damage / heal (floats + prevention) ----------------------------- */
function floatAt(elId,txt,color){const e=$(elId);if(!e)return;const r=e.getBoundingClientRect();
  const f=document.createElement("div");f.className="float";f.textContent=txt;f.style.color=color;
  f.style.left=(r.left+r.width/2-10+(rint(40)-20))+"px";f.style.top=(r.top+8)+"px";
  document.body.appendChild(f);setTimeout(()=>f.remove(),1000);
  e.classList.add("shake");setTimeout(()=>e.classList.remove("shake"),300);}
function bossDmg(G,n){if(n<=0)return;G.boss-=n;floatAt("boss","-"+n,"#ffd56b");checkEnd(G);}
function defeatMinion(G,src,m){
  G.minions=G.minions.filter(x=>x!==m);G.bossDiscard.push(m.name);
  log(`&nbsp;&nbsp;&#128165; ${m.name} defeated`);
  if(src&&src._slayer){src.slots=Math.min(5,src.slots+1);src._slayer=false;}
}
function bloodRitual(G,p){
  p.hp=Math.max(0,p.hp-2);floatAt("hero"+p.id,"-2","#ff8a80");
  if(G.minions.length){
    const m=G.minions.slice().sort((a,b)=>b.hp-a.hp)[0];
    defeatMinion(G,p,m);
  }else{bossDmg(G,4);G.minions.slice().forEach(m=>{m.hp-=4;if(m.hp<=0)defeatMinion(G,p,m);});}
  checkEnd(G);
}
function atk(G,src,n,forceMinion){if(n<=0)return;
  if(G.minions.length){
    const m=G.minions.slice().sort((a,b)=>a.hp-b.hp)[0];
    if(forceMinion||G.minions.length>=2||m.hp<=n){m.hp-=n;
      if(m.hp<=0)defeatMinion(G,src,m);
      return;}}
  bossDmg(G,n);}
function pdmg(G,p,n){if(p.prevent){const u=Math.min(p.prevent,n);p.prevent-=u;n-=u;}if(n<=0)return;
  p.hp=Math.max(0,p.hp-n);floatAt("hero"+p.id,"-"+n,"#ff8a80");if(p.hp<=0)log(`&nbsp;&nbsp;&#9760; ${p.cls} falls!`);checkEnd(G);}
function vdmg(G,n){if(G.vprev){const u=Math.min(G.vprev,n);G.vprev-=u;n-=u;}if(n<=0)return;
  G.village=Math.max(0,G.village-n);floatAt("vrow","-"+n,"#ff8a80");checkEnd(G);}
function heal(G,p,n){if(!p)return;p.hp=Math.min(p.maxhp,p.hp+n);floatAt("hero"+p.id,"+"+n,"#7CFC9A");}
function vheal(G,n){G.village=Math.min(G.vmax,G.village+n);floatAt("vrow","+"+n,"#7CFC9A");}
function draw(G,p,n){for(let i=0;i<n;i++){if(!p.deck.length){if(!p.discard.length)break;p.deck=p.discard;p.discard=[];}if(p.deck.length)p.hand.push(p.deck.shift());}}

/* ----------------------------- fx resolver ----------------------------- */
function statVal(G,p,s){
  if(s==="aff")return p.aff;
  if(s==="weaponsHand")return p.hand.filter(c=>c.cat==="Weapon").length;
  if(s==="supportHand")return p.hand.filter(c=>c.cat==="Support").length;
  if(s==="weaponsDiscard")return p.discard.filter(c=>(CARDS[c.name]?.cat||c.cat)==="Weapon").length;
  if(s==="missingHp")return Math.max(0,p.maxhp-p.hp);
  if(s==="anger")return G.anger;
  if(s==="maxArts")return Math.max(0,...G.players.map(pl=>pl.equipped.length));
  if(s==="artifactsEq")return p.equipped.length;
  if(s==="minions")return G.minions.length;
  if(s==="otherMana")return Math.max(0,(G.ctx.manaCards||0)-1);
  return 0;}
function applyScaleMana(G,p,sm){
  let extra=sm.b+(sm.per||0)*statVal(G,p,sm.stat);
  if(sm.step){const n=statVal(G,p,sm.stat);extra=sm.b+(n>=sm.step[2]?3:n>=sm.step[1]?2:n>=sm.step[0]?1:0);}
  G.ctx.mana+=extra;
}
function applyFxOp(G,p,op,done){
  if(op.mana!=null){G.ctx.mana+=op.mana;G.ctx.manaCards=(G.ctx.manaCards||0)+1;}
  else if(op.scaleMana){applyScaleMana(G,p,op.scaleMana);}
  else if(op.bonusIf){if(statVal(G,p,op.bonusIf.stat)>=(op.bonusIf.min||1))G.ctx.mana+=op.bonusIf.add;}
  else if(op.divineFavor){
    const w=p.hand.some(c=>c.cat==="Weapon"),a=p.equipped.length>0;
    G.ctx.mana+=1+(w||a?1:0)+(w&&a?1:0);G.ctx.manaCards=(G.ctx.manaCards||0)+1;
  }
  else if(op.bloodRitual)bloodRitual(G,p);
  else if(op.dmg!=null){if(op.slayer)p._slayer=true;atk(G,p,op.dmg);p._slayer=false;}
  else if(op.aoe!=null){bossDmg(G,op.aoe);G.minions.slice().forEach(m=>{m.hp-=op.aoe;if(m.hp<=0)defeatMinion(G,p,m);});}
  else if(op.dmgAff){let v=op.dmgAff.b+op.dmgAff.per*p.aff;if(op.dmgAff.min)v=Math.max(op.dmgAff.min,v);if(op.dmgAff.max)v=Math.min(op.dmgAff.max,v);atk(G,p,v);}
  else if(op.dmgWeapons)atk(G,p,op.dmgWeapons.per*G.ctx.weapons+op.dmgWeapons.aff*p.aff);
  else if(op.dmgArt)atk(G,p,op.dmgArt.b+op.dmgArt.per*p.equipped.length);
  else if(op.heal!=null){
    const tgt=op.who==="self"?p:(op.who==="lowest2"?lowestHero(G,lowestHero(G)):lowestHero(G));
    heal(G,tgt,op.heal);
  }
  else if(op.vheal!=null){if(op.vheal<0){G.village=Math.max(0,G.village+op.vheal);}else vheal(G,op.vheal);}
  else if(op.draw!=null)draw(G,p,op.draw);
  else if(op.drawAll!=null)G.players.forEach(h=>draw(G,h,op.drawAll));
  else if(op.discard!=null){
    if(op.discard===1&&p.hand.length){
      askChoice("Discard which card?",p.hand.map((c,i)=>({label:`${i}: ${c.name}`})),(label,i)=>{
        p.discard.push(p.hand.splice(i,1)[0]);if(done)done();render();
      });return false;
    }
    for(let i=0;i<op.discard&&p.hand.length;i++)p.discard.push(p.hand.pop());
  }
  else if(op.prevent!=null){
    if(op.who==="choose"){
      askChoice(`Apply ${op.prevent} prevention to`,[{label:"Village"},{label:`P${p.id} ${p.cls} (you)`}],(label)=>{
        if(label.startsWith("Village"))G.vprev+=op.prevent;else p.prevent+=op.prevent;
        if(done)done();render();
      });return false;
    }
    if(op.who==="village")G.vprev+=op.prevent;else p.prevent+=op.prevent;
  }
  else if(op.refire!=null){refireArtifacts(G,p,op.refire,done);return false;}
  else if(op.affinity!=null)p.aff=Math.min(3,p.aff+op.affinity);
  else if(op.slot!=null)p.slots=Math.min(5,p.slots+op.slot);
  else if(op.villageStrike!=null)atk(G,p,op.villageStrike);
  else if(op.postponeBoss){G.postponeBoss=true;if(G._firingEq){p.equipped=p.equipped.filter(e=>e!==G._firingEq);G._firingEq=null;}}
  else if(op.reshuffleMarket){["Mana","Weapon","Artifact","Support"].forEach(c=>G.market.forEach((s,i)=>{if(s.cat===c)replaceMarketSlot(i);}));}
  else if(op.optionalTutor){
    const ot=op.optionalTutor;
    askChoice(`Destroy to fetch a ${ot.cat||"card"} (≤${ot.max} Mana) to discard?`,[{label:"Yes — tutor + destroy"},{label:"No — keep"}],(label)=>{
      if(label.startsWith("Yes"))tutorToDiscard(G,p,ot.cat,ot.max,()=>{if(ot.self&&G._playingCard)G._skipDiscard=true;if(ot.self&&G._firingEq)p.equipped=p.equipped.filter(e=>e!==G._firingEq);if(done)done();});
      else if(done)done();
    });return false;
  }
  else if(op.tutor){tutorToDiscard(G,p,op.tutor.cat,op.tutor.max,done);return false;}
  else if(op.tutorHand){tutorToHand(G,p,op.tutorHand.cat,op.tutorHand.max,done);return false;}
  else if(op.helpingHand){helpingHand(G,p,done);return false;}
  else if(op.fromDiscard){pickFromDiscard(G,p,op.fromDiscard,done);return false;}
  else if(op.optionalDestroy){
    destroyOne(G,p,op.optionalDestroy.cat||null,()=>{if(done)done();});return false;
  }
  else if(op.destroyDraw){
    destroyOne(G,p,null,(removed)=>{if(removed)draw(G,p,1);if(done)done();});return false;
  }
  else if(op.tryAbility){tryAbilityFree(G,p,done);return false;}
  else if(op.secretTechnique){
    const tgt=G.village>=15?lowestHero(G):p;
    askChoice(`Secret Technique — use ${tgt.cls} ability for free?`,[{label:"Yes"},{label:"No"}],(label)=>{
      if(label.startsWith("Yes"))ABILITIES[tgt.cls](G,tgt);
      if(done)done();render();
    });return false;
  }
  else if(op.dmgOrDraw){
    const d=op.dmgOrDraw;
    askChoice("Celestial Slicer — choose mode:",[{label:`${d.dmg} DMG`},{label:`Draw ${d.drawTotal} collectively (max ${d.maxPerPlayer} each)`}],(label)=>{
      if(label.includes("DMG")){atk(G,p,d.dmg);if(done)done();render();}
      else collectiveDraw(G,d.drawTotal,d.maxPerPlayer,()=>{if(done)done();render();});
    });return false;
  }
  else if(op.fateArbiter){
    if(G.minions.length){const m=G.minions.slice().sort((a,b)=>b.hp-a.hp)[0];defeatMinion(G,p,m);}
    else draw(G,p,1);
  }
  else if(op.genesisEdge){
    if(G.minions.length)G.minions=[];
    else G.players.forEach(h=>draw(G,h,1));
  }
  else if(op.pacifier){const miss=Math.max(0,p.maxhp-p.hp);atk(G,p,miss);G.anger=Math.max(0,G.anger-2);}
  else if(op.bloodfire){
    const maxSpend=Math.min(3,Math.max(0,p.hp-1));
    const opts=Array.from({length:maxSpend+1},(_,n)=>({label:n?`Sacrifice ${n} HP → ${2+2*n} DMG`:"No sacrifice → 2 DMG"}));
    askChoice("Bloodfire Charm — sacrifice HP for +2 DMG each?",opts,(label,i)=>{
      p.hp=Math.max(0,p.hp-i);floatAt("hero"+p.id,i?("-"+i):"","#ff8a80");atk(G,p,2+2*i);
      if(done)done();render();
    });return false;
  }
  else if(op.dmgScaleArts)atk(G,p,Math.max(op.dmgScaleArts.min,p.equipped.length));
  else if(op.vhealOrHeal){if(G.village<G.vmax/2)vheal(G,2);else heal(G,lowestHero(G),2);}
  else if(op.triggerVillage)atk(G,p,2);
  else if(op.encourage){encourage(G,p,done);return false;}
  else if(op.replayWeapon){replayFromDiscard(G,p,"Weapon");}
  else if(op.passWisp){
    const nb=G.players[(p.id+1)%G.P];
    nb.discard.push(card("Wandering Wisp"));
    G._skipDiscard=true;
    log(`&nbsp;&nbsp;Wandering Wisp passes to P${nb.id} ${nb.cls}'s discard`);
  }
  else if(op.optionalSelfDestroy){
    askChoice(`Destroy ${G._playingCard?.name||"this card"} after use? (removed permanently)`,[{label:"Yes — destroy"},{label:"No — discard normally"}],(label)=>{
      if(label.startsWith("Yes"))G._skipDiscard=true;
      if(done)done();render();
    });return false;
  }
  else if(op.dmgSupport)atk(G,p,op.dmgSupport.b+op.dmgSupport.per*(G.ctx.supportUsed||0));
  else if(op.villageReduce)G.village=Math.max(0,G.village-op.villageReduce);
  else if(op.selfdmg!=null)p.hp=Math.max(0,p.hp-op.selfdmg);
  return true;
}
function applyFx(G,p,fx,done){
  let i=0;
  const advance=()=>{
    if(i>=fx.length){if(done)done();return;}
    const cont=()=>{i++;advance();};
    if(applyFxOp(G,p,fx[i],cont)===false)return;
    cont();
  };
  advance();
}
function fireArtifacts(G,p,n,extra){refireArtifacts(G,p,n);if(extra)log(`&nbsp;&nbsp;&#10024; ${p.cls} re-fires artifact`);}

/* ----------------------------- game start ----------------------------- */
function startGame(P,comboIdx=0){
  const entry=(TOP_COMBOS[String(P)]||[])[comboIdx]||(TOP_COMBOS[String(P)]||[])[0];
  if(!entry)return;
  const comp=entry.classes;
  const players=comp.map((cls,i)=>{
    const deck=STARTER_DECKS[cls].map(n=>card(n));
    return {id:i,cls,hp:10,maxhp:10,aff:1,slots:0,equipped:[],turn:0,prevent:0,deck:shuffle(deck),discard:[],hand:[]};
  });
  players.forEach(p=>{for(let i=0;i<5;i++)if(p.deck.length)p.hand.push(p.deck.shift());});
  const bossDeck=shuffle(Object.keys(BOSS_CARDS).filter(n=>BOSS_CARDS[n].type==="Boss")
    .concat(sample(Object.keys(BOSS_CARDS).filter(n=>BOSS_CARDS[n].type==="Minion"),4)));
  G={P,players,village:20+10*P,vmax:20+10*P,boss:40+10*P,bossMax:40+10*P,
     anger:1,angerStep:1,bossLevel:0,bossDeck,bossDiscard:[],
     disaster:shuffle(Object.keys(DISASTERS)),disasterDiscard:[],minions:[],
     market:buildMarket(),round:0,order:[],oi:0,active:null,vprev:0,result:null,ctx:null};
  $("setup").style.display="none";
  $("comp").textContent="Party: "+comp.join(" + ")+(entry.winrate?` (${entry.winrate}% sim)`:"");
  log(`<b>A ${P}-hero party faces the Red Dragon (HP ${G.boss}).</b>`);
  startRound();
}
function buildMarket() {
  const used = {};
  return MARKET_SPEC.map(([cat, tier]) => {
    const key = cat + (tier || "");
    const taken = used[key] || (used[key] = []);
    const pool = poolFor(cat, tier).filter(n => !taken.includes(n));
    const pick = pool.length ? pool[rint(pool.length)] : poolFor(cat, tier)[0];
    taken.push(pick);
    return {cat, tier, name: pick};
  });
}
function replaceMarketSlot(i) {
  const s = G.market[i];
  const taken = G.market.map((m, j) => j === i ? null : m.name);
  const pool = poolFor(s.cat, s.tier).filter(n => !taken.includes(n));
  if (pool.length) s.name = pool[rint(pool.length)];
}

/* ----------------------------- round / turn flow ----------------------------- */
function startRound(){
  G.round++;G.vprev=0;G.players.forEach(p=>p.prevent=0);
  G.order=[];aliveHeroes(G).forEach(p=>G.order.push({k:"P",p}));
  if(G.P%2===1){const j=aliveHeroes(G).slice().sort((a,b)=>(b.equipped.length-a.equipped.length)||(b.aff-a.aff))[0];if(j)G.order.push({k:"J",p:j});}
  for(let i=0;i<Math.ceil(G.P/2);i++)G.order.push({k:"B"});
  shuffle(G.order);G.oi=0;
  log(`<b>&mdash; Round ${G.round} &mdash;</b> (order: ${G.order.map(o=>o.k==="B"?"BOSS":("P"+o.p.id+(o.k==="J"?"*":""))).join(", ")})`);
  processOrder();
}
function processOrder(){
  while(G.oi<G.order.length&&!G.result){const t=G.order[G.oi];
    if(t.k==="B"){G.oi++;bossTurn();}
    else{if(t.p.hp<=0){G.oi++;continue;}beginPlayerTurn(t.p);return;}}
  if(G.result)return;
  if(G.minions.length){log("<b>End of round &mdash; minions attack</b>");G.minions.slice().forEach(m=>{if(!G.result)BOSS_CARDS[m.name].fn(G);});}
  if(!G.result)startRound();
}
function beginPlayerTurn(p){
  G.active=p;p.turn++;G.ctx={mana:0,spent:0,weapons:0,abilityUsed:false,manaCards:0,supportUsed:0,firedArts:new Set(),refiredArts:new Set()};
  p.equipped.forEach(eq=>{if(eq.fireTurn<=p.turn){log(`&nbsp;&nbsp;&#10024; ${eq.name} fires`);G._firingEq=eq;applyFx(G,p,CARDS[eq.name].fx,()=>{G.ctx.firedArts.add(eq);G._firingEq=null;});}});
  render();
}
function finishDrawPhase(p,keepIdx){
  const kept=keepIdx?p.hand.filter((c,i)=>keepIdx.has(i)):[];
  p.hand.forEach(c=>{if(!kept.includes(c))p.discard.push(c);});
  p.hand=kept;
  while(p.hand.length<5){
    if(!p.deck.length){if(!p.discard.length)break;p.deck=p.discard;p.discard=[];}
    if(p.deck.length)p.hand.push(p.deck.shift());
  }
  G.drawPhase=false;
  G.active=null;G.oi++;render();processOrder();
}
function cancelDrawPhase(){
  if(!G||!G.drawPhase)return;
  G.drawPhase=false;
  $("choice").style.display="none";
  render();
}
function endPlayerTurn(){
  const p=G.active;if(!p||choiceCb||G.drawPhase)return;
  if(!p.hand.length){finishDrawPhase(p,new Set());return;}
  G.drawPhase=true;
  const rows=p.hand.map((c,i)=>`<label style="display:block;margin:6px 0;cursor:pointer"><input type="checkbox" data-ki="${i}"> Keep <b>${c.name}</b></label>`).join("");
  $("chtitle").textContent="Draw phase — tick cards to keep, then redraw to 5";
  $("chbody").innerHTML=rows+
    `<button style="width:100%;margin-top:12px" id="chcancel">Cancel — keep playing</button>`+
    `<button class="primary" style="width:100%;margin-top:8px" id="chconfirm">Confirm & redraw</button>`;
  $("choice").style.display="flex";
  $("chcancel").onclick=cancelDrawPhase;
  $("chconfirm").onclick=()=>{
    const kept=new Set([...$("chbody").querySelectorAll("input:checked")].map(el=>+el.dataset.ki));
    G.drawPhase=false;
    $("choice").style.display="none";
    finishDrawPhase(p,kept);
  };
}
function bossTurn(){
  if(G.postponeBoss&&G.bossDeck.length){
    G.postponeBoss=false;
    const skip=G.bossDeck.shift();
    G.bossDeck.splice(rint(G.bossDeck.length+1),0,skip);
    log(`&nbsp;&nbsp;&#10024; Timeless Talisman — postponed <b>${skip}</b>`);
  }
  if(!G.bossDeck.length){G.bossLevel++;G.angerStep++;G.bossDeck=shuffle(G.bossDiscard);G.bossDiscard=[];log(`<b>&#9888; LEVEL UP ${G.bossLevel}</b> &mdash; minions +${2*G.bossLevel} HP, anger faster`);}
  const name=G.bossDeck.shift(),c=BOSS_CARDS[name];
  if(c.type==="Minion"){const hp=c.hp+2*G.bossLevel;G.minions.push({name,hp,maxhp:hp});log(`&#128081; Dragon summons <b>${name}</b> (${hp} HP)`);}
  else{log(`&#128009; Dragon: <b>${name}</b> &mdash; ${c.desc}`);c.fn(G);G.bossDiscard.push(name);}
  G.anger+=G.angerStep;
  if(G.anger>=G.P+2){G.anger=1;if(!G.disaster.length){G.disaster=shuffle(G.disasterDiscard);G.disasterDiscard=[];}
    const dn=G.disaster.shift();log(`&nbsp;&nbsp;&#128293; ANGER PEAKS &mdash; DISASTER: <b>${dn}</b>`);DISASTERS[dn](G);G.disasterDiscard.push(dn);}
  render();
}
function checkEnd(G){if(G.result)return;
  if(G.boss<=0)G.result="win";else if(G.village<=0)G.result="village";else if(G.players.every(p=>p.hp<=0))G.result="players";
  if(G.result)setTimeout(showEnd,300);}

/* ----------------------------- player actions ----------------------------- */
function playCard(idx){const p=G.active,c=p.hand[idx];if(!c||choiceCb||G.drawPhase)return;
  if(c.cat==="Artifact"&&c.name!=="Wandering Wisp"){equipCard(idx);return;}
  p.hand.splice(idx,1);G._playingCard=c;
  if(c.cat==="Weapon")G.ctx.weapons++;
  if(c.cat==="Support")G.ctx.supportUsed=(G.ctx.supportUsed||0)+1;
  applyFx(G,p,c.fx,()=>{
    if(!G._skipDiscard)p.discard.push(c);
    G._skipDiscard=false;G._playingCard=null;
    log(`P${p.id} plays ${c.name}`);render();
  });
}
function equipCard(idx){const p=G.active,c=p.hand[idx];
  if(c.name==="Wandering Wisp"){playCard(idx);return;}
  if(p.equipped.length>=p.slots){if(!buySlot(true)){log(`&nbsp;&nbsp;no free slot &mdash; buy one first (Buy Slot button)`);render();return;}}
  p.hand.splice(idx,1);p.equipped.push({name:c.name,fireTurn:p.turn+1});
  log(`P${p.id} equips ${c.name} (fires next turn)`);render();}
function buySlot(silent){const p=G.active;if(!p||p.slots>=5)return false;const cost=p.slots+1;
  if(manaLeft()<cost){if(!silent)log(`&nbsp;&nbsp;next slot costs ${cost} Mana`);return false;}
  G.ctx.spent+=cost;p.slots++;log(`P${p.id} buys artifact slot #${p.slots} (-${cost} Mana)`);render();return true;}
function buyCard(i){const s=G.market[i],c=CARDS[s.name];if(manaLeft()<c.cost)return;
  if(locked(c))return;G.ctx.spent+=c.cost;G.active.deck.push(card(s.name));
  replaceMarketSlot(i);
  log(`P${G.active.id} buys ${c.name} (-${c.cost})`);render();}
function reshuffleMarket(cat) {
  if (manaLeft() < 1) return;
  G.ctx.spent += 1;
  G.market.forEach((s, i) => { if (s.cat === cat) replaceMarketSlot(i); });
  log(`P${G.active.id} reshuffles ${cat} (-1 Mana)`);
  render();
}
function raiseAffinity(){const p=G.active;if(p.aff>=3||manaLeft()<3)return;G.ctx.spent+=3;p.aff++;log(`P${p.id} raises Affinity to ${p.aff}`);render();}
function useAbility(){const p=G.active;if(G.ctx.abilityUsed||manaLeft()<3)return;G.ctx.spent+=3;G.ctx.abilityUsed=true;log(`P${p.id} uses ${p.cls} ability`);ABILITIES[p.cls](G,p);render();}

/* ----------------------------- render ----------------------------- */
function bar(spanId,lblId,cur,max){$(spanId).style.width=Math.max(0,Math.min(100,100*cur/max))+"%";$(lblId).textContent=Math.max(0,cur)+" / "+max;}
function render(){
  if(G.result)return;
  $("roundlbl").textContent="· Round "+G.round;
  bar("bosshp","bosshplbl",G.boss,G.bossMax);
  $("angerb").style.width=Math.min(100,100*G.anger/(G.P+2))+"%";$("angerlbl").textContent=G.anger+" / "+(G.P+2);
  bar("vhp","vhplbl",G.village,G.vmax);$("vhplbl").textContent=Math.max(0,G.village)+" / "+G.vmax+(G.vprev?"  🛡"+G.vprev:"");
  const nx=G.bossDeck[0];$("telegraph").textContent=nx? (BOSS_CARDS[nx].type==="Minion"
    ? `Next: ${nx} (minion, ${BOSS_CARDS[nx].hp+2*G.bossLevel} HP) — ${BOSS_CARDS[nx].desc}`
    : `Next: ${nx} — ${BOSS_CARDS[nx].desc}`) : "Next: (deck reshuffles)";
  $("minions").innerHTML=G.minions.map(m=>`<div class="minion"><div>${m.name}</div><div class="mhp"><span style="width:${100*m.hp/m.maxhp}%"></span></div><div class="small">${m.hp}/${m.maxhp} HP — ${BOSS_CARDS[m.name].desc}</div></div>`).join("")||'<span class="small">no minions</span>';
  $("heroes").innerHTML=G.players.map(p=>{
    const pips=[1,2,3].map(n=>`<span class="pip ${p.aff>=n?'on':''}"></span>`).join("");
    const sh=p.prevent?` 🛡${p.prevent}`:"";
    return `<div class="hero ${p===G.active?'active':''} ${p.hp<=0?'down':''}" id="hero${p.id}">
      <div class="nm">P${p.id} ${p.cls}</div><div>❤️ ${Math.max(0,p.hp)}/${p.maxhp}${sh}</div>
      <div>Aff ${pips}</div><div class="small">slots ${p.equipped.length}/${p.slots}</div></div>`;}).join("");
  const a=G.active;
  if(a){
    $("manalbl").textContent=manaLeft();
    let slots="";for(let i=0;i<Math.max(a.slots,a.equipped.length,1);i++){const eq=a.equipped[i];
      if(eq){const ch=eq.fireTurn>a.turn;
        slots+=`<div class="slot filled ${ch?'charging':''}" style="width:auto;min-width:130px;height:auto;flex-direction:column;align-items:flex-start;padding:6px 9px;gap:2px">
          <div style="font-weight:600;font-size:11px">✦ ${eq.name}${ch?' (charging)':''}</div>
          <div class="small" style="font-size:10px;color:var(--muted)">${CARDS[eq.name].text}</div></div>`;}
      else slots+=`<div class="slot">+</div>`;}
    $("slots").innerHTML=slots;
    $("hand").innerHTML=a.hand.map((c,i)=>`<div class="card ${c.cat}" onclick="playCard(${i})"><span class="cc">${c.cost||0}</span>
        <div class="cat">${c.cat}${c.name==="Wandering Wisp"?" · slotless":""}${c.tier?' · '+c.tier:''}</div><div class="cn">${c.name}</div><div class="ct">${c.text}</div></div>`).join("");
    $("btnSlot").disabled=a.slots>=5||manaLeft()<a.slots+1;$("btnSlot").textContent=a.slots>=5?"Slots full":`Buy Slot (${a.slots+1})`;
    $("btnAff").disabled=a.aff>=3||manaLeft()<3;$("btnAff").textContent=a.aff<3?"Raise Affinity (3)":"Affinity max";
    $("btnAbility").disabled=G.ctx.abilityUsed||manaLeft()<3;
    $("btnAbility").title=ABILITY_DESC[a.cls]?ABILITY_DESC[a.cls][a.aff>=3?"u":"n"]:"";
    $("btnAbility").textContent=`Use Ability (3)`;
    $("abilityinfo").innerHTML=`⚡ ${abilityBlurb(a.cls,a.aff)}<span class="small"> · 3 Mana · once per turn</span>`;
  }
  renderMarket();
}
function renderMarket(){
  if(!G.active)return;
  const cats=["Mana","Weapon","Artifact","Support"];
  $("mktbody").innerHTML=cats.map(cat=>{
    const cards=G.market.map((s,i)=>({s,i})).filter(x=>x.s.cat===cat).map(({s,i})=>{const c=CARDS[s.name];
      const lk=c.tier&&LOCKED_TIERS.includes(c.tier)&&G.active.aff<2;const dis=manaLeft()<c.cost||lk;
      return `<div class="mkcard ${dis?'dis':''}" ${dis?'':`onclick="buyCard(${i})"`}>
        <div class="row" style="justify-content:space-between"><span class="mn">${s.name}${s.tier?' · '+s.tier:''}</span><span class="mc">${c.cost}${lk?'🔒':''}</span></div>
        <div class="ct">${c.text}</div></div>`;}).join("");
    return `<div class="sectlabel">${cat} <button style="padding:2px 8px;font-size:11px" onclick="reshuffleMarket('${cat}')">↻ 1 Mana</button></div><div class="mkrow">${cards}</div>`;
  }).join("");
}
function showEnd(){
  const t={win:"🏆 Victory!",village:"🏰 The Village has fallen…",players:"☠️ The heroes are slain…"}[G.result];
  const s={win:"The Red Dragon is defeated. Well played!",village:"Defend the Village next time.",players:"Heal and survive — race the Dragon."}[G.result]||"";
  $("ovtitle").textContent=t;$("ovsub").textContent=s;$("overlay").style.display="flex";
}

/* ----------------------------- wire up ----------------------------- */
document.querySelectorAll("#pcount button").forEach(b=>{
  b.onclick=()=>{
    setupP=+b.dataset.p;
    document.querySelectorAll("#pcount button").forEach(x=>x.classList.toggle("primary",+x.dataset.p===setupP));
    fillComboPicker(setupP);
    $("btnStart").disabled=false;
  };
});
$("btnStart").onclick=()=>{if(setupP)startGame(setupP,+($("compick").value||0));};
fillComboPicker(2);
setupP=2;
document.querySelector("#pcount button[data-p='2']").classList.add("primary");
$("btnStart").disabled=false;
$("btnEnd").onclick=()=>{if(G&&G.active&&!G.drawPhase)endPlayerTurn();};
$("btnSlot").onclick=()=>buySlot(false);
$("btnAff").onclick=raiseAffinity;
$("btnAbility").onclick=useAbility;
$("btnMarket").onclick=()=>$("market").classList.toggle("open");
$("closemkt").onclick=()=>$("market").classList.remove("open");
window.playCard=playCard;window.buyCard=buyCard;window.reshuffleMarket=reshuffleMarket;
