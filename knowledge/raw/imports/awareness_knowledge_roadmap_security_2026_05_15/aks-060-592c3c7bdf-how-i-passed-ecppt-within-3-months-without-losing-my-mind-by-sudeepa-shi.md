# How I Passed eCPPT within 3 months Without Losing My Mind | by Sudeepa Shiranthaka | InfoSec Write-ups

**Published:** 2026-03-06


How I Passed eCPPT within 3 months Without Losing My Mind

![Image](https://miro.medium.com/v2/resize:fit:700/1*CgEvD07IQmZwIYinDaquWQ.png)

It’s been a while since I passed my **eCPPTv3** exam, and now I’d like to publish the write-up. The **eCPPT (Certified Professional Penetration Tester)** exam is a practical, hands-on assessment that evaluates your real-world penetration testing skills.

In this article, I share 7 important tips to help you clear the exam easily and effectively. However, the blog will not include commands or screenshots.

## Exam Structure and Cost

*   24-hour exam.
*   100% practical and hands-on penetration testing exam.
*   The exam voucher was only ($399), but the new price is ($450) — Check the [INE](https://checkout.ine.com/#certifications) site.
*   I purchased the one-year annual subscription, which included one free exam voucher, for $799.

## Focus Areas

*   Initial Access Vectors and Techniques
*   Exploit Development
*   AD Enumeration
*   Exploitations and Post-Exploitations
*   Active Directory Penetration Testing
*   Web Application Penetration Testing

## Exam Summary

In the exam, we had to begin with host discovery across the entire subnet to identify the live systems. I can’t reveal the exact number of active hosts, but there were more than two, including several domain controllers. The objective was clear, we ultimately needed to compromise a domain controller.

There was also an external network in scope. We first had to compromise the external targets and then pivot into the internal network to continue the attack path.

## Key Points to Remember

1.  Make sure to keep clear and **well-organized notes of commands** and each **command's outputs** throughout the process.

2\. Carefully **review each output** and scroll through it slowly to ensure you don’t miss any important details.

3\. Make sure to **document all discovered hosts and compromised credentials** in a table. Don’t forget to reuse the identified passwords where applicable and perform password spraying using the previously discovered credentials.

![Image](https://miro.medium.com/v2/resize:fit:300/1*KR7T7p88sfVg3ulVecNB5g.png)

*Target info — Break Down*![Image](https://miro.medium.com/v2/resize:fit:553/1*ZWEHCEDXrAWV84uj9CRkRA.png)

*Compromised users & Targets*

4\. Do not save your result outputs on the exam VM. Instead, store them on your own machine or in cloud storage. I used [**Notion**](https://www.notion.com/) for note-taking.

5\. Study common AD enumeration techniques and **Active Directory initial access vectors.** There are plenty of tools that can be used to enumerate Active Directory users, such as [**kerbrute**](https://github.com/ropnop/kerbrute).

6\. Make sure you understand how to properly use the relevant tools and perform SMB enumeration and **password spraying** against AD users effectively. (e.g., [Crackmapexec](https://github.com/byt3bl33d3r/CrackMapExec))

7\. Learn Active Directory persistence techniques, such as extracting a Kerberos ticket for a [**pass-the-ticket (PtT)**](https://attack.mitre.org/techniques/T1550/003/) attack. Also study Golden Tickets and Silver Tickets and how they work for long-term persistence in Active Directory environments.

Thanks for reading this blog. Here’s what I got.😊

![Image](https://miro.medium.com/v2/resize:fit:700/1*WSCUHwzc3wr--vUeixWhww.png)

You can find me on😊:

LinkedIn: [www.linkedin.com/in/sudeepashiranthaka](http://www.linkedin.com/in/sudeepashiranthaka)

Medium: [https://sudeepashiranthaka97.medium.com/](https://sudeepashiranthaka97.medium.com/)

Twitter: [https://twitter.com/sudeepashiran97](https://twitter.com/sudeepashiran97)