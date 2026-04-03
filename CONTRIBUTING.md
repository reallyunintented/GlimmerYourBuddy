# Contributing

Found a bug? Have a feature idea? Love Glimmer and want to help?

## Ideas for Improvement

- **Export formats** — HTML, JSON, plaintext collections
- **Search** — Find bubbles by keyword or date range
- **Stats** — More detailed analytics on buddy comments
- **Sync** — Optional cloud backup (respecting privacy)
- **Themes** — Custom display styles for `glimmer-log`
- **Integration** — IDE plugins to view bubbles within your editor

## Getting Started

1. Fork the repo
2. Make your changes
3. Test with `glimmer-claude` to ensure bubble detection still works
4. Submit a PR

## Code Style

- Shell scripts: keep it simple and portable (bash 4+)
- Python: follow PEP 8
- Comments: explain *why*, not what

## Testing

The trickiest part is testing the bubble detection. You can manually trigger it:

```bash
# Edit glimmer-watcher.py to lower MIN_BOX_WIDTH temporarily
# Or add test data to a typescript file and run the watcher on it
```

## Questions?

Open an issue. We're all learning here.

---

Thanks for helping make buddy memories last forever.
