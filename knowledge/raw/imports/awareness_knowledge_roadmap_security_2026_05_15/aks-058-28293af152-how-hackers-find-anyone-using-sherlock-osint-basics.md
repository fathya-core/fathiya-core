# How hackers find ANYONE using Sherlock (OSINT basics)

**Published:** 2025-11-05


_An easy OSINT demo and safety guide_

![Image](https://miro.medium.com/v2/resize:fit:256/0*_b6p8DaWMT7t4pbZ.png)

**Quick disclaimer:** This article is for educational purposes only. Do not use these techniques on people or organizations without explicit written permission. Misuse could get you into legal trouble.

Open-source intelligence (OSINT) tools make it easy to gather publicly available information — and one of the most useful tools for tracking username footprints across the web is **Sherlock**. In this short guide I’ll show what Sherlock is, how to install it, a quick demo of running scans, and important ethical considerations you need to keep in mind.

**Sherlock on GitHub:** [https://github.com/sherlock-project/sherlock](https://github.com/sherlock-project/sherlock)

## Installation (how I did it)

Installation is very simple. In the video I used `pip install`, but there are other methods shown on the project page — legacy `pip`, `brew`/`apt` packages, `git clone` the repo, or run it in Docker. For a quick Windows setup, `pip` worked fine for me. Docker is probably the cleanest if you want isolated dependencies, and cloning the GitHub repo is useful if you want to tinker with the source or contribute — but for most users `pip` is the fastest path.

## Quick demo (what I ran)

First I showed that I had a `sherlock.exe` and a previous scan log against **Nahamsac** (shout-out — an awesome hacker YouTuber; check him out). Then I ran a fresh scan from the command line:

sherlock nahamsac

If you’ve installed via Python directly it might be:

python3 -m sherlock nahamsac

The default run can be a bit slow. In the video I let it run briefly, then stopped it and sped things up using the `--timeout` flag so each site only gets one second:

sherlock --timeout 1 nahamsac

That makes the scan noticeably faster, but it can also make results a bit less reliable — timeout 1 is for demo speed, not deep sweeps.

![Image](https://miro.medium.com/v2/resize:fit:700/0*RRoMU5BJqaY7gIiQ.png)

Then I scanned another example, **NetworkChuck** (great beginner-friendly networking content — go check him out). You’ll see Sherlock chug through its list; sometimes you’ll hit false positives (I spotted a few chess-site matches that looked questionable). For example, a chess site appeared in the output and I opened the link to confirm whether it was a real account — it turned out to be real in that case.

![Image](https://miro.medium.com/v2/resize:fit:700/0*-IGg4eQ52wcuwHOX.png)

## Final notes — use responsibly

Again, only run Sherlock when you have explicit written permission, or on your own accounts for learning. If you’re doing a pentest, make sure your contract covers this kind of activity and you have everything documented. Sherlock aggregates public info, but abusing it can still get you into trouble depending on where and how you use it.

That’s a super quick demo of how Sherlock works. I’ll cover more OSINT stuff in the future. I really appreciate the support.

Peace.