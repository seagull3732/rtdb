# Opportunity engine — 2026-10-12

Archetypes ranked by a weighted score (longevity 25%, room to enter 25%, mechanics 20%, trend 20%, cost 10%). Confidence reflects how much data each score rests on; briefs marked PROVISIONAL rest on less than 28 days of history.

| # | Archetype | Adjusted | Raw | Confidence | Games | Hits | Entrants 90d | Est. weeks | Brief |
|---|---|---|---|---|---|---|---|---|---|
| 1 | horror / Co-op PvE | 0.647 | 0.707 | 0.71 | 59 | 14 | 16 | 4 | Last Tide Salvage: Co-op Horror With Real Stakes |
| 2 | rng / PvE | 0.634 | 0.711 | 0.64 | 21 | 6 | 7 | 3 | Feed a Goblin: Lucky-Roll Tycoon With a Face |
| 3 | sports / PvP | 0.629 | 0.696 | 0.66 | 59 | 9 | 8 | 6 | Tilt Court: cosmetic-progression 5v5 arena sport |

### 1. horror / Co-op PvE — Last Tide Salvage: Co-op Horror With Real Stakes
*Adjusted score 0.647 (raw 0.707) · confidence 0.71 · PROVISIONAL · 59 games, 14 hits, 16 entrants in 90 days, est. 4 solo-dev weeks*

**The gap.** Horror co-op PvE has 59 games and 14 hits (23.7% hit rate), but it is top-heavy: the leader 99 Nights in the Forest peaked at 1.92M CCU against a median peak of 5,336. The leaders are survival-forest (99 Nights), room-by-room (DOORS), character-based (Dandy's World) and anomaly-spotting (Animal Hospital, Sarab, Huss Valley). The measured traits most associated with hits are round-based sessions (79% of hits vs 64% of other games, lift 1.22) and losable progress (71% vs 53%, lift 2.07). Escape-style structure is also over-represented (29% vs 18%, lift 3.92, moderate), and the archetype has no leader built around a short escape round with a real loss condition.

**Why now.** Entrants in the last 90 days more than doubled (16 vs 7 the previous 90 days), 13 of the 16 reached 2k CCU and 5 reached 20k, and the archetype holds 13 Trending top-100 slots with a median 7-day growth of +9.85%. Only 4 entrants arrived in the last 30 days, so the window is open but filling. The database has only 12.5 days of history, so these trend readings are early.

**Build to these constraints**
- session_shape = rounds: Discrete 10-14 minute rounds with a clear win/lose end state, not a persistent world — *79% of hits vs 64% of other games; lift 1.22 (solid)*
- can_lose_progress = true: A squad wipe loses the cargo carried in that run; banked items are safe — *71% of hits vs 53% of others; lift 2.07, the strongest solid trait in the profile*
- genre_l2 = Escape: Rounds structured as 'reach the exit / extract with the haul' — *29% of hits vs 18% of others; lift 3.92 (moderate, so provisional)*
- icon_has_face = true: Icon features the creature's face, readable at thumbnail size — *71% of hits; lift 1.18 (solid). Icons without a face are 7% of hits vs 20% of others*
- desc_has_codes = false and title_pattern = descriptive: No codes in the description; a plain descriptive title — *100% of 14 hits have no codes (lift 1.16) and 100% have descriptive titles (lift 0.97, so neutral rather than a booster)*
- server_size and pass pricing: 25-player servers; 3 passes with the cheapest at about 99 R$ and the median near 149 R$ — *Hit medians: server size 25, pass_count 3, min price 99, median price 149*
- pass_has_vip = true, pass_has_boost = false: Include a VIP pass; do not sell a boost pass — *50% of hits have a VIP pass vs 29% of others, but lift is 0.99, so this is a common pattern rather than a proven lift. Boost passes: 29% of hits vs 60% of others, lift 1.01 (moderate)*

**Avoid**
- Stat-level progression (progression_type = levels): Only 14% of hits use it and its lift is 0.40 (weak, 2 hits). Use cosmetic-only progression instead (14% of hits, lift 2.01, also weak).
- Story-led genre: 0 of 14 hits vs 27% of other games; lift 0.20 (weak, so provisional). It is common among the misses.
- Boost game passes: Hits skip them more often (29% vs 60% of other games). Lift is about 1.0, so there is no evidence they help.
- Codes in the description: No hit uses them (0 of 14), while 4% of other games do.
- Copying the leaders' hooks (anomaly-spotting, forest survival, door rooms): Those are the exact slots 99 Nights, Animal Hospital and DOORS hold. Borrowing from other games has lift 1.54, but only as an influence on mechanics, not as a clone.
- Real-time FOMO timers on store items: 71% of hits have none (lift 0.97 / 1.04, so neutral). The extra build and ops cost has no measured payoff.

**Concept: Last Tide Salvage** — Dive a sinking shipwreck with your squad, grab cargo before the tide rises, and get it to the surface bell, because anything still on you when the squad wipes is lost.

- Core loop: A 25-player server fills a lobby and splits into squads of 4. Each round drops a squad into a flooding wreck for about 12 minutes. Players find cargo of different weights and values. Heavier cargo slows the carrier and makes more noise, which draws a sound-hunting creature. The round ends when the squad rings the surface bell (extract) or wipes. Extracted cargo is banked into a permanent cosmetic ledger. Cargo carried at a wipe is lost, which provides the can-lose-progress stakes (lift 2.07). The tide is a round clock, not a store timer.
- First 60 seconds: Spawn on the dock with three teammates and a lantern. Within 20 seconds, descend through the first flooded hatch. At about 45 seconds, find the first small cargo crate and carry it to the practice bell to bank a lantern charm cosmetic. The creature's silhouette is visible as a face in the dark by about 55 seconds.
- Social mechanic: A tether-and-revive system: a downed diver can be hauled and revived by a teammate, while the carrier of heavy cargo must be covered by others. Half of the archetype's hits use 'help' asymmetry (50% vs 36% of other games), though its global lift is 0.73, so treat it as an in-archetype pattern rather than a proven lift. Squads of 4 inside 25-player servers keep the server size at the hit median.
- Monetization: Three passes, priced from about 99 to 149 R$: a VIP pass (50% of hits have one), a cosmetic diver-suit pack, and a ledger-slot or emote pack. No boost pass. No stat levels, so spending never changes survival odds.
- Content cadence: Launch with 3 wrecks. Add one wreck every 2-3 weeks. The database has no update-cadence data yet (needs 14+ days of change-log history), so this cadence is general knowledge and should be re-checked against the leaders once data exists.

**Features**
- Round-based extraction runs of about 12 minutes (rounds: lift 1.22)
- Cargo carry-weight system: carried cargo is lost on a squad wipe (can_lose_progress: lift 2.07)
- Escape-structured wrecks with a single surface bell exit (Escape genre: lift 3.92, moderate)
- Creature with a distinct face used as the game icon (icon_has_face: lift 1.18)
- Tether revive and haul mechanic for the 'help' social pattern (50% of hits)
- Cosmetic-only permanent ledger of banked cargo (cosmetic_only progression: lift 2.01, weak evidence)
- 25-player servers split into squads of 4 (hit median server size 25)
- A VIP pass plus two cosmetic passes, no boost pass (hit median 3 passes)

**Rewards and retention**
- First minute: At about 45 seconds the player banks a crate at the practice bell and earns the lantern charm cosmetic.
- First session: After 2-3 rounds, the player completes a first extraction and fills the first page of the cosmetic ledger, which unlocks the first diver-suit color.
- First week: Complete one ledger set (about 8 cosmetics) from the first 3 wrecks and earn a deep-diver title that is visible to squadmates.
- Progression system: Cosmetic-only progression (the measured type is none for 50% of hits and cosmetic_only for 14%, weak evidence). Cargo rarity and value only affect the ledger and cosmetics, never survival stats, so numbers feed collection rather than power. This avoids the levels pattern (lift 0.40).
- Retention hook: Day 2: the ledger page is partly filled and the second wreck unlocks on first extraction, so there is an obvious next step. Losable cargo (lift 2.07) gives unfinished business after a wipe.
- Retention hook: Day 8: a new wreck release and 'deep haul' cargo with higher value and higher loss risk, aimed at players who completed set one. No time-limited store pressure, since 71% of hits have none.

**Scope.** ~5 weeks · 1 solo developer, with a part-time artist or contractor for the creature and wreck kit · biggest risk: The database rubric puts horror at 4 solo weeks, but a flooding-tide system with creature AI likely adds a week. The larger risk is that the loss mechanic feels punishing without a progression buffer, which hurts retention. The 12.5-day history means longevity is unproven (half-life 2.0 days comes from only 23 early games).

**28-day test.** Kill if: By day 14, peak CCU is under 2,000 (13 of 16 recent entrants cleared that), or the like ratio is below 0.85 (archetype median 0.882), or by day 28 staying power (share of peak kept on days 8-28) is below 0.35 (archetype median 0.563, n=20). · Scale if: By day 28, peak CCU is above the archetype median of 5,336, the like ratio is at least 0.88, staying power is at least 0.56, and 7-day growth is at or above +9.85%. Reaching 20k peak would put it with the 5 recent entrants that became hits. · Watch: Peak CCU vs the median of 5,336 and the 2k bar; Median fav per 1k vs 6.06 for the archetype; Staying power (days 8-28) vs 0.563; Like ratio vs 0.882; Whether new entrants copy the extraction-with-loss hook (entrants_30d is currently 4)

*Components — longevity 0.50, room 0.74, mechanics 0.85, trend 0.72, cost 0.83; cost basis: rubric: base 4 for horror*

---

### 2. rng / PvE — Feed a Goblin: Lucky-Roll Tycoon With a Face
*Adjusted score 0.634 (raw 0.711) · confidence 0.64 · PROVISIONAL · 21 games, 6 hits, 7 entrants in 90 days, est. 3 solo-dev weeks*

**The gap.** Of 21 rng/PvE games, 6 are hits (28.6% hit rate) and median peak is 8,569 CCU, but the top of the list is one-note: Kick a Lucky Block (237,042 peak, only 11,905 now) and Launch a Lucky Block (32,764 peak, 2,497 now) both fade fast. Anime Dice (75,190 peak, 61,510 now) is the only leader still holding most of its peak. The measured winning combo is numbers_go_up|rarity_collection progression (100% of hits vs 47% of other games, lift 1.77) inside the Tycoon genre (67% of hits vs 40%, lift 1.95), yet only 2 of the 6 leaders are tycoon-flavoured builders (Build An Ant Empire, Anime Card Farm). A roll-to-staff tycoon with an original theme is under-served.

**Why now.** Entrants are slowing (7 in the last 90 days vs 11 in the previous 90), but all 7 reached 2k peak, so room is open. Momentum is cooling, though: median 7-day growth is -11.85% and only 2 games sit in the trending top 100, so the entry has to be differentiated rather than a lucky-block clone.

**Build to these constraints**
- progression_type = numbers_go_up + rarity_collection (combined): Every roll result has both a rarity tier and a numeric multiplier that feeds an income number. — *6/6 hits vs 7/15 other games; lift 1.77 (solid).*
- genre_l2 = Tycoon: Rolled creatures staff a plot or base that produces currency. — *67% of hits vs 40% of others; lift 1.95 (moderate, n=6).*
- play_mode = pve: Fully cooperative or solo with no PvP and no social asymmetry. — *6/6 hits pve, global lift 1.54; social_asymmetry=none in 6/6 hits (lift 0.96, so it is a baseline, not an edge).*
- icon_has_face = true: Icon shows a large character face (the goblin). — *6/6 hits vs 8/15 others; lift 1.18 (solid). Icons without a face: 0/6 hits, lift 0.66.*
- borrows_meme_or_ip = meme: Theme leans on a general internet-meme sensibility, not a specific IP or another game. — *50% of hits vs 13% of others; lift 1.30 (moderate).*
- Game Pass pricing: About 5 passes with a minimum near 149 R$ and a median near 300 R$, including a boost pass. — *Hit medians: pass_count 5, min price 149, median price 303 (others: 6, 139.5, 211.5). pass_has_boost is 67% of hits, lift 1.01, so it is a baseline rather than an edge.*
- desc_has_codes = false: No promo-code language in the description. — *83% of hits; lift 1.16 for false vs 0.41 for true (weak on the true side).*
- session_shape = persistent, server_size 7: Persistent sessions, 7-player servers. — *Persistent in 83% of hits (lift 0.93, moderate); server size median 7 for both hits and others, so it matches the field rather than differentiating.*

**Avoid**
- title_pattern = x_rng (e.g. 'Pet RNG'): 0/6 hits vs 20% of other games; lift 0.39 (weak, n small but the direction is clear).
- progression_type = rarity_collection alone (no numbers_go_up): 0/6 hits vs 20% of others; lift 0.48. Rarity only works here when tied to numbers.
- Icon with no face: 0/6 hits vs 47% of others; lift 0.66.
- Codes in the description: Lift 0.41 (weak); the 1 hit that has them is an outlier.
- Anime theme as the hook: Lift 0.79 (weak), and Anime Dice and Anime Card Farm already occupy it. Anime Dice holds 61,510 players now.
- Copying the lucky-block throw/kick/launch verb-noun loop: Kick a Lucky Block is at 5% of its peak (11,905 vs 237,042) and Launch a Lucky Block at 7.6%. The format spikes and fades.
- Hybrid session shape: Lift 0.79 and only 1/6 hits (weak). Stay persistent.

**Concept: Feed a Goblin** — Throw offerings into a chaotic goblin's furnace and roll mismatched creatures that staff your growing junk-workshop.

- Core loop: Drop an offering into the Goblin's Furnace to roll a worker creature with a rarity tier and a numeric multiplier. Place workers on your workshop plots, where they convert scrap into coins. Spend coins on better offerings (higher rarity odds), more plots, and bigger multipliers. Duplicates fuse into a stronger version of the same creature, so numbers keep rising while the collection index fills. Everything is PvE, and nothing is lost if you fail a roll.
- First 60 seconds: The player spawns facing the goblin's furnace and gets a free offering. The first roll resolves within about 10 seconds (guaranteed Common worker), and the worker auto-starts producing coins. By about 45 seconds the player can afford a second roll with a boosted chance of Uncommon, and the HUD shows a collection index with 1 slot filled.
- Social mechanic: Shared 7-player server with a communal 'Goblin Hunger' meter that everyone's offerings fill. When it fills, every player in the server gets a temporary income boost. There is no PvP and no asymmetry. Rare pulls are announced server-wide.
- Monetization: About 5 passes. Target a minimum price near 149 R$ and a median near 300 R$ (hit medians 149 / 303). Include a Luck/Income Boost pass, since pass_has_boost is 67% of hits. VIP is optional (50% of hits vs 33% of others, lift 0.99, so no proven edge). No codes mention in the description.
- Content cadence: Weekly update adding a new creature set plus a new offering type, since the half-life of this archetype is very short (median 2.0 days, n=7, early data). Update frequency is not yet measurable in the database, so treat the cadence as general knowledge.

**Features**
- Roll result = rarity tier + numeric multiplier, mirroring the progression combo (100% of hits, lift 1.77).
- Workshop plots staffed by rolled creatures (Tycoon, lift 1.95).
- Goblin face as the icon and in-game mascot (icon_has_face, lift 1.18).
- Collection index with rarity completion bonuses.
- Fusion of duplicates into stronger variants, so numbers keep rising.
- Server-wide Goblin Hunger meter (cooperative PvE, lift 1.54, no asymmetry).
- Offline coin accrual from placed workers: a test feature only (lift 2.03 but weak, only 2 of 6 hits carry it).
- 5-pass shop priced from 149 to about 300+ R$ including a Luck/Income Boost pass.

**Rewards and retention**
- First minute: Free first roll at about 10 seconds (guaranteed Common), a second roll with improved odds by about 45 seconds, and the first collection-index slot filled.
- First session: 5-8 rolls, first Uncommon/Rare worker, first plot expansion, and one Goblin Hunger meter fill that grants a server-wide boost.
- First week: A full early rarity set (about 60-70% of the index), the first fusion into an upgraded creature, a second workshop tier, and a milestone creature for a 5-day streak.
- Progression system: numbers_go_up + rarity_collection: each creature has a rarity tier (sets the multiplier range) and a level (sets the exact number). Fusion raises the number, higher-tier offerings raise rarity odds, and income = sum of worker numbers x plot bonuses. Pure rarity without numbers is avoided (lift 0.48).
- Retention hook: Day 2: offline accrual coins waiting (offline_accrual lift 2.03, weak evidence, so A/B it) plus an unfinished fusion.
- Retention hook: Day 8: nearing a rarity-set completion bonus in the collection index (progression combo lift 1.77) and a new weekly creature set. Timers/FOMO are neutral (lift 1.04), so use only light limited-time sets rather than leaning on FOMO.

**Scope.** ~4 weeks · 1 scripter/designer plus 1 part-time artist for about 30 creatures and the goblin icon. The database rubric estimates 3 solo weeks for rng + persistent; I added about 1 week for the tycoon plot layer (general knowledge). · biggest risk: Longevity is unproven: the database has only 12.5 days of history, half-life (2.0 days, n=7) comes from games that crashed, and median 7-day growth is -11.85%. The loop may spike and fade like the lucky-block leaders.

**28-day test.** Kill if: By day 14 peak CCU is below 2,000 (all 7 entrants in the last 90 days reached 2k), OR by day 28 staying power (share of peak kept on days 8-28) is below 0.30 vs the archetype median 0.5945, OR like ratio is below 0.90 (median 0.963), OR favorites per 1k is below 3 (median 6.4). · Scale if: Peak CCU of at least 8,569 (archetype median) with staying power at or above 0.59, like ratio at or above 0.95, favorites per 1k at or above 6.4, and 7-day growth better than the archetype median of -11.85%. A peak of 20k or more would put it in the top tier, since only 1 of 7 recent entrants got there. · Watch: Half-life days (archetype median 2.0, so beating it is the real signal); Players now / peak ratio (Kick a Lucky Block sits at about 5%); Median server fill vs the 7-player target; Trending top-100 appearances (archetype has 2 slots); Whether offline accrual lifts day-8 staying power (A/B)

*Components — longevity 0.50, room 1.00, mechanics 0.89, trend 0.33, cost 0.92; cost basis: rubric: base 2 for rng + session_shape=persistent (+1)*

---

### 3. sports / PvP — Tilt Court: cosmetic-progression 5v5 arena sport
*Adjusted score 0.629 (raw 0.696) · confidence 0.66 · PROVISIONAL · 59 games, 9 hits, 8 entrants in 90 days, est. 6 solo-dev weeks*

**The gap.** Sports/PvP has 59 games, 9 hits (15.3% hit rate) and 2 breakouts. The top six by peak are volleyball, soccer, basketball and football (Volleyball Legends 133,002, Blue Lock: Rivals 100,436, Illegal Soccer 74,927). The progression pattern 'cosmetic_only|levels' is carried by 56% of hits but only 12% of the archetype's other games (lift 1.39), so most competitors skip the structure that hits favour. At least 3 of the 8 newest entrants (Turbo Soccer, Street Soccer Pro, Freekick Challenge) are soccer by title, so the field is crowding into one sport rather than into one progression design.

**Why now.** Entrants are not slowing: 8 in the last 90 days vs 7 in the prior 90, all 8 reached 2k peak and 2 reached 20k (Blox League 21,644, Turbo Soccer 21,706). Median 7-day growth is +18.5% (n=49) and 6 trending top-100 slots are held, though the database has only 12.5 days of history, so trend is early.

**Build to these constraints**
- session_shape = rounds: Short fixed-length matches (about 4 min, general knowledge) with a clear win/loss end screen — *100% of hits (9/9) vs 84% of other games; lift 1.22. Hybrid and persistent shapes have 0 hits.*
- genre_l2 = Sports / play_mode = pvp: Plain team-vs-team PvP, no PvE or coop layer — *Sports 89% of hits vs 76% of others (lift 1.57). pvp 56% vs 42% (lift 1.43). pve|pvp has 0 hits.*
- progression_type = cosmetic_only|levels: Account levels that unlock only cosmetics; no stat gains — *56% of hits vs 12% of others (lift 1.39). Pure numbers_go_up has 0 hits (weak evidence).*
- server_size: 10 players per match (5v5) — *Median server size is 10 among hits vs 14 among others; archetype median is 12.*
- desc_has_codes = false: No codes in the description — *100% of hits vs 86% of others (lift 1.16). Games with codes have 0 hits (lift 0.41, weak).*
- title_pattern = descriptive, title length about 27 characters: A descriptive title, such as a name plus a format tag — *100% of hits use descriptive titles. Median title length is 27 among hits vs 19.5 among others.*
- pass_has_vip = true, price ladder: A VIP pass, 5 passes total, cheapest at about 49 Robux, median about 150 — *VIP is present in 78% of hits vs 50% of others, but its global lift is 0.99, so it is table stakes and not a differentiator. Hits show pass_count 5 (others 4), min price 49 (others 99) and median price 150 (others 203.5).*
- icon_has_face = true: A character face on the icon — *56% of hits; global lift 1.18 (moderate). Icons without a face have lift 0.66 (weak, under 3 hits).*

**Avoid**
- progression_type = none: Lift 0.72 globally. 33% of hits carry it, but it is the weakest progression value among the moderately supported ones.
- Description codes / code-driven growth: 0 of 9 hits use them, vs 14% of other games; lift 0.41 (weak evidence, but the direction is clear).
- Brand or anime borrowing as the hook: Brand is 11% of hits vs 40% of other games (lift 0.80). Anime is 33% of hits but lift 0.79. Borrowed IP is also a copy of the leaders' angle (Blue Lock: Rivals).
- Persistent or hybrid session shape, numbers_go_up stat grind: 0 hits in each, with lifts of 0.93, 0.79 and 0.82 (weak evidence).
- Racing or soccer-clone positioning: Racing has 0 hits among 8 games (16% of the archetype's other games). Soccer is where most of the visible entrants are crowding.
- Offline accrual, base defense, or losing progress: These are absent in 100% of hits. Their lifts are 0.92, 0.97 and 0.85, so they add nothing and risk confusing the genre.

**Concept: Tilt Court: 5v5 Arena Sports** — A 5v5 puck-and-paddle sport played on a floating court that physically tilts toward whichever team is crowding one side, so positioning matters as much as aim.

- Core loop: Queue into a 10-player match, which is the median server size for hits. Each round lasts about 4 minutes. Players hit a heavy puck into the opposing goal. The court tilts with team positioning, so the puck rolls toward the crowded side and defenders must spread out. At the end of each match everyone earns XP, even in a loss. XP raises an account level that unlocks only cosmetics: paddle skins, goal-celebration effects, court themes. There is no stat progression and no progress loss. The next match starts from the results screen.
- First 60 seconds: Spawn directly into a match in progress, with bot backfill if the lobby is short. A 10-second prompt explains move, hit and tilt. The first goal or assist awards the first cosmetic (a paddle trail) within about 60 seconds.
- Social mechanic: Parties of up to 5 queue together against another 5 on the same server (no asymmetric roles; 89% of hits have none). A post-match 'Player of the Match' vote gives a visible badge. Trading is excluded because only one hit carries it (weak evidence).
- Monetization: Cosmetic-only. A VIP pass (cosmetic tag, extra court themes, double celebration slots) plus 4 more passes with a 5-pass ladder from about 49 to about 150 Robux (hit medians). No stat boosts: boost passes are not a differentiator (44% of hits vs 40% of others, lift 0.98).
- Content cadence: General knowledge, not measured: a new court theme and cosmetic set every 2 weeks, and a new match modifier monthly. Update frequency is not yet in the database.

**Features**
- Fixed rounds of about 4 minutes with a results screen (rounds: 100% of hits, lift 1.22)
- 10-player matches, 5v5, with bot backfill to hold matches during low-population periods (hit median server size 10)
- Tilting court physics as the original hook (no copying of leader mechanics)
- Cosmetic-only level track with unlocks at every level (lift 1.39)
- Party queue for 1 to 5 friends (play_mode pvp, no asymmetric roles)
- A 5-pass store with a 49 Robux entry point and a VIP pass (hit medians)
- Descriptive title with a tag and a face-on-icon thumbnail (title median 27 chars, icon_has_face lift 1.18)
- Clean description with no codes (lift 1.16)

**Rewards and retention**
- First minute: The first goal or assist awards the Rookie paddle trail and fills the first XP bar to Level 1 within about 60 seconds.
- First session: About 3 matches (about 12 minutes) reach Level 3 and unlock a goal-celebration effect and a court theme preview. Losses still pay XP, so the first session never ends on zero reward.
- First week: Roughly Level 10 after about 2 to 3 hours, unlocking a paddle skin set and a profile badge slot, plus a first Player of the Match badge for active players.
- Progression system: The measured type is cosmetic_only|levels: levels are the gate and cosmetics are the reward. Levels never change puck speed, hit power or hitbox. No rarity tiers or stat numbers exist, since numbers_go_up has 0 hits and cosmetic_only|rarity_collection has 0 hits (lift 0.95).
- Retention hook: Day 2: Level 4 to 5 cosmetic unlock is visible on the level bar after match one, and a first-win-of-the-day XP bonus (general knowledge) gives a reason to return. It is a bonus, not a loss-based streak.
- Retention hook: Day 8: Level 15 unlocks a team crest for parties and a profile showcase. Party loyalty matters because match results are social (pvp lift 1.43). There is no demotion because can_lose_progress=false in 100% of hits.
- Retention hook: Day 8+: biweekly court themes give new cosmetic targets without FOMO timers on level progress (timers lift 1.04 vs 0.97, neutral).

**Scope.** ~6 weeks · One solo developer with contracted UI and VFX, per the database's 6-week sports rubric · biggest risk: Matchmaking liquidity and puck-physics networking at 10 players. If the lobby does not fill, rounds break, which is the one measured hit trait (rounds, lift 1.22). Mitigation is bot backfill and a 5-player party queue.

**28-day test.** Kill if: By day 28, peak concurrent is below 2,000 (all 8 recent entrants cleared 2k; archetype median peak is 2,549), OR days 8-28 staying power is below 0.40 (archetype median 0.6325), OR like ratio is below 0.80 (archetype median 0.865). · Scale if: Peak is 10,000 or more AND staying power is at or above 0.63 AND like ratio is at or above 0.87. A peak at or above 20,000 (2 of 8 entrants reached it) is a breakout signal that justifies a content team. · Watch: Days 8-28 staying power vs 0.6325 (archetype median). Note that the median half-life of 2.0 days comes only from games that crashed, so treat it as a floor, not a target.; Favorites per 1k vs 2.41 (archetype median); Server fill vs the 10-player target; Trending top-100 appearance (6 slots held by the archetype now); Any new entrants in tilt/sport variety that could change the gap; Share of visits from friends/party queues vs solo

*Components — longevity 0.50, room 0.97, mechanics 0.65, trend 0.66, cost 0.67; cost basis: rubric: base 6 for sports*

---
