# Opportunity engine — 2026-10-05

Archetypes ranked by a weighted score (longevity 25%, room to enter 25%, mechanics 20%, trend 20%, cost 10%). Confidence reflects how much data each score rests on; briefs marked PROVISIONAL rest on less than 28 days of history.

| # | Archetype | Adjusted | Raw | Confidence | Games | Hits | Entrants 90d | Est. weeks | Brief |
|---|---|---|---|---|---|---|---|---|---|
| 1 | horror / Co-op PvE | 0.656 | 0.765 | 0.59 | 49 | 13 | 11 | 4 | Low Tide Salvage: Round-Based Co-op Horror Extraction |
| 2 | rng / PvE | 0.609 | 0.747 | 0.44 | 16 | 4 | 4 | 4 | Run a Haunted Hotel: Tycoon-Fused Roll Game |
| 3 | sports / PvP | 0.609 | 0.713 | 0.51 | 51 | 7 | 7 | 6 | Round-Based 5v5 Ice Curling Brawler for Roblox |

### 1. horror / Co-op PvE — Low Tide Salvage: Round-Based Co-op Horror Extraction
*Adjusted score 0.656 (raw 0.765) · confidence 0.59 · PROVISIONAL · 49 games, 13 hits, 11 entrants in 90 days, est. 4 solo-dev weeks*

**The gap.** Horror / Co-op PvE has 49 games and 13 hits (26.5% hit rate, median peak 5,516), and 10 of its 11 entrants in the last 90 days reached a 2k peak. The top slots belong to 99 Nights in the Forest (peak 384k), Dandy's World (319k) and DOORS (123k), and the two biggest games hold about 47% of the 730,917 players now. The recent entrants cluster on animal-care and anomaly themes (Animal Hospital (Anomaly), Animal Daycare (Anomaly), 7 Days Cat-Sitting, The CAT). Nothing in the list is a short-round extraction game with a tethered 'support vs. diver' split, even though 85% of hits are round-based (lift 1.24) and 77% can lose progress (lift 2.41).

**Why now.** Entrants rose from 7 to 11 versus the previous 90 days, and 13 titles sit in the trending top 100, so demand is real but the animal-anomaly theme is getting crowded. The database has only 5.5 days of history, so there are no growth or retention readings yet.

**Build to these constraints**
- session_shape = rounds: Fixed 5-7 minute tide rounds with a lobby between them — *85% of hits vs 61% of other games; lift 1.24 (solid)*
- can_lose_progress = true: Unbanked salvage is lost if the squad wipes or misses extraction — *77% of hits vs 56% of others; lift 2.41, the strongest solid trait in the profile*
- play_mode = coop|pve: Squads of 4 against AI threats, with no PvP — *92% of hits; 89% of others, so this is table stakes, not a differentiator (lift 0.91)*
- social_asymmetry = help: Diver and surface-operator roles that depend on each other — *54% of hits vs 33% of others, a 21-point gap; global lift is only 0.96, so treat it as an archetype-specific lean*
- pass_has_boost = false: No gameplay-boost game passes — *54% of hits vs 14% of others have no boost pass; only 23% of hits have one vs 61% of others. Global lift 1.10*
- desc_has_codes = false, offline_accrual = false, title_pattern = descriptive: No codes in the description, no idle earnings, a plain descriptive title of about 18 characters — *100% of hits on all three; lift 1.16 for no codes, 0.94 and 0.96 for the others, so these are hygiene and not a source of edge. Median hit title is 18 chars*
- genre_l2 = Escape (extraction flavour): Each round ends with a timed escape to the surface — *23% of hits (3 of 13) vs 14% of others; lift 8.30, moderate evidence*
- pass pricing: 3 passes, cheapest 100 R$, median about 174 R$ — *Hits: median 3 passes, min price 100, median price 174. Others: 4 passes, min 79, median 150*

**Avoid**
- genre_l2 = Story: 33% of non-hit games are Story but 0 of 13 hits are (lift 0.23, weak evidence). Linear story content is costly and is not where the hits are.
- Boost game passes: Only 23% of hits have a boost pass vs 61% of other games. They correlate with non-hits in this archetype.
- Persistent open-world session shape: Only 15% of hits (2 of 13) are persistent vs 33% of others (weak evidence, lift 0.93). Rounds are the clear winner.
- Levels or rarity-collection progression: Levels have lift 0.39 and levels|rarity_collection 0.52, both weak with 1 hit each. Do not build a stat-treadmill economy.
- Animal-care / anomaly-spotting theme: Four of the recent entrants fit this pattern (general-knowledge reading of their names). Cloning it competes directly with Animal Hospital (Anomaly), which has an 80k peak.
- FOMO timers and base defense as the core: 77% of hits have no timers or FOMO. Base defense is a minority feature (23% of hits, moderate evidence), so do not make it the core loop.

**Concept: Low Tide Salvage** — Four players have 6 minutes of low tide to loot a drowned town while something that hunts by sound waits in the water, and only the squad's tethered surface operator can see the tide coming.

- Core loop: Each round the tide drops and a street of the sunken town is exposed. Two divers enter and grab salvage, while two operators on the pier run the winch, sonar and tide-gate. Divers can see the threat only as faint sonar pings, and operators can see the map and tide level but not the loot. Sprinting and splashing make noise that draws the hunter. At extraction, salvage in the winch crate is banked, and anything still carried is lost if the diver drowns or the squad wipes. Banked salvage buys cosmetics between rounds.
- First 60 seconds: The player spawns on a pier with a lantern, a 15-second guided tutorial tide, and a partner already tethered to them. The first salvage item is within 10 seconds. At about 40 seconds the first hunter ping appears and the operator shouts a warning through a prompt-based ping wheel, so the player learns right away that teammates matter.
- Social mechanic: Diver and operator are bound by a tether. The operator controls slack, winch pull-back (a rescue that costs the diver their carried load) and tide-gate timing. Revives need a second player. Roles swap every round, so nobody is stuck as support.
- Monetization: Cosmetic-only. Passes follow the archetype's measured pricing: a VIP pass (46% of hits have one) at about 199 R$, a 100 R$ cosmetic lantern pack and a 174 R$ diver-suit pack. No boost passes, no gameplay-affecting passes, no codes, and no idle income.
- Content cadence: Launch with one district, 3 hunter types and 2 operator tools. Add a new district and one hunter every 2 weeks, and a limited-run cosmetic set monthly. The database has no update-frequency data yet (it needs 14+ days of change-log), so this cadence is general knowledge and not measured.

**Features**
- 5-7 minute tide rounds with a lobby between them (rounds: 85% of hits, lift 1.24)
- Unbanked salvage lost on drowning or wipe (can_lose_progress: 77% of hits, lift 2.41)
- Tethered diver/operator split with rescue-winch trade-offs (social_asymmetry = help: 54% of hits vs 33%)
- Mandatory timed extraction at the end of each round (Escape genre: 23% of hits, lift 8.30)
- Server cap of 25 with 4-player squads (median hit server size is 25)
- Sound-based hunter AI that creates tension without a story campaign (avoids Story: 0 of 13 hits)
- Cosmetic-only shop and 3 passes starting at 100 R$, with no boost passes and no codes
- Monster-face icon with no text (icon_has_face = true: 69% of hits; no text: lift 1.15, moderate)

**Rewards and retention**
- First minute: The first salvage item banks at about 30 seconds, and a free starter lantern skin unlocks on the first successful extraction.
- First session: Each round pays banked salvage that buys 2-3 basic cosmetics. A second district teaser unlocks after 3 successful extractions.
- First week: Complete a cosmetic set of 5 pieces from banked salvage. A squad-extraction streak badge is shown on the player's profile.
- Progression system: Cosmetic-only progression (15% of hits vs 3% of others; lift 2.24, weak evidence from only 2 hits, so this is a bet). There are no levels and no stat gains. Rarity tiers apply only to looks. Salvage counts are the only number and work as currency. The tension comes from losing carried loot, not from power growth.
- Retention hook: Day 2: a half-finished cosmetic set and a daily 'first extraction' bonus. It is not a FOMO timer, because 77% of hits have none, and there is no offline accrual, which 100% of hits lack.
- Retention hook: Day 8: a new tide district with a new hunter, plus a role-swap challenge that needs a squad. The squad dependency is tied to the help-asymmetry share of 54% of hits. Measured retention evidence is missing, so this is general design knowledge.

**Scope.** ~4 weeks · 1 solo developer, plus a contract artist for the monster and icon and a freelance sound designer (general-knowledge staffing; the cost rubric gives a base of 4 solo weeks for horror) · biggest risk: Day-1 retention. Half-life is 1.0 day, measured from only 7 games that crashed, and staying power is null. The market is also concentrated: 99 Nights and Dandy's World hold about 47% of current players.

**28-day test.** Kill if: By day 14 the peak is under 2,000 (10 of 11 recent entrants cleared 2k), or the like ratio is under 0.85 against the 0.895 archetype median, or players_now falls below 10% of peak by day 8. The 10% figure is my judgment, because no staying-power baseline exists. · Scale if: Within 28 days the peak is at least 5,516 (the archetype median), the like ratio is at least 0.895, favourites per 1k visits are at least 5.34, and days 8-28 keep at least 30% of peak. The 30% figure is my judgment because the database has no staying-power baseline. A peak of 20k or more would put it in the breakout class (4 of 11 recent entrants). Then commit to a content cadence. · Watch: Peak and players_now over 28 days, plus staying power (share of peak kept on days 8-28); Like ratio and favourites per 1k vs the 0.895 and 5.34 medians; Whether new animal-anomaly entrants (Animal Hospital, Animal Daycare, 7 Days Cat-Sitting) continue to take trending slots; Entrant count against the 11 in the last 90 days, and the trending-slot count against 13

*Components — longevity 0.50, room 0.89, mechanics 0.87, trend 0.80, cost 0.83; cost basis: rubric: base 4 for horror*

---

### 2. rng / PvE — Run a Haunted Hotel: Tycoon-Fused Roll Game
*Adjusted score 0.609 (raw 0.747) · confidence 0.44 · PROVISIONAL · 16 games, 4 hits, 4 entrants in 90 days, est. 4 solo-dev weeks*

**The gap.** The rng / PvE archetype has 16 games, 4 hits (25% hit rate), 0 breakouts and a median peak of 3,516.5. All 4 hits combine numbers_go_up with rarity_collection (100% of hits vs 58% of the other 12 games; lift 1.74), and 75% of hits are Tycoon genre (vs 42%; lift 1.86). The current leaders are themed around anime (Anime Dice at 75,190 peak, Anime Card Farm), lucky blocks, ants or fishing, and none uses a hotel or host-the-guests tycoon frame, so a roll-plus-tycoon game with a non-anime theme is open.

**Why now.** Entrants slowed from 9 in the previous 90 days to 4 in the last 90, yet all 4 reached a 2k+ peak and 3 games hold Top-100 trending slots. Anime Dice alone holds about 52% of the archetype's 135,689 current players, so demand is concentrated in one theme and not yet spread across original ones.

**Build to these constraints**
- progression_type = numbers_go_up + rarity_collection together: Every roll result is a collectible with a rarity tier that also multiplies a number (income). Do not ship pure collection. — *100% of hits (4/4) vs 58% of other games; lift 1.74 (moderate). Pure rarity_collection has 0% of hits and lift 0.21 (weak).*
- genre_l2 = Tycoon: Rolled items occupy and upgrade a visible, buildable space (hotel rooms) rather than sitting in an inventory. — *75% of hits vs 42% of other games; lift 1.86 (moderate). Incremental Simulator is only 25% of hits (lift 1.17, weak).*
- icon_has_face = true: The icon features a character face (a ghost guest). — *100% of hits vs 58% of others; lift 1.12 (moderate). Faceless icons: 0% of hits, lift 0.77 (weak).*
- desc_has_codes = false: No codes in the description. Rely on the game itself for retention. — *100% of hits vs 83% of others; lift 1.16 (moderate).*
- offline_accrual = true: Ghosts keep earning while the player is away, with a capped collection on return. — *50% of hits, lift 1.72, but weak (fewer than 3 hits carry it). Costs about +1 week by the cost rubric.*
- Archetype table stakes: PvE, no base defense, no lost progress, no social asymmetry: Keep all four. They are shared by all or nearly all hits, so they are entry requirements, not differentiators. — *Each appears in 100% of hits (4/4) (moderate). Their global lifts are below 1 (0.79 to 0.95), meaning they are archetype-defining rather than universal winners.*
- Pricing and title shape: Pass median price around 299 Robux (hits) with about 6 passes, a title of about 20 characters, and a verb_a_noun pattern. — *Hit medians: pass price 299 vs 199 for others, pass_count 6 vs 6, title length 20.5 vs 23.5. verb_a_noun lift 1.19 (weak).*

**Avoid**
- Pure rarity_collection with no numbers layer: 0 of 4 hits carry it and its lift is 0.21 (weak signal but the lowest in the table).
- Faceless icon: 0% of hits vs 42% of other games; lift 0.77 (weak).
- x_rng title pattern (e.g. 'Something RNG'): 0 of 4 hits and lift 0.52 (weak). Also avoid copying the 'Roll a X' / 'Kick a X' / 'Pull A X' names already used by competitors.
- Hybrid session shape: Only 1 of 4 hits (25%), lift 0.78 (weak). Persistent is the hit shape at 75%.
- Anime borrowing as the hook: Anime is 50% of hits, but its global lift is 0.83 (weak) and the two largest leaders already own it, so it would be a copy.
- Heavy timers / FOMO as the retention engine: Only 25% of hits use timers/FOMO (vs 58% of others), and lift is 1.08 (weak). Evidence does not support leaning on it.

**Concept: Run a Haunted Hotel** — Roll for ghost guests of different rarities, move them into your hotel rooms, and watch each ghost's haunting generate income.

- Core loop: Roll a ghost guest with coins. Each ghost has a rarity tier and a haunt multiplier. Place ghosts in rooms, and each room produces coins from its resident. Spend coins on more rolls, room upgrades and new floors, which raise the income cap and unlock rarer ghost pools. A collection book tracks every ghost found, with set bonuses. Ghosts keep earning offline up to a cap, and the loop repeats at a bigger scale each floor.
- First 60 seconds: The player spawns in a lobby with one empty room, gets a free roll in the first 10 seconds, and a common ghost moves in with a visible haunting effect. Coins tick up within about 20 seconds, a second roll is affordable by about 40 seconds, and a rarity reveal animation plays on that roll.
- Social mechanic: Keep it symmetric and light (social_asymmetry = none in 100% of hits). Servers of about 7 players (hit median 7) share a lobby. Visitors can see each other's hotels and rare-ghost reveals are announced to the server. A co-op 'busy hotel' bonus scales with players online, and there is no stealing or PvP.
- Monetization: Passes in the 99 to 299 Robux band (hit median 299, min 99): a luck boost pass, a VIP-style pass, an auto-roll pass and an income boost pass, 6 passes in total. Boost and VIP are common in hits (75% and 50%), but their lifts are about 1.0, so they are table stakes and not a differentiator. No code system.
- Content cadence: Launch with floors 1 to 3 and about 40 ghosts. Add one themed floor or ghost set every 1 to 2 weeks (general knowledge: Roblox leaders here ship frequent updates; the database has no update-frequency data yet).

**Features**
- Roll system with visible rarity tiers where each tier multiplies income (numbers_go_up + rarity_collection, lift 1.74).
- Buildable hotel with rooms and floors that ghosts occupy (Tycoon genre, lift 1.86).
- Ghost character faces on the icon and the in-game roll reveal (icon_has_face, lift 1.12).
- Offline earnings with a cap, collected on return (offline_accrual, lift 1.72, weak).
- Collection book with set bonuses, so rarity feeds the numbers loop.
- Server of about 7 players with a shared lobby and a rare-roll announcement feed (median server size 7, no asymmetry).
- No loss mechanics: ghosts are never lost or consumed (can_lose_progress = false in 100% of hits).
- Six passes priced 99 to 299 Robux, with no codes in the description.

**Rewards and retention**
- First minute: A free roll at about 10 seconds gives a common ghost, and the first coins arrive by about 20 seconds. By about 60 seconds the player can afford a second roll.
- First session: Within about 10 minutes the player unlocks a second room and a guaranteed uncommon-or-better ghost (a pity mechanic), and starts the collection book.
- First week: Floor 2 unlocks, along with the first set bonus and the first rare-tier ghost. Several collection pages are completed.
- Progression system: numbers_go_up combined with rarity_collection (the only progression type in 100% of hits). Rarity sets the income multiplier, room level sets the number of slots and the base rate, and floors gate the ghost pools. Rarity never exists without a number attached.
- Retention hook: Day 2: offline accrual is waiting to collect (lift 1.72, weak), and one room upgrade is almost affordable.
- Retention hook: Day 8: unfinished collection pages and set bonuses, the next floor unlock, and a rare ghost tier that needs several floors of income to reach. This relies on the progression type that all hits share (lift 1.74), not on codes or timers.

**Scope.** ~5 weeks · 1 developer plus part-time UI/VFX and a ghost artist. · biggest risk: Staying power is unmeasured (median_staying_power is null, 0 games measured, only 5.5 days of history), so there is no evidence that this archetype retains players beyond the first week. The 2 measured half-lives have a median of 3.5 days and come only from games that crashed.

**28-day test.** Kill if: By day 28: peak CCU is below 2,000 (all 4 entrants in the last 90 days reached 2k+), or like ratio is below 0.90 (archetype median 0.967; Pull A Sword at 0.87 is the weak case), or players_now is under about 25% of peak on days 8 to 28 (my judgment: the database has no archetype baseline for staying power yet). · Scale if: By day 28: peak CCU reaches or exceeds 3,516 (archetype median), like ratio is at least 0.95, favourites per 1k are at least 6.9 (archetype median 6.91), and players_now stays at or above about 40% of peak on days 8 to 28. Scale up spending only if all four hold. A peak toward 20k+ would put it in the breakout tier, which only 1 of 4 recent entrants reached. · Watch: Peak CCU and players_now at days 7, 14 and 28.; Like ratio against the 0.967 median.; Favourites per 1k against 6.91.; Staying power (share of peak kept on days 8 to 28), which the database can measure once there are 28 days of history.; Whether the offline accrual and no-codes traits help or hurt, by comparing with later entrants.; Server fill versus the median of 7 to 7.5.

*Components — longevity 0.50, room 1.00, mechanics 0.85, trend 0.59, cost 0.83; cost basis: rubric: base 2 for rng + session_shape=persistent (+1), offline_accrual=true (+1)*

---

### 3. sports / PvP — Round-Based 5v5 Ice Curling Brawler for Roblox
*Adjusted score 0.609 (raw 0.713) · confidence 0.51 · PROVISIONAL · 51 games, 7 hits, 7 entrants in 90 days, est. 6 solo-dev weeks*

**The gap.** Sports / PvP has 51 games and 7 hits (13.7% hit rate), but the top six by peak are all soccer, volleyball, or American football (Volleyball Legends 77,805, Illegal Soccer 74,927, Realistic Street Soccer 38,135, NFL Universe 28,216, Blue Lock: Rivals 26,718, Azure Latch 24,932). Recent entrants are mostly soccer or established sports (Turbo Soccer, Street Soccer Pro, TFC, NBA: Heroes), plus 8 Ball Duels and SKI. All 7 entrants in the last 90 days peaked above 2,000 CCU and one (Blox League, 21,644) passed 20k, so demand exists. There have been 0 breakouts, and nobody is serving a physics-driven, non-ball sport.

**Why now.** Entrants were flat at 7 in the last 90 days versus 7 in the prior 90, and 8 games sit in the trending top 100, so the category is active but not flooded. Trend and longevity data are immature (5.5 days of history, no 7-day growth), so this reads as an open lane, not a proven rising one.

**Build to these constraints**
- session_shape = rounds: Fixed 3-4 minute rounds, with a match made of 3 ends — *7/7 hits (100%) vs 82% of other games; lift 1.24 (solid). Persistent and hybrid shapes have 0 hits.*
- play_mode = pvp: Head-to-head team PvP as the core mode, with no PvE layer — *57% of hits vs 39% of others; lift 1.68 (moderate). Hits that mix in coop/pve have weak support: 1 hit, lift 1.25.*
- genre_l2 = Sports: Present and label it clearly as a sport, not a shooter or obby — *86% of hits vs 75% of others; lift 1.56 (solid).*
- progression_type = cosmetic_only|levels: Account levels that unlock only cosmetics, with no stat gains — *57% of hits vs 16% of others; lift 1.57 (moderate). This is the largest within-archetype gap among the moderate-evidence traits.*
- pass_has_vip = true: Ship a VIP / private-server pass — *86% of hits vs 50% of others. The global lift is only 0.96, so it is an archetype convention and not a proven driver.*
- Pass pricing and count: About 5 passes, cheapest at or below 49 R$, median around 150 R$ — *Hit medians: 5 passes, min price 49, median price 150. Others: 4.5 passes, min 99, median 205.*
- server_size: 10 players per server (5v5) — *Hit median 10 vs 14 for other games. It also keeps matches fillable at low CCU (my inference).*
- desc_has_codes = false and title_pattern = descriptive: No codes in the description. A descriptive title of about 24 characters. — *No codes: 100% of hits, lift 1.16. Descriptive titles: 100% of hits, median length 24 vs 21.*
- icon_has_text = false: Text-free icon, preferably with a character face — *No text: 57% of hits vs 27% of others, lift 1.15 (moderate). Face: lift 1.12, but the hit and other shares are equal (57%).*

**Avoid**
- desc_has_codes = true: 0 of 7 hits and lift 0.39. This is weak evidence (fewer than 3 hits), but it is the lowest lift in the table.
- Brand IP borrowing: 14% of hits vs 36% of others; lift 0.82. It also invites a copy-of-leader comparison.
- Anime IP skin: 43% of hits vs 11% of others, but global lift is 0.83. Blue Lock: Rivals owns this angle, and the evidence conflicts, so do not build on it.
- Persistent or hybrid session shape: 0 of 7 hits; lifts 0.93 and 0.78 (weak).
- progression_type = none: 29% of hits vs 41% of others; lift 0.84 (weak). A bare match loop underperforms.
- Offline accrual, progress loss, base defense: All three are false for 100% of hits and 100% of other games, so they are not differentiators. Their lifts are 0.94, 0.79, and 0.95, so adding them has no measured upside.
- Rarity-collection or numbers-go-up progression: 0 of 7 hits carry it. The only high-lift variant (numbers_go_up|rarity_collection, lift 1.74) is a weak-evidence cell.

**Concept: Ice Curling Clash: 5v5** — Curling meets bumper-car physics: two teams of five slide stones across a shifting ice rink and can body-check rival stones out of the house.

- Core loop: A match is 3 ends of about 75 seconds each. Players take turns launching stones, using a short charge-and-aim slide. Between launches they control a sweeper character who can brush the ice to extend a slide or shove enemy stones within a short radius. Closest stones to the center score, and each end adds a hazard such as a crack, a bumper pillar, or a slick zone. Wins and rounds played give XP, levels unlock cosmetics only, and a queue-again prompt starts the next match straight away.
- First 60 seconds: The player spawns in a rink lobby and is auto-queued into a bot-filled 5v5. A one-stone tutorial end starts within 10 seconds. By about 40 seconds they have slid a stone, knocked a bot stone out, and earned a first trail cosmetic.
- Social mechanic: Five-player teams with a shout-out ping wheel and a party-queue. The VIP pass opens private scrim servers for friend groups, matching the 86% VIP share among hits. Trading is left out because there is only weak evidence for it (1 hit).
- Monetization: Five passes, with the cheapest at 49 R$ (a trail pack) and a median around 150 R$. They are a VIP/private server, a cosmetic stone skin pack, a sweeper outfit pack, a victory-emote pack, and a name-tag style. There is nothing pay-to-win, consistent with the cosmetic_only|levels progression.
- Content cadence: Weekly rotating arena hazard set, plus a 4-week cosmetic season with a limited-time stone skin. This leans on the moderately supported timers/FOMO lift of 1.08 without making FOMO the core.

**Features**
- 3-end, ~4-minute rounds with instant requeue (session_shape = rounds, lift 1.24)
- 5v5 team PvP with bot backfill for 10-player servers (play_mode = pvp, lift 1.68; hit server-size median of 10)
- Level track from 1 to 50 with cosmetic-only unlocks (cosmetic_only|levels, lift 1.57)
- VIP private-scrim server pass (86% of hits carry it)
- Low-priced pass ladder starting at 49 R$ (hit min price 49 vs 99)
- Weekly rotating hazard rink (supports a returning-player reason without codes)
- Text-free icon with a character face and a descriptive title around 24 characters, with no codes in the description (lifts 1.15 / 1.12 / 0.96 and 1.16)
- Post-match highlight replay of the best stone knock-out, for sharing

**Rewards and retention**
- First minute: A trail cosmetic after the first knock-out in the tutorial end (about 40 seconds), plus visible XP.
- First session: Level 4-5 after 3-4 matches, unlocking a sweeper hat and a stone color. Early XP is front-loaded, so the first level takes under 2 minutes.
- First week: Level 15-20 for regular players, one complete cosmetic set, and a first ranked-division placement.
- Progression system: The measured type is cosmetic_only|levels (57% of hits, lift 1.57). Levels only gate cosmetics and never affect stone mass or slide stats. There are no rarity tiers, because rarity_collection appears in 0 of 7 hits.
- Retention hook: Day 2: a new weekly hazard rink and a level-5 cosmetic unlock reachable in one more session. This uses the timers/FOMO trait (43% of hits vs 25% of others, lift 1.08) lightly.
- Retention hook: Day 8: a seasonal ranked ladder and a limited-time stone skin that rewards 50 matches played, plus the VIP scrim server so friend groups return together. No idle accrual, since offline_accrual is false in 100% of hits.

**Scope.** ~6 weeks · 1 developer (physics and netcode), with contract art for a rink, stones, and about 20 cosmetics · biggest risk: Cold-start matchmaking and physics netcode. With a 14-player median server size across the archetype and 5v5 target, low-CCU servers feel empty without bots, and replicated stone collisions can feel laggy. Only 1 of 7 recent entrants passed 20k, so the long tail is thin.

**28-day test.** Kill if: By day 28, peak CCU is below 2,000 (every one of the 7 entrants in the last 90 days cleared that mark), or the like ratio is below 0.80 (archetype median 0.863), or share of peak kept on days 8-28 is below 0.20. The last threshold is a judgment call because the database has no staying-power baseline for this archetype yet. · Scale if: Peak CCU is at or above 2,505 (the archetype median peak) and the like ratio is at least 0.86 with staying power of 0.40 or more. Scale harder if peak reaches 20,000 or more, which only 1 of 7 entrants has done. · Watch: Favorites per 1k visits vs the archetype median of 2.221; Like ratio vs the median of 0.863; Staying power (days 8-28 share of peak) and half-life vs the 1.0-day median, which comes only from early crashed games (n=15); Whether new soccer entrants (Turbo Soccer, Street Soccer Pro) are pulling players from the sports lane; Share of sessions with bot backfill, as a proxy for matchmaking health

*Components — longevity 0.50, room 1.00, mechanics 0.61, trend 0.74, cost 0.67; cost basis: rubric: base 6 for sports*

---
