# Opportunity engine — 2026-10-01

Archetypes ranked by a weighted score (longevity 25%, room to enter 25%, mechanics 20%, trend 20%, cost 10%). Confidence reflects how much data each score rests on; briefs marked PROVISIONAL rest on less than 28 days of history.

| # | Archetype | Adjusted | Raw | Confidence | Games | Hits | Entrants 90d | Est. weeks | Brief |
|---|---|---|---|---|---|---|---|---|---|
| 1 | horror / Co-op PvE | 0.606 | 0.698 | 0.53 | 43 | 7 | 10 | 4 | Fog Ferry: Round-Based Co-op Horror Crossings |
| 2 | round_pvp / PvP | 0.604 | 0.695 | 0.53 | 82 | 9 | 14 | 6 | Tilt Brawl: Small-Lobby Cosmetic Arena Fighter |
| 3 | sports / PvP | 0.591 | 0.709 | 0.43 | 47 | 6 | 6 | 6 | Original Arena Sport: Short Rounds, Cosmetic Levels |

### 1. horror / Co-op PvE — Fog Ferry: Round-Based Co-op Horror Crossings
*Adjusted score 0.606 (raw 0.698) · confidence 0.53 · PROVISIONAL · 43 games, 7 hits, 10 entrants in 90 days, est. 4 solo-dev weeks*

**The gap.** Horror / Co-op PvE has 43 games and 7 hits (16.3% hit rate), with a median peak of 3,901 and 358,232 players online now. The leaders are 99 Nights in the Forest (149,625 peak), DOORS (50,098) and Piggy (46,365). The newest wave (7 Days Cat-Sitting at 22,957, Animal Hospital (Anomaly) at 35,432, Animal Daycare (Anomaly) at 11,877) wraps horror in a mundane job. No hit in the profile is built on a short, role-based crew crossing that banks loot only on success, even though rounds (86% of hits vs 64% of others, lift 1.44) and losable progress (71% vs 61%, lift 1.60) are the strongest measured shapes.

**Why now.** Entrants rose from 6 to 10 in the last 90 days, and 9 of the 10 passed a 2k peak. Only 3 arrived in the last 30 days and 6 games hold Top-100 trending slots, so the space is active but not yet crowded. Longevity is unmeasured (history is 1.7 days), so the timing read is provisional.

**Build to these constraints**
- session_shape = rounds: Fixed-length crossings (about 8-10 minutes, general-knowledge sizing) with a clear win or wipe — *86% of hits vs 64% of other games; lift 1.44, solid*
- can_lose_progress = true: Unbanked salvage is lost on a wipe; banked salvage is kept — *71% of hits vs 61% of others; lift 1.60, moderate*
- social_asymmetry = help: Roles that revive, carry and cover each other — *71% of hits vs 39% of others; moderate. Global lift is only 0.92, so this is an archetype trait, not a universal one*
- pass_has_boost = false, pass_count about 2: Two cosmetic or convenience passes, no gameplay boosts, median price about 199 R$ and minimum about 100 R$ — *No-boost: 57% of hits vs 17% of others, lift 1.27. Hits have a median of 2 passes vs 4.5 for others, and median pass price of 199 vs 149 R$*
- icon_has_face = true: A creature or character face on the icon — *100% of hits vs 72% of others; lift 1.16, solid. Faceless icons: 0 of 7 hits, lift 0.69*
- Descriptive title, no codes in the description: A descriptive title of about 23 characters, no codes text — *Descriptive: 100% of hits. No codes: 100% of hits vs 94% of others, lift 1.15. Hits have a median title length of 23 vs 17.5*
- server_size about 25 (dormant lever): Lobby of 4 in a ferry crew, with a shared dock hub of about 25 — *Median server size is 25 for both hits (25) and others (24.5), so this is not a differentiator. Treat it as table stakes*

**Avoid**
- Levels as the progression type: Only 1 hit (14%) uses levels, and the lift is 0.23. Evidence is weak (n<3), but it is the weakest-lift progression value.
- Gameplay-boost passes and large pass menus: Boost passes appear in 14% of hits vs 64% of other games. Hits also carry fewer passes (median 2 vs 4.5).
- offline_accrual / persistent sessions: No hit has offline accrual (hits and others are both 100% false, lift 0.95). Persistent shape appears in 14% of hits vs 33% of others.
- Faceless icon: 0 of 7 hits, lift 0.69.
- Story-genre framing: 0 of 7 hits vs 31% of other games. Weak evidence, but hits skew toward round-based play. A linear narrative would fight the round structure.
- Renaming an existing hit (borrows_meme_or_ip = other_game): Hits borrow less often than other games (43% vs 64%), although global lift is 1.49. Mixed evidence. The brief picks originality for differentiation, and this is a judgment call. The 'none' value has a lift of 0.85, which is a risk accepted knowingly.

**Concept: Fog Ferry: Night Crossing** — Four crew members ferry passengers across a fog-bound river at night, and one passenger each trip is not what it seems.

- Core loop: Each round is one crossing with four roles: Pilot, Lamp-Keeper, Deckhand and Medic. The crew loads passengers and cargo at the dock, then steers through fog while the lamp fuel drains. Entities board disguised as passengers, and the crew must spot the tells, repair the hull and keep the lamp lit. Salvage picked up on the way is unbanked until the ferry docks on the far shore. A wipe loses the salvage, while a successful crossing banks it for cosmetics and unlocks a harder crossing.
- First 60 seconds: The player spawns on the dock with a lantern already in hand, and the icon creature is visible across the water. A 20-second guided mini-crossing teaches steering and the lamp. A first passenger boards with an obvious tell, and the player sees an unbanked salvage counter appear. A first cosmetic token is awarded at about 45 seconds.
- Social mechanic: Help-based asymmetry. Each role has a unique action that saves a teammate. The Medic revives, the Deckhand drags a downed player aboard, the Lamp-Keeper reveals tells in a cone and the Pilot can speed up or hold position. A downed player can still ring the bell to mark a passenger.
- Monetization: Two passes, no boosts. Captain's Crew at about 199 R$ (the hits' median) gives private crews and a lantern trail. A cosmetic bundle at about 100 R$ (the hits' minimum) is cosmetic only. No codes, no pay-to-win items.
- Content cadence: New crossing biomes and a new entity type roughly every 2 weeks (a general-knowledge cadence; the database has no update-frequency data yet). Weekly rotating cosmetic event, kept off core progress.

**Features**
- Round-based crossings of about 8-10 minutes (rounds: 86% of hits, lift 1.44)
- Unbanked vs banked salvage, lost on a wipe (can_lose_progress: lift 1.60)
- Four support-oriented roles with revive, drag and cover actions (help asymmetry: 71% of hits)
- Passenger-tell deduction mechanic that gives the crew a puzzle layer and is not a renamed copy of any leader
- Distinct creature face on the icon, with the same character on the first boarding (icon_has_face: 100% of hits)
- Cosmetic-only progression: lantern skins, ferry paint, crew emotes (cosmetic_only: 29% of hits vs 3% of others, lift 2.48, weak)
- Two passes at about 199 and 100 R$, no boosts (pass_has_boost false: lift 1.27)
- One weekly rotating cosmetic event as a low-intensity timer hedge (timers/FOMO: 43% of hits vs 17% of others, lift 1.28, moderate; but FOMO=false also in 57% of hits)

**Rewards and retention**
- First minute: A cosmetic lantern token at about 45 seconds, plus the first unbanked salvage item on the guided mini-crossing.
- First session: Bank the first successful crossing and unlock one cosmetic from salvage. Even a wipe on crossing 2 shows the salvage-lost screen with a specific hint, which pushes a retry.
- First week: Complete the first biome set (about 6 cosmetics) and unlock crossing tier 2. A first cosmetic rarity tier appears as a trophy case entry.
- Progression system: Cosmetic-only (29% of hits vs 3% of others, lift 2.48, weak with n=2). There are no levels (lift 0.23) and no stat numbers. Rarity applies only to cosmetic variants, and numbers appear only in crossing tier and salvage count. Difficulty tiers gate content, not power.
- Retention hook: Day 2: unbanked-salvage stakes (can_lose_progress, lift 1.60) and a visible 'next crossing tier' unlock keep the retry loop alive. Friends rely on role synergy (help asymmetry).
- Retention hook: Day 8: the weekly rotating cosmetic event (timers lift 1.28) and cosmetic set completion, plus a new biome. Retention is unmeasured in the database (staying power n=0), so these are hypotheses.

**Scope.** ~5 weeks · 2 people: 1 Luau developer and 1 environment/audio artist. The horror base rubric is 4 solo-dev weeks, and I add 1 for four roles and the passenger-tell system. · biggest risk: Passenger-tell deduction may be too hard to read, leaving a plain jump-scare ferry that lands as a copy of the Anomaly games. Longevity data is also missing, so day-8+ retention is a guess.

**28-day test.** Kill if: By day 28, peak CCU is under 2,000 (9 of the last 10 entrants cleared 2k), or like ratio is under 0.85 (archetype median 0.895), or the share of peak kept on days 8-28 falls under 0.25. The staying-power threshold is my own, as the archetype has no baseline (n=0). · Scale if: Peak CCU reaches at least 3,901 (archetype median) with like ratio at least 0.895 and favourites per 1k at least 5.06. Staying power on days 8-28 is at least 0.4 (my threshold). A 20k peak would count as a hit (the database's apparent line, inferred from entrants_90d_reaching_20k and hits both being 1). Scale team and content cadence if those are met. · Watch: 7-day and 28-day growth (currently null in the archetype); Staying power and half-life once 14+ days of history exist; Like ratio against 0.895 and favourites per 1k against 5.06; Entrant count over the next 30 days (3 in the last 30, 10 in 90) as a saturation signal; Whether newer Anomaly-style entrants keep holding their peaks, as a read on the genre's direction

*Components — longevity 0.50, room 0.87, mechanics 0.68, trend 0.68, cost 0.83; cost basis: rubric: base 4 for horror*

---

### 2. round_pvp / PvP — Tilt Brawl: Small-Lobby Cosmetic Arena Fighter
*Adjusted score 0.604 (raw 0.695) · confidence 0.53 · PROVISIONAL · 82 games, 9 hits, 14 entrants in 90 days, est. 6 solo-dev weeks*

**The gap.** Round PvP has 82 games, 9 hits (11.0%) and a median peak of 3,028. Of the 14 entrants in the last 90 days, 12 reached a 2k peak but only 1 reached 20k (Ball VS Ball, 37.8k). Hits are concentrated in 'Battlegrounds & Fighting' (67% of hits vs 22% of other games, lift 4.69), while the newest entrants, judging by their names (general-knowledge inference), lean toward word, bingo and quiz duels. The leaders are Murder Mystery 2 (224k peak, created 2014), Jujutsu Shenanigans (138k), Murderers VS Sheriffs (73k) and The Strongest Battlegrounds (55k). They are mostly old or built on a single IP or mode, and none is a small-lobby, cosmetic-only arena fighter with changing rules.

**Why now.** Entrants rose to 14 in the last 90 days from 10 in the prior 90, and the archetype holds 11 trending top-100 slots with 636,904 players now. The 2k floor is easy to clear (12 of 14), so the question is whether a game can reach the top tier, not whether it can launch at all.

**Build to these constraints**
- genre_l2 = Battlegrounds & Fighting: Direct player-vs-player melee/ability combat, not a party or minigame format — *67% of hits vs 22% of other games; lift 4.69 (solid)*
- play_mode = pvp (pure): Pure PvP with no party-game layer — *56% of hits vs 33% of others; lift 2.30 (moderate). party|pvp is 41% of non-hits but 0 of 9 hits.*
- progression_type = cosmetic_only: Levels unlock cosmetics only, with no stat power — *44% of hits vs 19% of others; lift 2.48 (moderate)*
- session_shape = rounds: Short, self-contained rounds — *78% of hits; lift 1.44 vs controls (solid). Within the archetype it is common (89% of non-hits), so it is table stakes, not a differentiator.*
- server_size: About 16 players per server — *Median 16 among hits vs 22 among others; archetype median 20.5*
- pass_has_boost = false: No boost gamepass — *56% of hits vs 22% of others; lift 1.27 (moderate)*
- pass pricing: About 4 passes, median price around 190 Robux, cheapest around 115 — *Hits: pass_count 4, median price 189.5, min price 113.5. Others: 3 passes, median 274, min 99.*
- can_lose_progress = false: Never remove owned items or levels — *100% of hits (9/9) vs 95% of others; lift 0.91. Near-universal, so treat it as hygiene.*
- desc_has_codes = false: No codes in the description — *78% of hits; lift 1.15 (solid)*

**Avoid**
- play_mode = party|pvp: 41% of non-hits use it but 0 of 9 hits do. The label is weak (fewer than 3 hits), so this is a caution, not a proven penalty.
- pass_has_boost = true: Only 33% of hits carry it vs 63% of non-hits (lift 0.92). Power-selling passes are over-represented among the misses.
- desc_has_codes = true: Lift 0.41, and only 22% of hits carry it (weak sample). Codes signal a grind-game playbook that doesn't suit this archetype.
- progression_type = rarity_collection (alone) or none: Lifts of 0.37 and 0.64 (both weak, fewer than 3 hits). Pure rarity grinds and no progression both under-index; keep rarity out of the power layer.
- Large lobbies and expensive passes: Hit medians are 16 players (vs 22) and 189.5 Robux (vs 274). Large servers and pricey passes both skew toward non-hits.
- Copying the leaders' hook: Murder Mystery 2 and Murderers VS Sheriffs hold the social-deduction niche, and Jujutsu Shenanigans/The Strongest Battlegrounds hold the IP-brawler niche. Borrowing another game's IP has 33% share among hits (lift 1.49) but is not required, since 'none' is also 33% of hits.

**Concept: Tilt Brawl** — Sixteen fighters brawl on one giant floating slab that tilts toward whoever is winning, so the leader always fights uphill.

- Core loop: A lobby fills to about 16 players and a 3-minute round starts on a slab that slowly tilts toward the current kill leader. Players use a 4-move kit (strike, dash, grab, one charge move) to knock rivals off the edge. A rotating mutator such as low gravity, slippery ice or bouncy rim changes each round. The round ends when one player is left or the timer runs out. Results pay XP into a cosmetic-only level track, and the lobby resets within 15 seconds so the next round starts fast.
- First 60 seconds: The player drops straight into a round with a one-line prompt: 'Knock people off.' The first dash and first knock-off teach themselves. At about 45 seconds of play, even after being eliminated, a cosmetic trail unlocks and the next round queues automatically.
- Social mechanic: Rival Mark (social_asymmetry 'take': 33% of hits vs 22% of others, lift 1.61, moderate). When you are knocked off, you can mark your killer. If you knock them off next round you 'take' their round-only streak banner as a trophy. Nothing owned is ever lost (can_lose_progress=false in 9/9 hits).
- Monetization: A VIP pass (present in 67% of hits, lift 1.02, so optional and not differentiating) plus about 3 cosmetic passes (kill effects, trails, emotes), 4 in total. Median price about 190 Robux, cheapest about 115. No boost passes and no stat items.
- Content cadence: Weekly mutator and arena-skin rotation; a new cosmetic season every 3-4 weeks. Update frequency is not measurable yet (under 14 days of change-log), so this cadence is general knowledge, not a measured trait.

**Features**
- 16-player lobbies, matching the hit median server size of 16 (vs 22 for others)
- Tilting slab arena with a 'fight uphill' leader penalty, an original hook inside the Battlegrounds & Fighting genre (lift 4.69)
- Pure PvP mode only, no party minigames (play_mode pvp lift 2.30)
- Cosmetic-only level track with no stat unlocks (lift 2.48)
- Rival Mark 'take' mechanic using round-only trophies (lift 1.61)
- 4 gamepasses with a ~190 Robux median and no boost pass (hit medians; boost=false lift 1.27)
- Weekly rotating mutators (general knowledge: keeps rounds fresh without new maps)
- Fast queue with a 15-second reset, matching the rounds session shape (lift 1.44)

**Rewards and retention**
- First minute: A cosmetic trail at about 45 seconds, regardless of win or loss.
- First session: Reach cosmetic levels 3-5 over about 6 rounds, unlocking a kill effect and an emote. Players can try one free 'mutator spotlight' arena skin.
- First week: Complete the first season-track tier set, which unlocks a distinct weapon skin and a title; players can display Rival Mark trophy counts.
- Progression system: cosmetic_only (44% of hits vs 19% of others, lift 2.48). Levels come from round XP and unlock only skins, trails, emotes and banners, never stats. Rarity is limited to colour variants and does not gate power (rarity-only lift 0.37, weak).
- Retention hook: Day 2: a daily cosmetic track step and a new mutator in the rotation (timers/FOMO true lift 1.28 but only 33% of hits, so keep timers light)
- Retention hook: Day 8: first season-tier unlock, plus a visible Rival Mark tally against the players who knocked you off (take lift 1.61)
- Retention hook: Weekly mutator rotation as a standing reason to return (general knowledge, since no longevity data exists yet)

**Scope.** ~6 weeks · 1 developer (scripting, combat, netcode) plus part-time contract VFX/animation. The 6-week figure is the database rubric base for round_pvp. · biggest risk: Combat feel and netcode on a physics-driven arena. Separately, the data cannot yet show whether round-PvP novelty holds beyond a launch spike.

**28-day test.** Kill if: By day 7, peak CCU is under 2,000 (12 of 14 recent entrants cleared it), or the like ratio is under 0.82 (the archetype median is 0.8745, and the weakest leader, BedWars, is 0.823). Also kill if by day 28 the game keeps under 25% of its peak on days 8-28 (the staying-power metric; the 25% cut is my own threshold, not measured). · Scale if: Peak CCU is at or above 3,028 (archetype median) within 28 days, the like ratio is at least 0.87, favorites per 1k are at least 3.3 (median 3.302), and staying power is at least 0.40 on days 8-28. Reaching 20k+ would put it in the top tier, which only 1 of the 14 recent entrants has done. · Watch: Staying power (share of peak kept on days 8-28), which is currently null for the archetype (n=0); Half-life in days, since the archetype figure is 1.0 from n=1 (a crashed game); Like ratio and favorites per 1k vs 0.8745 and 3.302; 7-day and 28-day growth, which the database has none of yet; Entrant count: 14 in 90 days vs 10 the prior 90

*Components — longevity 0.50, room 0.92, mechanics 0.57, trend 0.80, cost 0.67; cost basis: rubric: base 6 for round_pvp*

---

### 3. sports / PvP — Original Arena Sport: Short Rounds, Cosmetic Levels
*Adjusted score 0.591 (raw 0.709) · confidence 0.43 · PROVISIONAL · 47 games, 6 hits, 6 entrants in 90 days, est. 6 solo-dev weeks*

**The gap.** Sports / PvP has 47 games and 6 hits (12.8% hit rate, 0 breakouts) with a median peak of only 2,169, yet the top four are all 31k-55k peak: Illegal Soccer 54,927, Volleyball Legends 46,288, Realistic Street Soccer 32,023 and Blue Lock: Rivals 31,506. Every leader whose sport is clear from its name is an existing real-world sport (soccer, volleyball, NFL football) or a licensed anime. In the last 90 days all 6 entrants passed 2k peak and 1 (Blox League, 20,564) passed 20k, so demand exists for new entrants. An invented sport built on the measured hit traits is not among the named leaders.

**Why now.** Entrants rose from 5 (prior 90d) to 6 (last 90d), all 6 reached 2k peak, and the archetype holds 11 trending top-100 slots with 210,807 players now. Saturation is low in the entrant data, but the database has only 1.7 days of history, so trend and longevity are unmeasured.

**Build to these constraints**
- session_shape = rounds: Fixed 3-4 minute matches with a clear end and a re-queue. No persistent world. — *100% of 6 hits vs 83% of other games; lift 1.44, solid. Hybrid and persistent have 0 hits.*
- genre_l2 = Sports: Classify and present the game as a sport (rules, teams, scoreboard), not a racing or brawler hybrid. — *83% of hits vs 71% of others; lift 2.20, moderate. Racing: 0 of 6 hits vs 20% of others.*
- progression_type = cosmetic_only|levels: Player level unlocks cosmetics only. No stat gains. — *67% of hits vs 17% of others; lift 2.79, moderate. 'none' is only 17% of hits vs 46% of others (lift 0.64, weak).*
- play_mode = pvp: Pure team PvP, no PvE or co-op layer. — *50% of hits vs 41% of others; lift 2.30, moderate. pve|pvp has 0 hits vs 15% of others.*
- server_size: 10 players per server (e.g. 5v5 or 3v3 plus subs). — *Median 10 among hits vs 14 among others (numeric trait; small n).*
- pass_has_vip = true, pass_has_boost = false: Include a VIP pass. Include no gameplay-boost pass. — *VIP in 83% of hits vs 51% of others (lift only 1.02, moderate). Boost-free is 50% of hits (lift 1.27); boost-pass has lift 0.92 (weak).*
- pass pricing: Cheapest pass about 49 Robux, median pass about 375 Robux, around 5 passes. — *Hits: min price 49, median 374, count 5. Others: min 99, median 199, count 5.*
- has_timers_or_fomo = true: Rotating limited-time cosmetic shop and season timer. — *50% of hits vs 22% of others; lift 1.28, moderate.*
- desc_has_codes = false: No codes in the description. — *100% of hits vs 93% of others; lift 1.15, solid. Codes: 0 hits, lift 0.41, weak.*

**Avoid**
- progression_type = none: Only 17% of hits vs 46% of other games (lift 0.64, weak: fewer than 3 hits carry it).
- Persistent or hybrid session shape: 0 of 6 hits; lifts 0.88 and 0.46 (weak, but the solid 'rounds' trait points the same way).
- Codes advertised in the description: 0 hits vs 7% of others; lift 0.41 (weak).
- Gameplay-boost game passes: Only 33% of hits carry them vs 50% without; lift 0.92 vs 1.27 (weak). Cosmetic-only progression is the measured pattern.
- Copying the leaders (a soccer, volleyball or football reskin, or a licensed brand/anime): Brand IP has lift 0.87 and anime 0.98 (both weak). Leaders hold 31k-55k peaks against a 2,169 median, so a clone would compete head-on with them.
- Offline accrual, base defense, can_lose_progress: Every hit and nearly every other game lacks them (all 100% on hits; lifts 0.91-1.01). They add scope without differentiating.

**Concept: Skyrail Disc League** — A 3v3 invented sport where teams fling a magnetic disc along elevated rails and walls to score through moving goal rings.

- Core loop: Queue into a 3-minute 3v3 round on a small arena and fight over the disc. Throw it along rails and bank shots off walls into rings that rotate positions on a fixed timer. Win or lose, every round grants XP that raises the player level. Levels unlock cosmetics only (disc trails, goal-burst effects, outfits, emotes). Then the player re-queues with the same party, or with new teammates if solo. Top 10 players on the arena are 3v3 plus 4 substitutes, which matches the measured 10-player server median.
- First 60 seconds: The player spawns in a 20-second tutorial lane with a loose disc and a ring. They throw one scoring shot and earn Level 2 and a trail cosmetic. They are then dropped into a live 3v3 with a short 90-second first match. Bots fill empty slots in the first two matches so there is no empty queue.
- Social mechanic: Party queue with teammates and a post-round 'highlight throw' replay that the party can emote on. Clubs are a possible addition but not in the MVP. Social asymmetry 'none' is 83% of hits but 98% of others (lift 0.84), so no asymmetric roles or trading are added.
- Monetization: VIP pass (private-match access, chat tag and a cosmetic set) priced in the measured band, with a cheapest pass near 49 Robux and a median around 375. About 5 passes in total, all cosmetic or convenience, no boost passes. A rotating limited-time cosmetic shop and a season timer carry the FOMO trait.
- Content cadence: General knowledge, not measured (the database has no update-frequency data yet): a new arena or goal-ring mechanic every 2 weeks, and a new cosmetic shop rotation weekly.

**Features**
- 3-minute rounds with a re-queue button (session_shape = rounds, lift 1.44).
- 10-player servers, 3v3 plus substitutes (hit median server size 10 vs 14).
- Level track that unlocks cosmetics only (cosmetic_only|levels, lift 2.79).
- Limited-time rotating cosmetic shop and season countdown (timers/FOMO, lift 1.28).
- VIP pass plus about 4 cheap cosmetic passes, starting around 49 Robux and with a median of about 375, and no boost passes.
- Pure PvP matchmaking with bot fill for the first two matches (play_mode = pvp, lift 2.30).
- Sport-style presentation: scoreboard, referee voice lines, post-match MVP (genre_l2 = Sports, lift 2.20).
- Description with no codes (desc_has_codes false, lift 1.15).

**Rewards and retention**
- First minute: Level 2 and a disc trail after the tutorial throw (about 20 seconds), then a first-match completion reward at about 2 minutes.
- First session: About 4-5 matches, Level 5-6, 3 cosmetics unlocked, and a first-win goal-burst effect.
- First week: Level 20-25 with a full starter outfit set, one limited-shop item purchasable with earned coins, and a seasonal level reward visible ahead.
- Progression system: Measured type is cosmetic_only|levels (67% of hits, lift 2.79). Levels are the only number that goes up and they gate cosmetics, never stats. Rarity is a visual tier tied to level milestones, not to random drops. Pure rarity-collection and numbers-go-up combinations have 0 hits (weak), so neither is included.
- Retention hook: Day 2: the next level unlocks a cosmetic within one or two matches, and the limited shop has a timer (FOMO lift 1.28).
- Retention hook: Day 8: a seasonal level milestone and a rotating shop item that expires, plus the party-queue habit. The timer mechanism has measured lift 1.28 but the day-8 effect itself is not measured (staying power n = 0).

**Scope.** ~6 weeks · 1 solo developer (the database rubric gives 6 weeks for sports) plus a contract artist for cosmetics and arena kit. · biggest risk: Cold-start matchmaking: 10-player PvP rounds feel dead below about 10 concurrent players, and the database has no retention or half-life data to size the risk. Bot fill and a short queue timer mitigate it.

**28-day test.** Kill if: By day 28, peak CCU is below 2,000 (all 6 entrants in the last 90 days cleared 2k, so missing it is below the entrant cohort), or the like ratio is below 0.877 (archetype median), or the share of peak kept on days 8-28 is below roughly 0.25 (a general-knowledge heuristic; the database has no archetype baseline yet). · Scale if: By day 28, peak CCU is at or above 10,000 with staying power at or above 0.4 and like ratio at or above 0.90. A peak near 20,000 would match the level of the one recent entrant that reached 20k (Blox League). Also fav per 1k at or above the 2.283 median, and a positive 28-day growth reading. · Watch: Peak CCU vs the 2,169 archetype median.; Like ratio vs 0.877 and favourites per 1k vs 2.283.; Staying power (share of peak kept on days 8-28) once the database has 14+ days of history.; Average server fill vs the 10-player target.; VIP pass attach rate and limited-shop timer engagement.

*Components — longevity 0.50, room 0.96, mechanics 0.59, trend 0.80, cost 0.67; cost basis: rubric: base 6 for sports*

---
