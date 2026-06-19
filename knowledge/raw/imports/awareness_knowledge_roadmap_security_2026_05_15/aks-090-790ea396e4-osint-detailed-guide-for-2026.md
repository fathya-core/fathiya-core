# OSINT detailed guide for 2026

**Published:** 2025-11-17


## 1.0 Introduction

OSINT, or Open-Source INTelligence, refers to the process of gathering information from publicly accessible sources (open-source), whether for free or for purchase, and analyzing that information to develop insights about a target (Intelligence).

![Image](https://miro.medium.com/v2/resize:fit:651/1*S7I6DbzV_eh7s-KvT363oA.png)

OSINT is a passive mode of reconnaissance, meaning we avoid interaction with the target. However, _some_ interaction with the target can take place, such as browsing the company website. But if we start sending probes to the servers the site is running on, or trying to discover content by guessing (brute-forcing) files and directories on the site, we’re now actively engaging with the target. Here are several examples to help with this distinction:

**OSINT:**

*   Viewing the company’s LinkedIn profile.
*   Viewing previous scans done by third-party services.
*   Viewing domain registration details
*   Browsing the company website

**NOT OSINT:**

*   Requesting scans of our target from third-party scanner services.
*   Guessing credentials, subdomains, or other details to discover content (AKA brute forcing).

**Note:** What does and does not constitute OSINT can vary based on relevant privacy and computer laws. _It is your responsibility to ensure you are not in violation of the law or your client’s scope._

OSINT is used in many fields, including security, business, journalism, and general research. People generally aren’t very good at appreciating the value of what they publish online, so the public domain is a great place to look for some generous disclosures. It can play a large role in any reconnaissance effort, but it has particular utility in Red Team engagements where maximizing the intel acquired passively can increase the odds of avoiding early detection by the Blue Team when you opt to actively engage your target.

![Image](https://miro.medium.com/v2/resize:fit:607/1*bs0xXilhhqG7ZtwZ6crfMw.png)

**2.1 Information Categories:-**

![Image](https://miro.medium.com/v2/resize:fit:515/1*HYFIrOyWv4E7iClQnLcOzg.png)

**2.2 Information Resources:-**

![Image](https://miro.medium.com/v2/resize:fit:630/1*mVhm35gNzU1icfVV-C5LWA.png)

Tool For OSINT:-

*   [OSINT Tools and Resources](https://github.com/jivoi/awesome-osint)
*   [Bellingcats Online Investigation Toolkit](http://bit.ly/bcattools)
*   [OSINT start here](https://start.me/p/ZME8nR/osint?locale=en)
*   [OSINT Bookmarks](https://www.osintcombine.com/osint-bookmarks)
*   [OSINT Framework](https://osintframework.com/)