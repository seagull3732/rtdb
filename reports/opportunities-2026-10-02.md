# Opportunity engine — 2026-10-02

Archetypes ranked by a weighted score (longevity 25%, room to enter 25%, mechanics 20%, trend 20%, cost 10%). Confidence reflects how much data each score rests on; briefs marked PROVISIONAL rest on less than 28 days of history.

| # | Archetype | Adjusted | Raw | Confidence | Games | Hits | Entrants 90d | Est. weeks | Brief |
|---|---|---|---|---|---|---|---|---|---|
| 1 | horror / Co-op PvE | 0.608 | 0.7 | 0.54 | 43 | 8 | 10 | 4 | Drowned Town Salvage: 25-Player Co-op Horror Rounds |
| 2 | round_pvp / PvP | 0.605 | 0.695 | 0.54 | 82 | 9 | 14 | 6 | Small-Lobby Round Brawler With Cosmetic-Only Progression |
| 3 | rng / PvE | 0.585 | 0.743 | 0.35 | 14 | 4 | 3 | 4 | Unclaimed: a lost-luggage tycoon with rarity rolls |

### 1. horror / Co-op PvE — Drowned Town Salvage: 25-Player Co-op Horror Rounds
*Adjusted score 0.608 (raw 0.7) · confidence 0.54 · PROVISIONAL · 43 games, 8 hits, 10 entrants in 90 days, est. 4 solo-dev weeks*

**The gap.** Horror / Co-op PvE has 43 games and 8 hits (18.6% hit rate, 1 breakout) with a median peak of 3,479 CCU and 377,861 players now. Its leaders are survival, chase and escape games: 99 Nights in the Forest (149,625 peak), DOORS (50,098), Evade (42,117) and Piggy (39,164). Recent entrants cluster on the 'anomaly caretaker' premise: Animal Hospital (Anomaly) peaked at 35,432, Animal Daycare (Anomaly) at 11,877 and 7 Days Cat-Sitting at 22,957. Nobody in the database's recent entrants offers a shared-server, round-based salvage/extraction loop with a hard timer.

**Why now.** Entrants rose from 6 to 10 over the last two 90-day windows, and 9 of the 10 reached a 2k peak (2 reached 20k+), so the space is still rewarding new entrants with 5 trending top-100 slots. The risk is that the newest wave is converging on one premise, so a different theme matters. The database has only 2.1 days of history, so there are no growth or longevity numbers yet.

**Build to these constraints**
- session_shape = rounds: Fixed 8-10 minute rounds with a lobby and a results screen (the round length is general knowledge, not measured) — *88% of hits vs 63% of the archetype's other games; global lift 1.43 (solid)*
- can_lose_progress = true: Salvage carried in a round is lost if you drown, while banked items and cosmetics are safe — *62% of hits; global lift 1.53 (moderate). The share is the same among other games (63%), so it is a global-lift signal rather than a within-archetype separator.*
- play_mode = coop|pve: All players on one side against the environment, with no PvP — *100% of hits and 100% of other games, so it is the entry ticket and not a differentiator; global lift 0.70 (solid)*
- icon_has_face = true: A creature or diver face on the icon — *88% of hits vs 74% of others; lift 1.15 (solid). 0 of 8 hits had a faceless icon (lift 0.72).*
- desc_has_codes = false: No promo-code text in the description — *100% of hits vs 94% of others; lift 1.17 (solid)*
- pass_has_boost = false: No gameplay-boost game passes — *50% of hits vs 17% of others; lift 1.22 (moderate)*
- pass pricing and server size: 3-4 passes, cheapest about 150 Robux, median about 300; server size 24-28 — *Hits' median pass price is 299 vs 149 for others, minimum 149.5 vs 64.5, server size 27.5 vs 24, pass count 3.5 vs 4*
- title_pattern = descriptive: A descriptive title of about 20 characters — *100% of hits vs 97% of others; hits' median title is 20.5 characters. This is a hygiene trait; its lift is 0.93, so it gives no advantage.*

**Avoid**
- Story genre (genre_l2 = Story): 0 of 8 hits vs 31% of the archetype's other games. Weak evidence (fewer than 3 hits carry the value), but it is consistent with the rounds finding.
- persistent session shape: 12% of hits vs 34% of others; lift 0.86 (weak). Rounds are the hit shape.
- Faceless icon: 0 of 8 hits; lift 0.72
- Pass boosts (pass_has_boost = true): 25% of hits vs 63% of others; lift 0.93 (weak), and the pay-for-power direction is opposite to the hit pattern.
- Borrowing another game's identity: Only 38% of hits borrow from another game vs 66% of non-hits. The global lift is 1.41, so the signal is mixed. The leader-cloning wave is crowded and we want an original theme anyway.
- Base defense: 12% of hits; lift 0.87 (weak). It does not fit the exploration and extraction loop.
- Level-only progression: Only 1 of 8 hits (lift 0.24, weak). Use cosmetics-led progression instead.
- Offline accrual / idle mechanics: 0% of hits and 0% of others carry it, so there is no evidence it works in this archetype.

**Concept: Drowned Town Salvage** — Twenty-five players dive a sunken town during a shared low-tide window, hauling relics up before the water returns while something in the flooded streets hunts the stragglers.

- Core loop: Each round starts at low tide, when streets are exposed and a tide timer counts down. Players spread out, search buildings for relics and haul them back to the surface pier, carrying them in a limited-capacity pack. Carried relics are lost if you drown or get taken, but banked relics are safe, which gives the risk-and-lose-progress tension. A roaming 'Drowned' creature escalates as the tide rises, and the team hits a shared quota to unlock a better dive next round. Players who are downed can be revived by teammates sharing air.
- First 60 seconds: The player spawns on the pier with a lantern and a diver helmet and is told in one line to grab a relic before the tide comes in. A relic sits within 10 seconds' walk, and the first flooded building has a scripted creature glimpse. The player makes a first bank on the pier and gets a cosmetic reward before the first round timer is half done.
- Social mechanic: Help asymmetry: a shared air supply lets players donate air to a downed teammate, and a revive gets a tracked 'Lifeline' count and title. Teammates can also shout out relic locations on a ping wheel. No PvP, so everyone is on the same side.
- Monetization: A VIP pass at about 299 Robux (50% of hits carry VIP vs 40% of others) that grants a chat tag and cosmetic extras, plus cosmetic diver suit and lantern packs starting around 149 Robux. No boost passes and no pay-for-power. Codes are kept out of the description.
- Content cadence: Ship one new flooded district (map slice and creature variant) every 2 weeks and a seasonal cosmetic tide chart monthly. General knowledge: frequent updates are the norm for the leaders, but the database has no update-frequency data yet.

**Features**
- Round-based dive loop with a 24-28 player server and a visible tide timer (rounds: 88% of hits, lift 1.43; hits' median server size 27.5)
- Carry-at-risk pack: unbanked relics are lost on drowning (can_lose_progress lift 1.53)
- Shared air and revive mechanic with a Lifeline stat (social_asymmetry 'help' in 62% of hits vs 40% of others)
- A recognizable creature face for the icon and thumbnail (icon_has_face lift 1.15; 0 of 8 hits had a faceless icon)
- Cosmetic-only diver suits and lanterns, with level-gated unlocks (cosmetic_only|levels lift 1.94, weak)
- Escape-flavored extraction objective: reach the surface pier before the water closes (Escape genre lift 7.39, weak, 2 of 8 hits)
- 3-4 passes priced 149-299 Robux with no boosts (hits' median price 299; pass_has_boost false lift 1.22)
- Clean store page with no codes in the description (lift 1.17)

**Rewards and retention**
- First minute: First relic and first bank at about 45-60 seconds, which unlocks a starter lantern skin.
- First session: After 3-4 rounds, the player levels up enough to unlock the first diver suit and a Lifeline title for a first revive.
- First week: Complete the first district's relic set for a themed suit, and reach a level where the second district opens (cosmetic reward only).
- Progression system: Cosmetic_only plus levels: levels come from banked relic value and revives, and each level unlocks cosmetics (suits, lanterns, helmets, emotes). Rarity affects relic bank value, not player power, so the numbers never create a power gap between veterans and newcomers. Evidence is weak (cosmetic_only is 25% of hits vs 3% of others, lift 2.59; cosmetic_only|levels lift 1.94, each fewer than 3 hits).
- Retention hook: Day 2: a daily rotating 'tide chart' that changes the relic layout and creature behavior, plus the loss of unbanked salvage, which drives a retry (can_lose_progress lift 1.53).
- Retention hook: Day 8: a weekly district challenge with a cosmetic chain and a Lifeline leaderboard, which rewards the helping behavior seen in 62% of hits.
- Retention hook: Any limited-time cosmetics should be optional: timers/FOMO appear in only 38% of hits but with lift 1.29, so test them rather than rely on them.

**Scope.** ~5 weeks · 1 solo dev or 2 people (scripter plus builder/artist); the database rubric gives 4 solo weeks for horror, and I add 1 week as my own judgment for the 24-player rounds, revive and carry systems. · biggest risk: A 25-player round needs a minimum player count to feel scary, and a low-CCU launch would produce empty servers. The mitigation is a bot or NPC fill and a squad lobby. This is a general-knowledge risk; the database does not measure it.

**28-day test.** Kill if: By day 28 peak CCU is under 2,000 (9 of the last 10 entrants cleared it) and the like ratio is under 0.85 (archetype median 0.895), or favorites per 1k visits are under 3 (median 5.06). Also kill if days 8-28 staying power falls below about 0.25 of peak (a threshold from general knowledge, since the database has no staying-power baseline for this archetype). · Scale if: Peak CCU is at or above the archetype median of 3,479 by day 28, with like ratio at or above 0.895, favorites at or above 5.06 per 1k, and staying power above about 0.4. Go all-in on content if peak reaches 20k+, which only 2 of 10 recent entrants did. · Watch: Peak CCU and players_now at days 7, 14 and 28 compared with the 2k and 3,479 lines; Like ratio and favorites per 1k visits against the archetype medians; Staying power (share of peak kept on days 8-28) and half-life once the database has the history; 7-day and 28-day growth, which are currently null in the archetype data; Whether more 'anomaly caretaker' entrants arrive (entrants_90d currently 10 vs 6 in the previous window)

*Components — longevity 0.50, room 0.87, mechanics 0.73, trend 0.65, cost 0.83; cost basis: rubric: base 4 for horror*

---

### 2. round_pvp / PvP — Small-Lobby Round Brawler With Cosmetic-Only Progression
*Adjusted score 0.605 (raw 0.695) · confidence 0.54 · PROVISIONAL · 82 games, 9 hits, 14 entrants in 90 days, est. 6 solo-dev weeks*

**The gap.** round_pvp has 82 games and 9 hits (11.0% hit rate). Battlegrounds & Fighting is 67% of those hits but only 22% of the other games (lift 4.93). The top-peak leaders are old: Murder Mystery 2 (209k peak, 2014), Jujutsu Shenanigans (141k, 2022) and The Strongest Battlegrounds (48k, 2022). Most recent entrants are trivia, word or party-style games such as STOP! Word Duel (5.9k peak) and 50 Player BINGO (5.0k). So there is room for a fresh, round-based, small-lobby fighter that is not an anime or IP skin.

**Why now.** Entrants rose to 14 in the last 90 days from 10 in the prior 90. 12 of the 14 reached 2k peak CCU and 1 became a hit (Ball VS Ball, 37.8k peak, created 2026-08-12), so the space is open but not empty. The archetype holds 10 trending top-100 slots and 628,656 players now. Longevity and growth data are missing, so the trend read is thin.

**Build to these constraints**
- session_shape = rounds: Fixed rounds of about 3-4 minutes with a clear winner each round (the round length is general knowledge, not measured) — *78% of hits vs 89% of other games, but lift vs controls is 1.43 (solid). Rounds are the baseline, not a differentiator within the archetype.*
- genre_l2 = Battlegrounds & Fighting: Build the combat as a fighting or brawler game rather than a party or trivia round — *67% of hits vs 22% of other games, lift 4.93 (solid).*
- play_mode = pvp (pure): Pure PvP, with no party-minigame framing — *56% of hits vs 33% of others, lift 2.18. 'party|pvp' is 41% of other games and 0% of hits (weak: n=9).*
- progression_type = cosmetic_only: All progression is cosmetic and gives no stat advantage — *44% of hits vs 19% of others, lift 2.59 (moderate).*
- server_size: About 16 players per server, with a ceiling of 20 — *Median server size is 16 among hits vs 22 among other games. The archetype median is 20.*
- pass_has_vip = true, pass_has_boost = false: 4 passes: a VIP pass plus cosmetic passes, priced around 114-190 Robux, with no boost passes — *VIP is 67% of hits (lift 1.04). No-boost is 56% of hits vs 22% of others (lift 1.22). Median pass count is 4 vs 3 among others. Median pass price is 189.5 vs 274 among others, and the median minimum is 113.5.*
- can_lose_progress = false: Permanent progress can never be lost. Any 'steal' mechanic applies only inside a round. — *100% of hits (9/9) vs 95% of others, lift 0.92 (solid). This is a floor trait rather than a differentiator.*
- desc_has_codes = false: No codes in the game description — *78% of hits, lift 1.17 (solid). Codes = true has lift 0.35 (weak: fewer than 3 hits).*

**Avoid**
- pass_has_boost = true (pay-for-power passes): Only 33% of hits carry it vs 63% of other games (lift 0.93). It pairs badly with the cosmetic_only trait (lift 2.59).
- party|pvp mode / minigame-collection framing: 41% of other games use it and 0 of 9 hits do (weak, n=9). It is also where the recent entrants are crowded.
- Large lobbies above 22 players: Hit median server size is 16 vs 22 for other games. Large lobbies may dilute fights (an interpretation, not measured).
- rarity_collection as the sole progression: Lift is 0.39, with only 1 hit carrying it (weak). Keep rarity on cosmetics only.
- Description codes: Lift 0.35 on weak evidence (fewer than 3 hits).
- A copy of the Jujutsu, anime or Murderers-vs-Sheriffs formula: Borrowing another game's IP has only moderate support (other_game is 33% of hits, lift 1.41). The leaders already own those slots, and 12 of 14 entrants reached 2k but only 1 was a hit.

**Concept: Lowtide Brawl** — Sixteen fighters on a drowning harbor arena where the tide pulls the floor out from under you every 40 seconds, and the last one standing keeps the tide's pearl.

- Core loop: A round starts with 16 players on a large harbor of docks and boats. Every 40 seconds the tide recedes or floods a section, so the arena shrinks, changes shape and opens new routes. Each player has one of a few kits with four moves, and fights are short melee skirmishes with knockback into the water. Players grab a round-scoped 'pearl' from whoever holds it, which creates a chase target and a comeback mechanic. The last player standing or the pearl holder at the final tide wins. Between rounds there is a 20-second lobby for cosmetic equipping and queueing the next round.
- First 60 seconds: The player spawns directly into a short 8-player practice tide with bots, learns the four moves and the knockback-into-water rule, and gets knocked into the water once. The first pearl grab and the first cosmetic drop come in the same minute, before the first real round starts.
- Social mechanic: Take asymmetry, scoped to the round: you take the pearl from another player, and only for that round. No permanent progress is ever lost (can_lose_progress = false in 100% of hits). 'Take' appears in 33% of hits at lift 1.66 (moderate). Rivalry shows up through a post-round replay ('who knocked you off') and a one-tap rematch queue.
- Monetization: Four passes, all cosmetic or social: a VIP pass (name tag, queue priority for friends, lobby flair), a trail pack, an emote pack and a kit-skin pack. Price at roughly 114-190 Robux (hit medians: min 113.5, median 189.5). No boost, XP or power passes.
- Content cadence: General knowledge, not measured: ship a new harbor map or tide pattern every 2 weeks and a cosmetic season every 4 weeks. The database has no update-frequency data yet (it needs 14+ days of change-log history).

**Features**
- 16-player servers, capped at 20 (hit median server size 16 vs 22 for others).
- Rounds of about 3-4 minutes with a tide-phase timer (session_shape rounds, lift 1.43).
- Fighting kits with four moves each and knockback into water (Battlegrounds & Fighting, lift 4.93).
- Round-scoped pearl 'take' mechanic with no permanent loss (social_asymmetry take, lift 1.66; can_lose_progress false).
- Cosmetic-only unlocks: trails, kit skins, emotes and victory poses (cosmetic_only, lift 2.59).
- Four-pass shop with VIP and cosmetic passes, no boosts, priced around 114-190 Robux.
- Post-round replay with one-tap rematch queue.
- Icon with a character face on it (icon_has_face = true, 67% of hits, lift 1.15), using descriptive title wording such as 'Lowtide Brawl' (descriptive titles are 100% of hits).

**Rewards and retention**
- First minute: A first cosmetic (a basic trail) drops after the practice tide ends, before the first real round, to establish the cosmetic-reward loop.
- First session: Every round pays 'tide marks' for survival time, pearl time and knockouts. After about 5 rounds the player has enough for a common kit skin and sees a progress bar toward an uncommon one.
- First week: Mastery marks per kit unlock kit-specific cosmetics (stance, victory pose). A weekly season track gives one featured cosmetic with no stat effects.
- Progression system: cosmetic_only (lift 2.59, moderate). Tide marks buy cosmetics, and rarity (common/uncommon/rare/epic) is a visual tier only, never a stat. There are no player levels with power effects, and rarity-only collection is avoided (lift 0.39, weak).
- Retention hook: Day 2: a 'daily tide' with a rotating modifier and one cosmetic shard for the first win. This is a light timer, because has_timers_or_fomo = true has lift 1.29 but is present in only 33% of hits (moderate), so keep timers cosmetic and low-pressure.
- Retention hook: Day 8: the weekly season cosmetic is about 60% complete and a new kit mastery tier unlocks, so players return to finish both. The cosmetic_only trait (lift 2.59) carries the retention argument.
- Retention hook: Ongoing: rematch queue and friend VIP queue priority for social pull (VIP lift 1.04).

**Scope.** ~7 weeks · 1 solo developer plus a part-time artist or contract animator. The 6-week base is the database rubric for round_pvp; the extra week is my allowance for combat feel and netcode. · biggest risk: Combat feel and netcode are the product here, and the profile has no longevity data. Staying power is null and the only half-lives (1.5 days, n=2) come from games that crashed, so a strong week-1 peak could still fade fast.

**28-day test.** Kill if: By day 28, any of the following: peak CCU below 2,000 (the level 12 of 14 recent entrants reached), like ratio below 0.80 (archetype median is 0.8745), or staying power (share of peak kept on days 8-28) below 0.20. The staying-power threshold is a judgment call because the database has no archetype benchmark yet. Also kill if half-life is under 3 days. · Scale if: By day 28: peak CCU at or above the archetype median of about 2,940, like ratio at or above 0.875, favorites per 1k visits at or above 3.3 (archetype median 3.30), and staying power at or above 0.35 (judgment). Treat 20k peak as breakout territory, which only 1 of 14 recent entrants reached. · Watch: Peak CCU and players_now vs the archetype median peak of 2,938.5.; Like ratio vs the 0.8745 median.; Favorites per 1k visits vs the 3.30 median.; Staying power (days 8-28) and half-life days as they become measurable.; 7-day and 28-day growth, which are currently null for the archetype.; Recent entrants (e.g. Ball VS Ball, Swift Modded Rivals) to see whether a new fighter or round-PvP entrant crowds the space.

*Components — longevity 0.50, room 0.92, mechanics 0.57, trend 0.80, cost 0.67; cost basis: rubric: base 6 for round_pvp*

---

### 3. rng / PvE — Unclaimed: a lost-luggage tycoon with rarity rolls
*Adjusted score 0.585 (raw 0.743) · confidence 0.35 · PROVISIONAL · 14 games, 4 hits, 3 entrants in 90 days, est. 4 solo-dev weeks*

**The gap.** RNG / PvE has 14 games and 4 hits (28.6% hit rate), but 0 breakouts and a median peak of only 2,164 CCU. Players now total 121,747, and the newest leader, Anime Dice, holds 68,010 of them (56%). All 4 hits combine 'numbers_go_up' with 'rarity_collection' progression (lift 2.00 vs 50% of the other games), and 75% of hits are Tycoon (lift 1.53 vs 30% of others). The leaders (Anime Dice, Anime Card Farm, Kick a Lucky Block, Build An Ant Empire, Roll a Fisherman, Roll A Gnome) are all roll-and-collect games, so a roll loop wrapped in a real tycoon structure with a clear in-world reason to roll is not yet crowded among them.

**Why now.** Entrants fell from 9 (previous 90 days) to 3 (last 90 days), but all 3 reached 2k CCU and 1 passed 20k (Anime Dice, 76,039 peak), so players are active and the field is thin. There are 3 trending top-100 slots, but the database has only 2.1 days of history, so trend and longevity are unproven.

**Build to these constraints**
- progression_type: Combined numbers_go_up + rarity_collection: rarity sets the base income of each item, and upgrades multiply it — *4/4 hits vs 5/10 other games; lift 2.00 (moderate evidence)*
- genre_l2: Tycoon structure: a base or shop where collected items are displayed and produce income — *75% of hits vs 30% of other games; lift 1.53 (moderate). Incremental Simulator is only 25% of hits despite its 1.77 lift (weak)*
- play_mode / base_defense / can_lose_progress: PvE, no base defense, and progress can never be lost — *4/4 hits share all three; global lifts 1.24, 1.01 and 0.92. Moderate evidence, but the archetype has no variation to learn from, so these are conventions rather than proven drivers*
- desc_has_codes: No codes advertised in the description — *100% of hits vs 80% of other games; lift 1.17 (moderate)*
- icon_has_face: The icon shows a character face — *4/4 hits vs 5/10 other games; lift 1.15 (moderate)*
- offline_accrual: Earnings accrue while the player is away, with a cap — *50% of hits; lift 1.65 (weak: fewer than 3 hits carry this value). It also adds +1 week to the build cost*
- gamepass pricing: 6 passes, including at least one boost pass, minimum price 99 R$ and median 299 R$ — *Hits: median 6 passes, median price 299, minimum 99. Others: 199 median, 80 minimum. Boost passes are on 75% of hits (lift 0.93, so they are not a differentiator)*
- server_size: 8 players maximum — *Hits' median server size is 7 (others 9); the archetype median is 8. Weak numeric signal*

**Avoid**
- progression_type = rarity_collection alone (no numbers-go-up layer): 0/4 hits vs 30% of other games; lift 0.39. A pure collection game without income scaling is where the non-hits cluster.
- icon_has_face = false: 0/4 hits vs 50% of other games; lift 0.72.
- Anime as the hook: Anime is borrowed by 50% of hits but its lift is 1.02, so it adds nothing measurable. Two of the six leaders already use it, including the 76k-peak leader, so a new anime title competes directly with them.
- Copying another game's setting (other_game borrowing, 'x_rng' titles): 0/4 hits use either. Lifts are 1.41 and 0.96, both weak. Following the leaders' dice, lucky-block, ant, fisherman or gnome themes means competing with them head on.
- session_shape = hybrid: Lift 0.72 (1 hit, weak). Keep the game persistent, which 75% of hits are.
- Hard FOMO timers as the core hook: The evidence is split: timers_or_fomo = true has lift 1.29 but is on only 25% of hits, and false has lift 0.78 on 50% of hits. Neither is established, so do not make timers the retention mechanism.

**Concept: Unclaimed: Lost Luggage Depot** — Run a lost-luggage depot where every suitcase on the belt is a rarity roll, and the odd items you unpack become the stock that earns your shop income.

- Core loop: A conveyor belt delivers suitcases. The player opens them to roll an item of a given rarity, which is the RNG layer. Each item sits on a display shelf in the player's depot and earns income that scales with its rarity (rarity_collection + numbers_go_up). Income buys faster belts, better luck, extra shelf slots and new rooms (Tycoon structure). Completing a themed set, such as 'Beach Trip' or 'Expedition', gives a permanent multiplier. The game is PvE with no base defense, and nothing is ever lost.
- First 60 seconds: The player spawns at the belt and is told by a cartoon baggage-handler (the icon face) to open the first case. The first roll is a guaranteed uncommon item. The player places it on a shelf and sees the first income tick before 30 seconds. The second suitcase is a real roll, and the first upgrade is affordable by about 60 seconds.
- Social mechanic: Servers hold up to 8 players, matching the archetype median. Players share a luck aura: each other player in the server adds a small luck bonus for everyone. There is also a gift-swap table for duplicates. Both are cooperative with no asymmetric roles, because all 4 hits have social_asymmetry = none.
- Monetization: 6 gamepasses with a 99 R$ minimum and 299 R$ median: auto-open 199, 2x cash 299, luck 299, extra shelf row 399, VIP 99 (VIP is on 50% of hits, lift 1.04), and a premium belt skin 599. At least one is a boost pass, matching the 75% of hits that have one. Codes are not advertised in the game description.
- Content cadence: General knowledge, not from the profile: ship a new set of 8-10 items every week. Each month adds a new depot wing, which is a new rarity tier and shelf type. The database has no update-frequency data yet (14+ days of change log needed), so this cadence is untested.

**Features**
- Conveyor-belt suitcase opening with a 7-tier rarity table (the rarity_collection layer, lift 2.00 when combined with income scaling)
- Shelf display with per-item income that scales with rarity (numbers_go_up layer)
- Tycoon depot expansion: new rooms, shelves and belts bought with income (Tycoon, lift 1.53)
- Offline accrual with a cap of about 8 hours and a collect-on-return animation (lift 1.65, weak)
- Collection index with set-completion multipliers (rarity tied to permanent power)
- Co-op luck aura and duplicate swap table in 8-player servers (server size median 8)
- No progress loss: failed or low rolls always yield something sellable (can_lose_progress = false)
- Face-forward icon of the baggage handler, and a title in a verb-a-noun style such as 'Claim a Suitcase' as an alternative (lift 1.46, weak)

**Rewards and retention**
- First minute: A guaranteed uncommon item at about 10 seconds, the first shelf income tick before 30 seconds, and the first belt-speed upgrade at about 60 seconds.
- First session: Within 10-15 minutes the player reaches rare tier, opens a second room, and gets 30-40% of the first set in the collection index. The first auto-open pass is shown as an optional purchase.
- First week: Complete 2-3 sets for permanent multipliers, unlock the third and fourth rooms, and chase one 'epic' item (about 1-in-500 on the base roll table). General knowledge, not measured.
- Progression system: numbers_go_up|rarity_collection (4/4 hits, lift 2.00). Each rarity tier has a base income number. Upgrades (belt speed, luck, shelf count) raise the numbers. Set completion gives permanent multipliers, so rarity and numbers feed each other and neither works alone.
- Retention hook: Day 2: capped offline earnings are waiting on return (offline_accrual, lift 1.65, weak) plus one unopened suitcase ready to claim.
- Retention hook: Day 8: collection index sets that need a rare item from the week-1 table to complete, plus the next weekly item set, giving a concrete numbers-and-rarity goal (progression_type lift 2.00).
- Retention hook: Day 8: a co-op luck aura that is stronger in full 8-player servers, giving a social reason to return (server size 8).

**Scope.** ~4 weeks · 1 developer, with art for the item set bought or commissioned. The database cost rubric is base 2 for rng + 1 for persistent session shape + 1 for offline accrual = 4 solo weeks. · biggest risk: Longevity is unmeasured (2.1 days of history, no staying-power or half-life data), and 0 breakouts exist in the archetype. The hit pattern comes from only 4 hits, and 56% of current players sit in one game. The recipe may be a coincidence of small numbers.

**28-day test.** Kill if: By day 14 the game's peak is below 500 CCU (about a quarter of the 2,164 archetype median), or like ratio is below 0.93 (under the lowest listed leader, Roll A Gnome at 0.932), or by day 28 staying power (share of peak kept on days 8-28) is below 0.25. The staying-power floor is a judgment call, because the archetype has no measured median. · Scale if: By day 28 peak is at or above 2,164 CCU, like ratio is at or above 0.972 (archetype median), favorites are at or above 8.8 per 1k (archetype median 8.771), and staying power is at or above 0.4 with positive 7-day growth. A peak above 20k is the breakout case, as Anime Dice showed. The staying-power threshold is a judgment call. · Watch: Peak CCU against the 2,164 median, and the share of players in servers of 8; Like ratio (archetype median 0.972) and favorites per 1k (8.771); Staying power on days 8-28 and half-life, once the database has enough history; Day-1 pass conversion on the 299 R$ median pass, and whether offline-accrual players return on day 2; Whether Anime Dice's share of the archetype falls or keeps growing, as a read on saturation

*Components — longevity 0.50, room 1.00, mechanics 0.83, trend 0.59, cost 0.83; cost basis: rubric: base 2 for rng + session_shape=persistent (+1), offline_accrual=true (+1)*

---
