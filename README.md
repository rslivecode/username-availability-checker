# Username Availability Checker

A professional interactive command-line tool that checks whether a username is **available** or **taken** across major social media and developer platforms.

When you run the tool, a clean logo appears, you type a username, and it checks platforms **one by one** in real time. At the end you get a summary table and can **download the results as CSV**.

---

## Features

- Beautiful ASCII logo on startup
- Interactive mode – just type a username and press Enter
- Real-time progress: platforms are checked and shown **one by one**
- Final summary table with status (Available / Taken / Unknown)
- **CSV export** with one click
- 15 popular platforms supported
- No API keys required
- MIT License – ready for public GitHub

---

## Supported Platforms

| Platform       | Category   | Notes                          |
|----------------|------------|--------------------------------|
| GitHub         | Developer  | Highly reliable                |
| GitLab         | Developer  | Highly reliable                |
| Reddit         | Social     | Reliable (JSON endpoint)       |
| YouTube        | Social     | Checks `@handle`               |
| TikTok         | Social     | Best-effort                    |
| Instagram      | Social     | Often blocked – verify manually|
| X (Twitter)    | Social     | Limited reliability            |
| Twitch         | Social     | Good reliability               |
| Pinterest      | Social     | Medium reliability             |
| Telegram       | Social     | Best-effort                    |
| Medium         | Creator    | Medium reliability             |
| Dev.to         | Creator    | Reliable                       |
| Hashnode       | Creator    | Medium reliability             |
| SoundCloud     | Creator    | Medium reliability             |
| Product Hunt   | Creator    | Medium reliability             |

> **Important:** Results are best-effort. Platforms with strong anti-bot protection (especially Instagram, TikTok, and X) may return “Unknown”. Always double-check manually before registering a username.

---

## Requirements

- Python 3.8+
- `requests`
- `rich`

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/username-availability-checker.git
cd username-availability-checker

# Recommended: create a virtual environment
python -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

---

## Usage

### Interactive Mode (Recommended)

Just run the script without any arguments:

```bash
python check_username.py
```

You will see the logo, then:

```
Enter username to check (or 'q' to quit):
```

Type a username and press Enter. The tool will check every platform one by one and show live results. At the end you can save everything as a CSV file.

### Non-interactive Mode

```bash
python check_username.py johndoe
```

---

## Sample Flow

```
 ██╗   ██╗███████╗███████╗██████╗      ██████╗██╗  ██╗███████╗ ██████╗██╗  ██╗
 ...
          Username Availability Checker

Enter username to check (or 'q' to quit): coolname

Checking coolname across 15 platforms...

  ✅  GitHub            Username is available
  ❌  Reddit            Profile exists
  ✅  YouTube           Handle appears available
  ...

╭──────────────────────── Results for coolname ────────────────────────╮
│ Platform     Status        Details                    Profile URL    │
│ ...                                                                  │
╰──────────────────────────────────────────────────────────────────────╯

Download results as CSV? [Y/n]: Y
✓ Saved to: username_check_coolname_20251121_001500.csv
```

---

## CSV Export

The exported CSV contains:

| Platform | Status    | Details              | Profile URL                  |
|----------|-----------|----------------------|------------------------------|
| GitHub   | Available | Username is available| https://github.com/coolname  |
| Reddit   | Taken     | Profile exists       | https://www.reddit.com/...   |
| ...      | ...       | ...                  | ...                          |

---

## Project Structure

```
username-availability-checker/
├── check_username.py      # Main interactive CLI
├── platforms.py           # All platform checkers
├── requirements.txt
├── LICENSE                # MIT
├── .gitignore
└── README.md
```

---

## License

MIT License – free to use, modify, and distribute.

---

## Disclaimer

This tool only makes public HTTP requests. It does not bypass any security measures or private data. Results can be inaccurate due to rate limits, anti-bot systems, or website changes. Always verify the username yourself on the official website before claiming it.
