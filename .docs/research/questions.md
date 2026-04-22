Research memo is persisted at `.docs/research/asset-category-taxonomy.md`.

Decision captured (approved):
- Keep the 9-category taxonomy and value-capture logic.
- Remove `wyckoff` from category weights.
- Treat Wyckoff as a global post-score filter (same family as GLI / Fear-Greed / RSI).
- Use Wyckoff only to downgrade high-risk entries (especially distribution / markdown), not to define fundamental category score.

Why:
- Wyckoff is technical market-structure context (accumulation/markup/distribution/markdown), not a category-specific fundamental driver.
- Adoption / interest signal is already represented by other dimensions (`institutional`, `adoption_activity`, `value_capture` where applicable).
- This avoids double-counting adoption/interest and keeps cross-category scores cleaner.

Next implementation step (pending code approval):
- Reweight all categories without `wyckoff`.
- Add a post-composite Wyckoff downgrade rule:
  - accumulation: no downgrade
  - markup: mild downgrade
  - distribution: strong downgrade
  - markdown: strongest downgrade / blocks strong-accumulate